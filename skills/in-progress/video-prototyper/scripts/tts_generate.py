#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Generate narration scene by scene for one voice.

One request per scene avoids per-request length limits and dropped endings, allows a
style line per scene, and lets one bad scene be regenerated alone. Output is
<out-dir>/s<N>.wav (16-bit PCM). A scene is skipped on resume only when the s<N>.json
beside it records the same adapter, model (or command), voice id and words hash, and,
when this run sends the scene plain, a plain record; a mismatch is left in place and
counted as failed until --only and --force. A run without --plain-scenes or --plain-all
keeps a scene that was sent plain. A scene file with no record
is kept, with the note "no generation record". The record also says whether the scene was sent plain ("plain"), which voice_batch.py reads.

Adapters:
  command               any local voice tool, run without a shell from a template with
                        {text_file}, {out}, {voice} and {style} placeholders, for example
                        --command "say -v {voice} -o {out} -f {text_file}" --command-ext aiff.
                        Add --paid when the tool costs money (a vendor's CLI, or a short
                        script that reads the key from the environment): the same spend
                        guard as the API adapters then applies.
  gemini-interactions   worked example: an Interactions-style speech endpoint (see
                        references/example-speech-providers.md); needs --model and --key-env
  openai-speech         worked example: an audio/speech endpoint, or any OpenAI-compatible
                        speech endpoint given with --endpoint; needs --model and --key-env.
                        Delivery tags and the -- cue are stripped before sending, because
                        this voice may read them aloud, unless the scene has its own
                        variants["openai-speech"] text.
For another provider, wrap its CLI, or a short script that reads the key from the
environment, in the command adapter with --paid, --ledger, --est-usd-per-request and a
cap; an OpenAI-compatible endpoint works with --adapter openai-speech --endpoint.
API endpoints and model ids are arguments; re-check the vendor's current docs before use.

Usage:
  python3 tts_generate.py --scenes script/scenes.json --voice-id ID --out-dir voices/<voice> \
      --adapter command|gemini-interactions|openai-speech [--model M] [--endpoint URL] \
      [--key-env NAME] [--command TEMPLATE --command-ext wav [--paid]] [--only 1,3] \
      [--plain-scenes 2,5 | --plain-all] [--style-off] [--instructions] [--instructions-file PATH] \
      [--min-interval 7] [--max-retries 4] \
      [--backoff 30] [--max-requests N] [--ledger media/ledger.jsonl --est-usd-per-request X \
      --cap-usd-request X --cap-usd-day Y --cap-usd-project Z] [--force] [--join-audio-parts] \
      [--dry-run [--dry-run-out FILE]]

Audio parts. When a response holds more than one audio part, the scene keeps the last one,
as the vendors' own samples do; --join-audio-parts joins them all instead. Either way the
part count and each part's length are logged, and a scene whose audio runs past about 1.5
times the length its word count predicts at 2.4 words a second gets a warning: listen for
repeated speech.

Spend guard. A live run of an API adapter, or of the command adapter with --paid, needs
--ledger, an explicit --est-usd-per-request (finite, 0 or more; 0 suits a free local
endpoint) and at least one of --cap-usd-request, --cap-usd-day or --cap-usd-project.
Without them it exits 2 before reading any key. Every attempt, retries included, is
reserved in the ledger and counts toward --max-requests.

--dry-run prints every request in full and the estimated list cost (requests x
--est-usd-per-request), checks the caps against the ledger when a ledger or a cap is
given, and checks --max-requests for every adapter (exit 3 when either would stop it).
It reads no key, sends nothing, and creates no folder or ledger line. --dry-run-out FILE
also writes one JSON line per request: scene, endpoint, header names only, and body.
--plain-scenes strips <tags> and the -- cue from the named scenes (use after a tag leak).
Pass --script script/script.txt with --plain-all or --plain-scenes to send that scene's
paragraph of the canonical script instead, so stress CAPS do not reach the plain pass.
Without --script, a plain scene keeps CAPS and the script says so.
--style-off sends an empty style line (plain-first auditions).
--instructions-file PATH is accepted only with --adapter openai-speech. It sends that
file's text as instructions, then a line "Scene: <style>" when the scene has a style
line and --style-off is not set. It implies --instructions. A dry run prints the full
instructions text. With --style-off the body holds the file alone.
The key is read from the environment variable named by --key-env and is never printed,
logged or written. An HTTP error logs the status and reason plus the error's status and
message from the response body (cut to 300 characters, any occurrence of the key value
replaced by <redacted>); the rest of the body and the request headers are never printed.
On macOS with a python.org Python, HTTPS may need SSL_CERT_FILE=/etc/ssl/cert.pem.

Dependencies: Python 3.9 or later, standard library only; ffmpeg when a tool returns a
format other than 16-bit PCM WAV; spend_ledger.py beside this script for paid runs and
for cap checks in a dry run.
Exit codes: 0 every requested scene exists (or the dry run is within caps); 1 a scene
failed; 2 bad arguments, a missing key, a missing spend guard or a malformed ledger;
3 a cap or --max-requests stopped the run (in a dry run: a cap or --max-requests would stop it).
"""
import argparse
import base64
import errno
import http.client
import io
import json
import os
import re
import shlex
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import cue_check  # noqa: E402
DEFAULT_ENDPOINTS = {
    "gemini-interactions": "https://generativelanguage.googleapis.com/v1beta/interactions",
    "openai-speech": "https://api.openai.com/v1/audio/speech",
}


class SameOriginAuth(urllib.request.HTTPRedirectHandler):
    """Follow redirects, sending credentials only within the preceding origin."""
    KEEP = {"accept", "user-agent", "accept-encoding"}

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            a, b = urlsplit(req.full_url), urlsplit(new.full_url)
            if (a.scheme, a.hostname, a.port) != (b.scheme, b.hostname, b.port):
                for collection in (new.headers, new.unredirected_hdrs):
                    for name in list(collection):
                        if name.lower() not in self.KEEP:
                            del collection[name]
        return new


OPENER = urllib.request.build_opener(SameOriginAuth)


def never_sent(err):
    reason = getattr(err, "reason", err)
    if isinstance(reason, (ConnectionRefusedError, socket.gaierror, PermissionError, ssl.SSLError)):
        return True
    return isinstance(reason, OSError) and reason.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH)


def never_sent_report(err):
    """Ledger note, STOP line and log type for a request that never left the machine.
    A TLS failure keeps the not_sent outcome and says so; every other reason keeps the
    sandbox wording."""
    reason = getattr(err, "reason", err)
    if isinstance(reason, ssl.SSLError):
        message = "STOP: the TLS connection failed before the request was sent, so nothing was spent: %s." % reason
        if isinstance(reason, ssl.SSLCertVerificationError):
            message += (' With a python.org Python on macOS, rerun with SSL_CERT_FILE=/etc/ssl/cert.pem'
                        ' or run its Install Certificates command (references/example-local-tools.md,'
                        ' "Worked example: Python HTTPS on macOS"); behind a TLS-inspecting proxy,'
                        ' set SSL_CERT_FILE to the proxy\'s CA bundle.')
        return "not sent: TLS handshake failed", message, type(reason).__name__
    return ("not sent: connection refused, blocked or host not found",
            "STOP: nothing reached the endpoint. A sandbox may block the network; run this step where the network is reachable (see by-hand.md)",
            type(err).__name__)


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


def strip_cues(text):
    text = re.sub(r"\s*<[^>]*>\s*", " ", text)
    text = text.replace("--", " ")
    return re.sub(r"\s+", " ", text).strip()


def read_paragraphs(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read().replace("\r\n", "\n").strip()
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def write_scene_record(out, args, digest, plain=False):
    path = os.path.splitext(out)[0] + ".json"
    rec = {"adapter": args.adapter, "model": args.model or args.command,
           "voice_id": args.voice_id, "words_sha256": digest, "plain": bool(plain)}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
        fh.write("\n")


def http_error_detail(err, key):
    """The error object's status and message from an HTTP error's body (up to 64 KB read),
    cut to 300 characters, with the key value redacted; empty when the body has none."""
    try:
        text = (err.read(65536) or b"").decode("utf-8", errors="replace")
    except (OSError, http.client.HTTPException, ValueError):
        return ""
    if key:
        text = text.replace(key, "<redacted>")
    try:
        doc = json.loads(text) if text.strip() else None
    except ValueError:
        return ""
    err_obj = doc.get("error") if isinstance(doc, dict) else None
    if not isinstance(err_obj, dict):
        return ""
    status = str(err_obj.get("status") or err_obj.get("code") or err_obj.get("type") or "").strip()
    message = str(err_obj.get("message") or "").strip()[:300]
    return " ".join(x for x in (status, message) if x)


def log(out_dir, line):
    print(line, flush=True)
    with open(os.path.join(out_dir, "generate.log"), "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def wav_info(data):
    with wave.open(io.BytesIO(data)) as w:
        return w.getframerate(), w.getnchannels(), w.getsampwidth(), w.readframes(w.getnframes())


def write_wav(path, rate, channels, width, frames):
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(frames)


def convert_to_wav(src, dst):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed to convert this audio to WAV")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-c:a", "pcm_s16le", dst], check=True)


def part_seconds(data, mime):
    """Length of one audio part in seconds, or None when it is not WAV or raw PCM."""
    mime = (mime or "").lower()
    try:
        if data[:4] == b"RIFF":
            rate, ch, width, frames = wav_info(data)
            return len(frames) / float(rate * ch * width)
        if "l16" in mime or "pcm" in mime:
            m = re.search(r"rate=(\d+)", mime)
            return len(data) / float((int(m.group(1)) if m else 24000) * 2)
    except (wave.Error, EOFError, ZeroDivisionError):
        return None
    return None


def save_parts(parts, path, join=False):
    """parts: list of (bytes, mime). Keep the last part, as the vendors' samples do, or with
    join=True (--join-audio-parts) join every part, into one 16-bit WAV."""
    if not join:
        parts = parts[-1:]
    pcm, params = [], None
    simple = True
    for data, mime in parts:
        mime = (mime or "").lower()
        if data[:4] == b"RIFF":
            try:
                rate, ch, width, frames = wav_info(data)
            except (wave.Error, EOFError):
                simple = False
                break
        elif "l16" in mime or "pcm" in mime:
            m = re.search(r"rate=(\d+)", mime)
            rate, ch, width, frames = int(m.group(1)) if m else 24000, 1, 2, data
        else:
            simple = False
            break
        if width != 2 or (params and params != (rate, ch, width)):
            simple = False
            break
        params = (rate, ch, width)
        pcm.append(frames)
    if simple and params:
        write_wav(path, params[0], params[1], params[2], b"".join(pcm))
        return
    tmp = tempfile.mkdtemp()
    try:
        files = []
        for i, (data, mime) in enumerate(parts):
            ext = "mp3" if "mpeg" in (mime or "") or "mp3" in (mime or "") else "bin"
            f = os.path.join(tmp, f"part{i}.{ext}")
            with open(f, "wb") as fh:
                fh.write(data)
            files.append(f)
        if len(files) == 1:
            convert_to_wav(files[0], path)
        else:
            lst = os.path.join(tmp, "list.txt")
            with open(lst, "w") as fh:
                fh.writelines(f"file '{f}'\n" for f in files)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                            "-i", lst, "-c:a", "pcm_s16le", path], check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def find_audio_parts(obj):
    """Collect base64 audio from any steps[].content[] (or nested) item of type audio."""
    found = []

    def visit(node):
        if isinstance(node, dict):
            kind = str(node.get("type", "")).lower()
            mime = node.get("mime_type") or node.get("mimeType") or ""
            if node.get("data") and (kind == "audio" or str(mime).startswith("audio/")):
                found.append((base64.b64decode(node["data"]), mime))
                return
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(obj)
    return found


def build_request(args, text, style, key):
    headers = {"Content-Type": "application/json"}
    if args.adapter == "gemini-interactions":
        content = {"type": "text", "text": text}
        if style:
            content["annotations"] = [{"type": "speech_metadata", "style": style}]
        body = {"model": args.model, "input": [{"type": "user_input", "content": [content]}],
                "response_format": {"type": "audio"},
                "generation_config": {"speech_config": [{"voice": args.voice_id}]}}
        if key:
            headers["x-goog-api-key"] = key
    else:
        if len(text) > 4096:
            raise ValueError("scene text is over 4,096 characters; split the scene")
        body = {"model": args.model, "voice": args.voice_id, "input": text, "response_format": "wav"}
        if args.instructions:
            standing = getattr(args, "instructions_text", "") or ""
            if standing:
                instr = standing
                if style and not args.style_off:
                    instr += "\nScene: " + style
                body["instructions"] = instr
            elif style:
                body["instructions"] = style
        if key:
            headers["Authorization"] = "Bearer " + key
    return body, headers


def call_api(args, text, style, key, response_path=None):
    body, headers = build_request(args, text, style, key)
    req = urllib.request.Request(args.endpoint, data=json.dumps(body).encode("utf-8"), method="POST", headers=headers)
    with OPENER.open(req, timeout=300) as resp:
        ctype = resp.headers.get("Content-Type", "")
        raw = resp.read()
    # Save the received bytes until decoding and conversion succeed.
    if response_path:
        with open(response_path, "wb") as fh:
            fh.write(raw)
    if "json" in ctype:
        doc = json.loads(raw)
        parts = find_audio_parts(doc)
        usage = doc.get("usage") or doc.get("usage_metadata") or doc.get("usageMetadata")
        if not parts:
            raise RuntimeError("the response held no audio part")
        return parts, usage
    return [(raw, ctype)], None


def run_command(args, text, style, out_wav):
    tmp = tempfile.mkdtemp()
    try:
        text_file = os.path.join(tmp, "scene.txt")
        with open(text_file, "w", encoding="utf-8") as fh:
            fh.write(text)
        raw_out = os.path.join(tmp, "out." + args.command_ext)
        values = {"text_file": text_file, "out": raw_out, "voice": args.voice_id, "style": style or ""}
        argv = [part.format(**values) for part in split_cmd(args.command)]
        subprocess.run(argv, check=True, stdout=subprocess.DEVNULL)
        if args.command_ext.lower() == "wav":
            with open(raw_out, "rb") as fh:
                data = fh.read()
            try:
                rate, ch, width, frames = wav_info(data)
                if width == 2:
                    write_wav(out_wav, rate, ch, width, frames)
                    return
            except (wave.Error, EOFError):
                pass
        convert_to_wav(raw_out, out_wav)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def parse_set(value):
    return {int(x) for x in value.split(",") if x.strip()} if value else set()


KEY_HEADERS = {"gemini-interactions": "x-goog-api-key", "openai-speech": "Authorization"}


def finite(value):
    return value == value and value not in (float("inf"), float("-inf"))


def guard_missing(args, est):
    """What a live paid run still needs: a ledger, an explicit estimate and a cap."""
    missing = []
    if not args.ledger:
        missing.append("--ledger")
    if est is None:
        missing.append("--est-usd-per-request (0 for a free endpoint)")
    if all(c is None for c in (args.cap_usd_request, args.cap_usd_day, args.cap_usd_project)):
        missing.append("a cap (--cap-usd-request, --cap-usd-day or --cap-usd-project)")
    return missing


def dry_run(args, jobs, api, guarded, est):
    out_fh = None
    if args.dry_run_out:
        parent = os.path.dirname(os.path.abspath(args.dry_run_out))
        os.makedirs(parent, exist_ok=True)
        out_fh = open(args.dry_run_out, "w", encoding="utf-8")
    try:
        for n, _out, text, style, _digest, _plain in jobs:
            if api:
                try:
                    body, headers = build_request(args, text, style, None)
                except ValueError as err:
                    print(f"FAIL: s{n}: {err}")
                    return 2
                names = sorted(headers) + [KEY_HEADERS[args.adapter]]
                print(f"s{n}: POST {args.endpoint}")
                print("  headers: " + ", ".join(names) + f" (key from ${args.key_env or '<set --key-env>'}, not read)")
                print("  body: " + json.dumps(body, ensure_ascii=False))
                rec = {"scene": n, "endpoint": args.endpoint, "headers": names, "body": body}
            else:
                ext = args.command_ext or "wav"
                values = {"text_file": "<temp text file>", "out": f"<temp out.{ext}>",
                          "voice": args.voice_id, "style": style or ""}
                try:
                    argv = [part.format(**values) for part in split_cmd(args.command)]
                except (KeyError, IndexError, ValueError):
                    argv = split_cmd(args.command)
                print(f"s{n}: " + " ".join(argv))
                print(f"  voice: {args.voice_id}")
                print(f"  style: {style!r}")
                print("  text: " + text)
                rec = {"scene": n, "command": argv, "voice": args.voice_id, "style": style, "text": text}
            if out_fh:
                out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    finally:
        if out_fh:
            out_fh.close()
    count = len(jobs)
    stop = args.max_requests is not None and count > args.max_requests
    print(f"requests: {count}" + (f"; a live run stops at --max-requests {args.max_requests}" if stop else ""))
    if args.dry_run_out:
        print(f"wrote {count} request(s) to {args.dry_run_out}")
    reasons = []
    if guarded:
        if est is None:
            print("estimated list cost: unknown; a live run needs --est-usd-per-request")
        else:
            print(f"estimated list cost: {count} x ${est:g} = ${count * est:.4f} before credits; each retry adds one request")
        if est is not None and (args.ledger or any(c is not None for c in (args.cap_usd_request, args.cap_usd_day, args.cap_usd_project))):
            sys.path.insert(0, HERE)
            sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
            import spend_ledger  # noqa: E402
            try:
                rows = spend_ledger.read(args.ledger) if args.ledger else []
            except spend_ledger.LedgerError as err:
                print(f"FAIL: {err}")
                return 2
            day = spend_ledger.utc_now().date().isoformat()
            reasons = (spend_ledger.check_caps(est, rows, day, args.cap_usd_request, None, None)
                       + spend_ledger.check_caps(round(count * est, 6), rows, day, None, args.cap_usd_day, args.cap_usd_project))
            today, project = spend_ledger.totals(rows, day)
            print(f"ledger: today ${today:.4f}, project ${project:.4f}" + (f"; caps would REFUSE: {'; '.join(reasons)}" if reasons else "; within caps"))
        missing = guard_missing(args, est)
        if missing:
            print("NOTE: a live run would stop until it has " + ", ".join(missing))
    if reasons:
        print("REFUSED (dry run): raise a cap only with the owner's explicit yes")
        return 3
    if stop:
        print(f"STOP (dry run): {count} requests are more than --max-requests {args.max_requests}; "
              "a live run stops part way. Raise it only with the owner's yes")
        return 3
    if guarded:
        print("next: the owner's yes for this batch and its cap, then run again without --dry-run")
    print("done (dry run, nothing sent)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--voice-id", required=True, help="the provider's voice id, or the local tool's voice name")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--adapter", required=True, choices=["command", "gemini-interactions", "openai-speech"])
    ap.add_argument("--model")
    ap.add_argument("--endpoint")
    ap.add_argument("--key-env", help="name of the environment variable holding the key")
    ap.add_argument("--instructions", action="store_true", help="openai-speech: send the style line as instructions (only some models accept it)")
    ap.add_argument("--instructions-file", help="openai-speech only: standing instructions text; implies --instructions and is followed by Scene: <style>")
    ap.add_argument("--command")
    ap.add_argument("--command-ext", default="wav")
    ap.add_argument("--paid", action="store_true", help="command adapter: the tool costs money; apply the ledger, estimate, cap and --max-requests rules")
    ap.add_argument("--only")
    ap.add_argument("--plain-scenes")
    ap.add_argument("--plain-all", action="store_true")
    ap.add_argument("--script", help="canonical script.txt; a plain scene sends paragraph N instead of the cued text")
    ap.add_argument("--style-off", action="store_true")
    ap.add_argument("--min-interval", type=float, default=0.0, help="seconds between requests (60 / the per-minute limit, plus about 1)")
    ap.add_argument("--max-retries", type=int, default=4)
    ap.add_argument("--backoff", type=float, default=30.0)
    ap.add_argument("--max-requests", type=int, help="cap on attempts, retries included")
    ap.add_argument("--ledger")
    ap.add_argument("--est-usd-per-request", type=float, default=None, help="list-price estimate per request; required for a live paid run")
    ap.add_argument("--cap-usd-request", type=float)
    ap.add_argument("--cap-usd-day", type=float)
    ap.add_argument("--cap-usd-project", type=float)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--join-audio-parts", action="store_true", help="join every audio part of a response (default: keep the last, as the vendors' samples do)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dry-run-out", help="with --dry-run: write one JSON line per request to this file")
    args = ap.parse_args()

    api = args.adapter != "command"
    guarded = api or args.paid
    if api and not args.model:
        ap.error("API adapters need --model")
    if api and not args.dry_run and not args.key_env:
        ap.error("API adapters need --key-env (the variable name, never the key)")
    if args.adapter == "command" and not args.command:
        ap.error("the command adapter needs --command")
    if args.instructions_file and args.adapter != "openai-speech":
        ap.error("--instructions-file is accepted only with --adapter openai-speech")
    args.instructions_text = ""
    if args.instructions_file:
        args.instructions = True
        try:
            with open(args.instructions_file, encoding="utf-8") as fh:
                args.instructions_text = fh.read().strip()
        except OSError as err:
            print(f"FAIL: cannot read --instructions-file ({err.strerror})")
            return 2
    if args.dry_run_out and not args.dry_run:
        ap.error("--dry-run-out needs --dry-run")
    est = args.est_usd_per_request
    if est is not None and (not finite(est) or est < 0):
        print("FAIL: --est-usd-per-request must be a finite number of 0 or more")
        return 2
    for name in ("cap_usd_request", "cap_usd_day", "cap_usd_project"):
        value = getattr(args, name)
        if value is not None and (not finite(value) or value < 0):
            print(f"FAIL: --{name.replace('_', '-')} must be a finite number of 0 or more")
            return 2
    args.endpoint = args.endpoint or DEFAULT_ENDPOINTS.get(args.adapter)

    with open(args.scenes, encoding="utf-8") as fh:
        scenes = json.load(fh)["scenes"]
    only, plain = parse_set(args.only), parse_set(args.plain_scenes)

    paragraphs = read_paragraphs(args.script) if args.script else []
    if (args.plain_all or plain) and not args.script:
        print("NOTE: plain scenes keep CAPS stress; pass --script for the canonical words")
    jobs, stale = [], []
    for scene in scenes:
        n = int(scene["n"])
        if only and n not in only:
            continue
        out = os.path.join(args.out_dir, f"s{n}.wav")
        variants = scene.get("variants") or {}
        text = variants.get(args.adapter) or scene["text_cued"]
        own_variant = bool(variants.get(args.adapter))
        digest = cue_check.words_sha256(scene.get("text_cued") or "")
        is_plain = args.plain_all or n in plain
        if is_plain and args.script:
            if 1 <= n <= len(paragraphs):
                text = paragraphs[n - 1]
            else:
                text = strip_cues(text)
                print(f"NOTE: script.txt has no paragraph for scene {n}; this plain scene keeps the cued words with tags removed")
        elif (is_plain or args.adapter == "command" or (args.adapter == "openai-speech" and not own_variant)):
            text = strip_cues(text)
        if os.path.exists(out) and not args.force:
            rec_path = os.path.splitext(out)[0] + ".json"
            if not os.path.exists(rec_path):
                print(f"s{n}: exists, skipped (no generation record)")
                continue
            try:
                with open(rec_path, encoding="utf-8") as fh:
                    rec = json.load(fh)
            except (OSError, ValueError):
                rec = {}
            model = args.model or args.command
            if (rec.get("adapter") == args.adapter and rec.get("model") == model
                    and rec.get("voice_id") == args.voice_id and rec.get("words_sha256") == digest):
                if is_plain and not rec.get("plain"):
                    print(f"s{n}: exists but was sent with its delivery cues; to send it plain, rerun with --only {n} --force "
                          "and the same --plain-scenes or --plain-all (dry run and the owner's yes first for a paid voice)")
                    stale.append(n)
                    continue
                print(f"s{n}: exists, skipped")
                continue
            print(f"s{n}: exists but was made from other words, voice or model; rerun with --only {n} --force "
                  "(dry run and the owner's yes first for a paid voice)")
            stale.append(n)
            continue
        style = "" if args.style_off else (scene.get("style") or "")
        jobs.append((n, out, text, style, digest, is_plain))

    if args.dry_run:
        code = dry_run(args, jobs, api, guarded, est)
        if stale and code == 0:
            print("FAILED scenes: " + ",".join(str(n) for n in stale))
            return 1
        return code

    if guarded:
        missing = guard_missing(args, est)
        if missing:
            print("FAIL: a live paid run needs " + ", ".join(missing)
                  + ". Dry-run first, then get the owner's yes for the batch and its cap.")
            return 2
        import spend_ledger  # noqa: E402
        try:
            spend_ledger.read(args.ledger)
        except spend_ledger.LedgerError as err:
            print(f"FAIL: {err}")
            return 2
    key = None
    if api:
        key = os.environ.get(args.key_env)
        if not key:
            print(f"FAIL: environment variable {args.key_env} is not set. Ask the owner to place the key; never type it.")
            return 2
    os.makedirs(args.out_dir, exist_ok=True)
    ledger = None
    if guarded:
        sys.path.insert(0, HERE)
        sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
        import spend_ledger as ledger  # noqa: E402

    requests_made, failed = 0, list(stale)
    for n, out, text, style, digest, plain in jobs:
        attempt = 0
        while True:
            if args.max_requests is not None and requests_made >= args.max_requests:
                print(f"STOP: reached --max-requests {args.max_requests} (retries count)")
                return 3
            if api:
                try:
                    build_request(args, text, style, key)
                except ValueError as err:
                    print(f"FAIL: s{n}: {err}")
                    return 2
            reservation = None
            if ledger:
                try:
                    reservation = ledger.reserve(args.ledger, {"tool": "tts_generate", "kind": "speech",
                                                               "model": args.model or args.command,
                                                               "units": 1, "unit": "request", "est_usd": est,
                                                               "note": f"{args.voice_id} s{n}"},
                                                 args.cap_usd_request, args.cap_usd_day, args.cap_usd_project)
                except ledger.LedgerError as err:
                    print(f"STOP: {err}")
                    return 3
            requests_made += 1
            if args.adapter == "command":
                try:
                    run_command(args, text, style, out)
                    wav_info(open(out, "rb").read())
                    if ledger:
                        ledger.outcome(args.ledger, reservation, "completed")
                    write_scene_record(out, args, digest, plain)
                    log(args.out_dir, f"s{n}: {os.path.getsize(out)} bytes via command")
                except (subprocess.CalledProcessError, RuntimeError, OSError, wave.Error, EOFError) as err:
                    if ledger:
                        ledger.outcome(args.ledger, reservation, "failed")
                    log(args.out_dir, f"s{n}: command failed ({type(err).__name__})")
                    failed.append(n)
                break
            try:
                response_path = os.path.join(args.out_dir, f"s{n}.response.bin")
                parts, usage = call_api(args, text, style, key, response_path=response_path)
                save_parts(parts, out, join=args.join_audio_parts)
                if ledger:
                    ledger.outcome(args.ledger, reservation, "completed")
                write_scene_record(out, args, digest, plain)
                rate, ch, width, frames = wav_info(open(out, "rb").read())
                seconds = len(frames) / float(rate * ch * width)
                os.remove(response_path)
                log(args.out_dir, f"s{n}: {os.path.getsize(out)} bytes, {seconds:.2f} s, {len(parts)} part(s), usage {json.dumps(usage)[:200] if usage else 'n/a'}")
                if len(parts) > 1:
                    lengths = ", ".join("?" if x is None else f"{x:.2f} s" for x in (part_seconds(d, m) for d, m in parts))
                    log(args.out_dir, f"s{n}: the response held {len(parts)} audio parts ({lengths}); "
                        + ("joined them all" if args.join_audio_parts else "kept the last; pass --join-audio-parts to join them"))
                expected = len(cue_check.norm_words(text)) / 2.4
                if expected > 0 and seconds > 1.5 * expected:
                    log(args.out_dir, f"s{n}: WARNING {seconds:.1f} s is over 1.5 times the {expected:.1f} s its words predict at 2.4 words a second; listen for repeated speech")
                break
            except urllib.error.HTTPError as err:
                if ledger:
                    ledger.outcome(args.ledger, reservation, "failed", http=err.code)
                detail = http_error_detail(err, key)
                log(args.out_dir, f"s{n}: HTTP {err.code} {err.reason}" + (f": {detail}" if detail else ""))
                if err.code in (429, 500, 503) and attempt < args.max_retries:
                    attempt += 1
                    wait = args.backoff * attempt
                    print(f"s{n}: retry {attempt} of {args.max_retries} in {wait:.0f} s")
                    time.sleep(wait)
                    continue
                failed.append(n)
                break
            except urllib.error.URLError as err:
                if never_sent(err):
                    note, message, logged = never_sent_report(err)
                    if ledger:
                        ledger.outcome(args.ledger, reservation, "not_sent", note=note)
                    log(args.out_dir, f"s{n}: not_sent ({logged})")
                    print(message)
                    return 1
                if ledger:
                    ledger.outcome(args.ledger, reservation, "uncertain")
                log(args.out_dir, f"s{n}: failed ({type(err).__name__})")
                failed.append(n)
                break
            except (RuntimeError, ValueError, OSError, wave.Error, EOFError,
                    subprocess.CalledProcessError, http.client.HTTPException) as err:
                if ledger:
                    ledger.outcome(args.ledger, reservation, "uncertain")
                log(args.out_dir, f"s{n}: failed ({type(err).__name__})")
                if isinstance(err, http.client.IncompleteRead) and err.partial:
                    with open(response_path, "wb") as fh:
                        fh.write(err.partial)
                if os.path.exists(response_path):
                    if os.path.exists(out):
                        os.remove(out)  # do not mistake a partial conversion for a finished scene
                    log(args.out_dir, f"s{n}: saved the raw response; convert it by hand ({response_path})")
                failed.append(n)
                break
        if args.min_interval:
            time.sleep(args.min_interval)

    if failed:
        print("FAILED scenes: " + ",".join(str(n) for n in failed))
        return 1
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
