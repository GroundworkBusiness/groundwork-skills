#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Local static server with HTTP byte ranges, for previewing builds with audio.

Python's built-in http.server ignores Range requests, so a browser cannot seek voice
or music audio served by it. This server answers single ranges (bytes=a-b, bytes=a-,
bytes=-n) with 206 Partial Content, unsatisfiable ranges with 416, sends
Accept-Ranges on every response, and sends Cache-Control: no-store so edited
manifests are read fresh.

Usage:
  python3 serve_range.py [--port 8770] [--dir <project>] [--host 127.0.0.1]
  python3 serve_range.py --self-test

Serve the project folder, so builds, viewer, voices and music resolve as siblings.
The default host 127.0.0.1 keeps the server on this machine. Bind 0.0.0.0 only to test
on a phone on the same network, and stop the server afterwards.

Dependencies: Python 3.9 or later, standard library only.
Exit codes: 0 normal stop or self-test passed; 1 self-test failed; 2 bad arguments, or the port cannot be bound (in use, or refused by a sandbox).
"""
import argparse
import errno
import http.client
import os
import re
import shutil
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")
CHUNK = 64 * 1024


class RangeHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        self._range = None
        header = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not header or os.path.isdir(path) or not os.path.isfile(path):
            return super().send_head()
        match = RANGE_RE.match(header.strip())
        if not match or (not match.group(1) and not match.group(2)):
            return super().send_head()  # malformed or multi-range: full body is allowed
        size = os.path.getsize(path)
        if match.group(1):
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else size - 1
        else:
            start = max(0, size - int(match.group(2)))
            end = size - 1
        end = min(end, size - 1)
        if size == 0 or start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        handle = open(path, "rb")
        handle.seek(start)
        self._range = (start, end)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        return handle

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def copyfile(self, source, outputfile):
        if not getattr(self, "_range", None):
            return super().copyfile(source, outputfile)
        start, end = self._range
        remaining = end - start + 1
        while remaining > 0:
            chunk = source.read(min(CHUNK, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)

    def log_message(self, fmt, *args):
        if os.environ.get("SERVE_RANGE_QUIET") != "1":
            super().log_message(fmt, *args)


def make_server(host, port, directory):
    return ThreadingHTTPServer((host, port), partial(RangeHandler, directory=directory))


def self_test():
    os.environ["SERVE_RANGE_QUIET"] = "1"
    tmp = tempfile.mkdtemp()
    data = bytes(range(256)) * 4  # 1,024 bytes
    with open(os.path.join(tmp, "a.bin"), "wb") as fh:
        fh.write(data)
    try:
        server = make_server("127.0.0.1", 0, tmp)
    except OSError:
        print("SKIP: cannot bind a local port here; the host runs this check")
        shutil.rmtree(tmp, ignore_errors=True)
        return 0
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []

    def req(method, headers):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request(method, "/a.bin", headers=headers)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp, body

    def check(name, ok):
        results.append(ok)
        print(("PASS " if ok else "FAIL ") + name)

    r, b = req("GET", {})
    check("no Range gives 200 and the full body", r.status == 200 and b == data and r.getheader("Accept-Ranges") == "bytes")
    r, b = req("GET", {"Range": "bytes=0-99"})
    check("bytes=0-99 gives 206 with 100 bytes", r.status == 206 and b == data[0:100] and r.getheader("Content-Range") == "bytes 0-99/1024")
    r, b = req("GET", {"Range": "bytes=1000-"})
    check("bytes=1000- gives 206 with the last 24 bytes", r.status == 206 and b == data[1000:])
    r, b = req("GET", {"Range": "bytes=-50"})
    check("bytes=-50 gives 206 with the last 50 bytes", r.status == 206 and b == data[-50:])
    r, b = req("GET", {"Range": "bytes=5000-"})
    check("bytes=5000- gives 416 with bytes */1024", r.status == 416 and r.getheader("Content-Range") == "bytes */1024")
    r, b = req("HEAD", {"Range": "bytes=0-9"})
    check("HEAD with Range gives 206 headers and no body", r.status == 206 and b == b"" and r.getheader("Content-Length") == "10")
    server.shutdown()
    server.server_close()
    shutil.rmtree(tmp, ignore_errors=True)
    ok = all(results)
    print("self-test " + ("passed" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    directory = os.path.abspath(args.dir)
    if not os.path.isdir(directory):
        print(f"not a folder: {directory}")
        return 2
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(f"WARNING: binding {args.host} makes these files reachable from the network. Stop the server when the phone test is done.")
    try:
        server = make_server(args.host, args.port, directory)
    except OSError as err:
        if err.errno == errno.EADDRINUSE:
            print(f"FAIL: port {args.port} is in use; pass another --port")
        elif err.errno in (errno.EPERM, errno.EACCES):
            print("FAIL: this session cannot bind a local port (likely a sandbox); the host or the owner runs this command in their own terminal")
        else:
            print(f"FAIL: cannot serve on {args.host}:{args.port} ({err.strerror}); pass another --port")
        return 2
    print(f"Serving {directory} at http://{args.host}:{args.port}/ with byte ranges (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
