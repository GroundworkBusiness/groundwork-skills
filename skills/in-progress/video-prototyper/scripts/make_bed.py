#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Build a music bed: one file longer than the video with any take, at a fixed measured loudness.

Steps: measure the source (integrated loudness, true peak, last 8 s); trim a fade-in
head and a fade-out tail (auto by default: keep the stretch whose short-term loudness
stays within 1.5 LU of the track's steady middle level; an edge that is already steady at
the first full 3 s reading (head) or the last reading (tail) is kept untrimmed); join
enough plays with an equal-power crossfade to reach --min-seconds; apply one static gain
so the bed lands near --target LUFS; encode with metadata and cover art removed; verify
loudness and length; check every seam (short-term loudness around the seam within
--seam-tolerance LU of the music either side). A source that fades out leaves a hole at
the seam, which is why the tail is trimmed first.

Set --min-seconds to the longest video duration over every take and No voice, plus a
margin of about 10 s. For No voice the duration is `duration` in cues.json; for a take it
is the page's __video.duration, or the duration mix_audio.py prints. Both already include
the title-card pre-roll and the tail, and the fade-out ends inside them.

Usage:
  python3 make_bed.py --src music/source/<file> --out music/<id>-bed.mp3 --min-seconds 260 \\
      [--target -30] [--xfade 6] [--trim-head auto|SECONDS] [--trim-tail auto|SECONDS] \\
      [--seam-tolerance 3] [--format mp3|wav] [--id ID --label LABEL --origin owner-supplied|generated|licensed] \\
      [--media-log media/media-log.jsonl] \\
      [--vocals-check --stt-cmd "<transcriber> -m <model-file> -f {in} -np -nt"]

Working transcriber commands: references/example-local-tools.md.
The source file is only read, never changed. The script prints a tracks.json entry with
the measured fields. Ask the composition-rights question as soon as the track arrives.
Building and measuring the bed may go ahead, because it is local. Until the owner answers,
list the track with rights set to "pending: <question>, asked <date>", keep it out of the
default and out of any export or shared build, and carry the question in the report.
When the source's title tag, its file name or --label says cover, remix or "in the style of",
the script prints a WARN line and sets rights to "pending: ..." with the date asked left as
<YYYY-MM-DD> for the agent to fill in. A null rights field means not recorded: sync_embed.py
embeds the track as not ready and mix_audio.py refuses it until the owner's answer is recorded.

With --origin generated, --media-log names the media log api_media.py writes. The last
record whose "out" resolves to the same file as --src (paths in the log are read from the
current folder, so run from <project>/) fills generated_with (its endpoint),
requested_model, reported_model, generated_on (the date of created_at), prompt,
cost_list_usd (estimated_cost.usd) and watermark. With no matching record the script prints
a NOTE and leaves those fields null to fill by hand.

Dependencies: Python 3.9 or later, standard library only; ffmpeg and ffprobe; a
speech-to-text command for --vocals-check.
Exit codes: 0 bed written and every check passed; 2 written but a check failed (loudness,
length, seam or vocals); 1 tool error.
"""
import argparse
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path]).stdout.strip())


def ebur128(path, extra_in=None):
    """Return (integrated LUFS, true peak dBFS, [(t, short_term)])."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats"] + (extra_in or []) + ["-i", path, "-filter_complex", "ebur128=peak=true", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    curve = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r"t:\s*([\d.]+)\s+TARGET.*?S:\s*(-?[\d.]+|-inf)", err) if m.group(2) != "-inf"]
    summary = err[err.rfind("Summary:"):] if "Summary:" in err else ""
    i = re.search(r"I:\s*(-?[\d.]+|-inf) LUFS", summary)
    p = re.search(r"Peak:\s*(-?[\d.]+|-inf) dBFS", summary)
    integ = float(i.group(1)) if i and i.group(1) != "-inf" else float("-inf")
    peak = float(p.group(1)) if p and p.group(1) != "-inf" else float("-inf")
    return integ, peak, curve


def auto_trims(curve, length):
    """Find the steady level (median short-term loudness of the middle half of the track),
    then trim the head before and the tail after the stretch that stays within 1.5 LU of it.
    Short-term loudness covers the last 3 s, so a trimmed edge moves 1.5 s toward the window
    centre. ffmpeg reads near -120 LUFS until the first 3 s window fills, so the first loud
    reading is never before about t = 3: a head that is already steady at the first full
    reading, or a tail that is still steady at the last reading, is kept (no trim)."""
    middle = sorted(s for t, s in curve if length * 0.25 <= t <= length * 0.75)
    if not middle:
        return 0.0, 0.0
    steady = middle[len(middle) // 2]
    loud = [t for t, s in curve if s >= steady - 1.5]
    if not loud:
        return 0.0, 0.0
    full = [t for t, s in curve if t >= 2.95]  # readings whose 3 s window is full
    head = 0.0 if full and loud[0] <= full[0] + 0.05 else max(0.0, loud[0] - 1.5)
    tail_end = length if loud[-1] >= curve[-1][0] - 0.05 else min(length, max(head + 1.0, loud[-1] - 1.5))
    return round(head, 2), round(max(0.0, length - tail_end), 2)


def media_record(log_path, src):
    """The last media-log record whose "out" resolves to the same file as src, or None."""
    target = os.path.realpath(src)
    found = None
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("out") and os.path.realpath(rec["out"]) == target:
                found = rec
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


DERIVATIVE = re.compile(r"(?i)\b(cover|remix|in the style of)\b")


def title_tag(path):
    """The source's title tag, or an empty string when it has none or ffprobe fails."""
    try:
        res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags=title",
                              "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    except OSError:
        return ""
    return res.stdout.strip() if res.returncode == 0 else ""


def transcriber_lines(text):
    """Error lines from a transcriber, else its last lines, and whether a model file is named."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    matched = [ln for ln in lines if re.search(r"error|not found|no such file|failed|cannot|unable", ln, re.I)]
    return (matched[:5] if matched else lines[-5:]), bool(re.search(r"model file", text or "", re.I))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-seconds", type=float, required=True)
    ap.add_argument("--target", type=float, default=-30.0)
    ap.add_argument("--xfade", type=float, default=6.0)
    ap.add_argument("--trim-head", default="auto")
    ap.add_argument("--trim-tail", default="auto")
    ap.add_argument("--seam-tolerance", type=float, default=3.0)
    ap.add_argument("--format", choices=["mp3", "wav"], default=None)
    ap.add_argument("--id")
    ap.add_argument("--label")
    ap.add_argument("--origin", default="owner-supplied")
    ap.add_argument("--media-log", help="with --origin generated: the media log whose record for --src fills the generation fields")
    ap.add_argument("--vocals-check", action="store_true")
    ap.add_argument("--stt-cmd")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            print(f"FAIL: {tool} not found")
            return 1
    if args.vocals_check and not args.stt_cmd:
        print("FAIL: --vocals-check needs --stt-cmd")
        return 1
    fmt = args.format or ("wav" if args.out.lower().endswith(".wav") else "mp3")
    problems = []
    tmp = tempfile.mkdtemp()
    try:
        src_len = duration(args.src)
        integ, peak, curve = ebur128(args.src)
        tail_i, _, _ = ebur128(args.src, ["-sseof", "-8"])
        print(f"source: {src_len:.1f} s, integrated {integ:.1f} LUFS, peak {peak:.1f} dBFS, last 8 s {tail_i:.1f} LUFS"
              + ("  (fades out)" if tail_i < integ - 6 else ""))
        auto_head, auto_tail = auto_trims(curve, src_len)
        head = auto_head if args.trim_head == "auto" else float(args.trim_head)
        tail = auto_tail if args.trim_tail == "auto" else float(args.trim_tail)
        seg = src_len - head - tail
        if seg <= args.xfade * 2:
            print("FAIL: the trimmed source is too short for the crossfade")
            return 1
        print(f"trim: head {head:.2f} s, tail {tail:.2f} s -> {seg:.1f} s per play")
        plays = 1 if seg >= args.min_seconds else math.ceil((args.min_seconds - args.xfade) / (seg - args.xfade))
        n = max(1, plays)
        parts = [f"[0:a]aformat=sample_fmts=fltp,atrim=start={head}:duration={seg},asetpts=PTS-STARTPTS,asplit={n}" + "".join(f"[p{i}]" for i in range(n)) if n > 1
                 else f"[0:a]aformat=sample_fmts=fltp,atrim=start={head}:duration={seg},asetpts=PTS-STARTPTS[j0]"]
        last = "p0" if n > 1 else "j0"
        for i in range(1, n):
            parts.append(f"[{last}][p{i}]acrossfade=d={args.xfade}:c1=qsin:c2=qsin[j{i}]")
            last = f"j{i}"
        joined = os.path.join(tmp, "joined.wav")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", args.src, "-filter_complex", ";".join(parts),
             "-map", f"[{last}]", "-c:a", "pcm_f32le", joined])
        j_integ, _, _ = ebur128(joined)
        gain = args.target - j_integ
        codec = ["-c:a", "libmp3lame", "-b:a", "192k"] if fmt == "mp3" else ["-c:a", "pcm_s16le"]
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", joined, "-af", f"volume={gain:.2f}dB",
             "-map_metadata", "-1", "-vn"] + codec + [args.out])
        out_len = duration(args.out)
        o_integ, o_peak, o_curve = ebur128(args.out)
        print(f"bed: {n} play(s), {out_len:.1f} s, gain {gain:+.1f} dB, integrated {o_integ:.1f} LUFS, peak {o_peak:.1f} dBFS")
        if abs(o_integ - args.target) > 1.0:
            problems.append(f"loudness {o_integ:.1f} LUFS is more than 1 LU from the target {args.target}")
        if out_len < args.min_seconds:
            problems.append(f"bed is {out_len:.1f} s, shorter than --min-seconds {args.min_seconds}")
        if o_peak > -1.0:
            problems.append(f"peak {o_peak:.1f} dBFS is above -1 dBFS")

        seams = []
        for i in range(1, n):
            centre = i * (seg - args.xfade) + args.xfade / 2
            def mean(a, b):
                vals = [s for t, s in o_curve if a <= t <= b]
                return sum(vals) / len(vals) if vals else float("nan")
            at = mean(centre - 2, centre + 2)
            around = [v for v in (mean(centre - 15, centre - 5), mean(centre + 5, centre + 15)) if not math.isnan(v)]
            ref = sum(around) / len(around) if around else float("nan")
            ok = not math.isnan(at) and not math.isnan(ref) and abs(at - ref) <= args.seam_tolerance
            seams.append({"at_s": round(centre, 1), "seam_lufs": round(at, 1), "neighbours_lufs": round(ref, 1), "pass": ok})
            print(f"seam at {centre:.1f} s: {at:.1f} LUFS vs {ref:.1f} around -> {'pass' if ok else 'FAIL'}")
            if not ok:
                problems.append(f"seam at {centre:.1f} s dips or jumps more than {args.seam_tolerance} LU; trim more tail or pick steadier sections")

        vocals = None
        if args.vocals_check:
            wav16 = os.path.join(tmp, "src-16k.wav")
            out_base = os.path.join(tmp, "stt")
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", args.src, "-ar", "16000", "-ac", "1", wav16])
            argv = [p.format(**{"in": wav16, "out": out_base}) for p in split_cmd(args.stt_cmd)]
            try:
                text = subprocess.run(argv, capture_output=True, text=True, check=True).stdout
            except OSError as err:
                print(f"FAIL: could not run the transcriber ({type(err).__name__}); the vocals check did not run")
                return 1
            if "{out}" in args.stt_cmd:
                for candidate in (out_base + ".txt", out_base):
                    if os.path.exists(candidate):
                        with open(candidate, encoding="utf-8") as fh:
                            text = fh.read()
                        break
                else:
                    print("FAIL: the transcriber wrote no {out}.txt or {out}; the vocals check did not run")
                    return 1
            elif os.path.exists(out_base + ".txt"):
                with open(out_base + ".txt", encoding="utf-8") as fh:
                    text = fh.read()
            words = re.sub(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*", " ", text)
            words = [w for w in re.findall(r"[a-zA-Z']+", words)]
            vocals = "transcribed: no words heard" if not words else "transcribed: words heard: " + " ".join(words[:12])
            print("vocals check: " + vocals)
            if words:
                problems.append("the transcriber heard words; listen for vocals before use")
    except subprocess.CalledProcessError as err:
        err_text = err.stderr or ""
        picked, mentions_model = transcriber_lines(err_text)
        print(f"FAIL: {' '.join(err.cmd[:3])} ... exited {err.returncode}")
        for ln in picked:
            print(ln)
        if mentions_model:
            print("check the model path (`probe_tools.py --stt-model <path>`), or leave out `--vocals-check` and listen for vocals")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    title = title_tag(args.src)
    file_words = re.sub(r"[_-]", " ", os.path.splitext(os.path.basename(args.src))[0])
    rights = None
    for text in (title, file_words, args.label or ""):
        if text and DERIVATIVE.search(text):
            print(f'WARN: "{text}" names a cover, remix or "in the style of": ask the owner the '
                  'composition-rights question now, then fill in the date asked')
            rights = f'pending: composition rights for "{title or os.path.basename(args.src)}", asked <YYYY-MM-DD>'
            break
    out_dir = os.path.dirname(os.path.abspath(args.out))
    entry = {
        "id": args.id or os.path.splitext(os.path.basename(args.out))[0],
        "label": args.label or args.id or os.path.basename(args.out),
        "file": os.path.basename(args.out),
        "seconds": round(out_len, 1),
        "loudness_lufs": round(o_integ, 1),
        "peak_dbfs": round(o_peak, 1),
        "source_file": os.path.relpath(os.path.abspath(args.src), out_dir).replace(os.sep, "/"),
        "origin": args.origin,
        "bed": {"plays": n, "xfade_s": args.xfade, "trim_head_s": head, "trim_tail_s": tail, "gain_db": round(gain, 2), "seams": seams},
        "seam_check": ("pass" if all(s["pass"] for s in seams) else "fail") if seams else "no seam (one play)",
        "vocals_checked": vocals,
        "rights": rights, "rights_cleared_by": None, "rights_cleared_on": None,
        "generated_with": None, "requested_model": None, "reported_model": None, "generated_on": None,
        "prompt": None, "cost_list_usd": None, "watermark": None, "content_credentials_in_source": None,
        "gain_with_voice": None, "gain_no_voice": None,
    }
    if args.media_log:
        if args.origin != "generated":
            print("NOTE: --media-log is read only with --origin generated; the generation fields stay null")
        else:
            try:
                rec = media_record(args.media_log, args.src)
            except OSError as err:
                rec = None
                print(f"NOTE: cannot read {args.media_log} ({type(err).__name__}); fill the generation fields by hand")
            else:
                if rec is None:
                    print(f"NOTE: no record for {args.src} in {args.media_log}; fill the generation fields by hand")
            if rec is not None:
                cost = rec.get("estimated_cost") if isinstance(rec.get("estimated_cost"), dict) else {}
                entry.update({
                    "generated_with": rec.get("endpoint"),
                    "requested_model": rec.get("requested_model"),
                    "reported_model": rec.get("reported_model"),
                    "generated_on": (str(rec["created_at"])[:10] if rec.get("created_at") else None),
                    "prompt": rec.get("prompt"),
                    "cost_list_usd": cost.get("usd"),
                    "watermark": rec.get("watermark"),
                })
                print(f"filled the generation fields from the {args.media_log} record of {rec.get('created_at') or 'unknown date'}")
    print("tracks.json entry:")
    print(json.dumps(entry, indent=2))
    if problems:
        for p in problems:
            print("CHECK FAILED: " + p)
        return 2
    print(f"PASS: wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
