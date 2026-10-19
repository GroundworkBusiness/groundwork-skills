#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Static contract checks on a look or build page (index.html).

Checks:
  - API members are present (base, plus the read-only getters time and playing, for looks;
    those plus the viewer API for builds).
  - No wall clock, unseeded randomness or timers anywhere in the page:
    Math.random(, Date.now, new Date, setInterval(, setTimeout(. The playback clock may
    use performance.now(); the timeline may not.
  - At most two external scripts, each pinned to an exact version (x.y.z in the URL).
  - Caption font size of at least 44 px in a CSS rule whose selector mentions "caption".
  - Looks and builds: narration-tied elements carry data-cue; a title card element (data-title-card)
    exists. When the cues.json beside the page sets title_card.duration_s to 0 (a loop or
    text-only piece whose owner confirmed dropping the card in PLAN.md), the element stays
    in the page and never shows.
  - Banned strings (--ban, repeatable; none by default; pass the owner's list from
    PLAN.md) and required on-screen terms (--require, repeatable).

Bans and required terms are matched only against viewer-facing text: the page with <script>, <style> and
comments removed and the tags stripped, plus the text, title, label and kicker values in
the embedded cue-data JSON, the cues.json beside --page, and any data-type values. Code, CSS custom properties and
identifiers never match. Each hit is reported with the matching snippet. When the cues.json beside --page sets captions_default to off, --require skips the cue sentence text (the captions), so a term that is only spoken does not count as on screen; the title card and scene values still count, and --ban still checks every piece. To ban the long dash (U+2014), pass the character itself, for example --ban="$(python3 -c 'print(chr(0x2014))')", or paste it between the quotes. A value that starts with an ASCII hyphen goes in the --ban=<value> form. A -- in script.txt is always caught by cue_check.py, so it needs no ban. Bans match any capitalisation, and a ban that starts or ends with a letter or digit matches whole words only at that end (a ban of "ai" does not match "said"); required terms match exactly.

Usage:
  python3 static_check.py --page <folder>/index.html [--level look|build] [--ban STR ...]
      [--require TERM ...] [--min-caption-px 44]

Dependencies: Python 3.9 or later, standard library only.
Exit codes: 0 pass; 1 one or more problems.
"""
import argparse
import html as htmlmod
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cue_check  # noqa: E402

BASE_API = ["duration", "seek", "play", "pause", "mode", "ready"]
READONLY_API = ["time", "playing"]  # read-only getters; checked with a getter-only pattern
VIEWER_API = ["voices", "tracks", "setVoice", "setMusic", "setMode", "setCaptions", "seekScene", "state"]
FORBIDDEN = ["Math.random(", "Date.now", "new Date", "setInterval(", "setTimeout("]
CUE_TEXT_KEYS = ("text", "title", "label", "kicker")


def strip_comments(js):
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"(^|[^:\\'\"])//[^\n]*", r"\1", js)


def cue_values(node, out, source="cue-data"):
    """Collect the viewer-facing string values of the embedded cue-data JSON."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in CUE_TEXT_KEYS and isinstance(value, str):
                out.append((source + " " + key, value))
            else:
                cue_values(value, out, source)
    elif isinstance(node, list):
        for value in node:
            cue_values(value, out, source)


def viewer_text(page, page_path=None):
    """Return [(where, text)] for every piece of viewer-facing text in the page."""
    pieces = []
    m = re.search(r"<script\b[^>]*\bid\s*=\s*[\"']cue-data[\"'][^>]*>(.*?)</script>", page, flags=re.S | re.I)
    if m:
        try:
            cue_values(json.loads(m.group(1)), pieces)
        except ValueError:
            pieces.append(("cue-data (not valid JSON)", m.group(1)))
    if page_path:
        cues_path = os.path.join(os.path.dirname(os.path.abspath(page_path)), "cues.json")
        if os.path.exists(cues_path):
            try:
                with open(cues_path, encoding="utf-8") as fh:
                    cue_values(json.load(fh), pieces, "cues.json")
            except (OSError, ValueError):
                pieces.append(("cues.json (not valid JSON)", ""))
    body = re.sub(r"<!--.*?-->", " ", page, flags=re.S)
    body = re.sub(r"<script\b[^>]*>.*?</script>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<style\b[^>]*>.*?</style>", " ", body, flags=re.S | re.I)
    for a, b in re.findall(r"\bdata-type\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", body):
        pieces.append(("data-type", htmlmod.unescape(a or b)))
    text = htmlmod.unescape(re.sub(r"<[^>]+>", " ", body))
    pieces.append(("page text", re.sub(r"\s+", " ", text)))
    return pieces


def snippet(text, start, length, pad=30):
    a, b = max(0, start - pad), min(len(text), start + length + pad)
    return ("..." if a else "") + text[a:b].strip() + ("..." if b < len(text) else "")


def title_card_seconds(page_path):
    """title_card.duration_s from the cues.json beside the page, or None when unreadable."""
    path = os.path.join(os.path.dirname(os.path.abspath(page_path)), "cues.json")
    try:
        with open(path, encoding="utf-8") as fh:
            card = json.load(fh).get("title_card") or {}
        return float(card.get("duration_s", 3.5))
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def captions_default(page_path):
    """captions_default from the cues.json beside the page ("on" when absent), or None when unreadable."""
    path = os.path.join(os.path.dirname(os.path.abspath(page_path)), "cues.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("captions_default") or "on"
    except (OSError, ValueError, AttributeError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", required=True)
    ap.add_argument("--level", choices=["look", "build"], default="build")
    ap.add_argument("--ban", action="append", default=[], help="string banned from viewer-facing text (repeatable)")
    ap.add_argument("--require", action="append", default=[])
    ap.add_argument("--min-caption-px", type=float, default=44)
    args = ap.parse_args()

    with open(args.page, encoding="utf-8") as fh:
        page = fh.read()
    problems, notes = [], []
    scripts = re.findall(r"<script\b([^>]*)>(.*?)</script>", page, flags=re.S | re.I)
    inline_js = "\n".join(body for attrs, body in scripts if "src=" not in attrs and "application/json" not in attrs)
    code = strip_comments(inline_js)

    for name in BASE_API + (VIEWER_API if args.level == "build" else []):
        if not re.search(r"\b" + re.escape(name) + r"\b\s*[:(]|\bget\s+" + re.escape(name) + r"\b|\." + re.escape(name) + r"\s*=", code):
            problems.append(f"API member '{name}' not found on window.__video")
    for name in READONLY_API:
        if not re.search(r"\bget\s+" + re.escape(name) + r"\s*\(|defineProperty\([^)]*['\"]" + re.escape(name) + r"['\"]", code):
            problems.append(f"API member '{name}' not found on window.__video")
    if "__video" not in code:
        problems.append("window.__video is never defined")

    for token in FORBIDDEN:
        for m in re.finditer(re.escape(token), code):
            line = code[: m.start()].count("\n") + 1
            problems.append(f"'{token}' in the page script (script line {line}); the timeline must be a pure function of t")

    external = [re.search(r"src\s*=\s*[\"']([^\"']+)", attrs) for attrs, _ in scripts if "src=" in attrs]
    external = [m.group(1) for m in external if m]
    remote = [u for u in external if re.match(r"(https?:)?//", u)]
    if len(remote) > 2:
        problems.append(f"{len(remote)} external scripts; the contract allows two")
    for u in remote:
        if not re.search(r"\d+\.\d+\.\d+", u):
            problems.append(f"external script is not pinned to an exact version: {u}")

    sizes = []
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", " ".join(re.findall(r"<style[^>]*>(.*?)</style>", page, flags=re.S | re.I)), flags=re.S)):
        if "caption" in selector.lower():
            for m in re.finditer(r"font-size\s*:\s*([\d.]+)px", body):
                sizes.append(float(m.group(1)))
    if not sizes:
        notes.append("no caption font size found in a CSS rule mentioning 'caption'; check it by eye")
    elif max(sizes) < args.min_caption_px:
        problems.append(f"caption font size {max(sizes)} px is below {args.min_caption_px} px at 1080p")

    if "data-cue" not in page:
        problems.append("no data-cue attributes; tag every narration-tied element (rule R5)")
    cues_path = os.path.join(os.path.dirname(os.path.abspath(args.page)), "cues.json")
    if os.path.exists(cues_path):
        try:
            with open(cues_path, encoding="utf-8") as fh:
                cue_doc = json.load(fh)
        except (OSError, ValueError):
            cue_doc = None
            problems.append("cues.json beside the page is not valid JSON; rerun make_cues.py for this folder")
        if isinstance(cue_doc, dict):
            page_scenes = set(re.findall(r"""data-scene\s*=\s*["'](\d+)["']""", page))
            for sc in cue_doc.get("scenes") or []:
                n = str(sc.get("n"))
                if n and n not in page_scenes:
                    problems.append(f'scene {n} is in cues.json but the page has no [data-scene="{n}"] section')
    card = title_card_seconds(args.page)
    if card == 0:
        notes.append("cues.json sets title_card.duration_s to 0: the card never shows, but its element stays (the runtime and the timing audit read it); PLAN.md must record the owner's confirmation")
    if "data-title-card" not in page and 'id="title-card"' not in page:
        problems.append("no title card element (data-title-card); rule R1")

    pieces = viewer_text(page, args.page)
    for ban in args.ban:
        if not ban:
            continue
        for where, text in pieces:
            for m in cue_check.ban_pattern(ban).finditer(text):
                problems.append(f"banned string {ban!r} in {where}: {snippet(text, m.start(), m.end() - m.start())!r}")
    shown = pieces
    if captions_default(args.page) == "off":
        # captions off: a cue's sentence text is spoken, not shown, so it cannot satisfy --require
        shown = [(where, text) for where, text in pieces if where not in ("cue-data text", "cues.json text")]
    for term in args.require:
        if not any(term in text for _, text in shown):
            problems.append(f"required on-screen term missing: {term!r}")

    for n in notes:
        print("NOTE " + n)
    if problems:
        for p in problems:
            print("FAIL " + p)
        print(f"{len(problems)} problem(s) in {args.page}")
        return 1
    print(f"PASS: {args.page} meets the static {args.level} contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
