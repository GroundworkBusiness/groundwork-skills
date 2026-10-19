#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check every scene file of a take: tag words read aloud, the ending heard, the match rate.

For each s<N>.wav in the take folder it resamples to 16 kHz mono, transcribes with the
command you give, and compares the heard words with the scene's script words:
  - tag leak: a word from the scene's delivery tags (in text_cued or any variant) that was
    inserted relative to the script. Words the script itself contains never count, so a
    script that says "pause" does not raise a false alarm.
  - ending: at least two of the scene's last three script words are heard.
  - match rate: matched script words over all script words (default minimum 0.85).

Usage:
  python3 check_takes.py --scenes script/scenes.json --take-dir voices/<voice> \\
      --stt-cmd "<transcriber> -m <model-file> -f {in} -np -nt" \\
      [--tags "long pause,short pause,breath"] [--min-match 0.85] [--move-leaks] \\
      [--only 1,6] [--report voices/<voice>/check.json]

Working transcriber commands: references/example-local-tools.md.
--stt-cmd is run without a shell. {in} is the 16 kHz WAV. If the template has {out}, the
transcript is read from {out}.txt (or {out}); otherwise from standard output.
--only checks just the named scenes (an audition folder that holds scenes 1 and 6, say);
other scenes are not reported missing.
--move-leaks renames a leaking scene to s<N>-tagged.wav so it can be regenerated plain
and compared. Transcripts are kept as s<N>.txt.

Dependencies: Python 3.9 or later, standard library only; ffmpeg; a speech-to-text command.
Exit codes: 0 every scene is clean; 2 at least one scene needs regeneration; 1 tool error.
"""
import argparse
import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

APOSTROPHES = {"’": "'", "‘": "'", "ʼ": "'"}


def norm_words(text):
    text = re.sub(r"<[^>]*>", " ", text).lower()
    for curly, straight in APOSTROPHES.items():
        text = text.replace(curly, straight)
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return [w.strip("'") for w in text.split() if w.strip("'")]


def heard_words(text):
    # Drop bracketed non-speech markers such as [music] or (gentle music) and timestamps.
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*", " ", text)
    return norm_words(text)


class TranscriberError(RuntimeError):
    def __init__(self, code, stderr):
        self.code = code
        self.stderr = stderr or ""
        super().__init__(f"transcriber exit {code}")


def transcribe(template, wav16, workdir):
    out_base = os.path.join(workdir, "stt")
    values = {"in": wav16, "out": out_base}
    argv = [part.format(**values) for part in split_cmd(template)]
    proc = subprocess.run(argv, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise TranscriberError(proc.returncode, proc.stderr)
    if "{out}" in template:
        for candidate in (out_base + ".txt", out_base):
            if os.path.exists(candidate):
                with open(candidate, encoding="utf-8") as fh:
                    return fh.read()
        raise RuntimeError("the transcriber wrote no {out}.txt")
    return proc.stdout


def scene_files(take_dir):
    found = {}
    for name in os.listdir(take_dir):
        m = re.fullmatch(r"s(\d+)\.wav", name)
        if m:
            found[int(m.group(1))] = os.path.join(take_dir, name)
    return found


def split_cmd(t):
    posix = os.name != "nt"
    parts = shlex.split(t, posix=posix)
    if posix:
        return parts
    cleaned = []
    for p in parts:
        if len(p) > 1 and p[0] == p[-1] and p[0] in ("'", '"'):
            p = p[1:-1]
        cleaned.append(p)
    return cleaned


def transcriber_lines(text):
    """Error lines from a transcriber, else its last lines, and whether a model file is named."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    matched = [ln for ln in lines if re.search(r"error|not found|no such file|failed|cannot|unable", ln, re.I)]
    return (matched[:5] if matched else lines[-5:]), bool(re.search(r"model file", text or "", re.I))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--take-dir", required=True)
    ap.add_argument("--stt-cmd", required=True)
    ap.add_argument("--tags", help="comma-separated tag phrases; default: every <tag> in each scene's text_cued and variants")
    ap.add_argument("--min-match", type=float, default=0.85)
    ap.add_argument("--move-leaks", action="store_true")
    ap.add_argument("--only", help="comma-separated scene numbers to check; the rest are skipped")
    ap.add_argument("--report")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        print("FAIL: ffmpeg not found")
        return 1
    with open(args.scenes, encoding="utf-8") as fh:
        data = json.load(fh)
    files = scene_files(args.take_dir)
    only = {int(x) for x in args.only.split(",") if x.strip()} if args.only else set()
    report = {"take_dir": args.take_dir, "scenes": [], "needs_regen": []}
    tmp = tempfile.mkdtemp()
    try:
        for scene in data["scenes"]:
            n = int(scene["n"])
            if only and n not in only:
                continue
            if n not in files:
                report["scenes"].append({"scene": n, "missing": True, "needs_regen": True, "reason": "scene file missing"})
                report["needs_regen"].append(n)
                print(f"s{n}: MISSING")
                continue
            wav16 = os.path.join(tmp, f"s{n}-16k.wav")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", files[n], "-ar", "16000", "-ac", "1", wav16], check=True)
            text = transcribe(args.stt_cmd, wav16, tmp)
            with open(os.path.join(args.take_dir, f"s{n}.txt"), "w", encoding="utf-8") as fh:
                fh.write(text.strip() + "\n")
            expected = norm_words(scene["text_cued"])
            heard = heard_words(text)
            if args.tags:
                tags = [t.strip() for t in args.tags.split(",") if t.strip()]
            else:
                # The take may have been sent from text_cued or from any adapter's variant.
                sources = [scene.get("text_cued") or ""] + [v for v in (scene.get("variants") or {}).values() if v]
                tags = [t for src in sources for t in re.findall(r"<([^>]+)>", src)]
            tag_words = {w for t in tags for w in norm_words(t)}
            sm = difflib.SequenceMatcher(None, expected, heard, autojunk=False)
            inserted = []
            for op, a1, a2, b1, b2 in sm.get_opcodes():
                if op in ("insert", "replace"):
                    inserted.extend(heard[b1:b2])
            leaks = sorted({w for w in inserted if w in tag_words})
            matched_idx = set()
            for block in sm.get_matching_blocks():
                matched_idx.update(range(block.a, block.a + block.size))
            tail = list(range(max(0, len(expected) - 3), len(expected)))
            ending = sum(1 for i in tail if i in matched_idx) >= min(2, len(tail))
            rate = len(matched_idx) / max(1, len(expected))
            reasons = []
            if leaks:
                reasons.append("tag words heard: " + ", ".join(leaks))
            if not ending:
                reasons.append("ending not heard")
            if rate < args.min_match:
                reasons.append(f"match rate {rate:.2f} below {args.min_match}")
            rec = {"scene": n, "matched": len(matched_idx), "total": len(expected), "match_rate": round(rate, 3),
                   "ending_heard": ending, "inserted_tag_words": leaks, "needs_regen": bool(reasons), "reason": "; ".join(reasons)}
            if reasons:
                report["needs_regen"].append(n)
                if leaks and args.move_leaks:
                    target = os.path.join(args.take_dir, f"s{n}-tagged.wav")
                    k = 2
                    while os.path.exists(target):
                        target = os.path.join(args.take_dir, f"s{n}-tagged-{k}.wav")
                        k += 1
                    os.rename(files[n], target)
                    rec["moved_to"] = os.path.basename(target)
            report["scenes"].append(rec)
            print(f"s{n}: {len(matched_idx)} of {len(expected)} words, ending {'heard' if ending else 'NOT heard'}"
                  + (f", LEAK {', '.join(leaks)}" if leaks else "") + (" -> regenerate" if reasons else ""))
    except TranscriberError as err:
        if err.code < 0:
            print(f"FAIL: transcriber died with signal {-err.code}")
        else:
            print(f"FAIL: transcriber exited {err.code}")
        picked, mentions_model = transcriber_lines(err.stderr)
        for ln in picked:
            print(ln)
        if err.code in (-6, 134) or "GGML_ASSERT" in (err.stderr or ""):
            print("whisper.cpp aborted while loading the model, as it can inside a sandbox: add -ng (--no-gpu) to both transcriber commands (references/example-local-tools.md, whisper.cpp example); it runs on the CPU and keeps word times. Use --no-stt only when no transcriber can run.")
        if mentions_model:
            print("check the model path (`probe_tools.py --stt-model <path>`); with no transcriber, run "
                  "`voice_batch.py --config voices/batch.json --no-stt --merge-manifest`, or listen to every ending "
                  "and then run `join_scenes.py` and `align_words.py --no-stt`")
        return 1
    except (subprocess.CalledProcessError, RuntimeError, OSError) as err:
        print(f"FAIL: {type(err).__name__}: {err}")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out = args.report or os.path.join(args.take_dir, "check.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    if report["needs_regen"]:
        print("regenerate scenes: " + ",".join(str(n) for n in report["needs_regen"]) + f"  (report {out})")
        return 2
    print(f"PASS: every scene clean (report {out})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
