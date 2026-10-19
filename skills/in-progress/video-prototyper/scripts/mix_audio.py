#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Mix the export soundtrack the way the page plays it: voice after the title card, bed under it.

Reads the build's cues.json (title card length, tail, music gains and fades) and,
when a voice is chosen, its timing file (for the last sentence). Duration =
pre-roll + max(last sentence end + tail, take length), the same rule the page uses.
The voice is delayed by the pre-roll. The bed starts at t = 0 at gain_with_voice (or
gain_no_voice when there is no voice), fades in over fade_in seconds and out over the
last fade_out seconds (a fade of 0 means none, as in the page).
Each of gain_with_voice, gain_no_voice, fade_in and fade_out
resolves in one order, the same order the page uses: the track's own non-null value in
tracks.json, then the top level of tracks.json, then the music block of cues.json, then
the built-in default (0.5, 1.0, 2 s, 4 s). When --clips is given (the JSON list from
__video.clips()), each kept stage clip is trimmed from its in-point at its rate, delayed
to its anchor start, and mixed at gain 1.
With --bed, --tracks and --track-id are required, the bed must be the file tracks.json lists for that id, and a track whose rights are pending or not recorded is refused until the owner answers.

Usage:
  python3 mix_audio.py --cues <build>/cues.json --out export/mix.wav \
      [--voice-audio voices/<v>/<v>.wav --timing voices/<v>/<v>-timing.json] \
      [--bed music/<id>-bed.mp3 --tracks music/tracks.json --track-id <id>] \
      [--clips export/clips.json] [--target-lufs -16] [--sample-rate 48000]

--bed, --tracks and --track-id go together, so the bed's rights can be checked.

Without --voice-audio the mix is the bed or clips alone (No voice); without --bed it is the voice or clips alone.

Dependencies: Python 3.9 or later, standard library only; ffmpeg and ffprobe.
Exit codes: 0 written; 1 bad input or ffmpeg failed.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys


def usable(value):
    """A gain or fade given as a finite number of 0 or more; anything else falls to the next level."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v >= 0


def num(value, default):
    return float(value) if usable(value) else default


def has_audio_stream(path):
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    return res.returncode == 0 and bool(res.stdout.strip())


def atempo_filters(rate):
    parts = []
    r = float(rate)
    while r < 0.5:
        parts.append("atempo=0.5")
        r /= 0.5
    while r > 2.0:
        parts.append("atempo=2.0")
        r /= 2.0
    parts.append(f"atempo={r:.4f}")
    return ",".join(parts)


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cues", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice-audio")
    ap.add_argument("--timing")
    ap.add_argument("--bed")
    ap.add_argument("--tracks")
    ap.add_argument("--track-id")
    ap.add_argument("--clips")
    ap.add_argument("--target-lufs", type=float)
    ap.add_argument("--sample-rate", type=int, default=48000)
    args = ap.parse_args()
    if not args.voice_audio and not args.bed and not args.clips:
        print("FAIL: give --voice-audio, --bed or --clips")
        return 1
    if args.bed and not (args.tracks and args.track_id):
        print("FAIL: an export bed needs --tracks and --track-id so its rights can be checked")
        return 1
    if (args.tracks or args.track_id) and not args.bed:
        print("FAIL: --tracks and --track-id need --bed (the bed file tracks.json lists for that id)")
        return 1

    with open(args.cues, encoding="utf-8") as fh:
        cues = json.load(fh)
    pre = float(cues.get("title_card", {}).get("duration_s", 3.5))
    tail = float(cues.get("tail_s", 6))
    music = dict(cues.get("music") or {})
    if args.tracks:
        with open(args.tracks, encoding="utf-8") as fh:
            tracks = json.load(fh)
        for key in ("gain_with_voice", "gain_no_voice", "fade_in", "fade_out"):
            if usable(tracks.get(key)):
                music[key] = tracks[key]
        own = next((t for t in tracks.get("tracks", []) if t.get("id") == args.track_id), None)
        if args.track_id and own is None:
            print(f"FAIL: no track {args.track_id} in {args.tracks}")
            return 1
        own = own or {}
        if args.bed:
            listed = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(args.tracks)), own.get("file", "")))
            if os.path.realpath(args.bed) != listed:
                print(f"FAIL: --bed is not the file {args.tracks} lists for {args.track_id} ({own.get('file')})")
                return 1
        rights = own.get("rights")
        if isinstance(rights, str) and rights.strip().lower().startswith("pending"):
            print(f"FAIL: track {args.track_id} has rights pending ({rights}); an export waits for the owner's answer")
            return 1
        if args.bed and not (isinstance(rights, str) and rights.strip()):
            print(f"FAIL: track {args.track_id} has no rights recorded in {args.tracks}; ask the owner and record the answer first")
            return 1
        for key in ("gain_with_voice", "gain_no_voice", "fade_in", "fade_out"):
            if usable(own.get(key)):
                music[key] = own[key]

    if args.voice_audio:
        if not args.timing:
            print("FAIL: --voice-audio needs --timing")
            return 1
        with open(args.timing, encoding="utf-8") as fh:
            timing = json.load(fh)
        if not timing.get("sentences"):
            print("FAIL: timing file has no sentences (pass the take's -timing.json)")
            return 1
        cue_sentences = [c for scene in cues["scenes"] for c in scene["cues"]]
        try:
            sentences = repaired_sentences(cue_sentences, timing["sentences"])
        except ValueError as err:
            print(f"FAIL: {err}")
            return 1
        last_end = sentences[-1]["end"]
        duration = pre + max(last_end + tail, float(timing.get("duration", 0)))
    else:
        last_end = max(float(c["end"]) for s in cues["scenes"] for c in s["cues"])
        duration = pre + last_end + tail

    gain = num(music.get("gain_with_voice" if args.voice_audio else "gain_no_voice"), 0.5 if args.voice_audio else 1.0)
    fin, fout = num(music.get("fade_in"), 2.0), num(music.get("fade_out"), 4.0)
    inputs, chains, labels = [], [], []
    if args.voice_audio:
        inputs += ["-i", args.voice_audio]
        delay = int(round(pre * 1000))
        chains.append(f"[{len(labels)}:a]aresample={args.sample_rate},aformat=channel_layouts=stereo,adelay={delay}|{delay},apad,atrim=0:{duration:.3f}[v]")
        labels.append("[v]")
    if args.bed:
        inputs += ["-i", args.bed]
        fades = []
        if fin > 0:
            fades.append(f"afade=t=in:st=0:d={fin}")
        if fout > 0:
            fades.append(f"afade=t=out:st={max(0.0, duration - fout):.3f}:d={fout}")
        chains.append(f"[{len(labels)}:a]aresample={args.sample_rate},aformat=channel_layouts=stereo,apad,atrim=0:{duration:.3f},"
                      + ",".join([f"volume={gain:.4f}"] + fades) + "[b]")
        labels.append("[b]")
    if args.clips:
        with open(args.clips, encoding="utf-8") as fh:
            clip_entries = json.load(fh)
        build_dir = os.path.dirname(os.path.abspath(args.cues))
        for ci, entry in enumerate(clip_entries or []):
            rel = entry.get("file") or ""
            if not rel:
                print(f"FAIL: clip {ci} has no file; pass a src on the video or its source element")
                return 1
            clip_path = os.path.normpath(os.path.join(build_dir, rel))
            if not os.path.exists(clip_path):
                print(f"FAIL: clip file not found: {clip_path}")
                return 1
            if not has_audio_stream(clip_path):
                print(f"NOTE: skipping {rel}: no audio stream")
                continue
            inn = max(0.0, num(entry.get("in"), 0.0))
            rate = num(entry.get("rate"), 1.0)
            if rate <= 0:
                rate = 1.0
            start = max(0.0, num(entry.get("start"), 0.0))
            end = max(start, num(entry.get("end"), duration))
            span = max(0.0, end - start)
            if span <= 0:
                print(f"NOTE: skipping {rel}: zero duration")
                continue
            c_delay = int(round(start * 1000))
            idx = len(labels)
            lbl = f"[c{ci}]"
            inputs += ["-i", clip_path]
            chains.append(
                f"[{idx}:a]atrim=start={inn:.4f},asetpts=PTS-STARTPTS,{atempo_filters(rate)},"
                f"atrim=0:{span:.4f},asetpts=PTS-STARTPTS,adelay={c_delay}:all=1,apad,"
                f"atrim=0:{duration:.3f},aresample={args.sample_rate},aformat=channel_layouts=stereo{lbl}"
            )
            labels.append(lbl)
    if not labels:
        print("FAIL: no audio inputs with an audio stream to mix")
        return 1
    mix = "".join(labels) + (f"amix=inputs={len(labels)}:duration=first:normalize=0" if len(labels) > 1 else "anull")
    if args.target_lufs is not None:
        mix += f",loudnorm=I={args.target_lufs}:TP=-1.5:LRA=11"
    graph = ";".join(chains + [mix + "[out]"])
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + inputs + ["-filter_complex", graph, "-map", "[out]",
                                                                             "-ar", str(args.sample_rate), "-c:a", "pcm_s16le", args.out]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as err:
        print("FAIL: ffmpeg: " + (err.stderr or "")[-400:])
        return 1
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", args.out, "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+) LUFS", summary)
    p = re.search(r"Peak:\s*(-?[\d.]+) dBFS", summary)
    print(f"wrote {args.out}: {duration:.2f} s (pre-roll {pre} s, tail {tail} s), bed gain {gain if args.bed else 'none'}, "
          f"integrated {i.group(1) if i else '?'} LUFS, peak {p.group(1) if p else '?'} dBFS")
    if p and float(p.group(1)) > -1.0:
        print("WARNING: peak above -1 dBFS; lower the target or the bed gain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
