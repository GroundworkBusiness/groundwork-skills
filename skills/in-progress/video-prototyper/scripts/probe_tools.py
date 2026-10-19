#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Report which tools this machine can reach, for the intake tool map.

Looks for: ffmpeg and ffprobe (audio and video work), a speech-to-text command, Node
(the timing audit), a headless-capable browser, and local voice commands. For each
--key-env NAME it reports only whether the variable is set, never its value. For each
--stt-model PATH it reports whether the transcriber's model file is present: a
transcriber command without its model cannot run check_takes.py or voice_batch.py.
With a transcriber and no --stt-model, it lists ggml-*.bin files in $WHISPER_MODEL (a
file, or a folder to search), ~/.cache/whisper-cpp, ~/.cache/whisper and ~/models (top
level only, names only) as candidates.

Usage:
  python3 probe_tools.py [--stt whisper-cli --stt whisper ...] [--stt-model <model-dir>/<model-file>] \
      [--key-env NAME ...] [--json tool-map.json]

Default speech-to-text names tried: whisper-cli, whisper, faster-whisper.

Dependencies: Python 3.9 or later, standard library only.
Exit codes: 0 always (the report is informational).
"""
import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys

BROWSERS = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge"]
BROWSER_APPS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    os.path.expandvars("%LOCALAPPDATA%/Google/Chrome/Application/chrome.exe"),
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/chromium",
]
VOICES = ["say", "espeak-ng", "espeak", "piper"]


def version(cmd, flag="--version"):
    try:
        out = subprocess.run([cmd, flag], capture_output=True, text=True, timeout=10)
        line = (out.stdout or out.stderr).strip().splitlines()
        return line[0][:80] if line else "present"
    except (OSError, subprocess.SubprocessError):
        return "present"


def model_candidates():
    """ggml-*.bin files in the usual model places, top level only. Paths only; no file is read."""
    found, places = [], []
    env = os.environ.get("WHISPER_MODEL")
    if env:
        env = os.path.expanduser(env)
        if os.path.isfile(env):
            found.append(env)
        elif os.path.isdir(env):
            places.append(env)
    places += [os.path.expanduser(p) for p in ("~/.cache/whisper-cpp", "~/.cache/whisper", "~/models")]
    for place in places:
        try:
            names = sorted(os.listdir(place))
        except OSError:
            continue
        for name in names:
            path = os.path.join(place, name)
            if fnmatch.fnmatch(name, "ggml-*.bin") and os.path.isfile(path) and path not in found:
                found.append(path)
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stt", action="append", help="speech-to-text command name to look for (repeatable)")
    ap.add_argument("--stt-model", action="append", default=[], help="transcriber model file to report as present or missing (repeatable)")
    ap.add_argument("--key-env", action="append", default=[], help="environment variable to report as set or unset (repeatable)")
    ap.add_argument("--json", help="write the report as JSON to this path")
    args = ap.parse_args()

    report = {"tools": {}, "keys": {}, "models": {}}

    def found(name, path, detail=""):
        report["tools"][name] = {"present": bool(path), "path": path or None, "detail": detail}

    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        found(tool, path, version(tool, "-version") if path else "")
    stt = [s for s in (args.stt or ["whisper-cli", "whisper", "faster-whisper"]) if shutil.which(s)]
    found("speech_to_text", shutil.which(stt[0]) if stt else None, ", ".join(stt))
    node = shutil.which("node")
    node_detail = version("node") if node else ""
    node_major = None
    if node_detail:
        major = re.match(r"v?(\d+)", node_detail.strip())
        node_major = int(major.group(1)) if major else None
    found("node", node, node_detail)
    node_too_old = bool(node) and node_major is not None and node_major < 18
    if node_too_old:
        report["tools"]["node"]["too_old"] = True
    browser = next((shutil.which(b) for b in BROWSERS if shutil.which(b)), None) or next((p for p in BROWSER_APPS if "%" not in p and os.path.exists(p)), None)
    found("browser", browser, "browser found (a sandbox may still block headless launch)" if browser else "")
    local = [v for v in VOICES if shutil.which(v)]
    found("local_voice", shutil.which(local[0]) if local else None, ", ".join(local))
    for name in args.key_env:
        report["keys"][name] = "set" if os.environ.get(name) else "unset"
    for path in args.stt_model:
        report["models"][path] = "present" if os.path.isfile(os.path.expanduser(path)) else "missing"
    candidates = []
    if report["tools"]["speech_to_text"]["present"] and not args.stt_model:
        candidates = model_candidates()
        for path in candidates:
            report["models"][path] = "candidate"

    print("Tool map probe (presence only; nothing was run against a paid service):")
    for name, rec in report["tools"].items():
        print(f"  {name:15} {'yes' if rec['present'] else 'NO '}  {rec['detail']}" + (f"  {rec['path']}" if rec['path'] else ""))
    for name, state in report["keys"].items():
        print(f"  key {name:11} {state}")
    for path, state in report["models"].items():
        if state == "candidate":
            print(f"  stt model candidate  {path}")
        else:
            print(f"  stt model       {state}  {path}")
    if report["tools"]["speech_to_text"]["present"] and not args.stt_model:
        if candidates:
            print("  note: pass one of these as --stt-model <path> to check it")
        else:
            print("  note: a transcriber also needs its model file; pass --stt-model <path> to check it")
    if not report["tools"]["node"]["present"]:
        print("  note: the timing audit needs Node 18 or later")
    elif report["tools"]["node"].get("too_old"):
        found_version = report["tools"]["node"]["detail"].split()[0]
        if not found_version.startswith("v"):
            found_version = "v" + found_version
        print(f"  note: the timing audit needs Node 18 or later; found {found_version}")
    if not report["tools"]["ffmpeg"]["present"]:
        print("  note: beds, joins, checks and export need ffmpeg; ask the owner to install it")
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
            fh.write("\n")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
