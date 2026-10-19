#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check that delivery cues never change the words of the canonical script.

Compares every scene of scenes.json (text_cued and each entry in variants) with the
matching paragraph of script.txt after one normalisation: lowercase; remove <...> tags;
fold curly apostrophes to straight; replace every character outside a-z, 0-9 and the
apostrophe with a space (this removes the -- hesitation cue); split on whitespace; trim
apostrophes at the ends of each word. It also checks paragraph and scene counts, that the scene numbers (n) run 1 to N in script order, and
looks for banned strings in the viewer-facing script and scenes.json title, label,
text_cued and variants values.

With --cues it also checks a build's or look's cues.json against script.txt: the cue
texts of each scene, joined and normalised the same way, must equal that scene's
paragraph, and the scene counts must agree. This catches cues left over from another
script (for example a look's one-scene sample cues copied into a full build).

Usage:
  python3 cue_check.py --script script/script.txt --scenes script/scenes.json \\
      [--cues <video-id>/<build-id>/cues.json] [--ban STRING ...] [--fill]

Bans come only from --ban (repeatable; none by default): pass the owner's list from the
Banned line of PLAN.md. Bans match any capitalisation, and a ban that starts or ends with a letter or digit matches whole words only at that end (a ban of "ai" does not match "said"); required terms match exactly. To ban the long dash (U+2014), pass the character itself, for example
--ban="$(python3 -c 'print(chr(0x2014))')", or paste it between the quotes. A value that
starts with an ASCII hyphen goes in the --ban=<value> form. A -- in script.txt is always
caught by cue_check.py, so it needs no ban. The -- hesitation cue in text_cued and variants
is exempt from bans. One structural check is always on: a -- in script.txt is a
hesitation cue that leaked into the captions, because delivery cues belong in scenes.json.
--fill writes each scene's normalised words into scenes.json as text_plain_check for
readers.

Dependencies: Python 3.9 or later, standard library only.
Exit codes: 0 every word matches and nothing banned; 1 any mismatch, count difference,
leaked hesitation cue or ban.
"""
import argparse
import difflib
import hashlib
import json
import re
import sys

APOSTROPHES = {"’": "'", "‘": "'", "ʼ": "'"}
CUE_LEAK = "--"


def norm_words(text):
    text = re.sub(r"<[^>]*>", " ", text or "").lower()
    for curly, straight in APOSTROPHES.items():
        text = text.replace(curly, straight)
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return [w.strip("'") for w in text.split() if w.strip("'")]


def ban_pattern(ban):
    """Bans match any capitalisation. A ban that starts or ends with a letter or digit
    matches only at a word boundary on that side, so a ban of "ai" does not match "said";
    a ban made of punctuation, such as the long dash, matches anywhere."""
    head = r"\b" if re.match(r"\w", ban[0]) else ""
    tail = r"\b" if re.match(r"\w", ban[-1]) else ""
    return re.compile(head + re.escape(ban) + tail, re.IGNORECASE)


def words_sha256(text):
    """SHA-256 of the normalised words, so a re-take of the same words matches."""
    return hashlib.sha256(" ".join(norm_words(text)).encode("utf-8")).hexdigest()


def read_paragraphs(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read().replace("\r\n", "\n").strip()
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def diff_lines(expected, got, label="cued"):
    out = []
    sm = difflib.SequenceMatcher(None, expected, got, autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        out.append(f"    {op}: script [{' '.join(expected[a1:a2])}] {label} [{' '.join(got[b1:b2])}]")
    return out


def check_cues_file(path, paragraphs):
    """Return the number of problems between a cues.json and the script's paragraphs."""
    try:
        with open(path, encoding="utf-8") as fh:
            cues = json.load(fh)
    except (OSError, ValueError) as err:
        print(f"FAIL: cannot read {path} ({type(err).__name__})")
        return 1
    scenes = cues.get("scenes") or []
    problems = 0
    if len(scenes) != len(paragraphs):
        print(f"FAIL: {path} has {len(scenes)} scenes; script.txt has {len(paragraphs)} paragraphs (stale cues? regenerate with make_cues.py)")
        problems += 1
    for i, scene in enumerate(scenes[: len(paragraphs)]):
        expected = norm_words(paragraphs[i])
        got = norm_words(" ".join(c.get("text", "") for c in scene.get("cues") or []))
        if got != expected:
            problems += 1
            print(f"FAIL: {path} scene {scene.get('n', i + 1)} cue texts differ from script.txt (stale cues? regenerate with make_cues.py)")
            print("\n".join(diff_lines(expected, got, "cues.json")))
    if not problems:
        print(f"cues.json matches script.txt: {len(scenes)} scenes")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--cues", help="a cues.json to check against script.txt")
    ap.add_argument("--ban", action="append", default=[], help="string banned from viewer-facing text (repeatable)")
    ap.add_argument("--fill", action="store_true", help="write text_plain_check into scenes.json")
    args = ap.parse_args()

    try:
        paragraphs = read_paragraphs(args.script)
        with open(args.scenes, encoding="utf-8") as fh:
            data = json.load(fh)
        if args.cues:
            with open(args.cues, encoding="utf-8") as fh:
                json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"FAIL: {e}")
        return 1
    scenes = data.get("scenes", [])
    problems = 0
    if len(paragraphs) != len(scenes):
        print(f"FAIL: script.txt has {len(paragraphs)} paragraphs; scenes.json has {len(scenes)} scenes")
        problems += 1
    numbers = [str(s.get("n")) for s in scenes]
    if numbers != [str(i) for i in range(1, len(scenes) + 1)]:
        print(f"FAIL: scenes.json numbers its scenes {', '.join(numbers)}; n must run 1 to {len(scenes)} in script order (renumber after adding or removing a scene)")
        problems += 1

    total = matched = 0
    for i, scene in enumerate(scenes):
        if i >= len(paragraphs):
            break
        expected = norm_words(paragraphs[i])
        texts = [("text_cued", scene.get("text_cued", ""))] + sorted((scene.get("variants") or {}).items())
        for name, text in texts:
            got = norm_words(text)
            sm = difflib.SequenceMatcher(None, expected, got, autojunk=False)
            same = sum(b.size for b in sm.get_matching_blocks())
            if name == "text_cued":
                total += len(expected)
                matched += same if got == expected else min(same, len(expected) - 1)
            if got != expected:
                problems += 1
                print(f"FAIL: scene {scene.get('n', i + 1)} {name} changes the words")
                print("\n".join(diff_lines(expected, got)))
        if args.fill:
            scene["text_plain_check"] = " ".join(expected)

    with open(args.script, encoding="utf-8") as fh:
        script_lines = fh.read().splitlines()
    for n, line in enumerate(script_lines, start=1):
        if CUE_LEAK in line:
            problems += 1
            print(f"FAIL: hesitation cue '--' in script.txt line {n} (delivery cues belong in scenes.json)")
    for ban in args.ban:
        if not ban:
            continue
        pattern = ban_pattern(ban)
        for n, line in enumerate(script_lines, start=1):
            if pattern.search(line):
                problems += 1
                print(f"FAIL: banned string {ban!r} in script.txt line {n}")

    for i, scene in enumerate(scenes):
        fields = [(k, scene.get(k, "")) for k in ("title", "label", "text_cued")]
        fields += [("variants " + k, v) for k, v in (scene.get("variants") or {}).items()]
        for field, value in fields:
            spoken = value.replace("--", " ") if field == "text_cued" or field.startswith("variants ") else value
            for ban in args.ban:
                if ban and ban_pattern(ban).search(spoken):
                    problems += 1
                    print(f"FAIL: banned string in scenes.json scene {scene.get('n', i + 1)} {field}: {ban!r}")

    print(f"{matched} of {total} words match")
    if args.cues:
        problems += check_cues_file(args.cues, paragraphs)
    if args.fill:
        with open(args.scenes, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print(f"wrote text_plain_check into {args.scenes}")
    if problems:
        print(f"{problems} problem(s)")
        return 1
    print("PASS: delivery cues keep every word; paragraph and scene counts agree" + ("; cues.json matches the script" if args.cues else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
