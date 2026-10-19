#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Turn a take's word timestamps into its timing file, aligned to the canonical script.

The script's paragraphs are scenes and its sentences are captions, split exactly as
make_cues.py splits them, so sentence ids (c01, c02, ...) match the build's cue ids.
Heard words are aligned to script words with difflib; matched words copy their times,
unmatched words are interpolated between matched neighbours. With --scene-offsets (from
join_scenes.py) every word is pinned inside its scene's exact range.

Word input formats (--format):
  whisper-cpp  full JSON: transcription[] with text and offsets.from/to in milliseconds
  words        {"words": [{"word", "start", "end"}]} or {"segments": [{"words": [...]}]}
  list         [{"word" or "text", "start", "end"}] or [[word, start, end], ...]

Usage:
  python3 align_words.py --script script/script.txt --words take-words.json --format whisper-cpp \\
      --voice <voice-id> --audio voices/<voice>/<voice>.wav --out voices/<voice>/<voice>-timing.json \\
      [--scene-offsets voices/<voice>/<voice>-scenes.json] [--duration 196.7] \\
      [--aligner-label "whisper.cpp <version>, <model>"] [--min-match 0.6] [--allow-missing-ending]
  python3 align_words.py --no-stt --script ... --scene-offsets ... --voice ... --audio ... --out ...

--no-stt spreads each scene's words evenly inside its exact offsets (no transcriber needed)
and says so in "method". Without --duration the length comes from ffprobe.

Dependencies: Python 3.9 or later, standard library only; ffprobe when --duration is not given.
Exit codes: 0 written; 1 bad input; 3 the ending looks missing (a sentence shorter than
0.05 s, or unmatched words at the end) or the match rate is below --min-match. With
--allow-missing-ending the file is still written, with the problem in "warnings".
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cue_check  # noqa: E402

APOSTROPHES = {"’": "'", "‘": "'", "ʼ": "'"}
TERMINATOR = re.compile(r"(\.\.\.|…|[.!?]+)([\"'”’)]*)")


def norm(text):
    text = re.sub(r"<[^>]*>", " ", text).lower()
    for curly, straight in APOSTROPHES.items():
        text = text.replace(curly, straight)
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return [w.strip("'") for w in text.split() if w.strip("'")]


def split_sentences(paragraph):
    out, start = [], 0
    for m in TERMINATOR.finditer(paragraph):
        end = m.end()
        rest = paragraph[end:]
        if rest and not rest[0].isspace():
            continue
        if m.group(1) in ("...", "…") and re.match(r"\s+[a-z]", rest):
            continue
        piece = paragraph[start:end].strip()
        if piece:
            out.append(piece)
        start = end
    tail = paragraph[start:].strip()
    if tail:
        out.append(tail)
    return out


def cue_id(index):
    return "c" + str(index + 1).zfill(2)


def load_words(path, fmt):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    raw = []
    if fmt == "whisper-cpp":
        for seg in data.get("transcription", []):
            raw.append((seg.get("text", ""), seg["offsets"]["from"] / 1000.0, seg["offsets"]["to"] / 1000.0))
    elif fmt == "words":
        items = data.get("words")
        if items is None:
            items = [w for seg in data.get("segments", []) for w in seg.get("words", [])]
        for w in items:
            raw.append((w.get("word") or w.get("text") or "", float(w["start"]), float(w["end"])))
    else:
        for w in data:
            if isinstance(w, (list, tuple)):
                raw.append((str(w[0]), float(w[1]), float(w[2])))
            else:
                raw.append((w.get("word") or w.get("text") or "", float(w["start"]), float(w["end"])))
    heard = []
    for text, start, end in raw:
        if re.fullmatch(r"\s*[\[(].*[\])]\s*", text or ""):
            continue  # non-speech markers such as [music]
        for w in norm(text or ""):
            heard.append((w, start, end))
    return heard


def probe_duration(audio):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", audio],
                         check=True, capture_output=True, text=True).stdout.strip()
    return float(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True)
    ap.add_argument("--words")
    ap.add_argument("--format", choices=["whisper-cpp", "words", "list"], default="whisper-cpp")
    ap.add_argument("--voice", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scene-offsets")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--aligner-label", default="a speech-to-text word timestamp tool")
    ap.add_argument("--min-match", type=float, default=0.6)
    ap.add_argument("--no-stt", action="store_true")
    ap.add_argument("--allow-missing-ending", action="store_true")
    args = ap.parse_args()

    try:
        with open(args.script, encoding="utf-8") as fh:
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", fh.read().replace("\r\n", "\n").strip()) if p.strip()]
    except FileNotFoundError:
        print(f"FAIL: script file not found: {args.script}")
        return 1
    sentences, words = [], []
    for scene_n, paragraph in enumerate(paragraphs, start=1):
        for text in split_sentences(paragraph):
            idx = len(sentences)
            sentences.append({"id": cue_id(idx), "scene": scene_n, "text": text})
            for w in norm(text):
                words.append((w, idx))
    if not words:
        print("FAIL: the script has no words")
        return 1

    offsets = None
    if args.scene_offsets:
        try:
            with open(args.scene_offsets, encoding="utf-8") as fh:
                offsets = {s["scene"]: (float(s["start"]), float(s["end"])) for s in json.load(fh)["scenes"]}
        except FileNotFoundError:
            print(f"FAIL: scene-offsets file not found: {args.scene_offsets}")
            return 1
        except json.JSONDecodeError:
            print(f"FAIL: scene-offsets file unreadable: {args.scene_offsets}")
            return 1
        if len(offsets) != len(paragraphs):
            print(f"FAIL: {len(offsets)} scene offsets but {len(paragraphs)} script paragraphs")
            return 1
    duration = args.duration if args.duration is not None else probe_duration(args.audio)

    times = [None] * len(words)
    matched = 0
    if args.no_stt:
        if not offsets:
            print("FAIL: --no-stt needs --scene-offsets")
            return 1
        for scene_n, (s0, s1) in offsets.items():
            idxs = [i for i, (_, si) in enumerate(words) if sentences[si]["scene"] == scene_n]
            step = (s1 - s0) / max(1, len(idxs))
            for k, i in enumerate(idxs):
                times[i] = (s0 + k * step, s0 + (k + 1) * step)
        method = "no transcriber: words spread evenly by count inside exact scene offsets from the join; sentence times are approximate"
        matched = None
    else:
        if not args.words:
            print("FAIL: give --words, or --no-stt with --scene-offsets")
            return 1
        try:
            heard = load_words(args.words, args.format)
        except FileNotFoundError:
            print(f"FAIL: words file not found: {args.words}")
            return 1
        except json.JSONDecodeError:
            print(f"FAIL: words file unreadable: {args.words}")
            return 1
        sm = difflib.SequenceMatcher(None, [w for w, _ in words], [h[0] for h in heard], autojunk=False)
        for a, b, size in sm.get_matching_blocks():
            for k in range(size):
                times[a + k] = (heard[b + k][1], heard[b + k][2])
                matched += 1
        known = [i for i, t in enumerate(times) if t]
        if not known:
            print("FAIL: no script words were heard")
            return 3
        for i in range(len(times)):
            if times[i] is not None:
                continue
            lo = max((k for k in known if k < i), default=None)
            hi = min((k for k in known if k > i), default=None)
            if lo is not None and hi is not None:
                f = (i - lo) / (hi - lo)
                t = times[lo][1] + (times[hi][0] - times[lo][1]) * f
                times[i] = (t, t)
            elif lo is not None:
                times[i] = (times[lo][1], times[lo][1])
            else:
                times[i] = (times[hi][0], times[hi][0])
        if matched == len(words):
            word_note = f"all {len(words)} script words matched"
        else:
            word_note = (f"{matched} of {len(words)} script words matched, "
                         f"{len(words) - matched} interpolated between matched neighbours")
        method = (f"word timestamps from {args.aligner_label} aligned to the script; {word_note}"
                  + ("; scene boundaries pinned to the join offsets" if offsets else ""))

    if offsets:
        for i, (w, si) in enumerate(words):
            s0, s1 = offsets[sentences[si]["scene"]]
            a, b = times[i]
            times[i] = (min(max(a, s0), s1), min(max(b, s0), s1))

    for idx, s in enumerate(sentences):
        ws = [times[i] for i, (_, si) in enumerate(words) if si == idx]
        s["start"] = round(ws[0][0], 3) if ws else 0.0
        s["end"] = round(ws[-1][1], 3) if ws else 0.0
    scenes = []
    for n in range(1, len(paragraphs) + 1):
        mine = [s for s in sentences if s["scene"] == n]
        scenes.append({"scene": n, "start": mine[0]["start"], "end": mine[-1]["end"]})
    for i in range(len(scenes) - 1):
        scenes[i]["end_with_pause"] = scenes[i + 1]["start"]
    scenes[-1]["end_with_pause"] = round(duration, 3)

    warnings = []
    short = [s["id"] for s in sentences if s["end"] - s["start"] < 0.05]
    if short:
        warnings.append("sentences shorter than 0.05 s (likely missing from the audio): " + ", ".join(short))
    if not args.no_stt:
        trailing = 0
        for i in range(len(times) - 1, -1, -1):
            matched_here = any(a <= i < a + size for a, _, size in sm.get_matching_blocks())
            if matched_here:
                break
            trailing += 1
        if trailing >= 3:
            warnings.append(f"the last {trailing} script words were not heard; the ending may be missing")
        rate = matched / len(words)
        if rate < args.min_match:
            warnings.append(f"only {matched} of {len(words)} words matched ({rate:.0%}); check the take and the script")

    with open(args.script, encoding="utf-8") as fh:
        script_hash = cue_check.words_sha256(fh.read())
    out = {"schema": 1, "voice": args.voice, "file": os.path.basename(args.audio), "duration": round(duration, 3),
           "method": method, "matched": matched, "words": len(words), "source_words_sha256": script_hash,
           "scenes": scenes, "sentences": sentences}
    if warnings:
        out["warnings"] = warnings
    print(f"{args.voice}: matched {matched} of {len(words)} words" if not args.no_stt else f"{args.voice}: no-stt spread of {len(words)} words")
    for sc in scenes:
        print(f"  scene {sc['scene']}: {sc['start']:.2f} -> {sc['end']:.2f}")
    for w in warnings:
        print("  WARNING " + w)
    if warnings and not args.allow_missing_ending:
        print("FAIL: not written. Regenerate or re-record the scene, or pass --allow-missing-ending to keep it with a note.")
        return 3
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
