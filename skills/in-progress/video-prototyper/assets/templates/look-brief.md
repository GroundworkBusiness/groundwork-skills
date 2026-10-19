# Look brief: <scene name>, about 20 seconds

Every look builds this identical scene, so the only difference between them is the look.

## The scene

- Viewer:
- Narration: looks/sample-script.txt (fixed; captions match it word for word); cues.json from make_cues.py; add `--label "<label>" --kicker "<kicker>"` from the Title card line of PLAN.md when it has them; captions picked off: add `--captions off`; a loop or text-only piece: add `--target-seconds <the sample's length>`, `--loop` for a loop, `--title-card 0` when the Title card line of PLAN.md records the owner's confirmation, and the No voice pace flags (`--wps`, `--breath`, `--lead`, `--hold`; <skill>/references/timing-check.md, No voice)

| Beat | Anchor | Narration | On screen |
|---|---|---|---|
| 1 | | | |

Each look makes its cues.json from looks/sample-script.txt and keys its beats to anchors on those cues.

## Content rules

- Who presents (narration only, an on-screen presenter, a character):
- Any screen or interface shown in frame (recreated generically, with plain labels and no real logos unless the owner approves):
- Facts on screen come from: <source file>. Show only what the real thing does.
- Examples are plain, unbranded and labelled illustrative. No invented counts, ratings, prices or names presented as real.
- The owner's design rules (from PLAN.md):

## Captions

Draw captions on a plate of their own in every look, one cue for each sentence, matching the script exactly, at least 44 px at 1080p, high contrast. With captions on, captions are enabled by default; the plate stays hidden during the title card and appears when the first caption cue starts. With captions off, or a toggle whose page default is off, make cues.json with `--captions off`, so the plate is hidden when the page loads. Otherwise the picks differ only at export (SKILL.md, stage 1). For a piece with no voice, the approved on-screen lines are the canonical script.

## Technical contract

Meet the stage contract in <skill>/references/stage-contract.md (<skill>: the folder that holds SKILL.md, replaced with the absolute path given to this session): one self-contained index.html, a 1920x1080 stage, the window.__video API, URL parameters, deterministic seek, light and dark from one timeline. The timeline, render(t) and window.__video live in a classic inline script that needs no external globals, because the timing audit runs only the page's inline classic scripts; an optional CDN library (at most two, pinned) may only add enhancements behind a check that its global exists. Draw stand-ins and list wanted images in image-requests.json.

## Concepts

| Folder | Look | One-line concept | Builder |
|---|---|---|---|
| looks/<id>/ | | | |

## Inspiration

Where it is, and the rule: learn how an effect is done, and copy none of the inspiration's code, wording, pictures or typefaces. If the folder is empty, work from the written concept and say so in LOOK.md.

## Return

index.html, cues.json (from looks/sample-script.txt), LOOK.md, image-requests.json, optional frames/ named frames/<voice>/<mode>-t<SSS.SS>.png (voice none for a look), and what your checks did not prove.

Run from <project>/ and report each result as printed: `python3 <skill>/scripts/sync_embed.py --build looks/<id>`; `python3 <skill>/scripts/static_check.py --page looks/<id>/index.html --level look`, with each `--ban` from PLAN.md; `node <skill>/scripts/timing_audit.mjs --build looks/<id>`.
