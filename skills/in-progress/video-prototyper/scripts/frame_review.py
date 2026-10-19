#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Write the host's frame-review list for a build, and optionally capture the frames.

For each available voice (and No voice) and both modes it lists capture URLs at: t = 0
(the opening frame), the middle and the end of the title card (when the card is kept),
every scene start, the middle of
every sentence, and the last sentence's end, each with a short note of what should be on
screen. For a loop ("loop": true in cues.json) it adds t = duration - 1/30 and t = duration,
the two sides of the seam. A take is available when its audio and timing files exist, its
scene count matches the cues and its words hash is current; any other take is skipped with
the reason. The host opens or captures them and judges by eye: overlap, clipping, fonts,
contrast, the opening frame.

Usage:
  python3 frame_review.py --build <video-id>/<build-id> --base-url http://127.0.0.1:8770/<video-id>/<build-id>/index.html \\
      [--out <build>/qa/frame-review.json] [--modes light,dark] [--voices all|id,id] \\
      [--capture-cmd "<browser> --headless=new --hide-scrollbars --window-size=1920,1080 --screenshot={png} {url}"] \\
      [--frames-dir <build>/frames]

--capture-cmd is run without a shell, once per frame, with {url} and {png} filled in.
Frames are named <voice>/<mode>-t<SSS.SS>.png so they sort and never collide.

Dependencies: Python 3.9 or later, standard library only; a headless browser for --capture-cmd.
Exit codes: 0 list written (and captures ran); 1 bad input or a capture failed.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from urllib.parse import urlencode


def repaired_sentences(cue_sentences, take_sentences):
    """Keep in step with buildTiming in assets/build-template/index.html."""
    if len(cue_sentences) != len(take_sentences):
        raise ValueError("timing does not match the cues; re-run alignment")
    flat = [dict(c, start=float(t.get("start", 0)), end=float(t.get("end", 0)),
                 text=t.get("text") or c["text"]) for c, t in zip(cue_sentences, take_sentences)]
    for i, sentence in enumerate(flat):
        if i and sentence["start"] < flat[i - 1]["start"]:
            sentence["start"] = flat[i - 1]["start"]
            print(f"WARNING: {sentence['id']}: start clamped to the previous sentence")
        if sentence["end"] < sentence["start"]:
            sentence["end"] = sentence["start"]
            print(f"WARNING: {sentence['id']}: end clamped to its start")
    for j, sentence in enumerate(flat):
        if sentence["end"] - sentence["start"] >= 0.05:
            continue
        prev_end = flat[j - 1]["end"] if j else 0
        slot = max(0.6, len(sentence["text"].split()) / 2.4)
        if all(s["end"] - s["start"] < 0.05 for s in flat[j:]):
            sentence["start"] = prev_end + 0.3
            sentence["end"] = sentence["start"] + slot
            sentence["silent"] = True
            print(f"WARNING: {sentence['id']}: last line not in the audio; shown in a silent slot")
        else:
            sentence["end"] = max(sentence["start"] + 0.05,
                                  min(flat[j + 1]["start"], sentence["start"] + slot))
            print(f"WARNING: {sentence['id']}: zero-length sentence widened")
    return flat


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--out")
    ap.add_argument("--modes", default="light,dark")
    ap.add_argument("--voices", default="all")
    ap.add_argument("--capture-cmd")
    ap.add_argument("--frames-dir")
    args = ap.parse_args()

    build = os.path.abspath(args.build)
    with open(os.path.join(build, "cues.json"), encoding="utf-8") as fh:
        cues = json.load(fh)
    pre = float(cues.get("title_card", {}).get("duration_s", 3.5))
    tail = float(cues.get("tail_s", 6))
    base_sentences = [dict(c, scene=s["n"], scene_title=s.get("title", ""), on_screen=s.get("on_screen", "")) for s in cues["scenes"] for c in s["cues"]]
    voices = [("none", None, None)]
    vrel = (cues.get("voices") or {}).get("manifest")
    if vrel and os.path.exists(os.path.join(build, vrel)):
        vpath = os.path.normpath(os.path.join(build, vrel))
        with open(vpath, encoding="utf-8") as fh:
            for v in json.load(fh).get("voices", []):
                if v.get("id") == "none":
                    continue
                if not (isinstance(v.get("timing"), str) and v.get("timing").strip()):
                    print(f"skip {v['id']}: not available (no timing file listed)")
                    continue
                if not (isinstance(v.get("audio"), str) and v.get("audio").strip()):
                    print(f"skip {v['id']}: not available (no audio file listed)")
                    continue
                vdir = os.path.dirname(vpath)
                tpath = os.path.join(vdir, v["timing"])
                apath = os.path.join(vdir, v["audio"]) if v.get("audio") else None
                if not apath or not os.path.exists(apath) or not os.path.exists(tpath):
                    print(f"skip {v['id']}: not available (audio or timing file missing)")
                    continue
                with open(tpath, encoding="utf-8") as tf:
                    timing = json.load(tf)
                if len(timing.get("scenes") or []) != len(cues["scenes"]):
                    print(f"skip {v['id']}: not available (timing has {len(timing.get('scenes') or [])} scenes; cues have {len(cues['scenes'])})")
                    continue
                if (cues.get("source_words_sha256") and timing.get("source_words_sha256")
                        and cues["source_words_sha256"] != timing["source_words_sha256"]):
                    print(f"skip {v['id']}: not available (stale: the script changed after this take was aligned)")
                    continue
                voices.append((v["id"], timing, v))
    if args.voices != "all":
        keep = set(args.voices.split(","))
        voices = [v for v in voices if v[0] in keep]
    modes = [m for m in args.modes.split(",") if m]

    frames, durations = [], {}
    for vid, timing, _ in voices:
        sents = base_sentences
        audio_dur = None
        if timing:
            if len(timing["sentences"]) != len(base_sentences):
                print(f"skip {vid}: timing does not match the cues; re-run alignment")
                continue
            sents = repaired_sentences(base_sentences, timing["sentences"])
            audio_dur = float(timing.get("duration", 0))
        duration = pre + max(sents[-1]["end"] + tail, audio_dur or 0)
        durations[vid] = round(duration, 3)
        if pre > 0:
            points = [(0.0, "opening", "Title card visible; nothing else."),
                      (pre / 2, "title card", "Title card only: its title, plus its label and kicker when cues.json sets them. Nothing else."),
                      (pre + 0.05, "title card end", "The first scene's label and background, plus its first element and caption only if its first sentence starts at once; nothing overlaps or is clipped.")]
        else:
            # 0.4 s is SCENE_FADE in assets/build-template/index.html.
            points = [(0.0, "opening", "No title card (dropped with the owner's confirmation in PLAN.md): the background only, plus any whole-video line placed outside the scenes (such as a disclosure); the first scene fades in from here."),
                      (0.4, "first scene in", "The first scene's label and background, plus its first element and caption only if its first sentence starts at once; nothing overlaps or is clipped.")]
        seen = {sents[0]["scene"]}  # the first scene's opening is the title-card-end frame
        for s in sents:
            if s["scene"] not in seen:
                seen.add(s["scene"])
                points.append((pre + s["start"] - 0.05, f"scene {s['scene']} start", f"Scene {s['scene']} ({s['scene_title']}) opens with its label and background; an element anchored at its first sentence may already be fading in (reveals start 0.15 s before their anchor), but nothing from a later sentence shows; the previous scene has cleared."))
            mid = pre + (s["start"] + s["end"]) / 2
            points.append((mid, s["id"], f"Shows what is said: \"{s['text'][:70]}\" (the screen may leave off the end punctuation). Scene: {s['on_screen'][:80]}"))
        last_check = ("The last line is on screen and holds long enough to read." if vid == "none"
                      else "The last line is on screen and its words are heard in the take.")
        points.append((pre + sents[-1]["end"] - 0.05, "last line", last_check))
        if cues.get("loop"):
            points.append((duration - 1 / 30, "loop seam, last frame", "Background only, or nearly: this frame flows into the frame at t = 0."))
            points.append((duration, "loop seam", "t = duration matches t = 0: the same picture as the opening frame."))
        for t, cue, check in points:
            t = max(0.0, min(t, duration))
            rec = {"voice": vid, "cue": cue, "seconds": round(t, 3), "check": check}
            for mode in modes:
                rec[mode] = args.base_url + "?" + urlencode({"voice": vid, "music": "off", "render": "1", "mode": mode, "t": f"{t:.3f}"})
            frames.append(rec)

    out = args.out or os.path.join(build, "qa", "frame-review.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    doc = {"instruction": "Open or capture each URL at 1920x1080 and judge it against its check. Also check inside the viewer iframe and at about 375 px wide.",
           "durations": durations, "frames": frames}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {out}: {len(frames)} frames x {len(modes)} modes")

    if args.capture_cmd:
        frames_dir = args.frames_dir or os.path.join(build, "frames")
        failures = 0
        for rec in frames:
            for mode in modes:
                png = os.path.join(frames_dir, rec["voice"], f"{mode}-t{rec['seconds']:06.2f}.png")
                os.makedirs(os.path.dirname(png), exist_ok=True)
                argv = [p.format(url=rec[mode], png=png) for p in split_cmd(args.capture_cmd)]
                try:
                    subprocess.run(argv, check=True, capture_output=True, timeout=120)
                except FileNotFoundError:
                    failures += 1
                    print(f"capture failed for {png}: {argv[0]!r} was not found; check the path, and quote a path that contains spaces")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as err:
                    failures += 1
                    print(f"capture failed for {png}: {type(err).__name__}")
        print(f"captured into {frames_dir}" + (f" with {failures} failure(s)" if failures else ""))
        return 1 if failures else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
