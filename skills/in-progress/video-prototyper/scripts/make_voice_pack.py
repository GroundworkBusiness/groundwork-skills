#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Render voice-pack.md, the paste-ready document for auditioning voices by hand.

The pack is generated from script.txt and scenes.json, so the scripts calling an API and
the person pasting into a vendor's web app read the same words and delivery cues. Each scene
gets a Plain block (its paragraph of script.txt, for the plain pass) and a Cued block (its
text_cued, for the styled pass and the full read). Rerun it after any change to script.txt
or scenes.json.

Shortlist file (optional JSON):
  {"model": "<model id; which models take designed voices>",
   "prebuilt": [{"voice": "...", "character": "...", "why": "..."}],
   "design_prompts": [{"label": "...", "prompt": "one or two sentences, permanent traits only"}],
   "cue_notes": "how this provider reads tags, CAPS, ellipses and --"}

Usage:
  python3 make_voice_pack.py --scenes script/scenes.json --script script/script.txt \
      --out script/voice-pack.md [--shortlist script/voices-shortlist.json]

Example: assets/voices-shortlist.example.json.

Dependencies: Python 3.9 or later, standard library only.
Exit codes: 0 written; 1 bad input (including a script.txt whose paragraph count differs
from the scene count).
"""
import argparse
import json
import os
import re
import sys

FENCE = "`" * 3


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--script", required=True, help="the canonical script.txt; paragraph N is scene N's Plain block")
    ap.add_argument("--out", required=True)
    ap.add_argument("--shortlist")
    args = ap.parse_args()
    with open(args.scenes, encoding="utf-8") as fh:
        data = json.load(fh)
    with open(args.script, encoding="utf-8") as fh:
        script_text = fh.read().replace("\r\n", "\n").strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", script_text) if p.strip()]
    if len(paragraphs) != len(data["scenes"]):
        print(f"FAIL: {args.script} has {len(paragraphs)} paragraphs; {args.scenes} has {len(data['scenes'])} scenes. "
              "Keep one paragraph per scene, separated by a blank line, then run cue_check.py.")
        return 1
    short = {}
    if args.shortlist:
        with open(args.shortlist, encoding="utf-8") as fh:
            short = json.load(fh)
    conv = data.get("cue_convention", {})
    lines = [f"# Voice pack: {data.get('title', 'untitled')}", ""]
    lines += ["Generated from script.txt and scenes.json. For the plain pass, paste a scene's Plain block with the style setting empty; for the styled pass and the full read, paste its Cued block with its style line. The words must stay exactly as written; delivery cues change only how they are read.", ""]
    lines += ["## Model", "", short.get("model", "Pick a speech model that supports the voices you want. Check which models accept designed voices and style direction."), ""]
    lines += ["## Option A: audition ready-made voices", "", "| Voice | Character | Why try it |", "|---|---|---|"]
    for v in short.get("prebuilt", []):
        lines.append(f"| {v.get('voice', '')} | {v.get('character', '')} | {v.get('why', '')} |")
    if not short.get("prebuilt"):
        lines.append("| (add three or four) | | |")
    lines += ["", "## Option B: design a voice", "", "Describe permanent traits only: age range, gender if relevant, timbre, texture, accent, baseline pace. Emotion belongs in each scene's style line. For a regional accent, make the same prompt again with a neutral accent and compare.", ""]
    design_prompts = short.get("design_prompts") or []
    if not design_prompts:
        design_prompts = [
            {"label": "Design 1", "prompt": ""},
            {"label": "Design 2", "prompt": ""},
            {"label": "Design 3", "prompt": ""},
        ]
        lines += ["Write each design prompt in a block below: a sentence or two naming permanent traits only.", ""]
    for d in design_prompts:
        lines += [f"**{d.get('label', 'Design')}**", "", FENCE + "text", d.get("prompt", ""), FENCE, ""]
    lines += ["## How the delivery cues work", ""]
    lines += [short.get("cue_notes") or (
        f"Tags in angle brackets ({', '.join('<' + t + '>' for t in conv.get('tags', [])) or 'none listed'}) shape pauses and breaths. "
        f"{conv.get('stress', 'CAPS')} marks stress. {conv.get('hesitation', '--')} marks a hesitation. "
        "When a scene sounds overdone, remove its breath tags before anything else, and then the pauses inside lists."), ""]
    lines += ["## Test order", "",
              "1. Plain first: two short scenes, their Plain blocks, empty style line, three or four voices.",
              "2. The favourites again on the same scenes, with the Cued block and the style line; compare with step 1.",
              "3. Whole script, one scene per request: each scene's Cued block with its style line.",
              "4. Save each scene as <voice>/s<N>.wav so the agent can check, join and align it.", ""]
    lines += ["## The script, by scene", ""]
    for s, plain in zip(data["scenes"], paragraphs):
        lines += [f"### Scene {s['n']}: {s.get('title', '')}", "", f"Style: `{s.get('style', '')}`", "",
                  "Plain (paste for the plain pass, style setting empty):", "", FENCE + "text", plain, FENCE, "",
                  "Cued (paste for the styled pass and the full read, with the style line):", "", FENCE + "text", s["text_cued"], FENCE, ""]
    lines += ["## Troubleshooting", "",
              "- The voice drifts into a different character: cut the style line down, or leave it empty.",
              "- A tag is read aloud: regenerate that scene with the tags removed, keep the style line.",
              "- The last line is missing: regenerate that scene alone and listen to its ending.", ""]
    lines += ["## Generated takes", "", "| Take | Voice kind | Length | Words matched | Scenes redone plain |", "|---|---|---|---|---|", ""]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {args.out} ({len(data['scenes'])} scenes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
