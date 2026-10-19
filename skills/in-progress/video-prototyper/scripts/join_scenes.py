#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Join a take's scene files into one WAV with a fixed gap, and write exact scene offsets.

Finds s1.wav ... sN.wav in the take folder (the count comes from the files; s<N>-tagged.wav
and other names are ignored), checks they run 1..N without a hole, and writes the take
plus <take>-scenes.json with each scene's start and end in seconds, computed from sample
counts so they are exact. align_words.py uses those offsets to pin scene boundaries.
With --scenes (a scenes.json), it joins exactly the scene numbers that file lists, in
that order, fails if one is missing, and prints a warning for any other s<N>.wav without
deleting it. Without --scenes, it keeps the 1..N behaviour above.
It also measures the joined take's integrated loudness with ffmpeg's ebur128 filter,
prints it and records it as loudness_lufs in <take>-scenes.json (voice_batch.py copies it
into voices.json). Takes from different tools differ in level; when the owner hears jumps
between voices, apply one static gain to about -22 LUFS.

Usage:
  python3 join_scenes.py --take-dir voices/<voice> --out voices/<voice>/<voice>.wav [--gap 0.6]
      [--scenes script/scenes.json]

Scenes that differ in sample rate, channels or sample width from scene 1 are converted to
match it with ffmpeg first.

Dependencies: Python 3.9 or later, standard library only; ffmpeg to measure loudness
(skipped with a note when ffmpeg is missing) and to convert scenes whose formats differ.
Exit codes: 0 written; 1 a scene is missing or unreadable.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave


def read(path):
    with wave.open(path) as w:
        return (w.getframerate(), w.getnchannels(), w.getsampwidth()), w.readframes(w.getnframes())


def loudness(path):
    """Integrated loudness in LUFS from ffmpeg's ebur128 summary, or None."""
    if not shutil.which("ffmpeg"):
        return None
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-filter_complex", "ebur128",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):] if "Summary:" in err else ""
    m = re.search(r"I:\s*(-?[\d.]+) LUFS", summary)
    return float(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--take-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gap", type=float, default=0.6)
    ap.add_argument("--scenes", help="scenes.json; join exactly these scene numbers, in order")
    args = ap.parse_args()

    found = {}
    for name in os.listdir(args.take_dir):
        m = re.fullmatch(r"s(\d+)\.wav", name)
        if m:
            found[int(m.group(1))] = os.path.join(args.take_dir, name)
    if args.scenes:
        with open(args.scenes, encoding="utf-8") as fh:
            listed = json.load(fh)["scenes"]
        sequence = [int(s["n"]) for s in listed]
        missing = [n for n in sequence if n not in found]
        if missing:
            print("FAIL: missing scenes " + ",".join(map(str, missing)))
            return 1
        if not sequence:
            print("FAIL: no s<N>.wav files")
            return 1
        wanted = set(sequence)
        for n in sorted(found):
            if n not in wanted:
                print(f"WARNING: ignored s{n}.wav (not in scenes.json); move it aside when it is no longer needed")
    else:
        if not found:
            print("FAIL: no s<N>.wav files")
            return 1
        count = max(found)
        missing = [n for n in range(1, count + 1) if n not in found]
        if missing:
            print("FAIL: missing scenes " + ",".join(map(str, missing)))
            return 1
        sequence = list(range(1, count + 1))

    params, first = read(found[sequence[0]])
    rate, channels, width = params
    frame_bytes = channels * width
    gap = b"\x00" * (int(round(args.gap * rate)) * frame_bytes)
    chunks, scenes, cursor = [], [], 0
    tmp = tempfile.mkdtemp()
    try:
        for i, n in enumerate(sequence):
            p, frames = (params, first) if i == 0 else read(found[n])
            if p != params:
                if not shutil.which("ffmpeg"):
                    print(f"FAIL: s{n}.wav format differs and ffmpeg is not available to convert it")
                    return 1
                conv = os.path.join(tmp, f"s{n}.wav")
                codec = {1: "pcm_u8", 2: "pcm_s16le", 3: "pcm_s24le", 4: "pcm_s32le"}[width]
                subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", found[n], "-ar", str(rate),
                                "-ac", str(channels), "-c:a", codec, conv], check=True)
                p, frames = read(conv)
            if i > 0:
                chunks.append(gap)
                cursor += len(gap) // frame_bytes
            start = cursor
            chunks.append(frames)
            cursor += len(frames) // frame_bytes
            scenes.append({"scene": n, "file": os.path.basename(found[n]),
                           "start": round(start / rate, 4), "end": round(cursor / rate, 4)})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with wave.open(args.out, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b"".join(chunks))
    duration = round(cursor / rate, 4)
    lufs = loudness(args.out)
    meta_path = re.sub(r"\.wav$", "", args.out) + "-scenes.json"
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({"take": os.path.basename(args.out), "gap_s": args.gap, "sample_rate": rate,
                   "duration": duration, "loudness_lufs": lufs, "scenes": scenes}, fh, indent=2)
        fh.write("\n")
    print(f"joined {len(sequence)} scenes into {args.out} ({duration:.2f} s, gap {args.gap} s); offsets in {meta_path}")
    print(f"integrated loudness: {lufs:.1f} LUFS" if lufs is not None else "integrated loudness: not measured (ffmpeg not found)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
