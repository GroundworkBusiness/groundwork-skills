#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""One guarded paid generation call (image, clip, music or speech) to any JSON API.

Dry run first: --dry-run prints the request (long strings shortened), the estimated list
cost and the ledger totals, reads no key, sends nothing and writes nothing. A live call
checks the caps, reserves the estimate in the shared spend ledger under a lock, sends one
request (no automatic retries: a retried generation can bill twice), decodes every
base64 media part of the wanted types, downloads at once every part the vendor returns as
a link (uri, url, fileUri or file_uri; large results often come this way), saves the files
at once (servers delete them), and appends a generation record, with the operation id, to
the media log. A link is fetched with the key header only when its host is the
endpoint's own host; a redirect to any other host or scheme is followed without the key;
the key never goes into a URL. When a link cannot be downloaded the
reservation stays "uncertain" and the operation id is printed, so --poll can fetch the
result again without a new generation.

An existing <name>-<number>.<extension> in --out-dir refuses the name before reading the
key or reserving spend, even for a dry run or poll; pass a new --name or --out-dir.
Files use exclusive creation; a racing save keeps the paid bytes under a UTC-dated name.

A linked file that is not ready yet: when a link's download comes back as JSON, or with a
Content-Type that is not media (its top-level type is not in --types; an empty or
application/octet-stream type counts as media and is saved with the assumed type), the
body is saved as <out-dir>/<name>-link-response.json (or another extension for a non-JSON
body), any "state" it reports is printed, nothing is saved as media, the reservation stays
"uncertain", and the script exits 4 when the state is PROCESSING (else 1). --wait-file
waits instead: for a link of the form .../files/<id>:download?alt=media it reads
.../files/<id> (the key header only to the API's own host) every 5 s until its state is
ACTIVE, then downloads; FAILED keeps the reservation uncertain and exits 1; after
--wait-timeout seconds (default 600) it keeps the reservation uncertain, prints the
operation id and exits 4. A saved file's MIME comes from the download's Content-Type when
that is a media type.

Long-running jobs: when the response is an operation still running, the script prints its
name. Fetch it later with --poll URL (no new reservation); the result is decoded the same way. Pass the start call's --body, --prompt-field, --units, --unit, --unit-usd and --price-basis to --poll as well: they fill the generation record only, nothing is sent from them, and nothing new is reserved. A polled record's ledger_id stays empty; its operation id matches the start call's ledger line.

Usage:
  python3 api_media.py --endpoint URL --body request.json --name ID --out-dir media/generated \\
      --key-env NAME --auth bearer|header:<header name> \\
      --kind image|video|music|speech --units N --unit-usd PRICE --price-basis "list price, date, source" \\
      --ledger media/ledger.jsonl [--cap-usd-request X] [--cap-usd-day Y] [--cap-usd-project Z] (at least one cap) \\
      [--types audio,image,video] [--log media/media-log.jsonl] [--watermark "..."] \\
      [--wait-file [--wait-timeout 600]] [--dry-run]
  python3 api_media.py --poll URL --key-env NAME --auth bearer|header:<header name> --name ID --out-dir ... --log ... [--wait-file] [--body request.json --prompt-field PATH --units N --unit U --unit-usd PRICE --price-basis "..."]

The key is read from the environment variable named by --key-env, sent only in a header,
and never printed, logged or written. An HTTP error prints the status and reason plus the
error's status and message from the response body (cut to 300 characters), and saves the
body as <out-dir>/<name>-error.json, with any occurrence of the key value replaced by
<redacted>; request headers are never printed. The next line says what to do for each kind
of error.
A live call needs --ledger, an explicit --unit-usd (finite, 0 or more; 0 suits a free
endpoint) and at least one of --cap-usd-request, --cap-usd-day or --cap-usd-project;
without them it exits 2 before reading the key. The dry run says which are missing.
Prices come from the vendor's current price page; the estimate is list price before credits.

Dependencies: Python 3.9 or later, standard library only; spend_ledger.py beside this
script; ffprobe (optional) to record duration, resolution and audio of saved files.
Exit codes: 0 saved (or dry run within caps); 1 request failed, a linked result could not
be downloaded, or a linked file reports FAILED or a state other than PROCESSING; 2 bad
arguments, an existing name, a missing key or a malformed ledger; 3 a cap refused the request (also in a dry run); 4 the operation
is still running, or a linked file is still PROCESSING (or --wait-file timed out).
"""
import argparse
import base64
import datetime
import errno
import http.client
import json
import math
import mimetypes
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
import spend_ledger  # noqa: E402


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
    """Ledger note and STOP line for a request that never left the machine.
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
        return "not sent: TLS handshake failed", message
    return ("not sent: connection refused, blocked or host not found",
            "STOP: nothing reached the endpoint. A sandbox may block the network; run this step where the network is reachable (see by-hand.md)")


def shorten(obj, limit=160):
    if isinstance(obj, dict):
        return {k: shorten(v, limit) for k, v in obj.items()}
    if isinstance(obj, list):
        return [shorten(v, limit) for v in obj]
    if isinstance(obj, str) and len(obj) > limit:
        return obj[:limit] + f"... ({len(obj)} characters)"
    return obj


DEFAULT_MIME = {"image": "image/png", "audio": "audio/mpeg", "video": "video/mp4"}
LINK_KEYS = ("uri", "url", "fileUri", "file_uri")
FILE_LINK = re.compile(r"^(https?://[^?#]*/files/[^/:?#]+):download(?:[?#].*)?$")
WAIT_INTERVAL = 5.0


def media_parts(doc, types, media_kind=None):
    """Return parts of the wanted types: {"data": bytes, "mime": ...} for inline base64, or
    {"link": url, "mime": ...} for a result the vendor returns as a link. A part's kind is
    its type field, else its MIME type, else the key it sits under (for example "video").
    A step whose type is thought holds interim images that are not saved unless no wanted part exists outside those steps, in which case the last one is kept, marked from_thought and announced."""
    found = []
    thought_parts = []

    def take_part(node, parent, sink):
        if not isinstance(node, dict):
            return False
        mime = node.get("mime_type") or node.get("mimeType") or ""
        kind = str(node.get("type") or parent).lower()
        wanted = kind in types or mime.split("/")[0] in types
        requested = {"music": "audio", "speech": "audio"}.get(media_kind, media_kind)
        if ("b64_json" in node or "bytesBase64Encoded" in node) and requested in types:
            wanted = True
            kind = requested
        data = node.get("data") or node.get("bytesBase64Encoded") or node.get("b64_json")
        if isinstance(data, str) and data and wanted:
            sink.append({"data": base64.b64decode(data), "mime": mime or DEFAULT_MIME.get(kind, "")})
            return True
        link = next((node[k] for k in LINK_KEYS if isinstance(node.get(k), str) and node[k].startswith(("https://", "http://"))), None)
        if link and wanted:
            sink.append({"link": link, "mime": mime or DEFAULT_MIME.get(kind, "")})
            return True
        return False

    def walk(node, parent, sink, skip_thought):
        if isinstance(node, dict):
            if skip_thought and str(node.get("type") or "").lower() == "thought":
                walk(node, parent, thought_parts, False)
                return
            if take_part(node, parent, sink):
                return
            for key, value in node.items():
                walk(value, key, sink, skip_thought)
        elif isinstance(node, list):
            for value in node:
                walk(value, parent, sink, skip_thought)

    walk(doc, "", found, True)
    skipped = len(thought_parts)
    if not found and thought_parts:
        found = [thought_parts[-1]]
        found[0]["from_thought"] = True
        print("kept the last thought image as the result: the response held no image outside thought steps")
        skipped -= 1
    if skipped:
        print(f"skipped {skipped} interim thought image(s)")
    return found


def download(link, api_url, key, auth):
    """Fetch a linked result. The key header goes only to the API's own host, over HTTPS."""
    a, b = urlsplit(link), urlsplit(api_url)
    headers = {}
    if key and a.scheme == "https" and a.hostname and (a.scheme, a.hostname, a.port) == (b.scheme, b.hostname, b.port):
        if auth == "bearer":
            headers["Authorization"] = "Bearer " + key
        else:
            headers[auth.split(":", 1)[1]] = key
    req = urllib.request.Request(link, method="GET", headers=headers)
    with OPENER.open(req, timeout=600) as resp:
        return resp.headers.get("Content-Type", ""), resp.read()


def file_state(doc):
    """The state a file resource or a not-ready link reports, upper-cased, or None."""
    if not isinstance(doc, dict):
        return None
    state = doc.get("state")
    if state is None and isinstance(doc.get("file"), dict):
        state = doc["file"].get("state")
    return str(state).upper() if state is not None else None


def link_body(got_type, data, types):
    """Decide whether a downloaded link body is media. Returns (doc, mime): doc is the parsed
    JSON (or {} for a non-media body) when the file is not ready; mime is the media type to
    record (from the Content-Type when it is a media type, else None for the assumed one)."""
    ctype = (got_type or "").split(";")[0].strip().lower()
    if data[:64].lstrip()[:1] in (b"{", b"["):
        try:
            doc = json.loads(data.decode("utf-8"))
            return (doc if isinstance(doc, dict) else {"body": doc}), None
        except (UnicodeDecodeError, ValueError):
            pass
    top = ctype.split("/")[0]
    if top in types:
        return None, ctype
    if ctype in ("", "application/octet-stream", "binary/octet-stream"):
        return None, None
    return {}, None


def wait_for_file(link, api_url, key, auth, timeout):
    """Poll .../files/<id> until ACTIVE or FAILED. Returns (state, last doc); state TIMEOUT
    when time runs out, or SKIP when the link is not a files download link."""
    m = FILE_LINK.match(link)
    if not m:
        return "SKIP", None
    resource = m.group(1)
    deadline = time.monotonic() + timeout
    while True:
        _ctype, raw = download(resource, api_url, key, auth)
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            doc = None
        state = file_state(doc)
        if state in ("ACTIVE", "FAILED"):
            return state, doc
        if time.monotonic() + WAIT_INTERVAL > deadline:
            return "TIMEOUT", doc
        print(f"linked file {resource.rsplit('/', 1)[-1]}: {state or 'no state reported'}; checking again in {WAIT_INTERVAL:g} s")
        time.sleep(WAIT_INTERVAL)


def probe(path):
    if not shutil.which("ffprobe"):
        return {}
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                              "-of", "json", path], capture_output=True, text=True, check=True).stdout
        info = json.loads(out)
    except (subprocess.CalledProcessError, ValueError):
        return {}
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    rec = {"has_audio": any(s.get("codec_type") == "audio" for s in streams)}
    if info.get("format", {}).get("duration"):
        rec["duration_s"] = round(float(info["format"]["duration"]), 3)
    if video and video.get("width"):
        rec["resolution"] = f"{video['width']}x{video['height']}"
    return rec


def send(url, key, auth, body=None):
    headers = {"Content-Type": "application/json"}
    if auth == "bearer":
        headers["Authorization"] = "Bearer " + key
    else:
        headers[auth.split(":", 1)[1]] = key
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET", headers=headers)
    with OPENER.open(req, timeout=600) as resp:
        ctype = resp.headers.get("Content-Type", "")
        raw = resp.read()
    return ctype, raw


def requested_model(body, endpoint):
    """The model id from the body, or from an endpoint path such as .../models/<id>:predictLongRunning."""
    if isinstance(body, dict) and body.get("model"):
        return body["model"]
    m = re.search(r"/models/([^/:?]+)", endpoint or "")
    return m.group(1) if m else None


def field_at(body, path):
    """Value at a dotted path with list indexes, such as instances.0.prompt."""
    cur = body
    if not path:
        return None
    for part in str(path).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit():
            idx = int(part)
            if idx < 0 or idx >= len(cur):
                return None
            cur = cur[idx]
        else:
            return None
    return cur


def prompt_text(body, path):
    value = field_at(body, path) if body is not None else None
    return value if isinstance(value, str) else None


def http_error_report(err, key):
    """Read up to 64 KB of an HTTP error's body, redact the key value, and return
    (redacted text, one-line summary). The summary is the error object's status and message
    when the body is JSON with an "error" object, else the first 300 characters of the text."""
    try:
        raw = err.read(65536) or b""
    except (OSError, http.client.HTTPException, ValueError):
        raw = b""
    text = raw.decode("utf-8", errors="replace")
    if key:
        text = text.replace(key, "<redacted>")
    summary = ""
    try:
        doc = json.loads(text) if text.strip() else None
    except ValueError:
        doc = None
    err_obj = doc.get("error") if isinstance(doc, dict) else None
    if isinstance(err_obj, dict):
        status = str(err_obj.get("status") or err_obj.get("code") or err_obj.get("type") or "").strip()
        message = str(err_obj.get("message") or "").strip()[:300]
        summary = " ".join(x for x in (status, message) if x)
    elif text.strip():
        summary = " ".join(text.split())[:300]
    return text, summary


def http_error_guidance(reserved):
    """What to do next after an HTTP error; the reader matches it to the message above."""
    advice = ("A 4xx whose message names a field or value: fix the body and dry-run again. "
              "A 429: wait and run again later. "
              "A 400, 500 or 503 with no reason may be transient: one resend under a new reservation, "
              "within the owner's cap, is reasonable.")
    if reserved:
        advice += " The failed reservation stays in the ledger as possibly billed; check billing the next day."
    return advice


def guard_missing(args):
    """What a live paid call still needs: a ledger, an explicit price and a cap."""
    missing = []
    if not args.ledger:
        missing.append("--ledger")
    if args.unit_usd is None:
        missing.append("--unit-usd (0 for a free endpoint)")
    if all(c is None for c in (args.cap_usd_request, args.cap_usd_day, args.cap_usd_project)):
        missing.append("a cap (--cap-usd-request, --cap-usd-day or --cap-usd-project)")
    return missing


def save(parts, args):
    os.makedirs(args.out_dir, exist_ok=True)
    saved = []
    for i, (data, mime) in enumerate(parts, start=1):
        base = (mime or "").split(";")[0].strip().lower()
        ext = ".wav" if base in ("audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave") else (mimetypes.guess_extension(base) if base else None)
        ext = {".mpga": ".mp3", ".jpe": ".jpg"}.get(ext, ext) or ".bin"
        path = os.path.join(args.out_dir, f"{args.name}-{i}{ext}")
        original = path
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        collision = 0
        while True:
            try:
                with open(path, "xb") as fh:
                    fh.write(data)
                break
            except FileExistsError:
                collision += 1
                suffix = "" if collision == 1 else f"-{collision}"
                path = os.path.splitext(original)[0] + f"-{stamp}{suffix}{ext}"
        saved.append((path, mime, len(data)))
        print(f"saved {path} ({len(data)} bytes, {mime or 'unknown type'}); check the real type with a file-type tool")
    return saved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint")
    ap.add_argument("--body")
    ap.add_argument("--poll")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--key-env")
    ap.add_argument("--auth", help="how the key is sent: bearer, or header:<header name> (from the vendor's docs)")
    ap.add_argument("--kind", default="other", choices=["image", "video", "music", "speech", "other"])
    ap.add_argument("--units", type=float, default=1.0)
    ap.add_argument("--unit", default="request")
    ap.add_argument("--unit-usd", type=float, default=None, help="list price per unit from the vendor's price page; required for a live call (0 for a free endpoint)")
    ap.add_argument("--price-basis", default="unstated")
    ap.add_argument("--ledger")
    ap.add_argument("--cap-usd-request", type=float)
    ap.add_argument("--cap-usd-day", type=float)
    ap.add_argument("--cap-usd-project", type=float)
    ap.add_argument("--types", default="audio,image,video")
    ap.add_argument("--log")
    ap.add_argument("--watermark")
    ap.add_argument("--prompt-field", default="prompt", help="body field holding the prompt, for the log; a dotted path with list indexes is allowed, such as instances.0.prompt")
    ap.add_argument("--wait-file", action="store_true", help="wait for a linked .../files/<id> result to be ACTIVE before downloading it")
    ap.add_argument("--wait-timeout", type=float, default=600.0, help="seconds --wait-file waits (default 600)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.poll and args.dry_run:
        ap.error("--dry-run does not apply to --poll: a poll sends one GET with the key and starts no generation; run it without --dry-run")
    existing = re.compile(r"^" + re.escape(args.name) + r"-\d+\.[A-Za-z0-9]+$")
    if os.path.isdir(args.out_dir):
        for filename in sorted(os.listdir(args.out_dir)):
            path = os.path.join(args.out_dir, filename)
            if existing.fullmatch(filename) and os.path.isfile(path):
                print(f"FAIL: {path} already exists; pass a new --name or --out-dir (a new generation never replaces an earlier one)")
                return 2
    for name in ("units", "unit_usd", "cap_usd_request", "cap_usd_day", "cap_usd_project"):
        value = getattr(args, name)
        if value is not None and (not math.isfinite(value) or value < 0):
            print(f"FAIL: --{name.replace('_', '-')} must be a finite number of 0 or more")
            return 2
    types = {t.strip() for t in args.types.split(",") if t.strip()}
    est = round(args.units * (args.unit_usd if args.unit_usd is not None else 0.0), 6)

    if args.poll:
        if not args.key_env or not os.environ.get(args.key_env):
            print("FAIL: --poll needs --key-env naming a set variable")
            return 2
        body = None
        if args.body:  # the start request, read for the generation record only; nothing is sent from it
            with open(args.body, encoding="utf-8") as fh:
                body = json.load(fh)
    else:
        if not args.endpoint or not args.body:
            ap.error("give --endpoint and --body (or --poll)")
        with open(args.body, encoding="utf-8") as fh:
            body = json.load(fh)
        if est != est or est in (float("inf"), float("-inf")) or est < 0:
            print("FAIL: the estimate is not a finite, non-negative number")
            return 2
        try:
            rows = spend_ledger.read(args.ledger) if args.ledger else []
        except spend_ledger.LedgerError as err:
            print(f"FAIL: {err}")
            return 2
        day = spend_ledger.utc_now().date().isoformat()
        reasons = spend_ledger.check_caps(est, rows, day, args.cap_usd_request, args.cap_usd_day, args.cap_usd_project)
        if args.dry_run:
            today, project = spend_ledger.totals(rows, day)
            print(f"DRY RUN: POST {args.endpoint}")
            print(f"  auth: {args.auth or '<set --auth>'} from ${args.key_env or '<set --key-env>'} (not read)")
            print("  body: " + json.dumps(shorten(body), ensure_ascii=False))
            print(f"  estimate: {args.units:g} {args.unit}(s) x ${'<set --unit-usd>' if args.unit_usd is None else args.unit_usd} = ${est:.4f} list, before credits ({args.price_basis})")
            print(f"  ledger: today ${today:.4f}, project ${project:.4f}" + (f"; caps would REFUSE: {'; '.join(reasons)}" if reasons else "; within caps"))
            missing = guard_missing(args)
            if missing:
                print("  NOTE: a live call would stop until it has " + ", ".join(missing))
            print("  next: lower --units or ask the owner to raise the cap (their explicit yes)" if reasons else "  next: the owner's yes for this request, then run again without --dry-run")
            return 3 if reasons else 0
        if reasons:
            print("REFUSED: " + "; ".join(reasons))
            return 3
        missing = guard_missing(args)
        if missing:
            print("FAIL: a live call needs " + ", ".join(missing) + ". Dry-run first, then get the owner's yes for the request and its cap.")
            return 2
        if not args.key_env:
            print("FAIL: --key-env is required for a live call (the variable name, never the key)")
            return 2
        if not os.environ.get(args.key_env):
            print(f"FAIL: {args.key_env} is not set. Ask the owner to place the key.")
            return 2
    if not args.auth or not (args.auth == "bearer" or args.auth.startswith("header:")):
        print("FAIL: --auth must be bearer or header:<header name>")
        return 2

    key = os.environ[args.key_env]
    reservation = None
    if not args.poll:
        try:
            reservation = spend_ledger.reserve(args.ledger, {"tool": "api_media", "kind": args.kind, "model": requested_model(body, args.endpoint),
                                                             "units": args.units, "unit": args.unit, "est_usd": est,
                                                             "note": args.name, "price_basis": args.price_basis},
                                               args.cap_usd_request, args.cap_usd_day, args.cap_usd_project)
        except spend_ledger.LedgerError as err:
            print(f"REFUSED: {err}")
            return 3
    try:
        ctype, raw = send(args.poll or args.endpoint, key, args.auth, None if args.poll else body)
    except urllib.error.HTTPError as err:
        if reservation:
            spend_ledger.outcome(args.ledger, reservation, "failed", http=err.code)
        body_text, summary = http_error_report(err, key)
        saved_note = ""
        if body_text:
            os.makedirs(args.out_dir, exist_ok=True)
            error_path = os.path.join(args.out_dir, f"{args.name}-error.json")
            with open(error_path, "w", encoding="utf-8") as fh:
                fh.write(body_text if body_text.endswith("\n") else body_text + "\n")
            saved_note = f" Saved the response body to {error_path}."
        print(f"FAIL: HTTP {err.code} {err.reason}" + (f": {summary}" if summary else " (no reason in the response body)")
              + "." + saved_note)
        print(http_error_guidance(bool(reservation)))
        return 1
    except (urllib.error.URLError, OSError, http.client.HTTPException) as err:
        if never_sent(err):
            note, message = never_sent_report(err)
            if reservation:
                spend_ledger.outcome(args.ledger, reservation, "not_sent", note=note)
            print(message)
            return 1
        if reservation:
            spend_ledger.outcome(args.ledger, reservation, "uncertain")
        print(f"FAIL: {type(err).__name__}; the request may have billed. Check billing before trying again.")
        return 1

    doc = None
    if "json" in ctype:
        doc = json.loads(raw)
        parts = media_parts(doc, types, args.kind)
    else:
        parts = [{"data": raw, "mime": ctype}] if ctype.split("/")[0] in types else []
    reported = doc.get("model") if isinstance(doc, dict) else None
    op_id = (doc.get("name") or doc.get("id")) if isinstance(doc, dict) else None
    if not parts:
        err_obj = doc.get("error") if isinstance(doc, dict) and isinstance(doc.get("error"), dict) else None
        done_flag = doc.get("done") if isinstance(doc, dict) else None
        operation_error = err_obj is not None and (done_flag is True or "done" not in doc)
        running = isinstance(doc, dict) and not doc.get("error") and (
            doc.get("done") is False
            or ("done" not in doc and "/operations/" in str(doc.get("name", "")))
            or str(doc.get("status", "")).lower() in ("running", "pending", "in_progress"))
        if operation_error:
            if reservation:
                spend_ledger.outcome(args.ledger, reservation, "failed", operation=op_id)
            os.makedirs(args.out_dir, exist_ok=True)
            response_path = os.path.join(args.out_dir, f"{args.name}-response.json")
            with open(response_path, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            print(f"FAIL: operation error {err_obj.get('code', '')} {err_obj.get('status', '')}")
            return 1
        if reservation:
            spend_ledger.outcome(args.ledger, reservation, "pending" if running else "uncertain", operation=op_id)
        if running:
            print(f"RUNNING: operation {op_id}. Fetch it later with --poll <the vendor's URL for this operation, often the API base URL followed by this name> (no new reservation).")
            endpoint = args.endpoint or ""
            if "/models/" in endpoint and op_id:
                prefix = endpoint.split("/models/", 1)[0]
                print(f"For example: --poll {prefix}/{op_id}")
            return 4
        if doc is not None:
            os.makedirs(args.out_dir, exist_ok=True)
            response_path = os.path.join(args.out_dir, f"{args.name}-response.json")
            with open(response_path, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            print(f"FAIL: the response is saved to {response_path}; check it for media in a shape this script does not read")
        else:
            print("FAIL: the response held no media of the wanted types")
        return 1
    files, link_failed, waiting = [], False, False
    for part in parts:
        if "data" in part:
            files.append((part["data"], part["mime"]))
            continue
        host = urlsplit(part["link"]).hostname or "?"
        try:
            if args.wait_file:
                state, _doc = wait_for_file(part["link"], args.poll or args.endpoint, key, args.auth, args.wait_timeout)
                if state == "FAILED":
                    link_failed = True
                    print(f"FAIL: the linked file from {host} reports FAILED")
                    continue
                if state == "TIMEOUT":
                    waiting = True
                    print(f"STILL PROCESSING: the linked file from {host} was not ACTIVE after {args.wait_timeout:g} s")
                    continue
            got_type, data = download(part["link"], args.poll or args.endpoint, key, args.auth)
        except urllib.error.HTTPError as err:
            link_failed = True
            print(f"FAIL: linked result from {host}: HTTP {err.code} {err.reason}")
            continue
        except (urllib.error.URLError, OSError) as err:
            link_failed = True
            print(f"FAIL: linked result from {host}: {type(err).__name__}")
            continue
        not_ready, media_mime = link_body(got_type, data, types)
        if not_ready is not None:
            ctype = (got_type or "").split(";")[0].strip()
            ext = ".json" if not_ready or "json" in ctype else (mimetypes.guess_extension(ctype) or ".bin")
            os.makedirs(args.out_dir, exist_ok=True)
            response_path = os.path.join(args.out_dir, f"{args.name}-link-response{ext}")
            with open(response_path, "wb") as fh:
                fh.write(data)
            state = file_state(not_ready)
            print(f"NOT READY: the link from {host} returned {ctype or 'no type'}, not media"
                  + (f"; state: {state}" if state else "") + f". Saved the body to {response_path}")
            if state == "PROCESSING":
                waiting = True
            else:
                link_failed = True
            continue
        files.append((data, media_mime or part["mime"] or (got_type or "").split(";")[0]))
        print(f"downloaded a linked result from {host} ({len(data)} bytes)")
    saved = save(files, args) if files else []
    if reservation:
        spend_ledger.outcome(args.ledger, reservation, "uncertain" if (link_failed or waiting) else "completed", operation=op_id)
    if args.log and saved:
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        with open(args.log, "a", encoding="utf-8") as fh:
            for path, mime, size in saved:
                rec = {"created_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                       "name": args.name, "kind": args.kind, "out": path, "mime": mime, "bytes_written": size,
                       "endpoint": args.endpoint or args.poll, "requested_model": requested_model(body, args.endpoint or args.poll), "reported_model": reported,
                       "operation": op_id, "prompt": prompt_text(body, args.prompt_field),
                       "estimated_cost": {"usd": est, "units": args.units, "unit": args.unit, "unit_usd": args.unit_usd, "basis": args.price_basis},
                       "watermark": args.watermark, "content_credentials": "unchecked", "ledger_id": reservation}
                if any(p.get("from_thought") for p in parts):
                    rec["from_thought_step"] = True
                rec.update(probe(path))
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"logged {len(saved)} record(s) to {args.log}")
    if reported and body and body.get("model") and reported != body.get("model"):
        print(f"NOTE: requested model {body.get('model')} but the response reports {reported}; record both")
    if link_failed or waiting:
        print(f"The reservation stays (marked uncertain): the result may be billed. Operation: {op_id or 'none reported'}. "
              "Fetch it with --poll <the vendor's URL for this operation> --auth bearer|header:<header name> (no new reservation) before the vendor deletes it.")
        base = (args.endpoint or "").split("?")[0].rstrip("/")
        if op_id and base.endswith("/interactions"):
            print(f"For example: --poll {base}/{op_id} (a later GET of the interaction may return the result inline)")
        if not args.wait_file:
            print("Or rerun the fetch with --wait-file, which waits until a linked file is ACTIVE before downloading it.")
        return 1 if link_failed else 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
