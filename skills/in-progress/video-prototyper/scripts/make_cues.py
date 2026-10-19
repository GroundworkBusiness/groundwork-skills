#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Write a build's estimated cues.json from the canonical script.

Every sentence of script.txt becomes one cue, with an id (c01, c02, ...) that
matches the sentence ids align_words.py writes into each take's timing file.
Times are estimates in narration time (seconds after the title card), used
until a voice exists and for the No voice option.

Usage:
  python3 make_cues.py --script script/script.txt --scenes script/scenes.json \\
      --out <video-id>/<build-id>/cues.json [--title "..."] [--label "Part 1"] \\
      [--kicker "..."] [--wps 2.4] [--breath 0.45] [--lead 0.6] [--hold 2.5] \\
      [--title-card 3.5] [--tail 6 | --target-seconds 20] [--loop | --no-loop] \\
      [--voices-manifest ../../voices/voices.json | --no-voices] \\
      [--tracks-manifest ../../music/tracks.json | --no-music] [--message-type video:state] \\
      [--default-mode light|dark] [--captions on|off]

When --out already exists, its title card, pace, music, voices, message type, default mode,
loop, captions default and target length are kept unless a flag overrides them. A pace
value given by neither a flag nor the existing file takes the default shown in the Usage
line. To start from a copied template or look, delete its cues.json first, or its title
card and message type carry over. --title-card 0 drops the title card (a loop or text-only
piece, with the owner's confirmation recorded in PLAN.md). --no-voices sets voices.manifest
to null (a look: a silent one-scene proof). --no-music sets music.manifest to null and the
default to off, keeping the gains and fades (a look, or a project with music set to none);
a later music pick reruns with --tracks-manifest ../../music/tracks.json.

--loop writes "loop": true: the page clears the last scene over the video's last second,
so t = duration paints the same frame as t = 0, and playback wraps to 0 at the end. When
the tail after the last sentence is under 1 s, the fade takes the tail, and it still
starts only after the last sentence ends. --target-seconds N sets the tail so the duration
is exactly N, and fails when the lines need more than N at this pace; it is stored as
target_seconds and reapplied on a rerun (an explicit --tail replaces it). With --loop or
--target-seconds it prints each cue's estimated visible span. --captions on|off writes
captions_default, the page's captions setting when the URL gives none.

Dependencies: Python 3.9 or later, standard library only.
Exit codes: 0 written; 1 bad input (for example paragraph and scene counts differ).
"""
import argparse
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cue_check  # noqa: E402

APOSTROPHES = {"’": "'", "‘": "'", "ʼ": "'"}


def norm_words(text):
    """The shared normalisation: lowercase, drop <tags>, fold apostrophes,
    replace anything outside a-z, 0-9 and ' with a space, split, trim quotes."""
    text = re.sub(r"<[^>]*>", " ", text).lower()
    for curly, straight in APOSTROPHES.items():
        text = text.replace(curly, straight)
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return [w.strip("'") for w in text.split() if w.strip("'")]


TERMINATOR = re.compile(r"(\.\.\.|…|[.!?]+)([\"'”’)]*)")


def split_sentences(paragraph):
    """Split on . ! ? or an ellipsis followed by whitespace or the end.
    An ellipsis followed by a lowercase word continues the sentence."""
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


def read_paragraphs(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read().replace("\r\n", "\n").strip()
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def cue_id(index):
    return "c" + str(index + 1).zfill(2)


PACE_FIELDS = (
    ("wps", "words_per_second", 2.4, True),
    ("breath", "breath_after_sentence_s", 0.45, False),
    ("lead", "scene_lead_s", 0.6, False),
    ("hold", "scene_hold_s", 2.5, False),
)


def pace_number_ok(value, above_zero):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not math.isfinite(value):
        return False
    return value > 0 if above_zero else value >= 0


def resolve_pace(args, old):
    """Flag, else the existing file's pace, else the usage default. A kept value that is
    not a finite number fails: above 0 for words per second, 0 or more for the others."""
    pace = old.get("pace") if isinstance(old.get("pace"), dict) else {}
    from_file = False
    for attr, key, default, above_zero in PACE_FIELDS:
        if getattr(args, attr) is not None:
            continue
        if key in pace:
            value = pace[key]
            if not pace_number_ok(value, above_zero):
                print(f"FAIL: {args.out} has a pace value that is not a valid number; pass the flag")
                return False
            setattr(args, attr, value)
            from_file = True
        else:
            setattr(args, attr, default)
    if from_file:
        print(f"kept pace from {args.out}: wps {args.wps}, breath {args.breath}, lead {args.lead}, hold {args.hold}")
    return True


def print_spans(scenes, pre, duration, lead, loop):
    """Each cue's estimated time on screen under No voice: from its start until its scene
    clears (the next scene's start, or the end; a loop clears over its last second)."""
    for i, sc in enumerate(scenes):
        if i + 1 < len(scenes):
            clear = max(sc["end"], scenes[i + 1]["start"] - lead) + pre
        else:
            clear = max(duration - 1.0, sc["end"] + pre) if loop else duration
        for c in sc["cues"]:
            words = c["text"] if len(c["text"]) <= 40 else c["text"][:37] + "..."
            print(f"  {c['id']} \"{words}\": at most {clear - (pre + c['start']):.1f} s on screen (until its scene clears)")
    print("  These are ceilings: an element that a later beat clears with {until: [k, f]} leaves sooner; the real spans are visible_spans in the timing audit (qa/timing-audit.json).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True)
    ap.add_argument("--scenes", help="scenes.json for titles, labels and on-screen lines")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title")
    ap.add_argument("--label")
    ap.add_argument("--kicker")
    ap.add_argument("--wps", type=float, default=None)
    ap.add_argument("--breath", type=float, default=None)
    ap.add_argument("--lead", type=float, default=None)
    ap.add_argument("--hold", type=float, default=None)
    ap.add_argument("--title-card", type=float)
    ap.add_argument("--tail", type=float)
    ap.add_argument("--voices-manifest")
    ap.add_argument("--no-voices", action="store_true", help="set voices.manifest to null (a look: a silent one-scene proof)")
    ap.add_argument("--tracks-manifest")
    ap.add_argument("--no-music", action="store_true", help="set music.manifest to null and the default to off (a look, or music set to none)")
    ap.add_argument("--message-type")
    ap.add_argument("--default-mode", choices=["light", "dark"])
    ap.add_argument("--loop", action=argparse.BooleanOptionalAction, default=None,
                    help="a loop: clear the last scene by the end and wrap playback (--no-loop removes it)")
    ap.add_argument("--target-seconds", type=float, help="set the tail so the duration is exactly this many seconds")
    ap.add_argument("--captions", choices=["on", "off"], help="captions_default: the page's captions setting when the URL gives none")
    args = ap.parse_args()
    if args.no_music and args.tracks_manifest:
        ap.error("give --no-music or --tracks-manifest, not both")
    if args.target_seconds is not None and args.tail is not None:
        ap.error("give --tail or --target-seconds, not both")
    if args.target_seconds is not None and not (args.target_seconds > 0):
        ap.error("--target-seconds must be more than 0")

    paragraphs = read_paragraphs(args.script)
    with open(args.script, encoding="utf-8") as fh:
        script_hash = cue_check.words_sha256(fh.read())
    scene_meta = []
    scenes_doc = {}
    if args.scenes:
        with open(args.scenes, encoding="utf-8") as fh:
            scenes_doc = json.load(fh)
        scene_meta = scenes_doc.get("scenes", [])
        if len(scene_meta) != len(paragraphs):
            print(f"FAIL: script.txt has {len(paragraphs)} paragraphs but scenes.json has {len(scene_meta)} scenes")
            return 1

    old = {}
    old_existed = False
    old_cue_count = 0
    if os.path.exists(args.out):
        old_existed = True
        with open(args.out, encoding="utf-8") as fh:
            old = json.load(fh)
        old_cue_count = sum(len(s.get("cues") or []) for s in (old.get("scenes") or []))
    if not resolve_pace(args, old):
        return 1

    sentences = [(i + 1, s) for i, p in enumerate(paragraphs) for s in split_sentences(p)]
    total = len(sentences)
    scenes, cursor, idx = [], 0.0, 0
    for n, paragraph in enumerate(paragraphs, start=1):
        meta = scene_meta[n - 1] if scene_meta else {}
        cursor += args.lead
        cues = []
        for text in split_sentences(paragraph):
            words = max(1, len(norm_words(text)))
            start = cursor
            end = start + words / args.wps
            cues.append({"id": cue_id(idx), "start": round(start, 3), "end": round(end, 3), "text": text})
            cursor = end + args.breath
            idx += 1
        cursor = cues[-1]["end"] + args.hold
        scenes.append({
            "id": "s%d" % n,
            "n": n,
            "title": meta.get("title", "Scene %d" % n),
            "label": meta.get("label", meta.get("title", "Scene %d" % n)),
            "start": cues[0]["start"],
            "end": cues[-1]["end"],
            "on_screen": meta.get("on_screen", ""),
            "cues": cues,
        })

    title_card = old.get("title_card", {"duration_s": 3.5, "label": "", "title": "", "kicker": ""})
    if args.title_card is not None:
        title_card["duration_s"] = args.title_card
    for key, value in (("title", args.title), ("label", args.label), ("kicker", args.kicker)):
        if value is not None:
            title_card[key] = value
    scenes_title = scenes_doc.get("title") if isinstance(scenes_doc, dict) else ""
    if args.title is None and not old.get("title") and not (old.get("title_card") or {}).get("title") and scenes_title:
        title_card["title"] = scenes_title
    if not title_card.get("title"):
        print("NOTE: title card title is empty; pass --title")
    loop = args.loop if args.loop is not None else bool(old.get("loop"))
    target = args.target_seconds
    if target is None and args.tail is None:
        target = old.get("target_seconds")
    last_end = scenes[-1]["end"]
    if target is not None:
        need = title_card["duration_s"] + last_end
        tail = round(target - need, 3)
        if tail < 0:
            print(f"FAIL: the lines need {need:.1f} s at this pace; raise --wps, lower --hold, --breath or --lead, or raise the target")
            return 1
        if loop and tail < 1.0:
            print(f"NOTE: the loop's final clear has {tail:.2f} s after the last line; it fades over that time")
    else:
        tail = args.tail if args.tail is not None else old.get("tail_s", 6.0)
    if args.tail is not None and old.get("target_seconds") is not None:
        print("NOTE: --tail replaces the stored target_seconds")
    if loop and title_card["duration_s"] > 0:
        print("NOTE: a loop with a title card does not match at the seam; drop it with --title-card 0 (with the owner's confirmation)")
    music_defaults = {"manifest": "../../music/tracks.json", "default": "off",
                      "gain_with_voice": 0.5, "gain_no_voice": 1.0, "fade_in": 2.0, "fade_out": 4.0}
    music = old.get("music", music_defaults)
    if args.no_music:
        music = dict(music, manifest=None, default="off")
    elif args.tracks_manifest:
        music["manifest"] = args.tracks_manifest
    voices = old.get("voices", {"manifest": "../../voices/voices.json", "default": "none"})
    if args.no_voices:
        voices = {"manifest": None, "default": "none"}
    elif args.voices_manifest:
        voices["manifest"] = args.voices_manifest
    captions = args.captions or old.get("captions_default")
    out = {
        "schema_version": 1,
        "title": args.title or old.get("title") or title_card.get("title", "") or (scenes_title or ""),
        "source_words_sha256": script_hash,
        "status": "estimated",
        "note": "Times are narration time: seconds after the title card. Builds read the active take's timing at runtime; these estimates serve No voice. Regenerate with make_cues.py after any script change.",
        "message_type": args.message_type or old.get("message_type", "video:state"),
        "default_mode": args.default_mode or old.get("default_mode", "light"),
        "pace": {"words_per_second": args.wps, "breath_after_sentence_s": args.breath,
                 "scene_lead_s": args.lead, "scene_hold_s": args.hold},
        "title_card": title_card,
        "tail_s": tail,
        "duration": round(title_card["duration_s"] + last_end + tail, 3),
        "music": music,
        "voices": voices,
        "scenes": scenes,
    }
    if loop:
        out["loop"] = True
    if target is not None:
        out["target_seconds"] = target
    if captions:
        out["captions_default"] = captions
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {args.out}: {len(scenes)} scenes, {total} cues, estimated duration {out['duration']:.1f} s")
    if old_existed and old_cue_count != total:
        print(f"NOTE: the script now has {total} cues (was {old_cue_count}); renumber data-cue in each build from the first changed sentence onward (references/review-and-iterate.md, Script change)")
    if loop or target is not None:
        print_spans(scenes, title_card["duration_s"], out["duration"], args.lead, loop)
    return 0


if __name__ == "__main__":
    sys.exit(main())
