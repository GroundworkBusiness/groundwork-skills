# Build brief: <video-id>, <title>

## Narration, approved (version, date)

1. **<Scene name>.** <narration>
   On screen: <what the picture shows, beat by beat>.

## Facts for the pictures

The true facts each scene depicts: the real parts, the real order, which items belong in which group. Builders draw only these. Illustrative examples are labelled illustrative.

## Owner's rules

- Audience wording:
- Example names (plain, unbranded):
- Names allowed on screen, and where:
- Facts never to state:
- Design rules (from PLAN.md):
- Length (the owner's limit, or no limit):
- Disclosure line (from PLAN.md, word for word; when any voice, music, image or footage is generated, on the closing card, or for a loop where PLAN.md places it: small for the whole loop directly in `#stage`, outside every `[data-scene]` and `[data-bg]`, with no `data-cue`, or on the hosting page beside the screen):

## Timing until a voice exists

Use cues.json from make_cues.py (estimate: 2.4 words per second, 0.45 s breath, 0.6 s scene lead, 2.5 s scene hold). Key every beat to a cue anchor A(scene, k, f). Recorded takes replace the estimate at runtime with no code change. A loop or text-only piece makes cues.json with `--target-seconds <the piece's length>`, `--loop` for a loop, `--title-card 0` when the Title card line of PLAN.md records the owner's confirmation, and the No voice pace flags (`--wps`, `--breath`, `--lead`, `--hold`; <skill>/references/timing-check.md, No voice); captions picked off add `--captions off`, and music none adds `--no-music`.

## Technical contract

- The stage contract (<skill>/references/stage-contract.md; <skill>: the folder that holds SKILL.md, replaced with the absolute path given to this session) and the viewer contract (<skill>/references/viewer.md).
- Timing rules R1 to R5 (<skill>/references/timing-check.md); tag every narration-tied element with data-cue.
- The timeline, render(t) and window.__video live in a classic inline script that needs no external globals (the timing audit runs only inline classic scripts); an optional CDN library (at most two, pinned) may only add enhancements behind a check that its global exists.
- Shared folders (voices, music) are read-only from a build folder.

## Notes file

Keep SCENES-NOTES.md current at the end of every pass.

## Builds

| Folder | Starts from | Builder | Look |
|---|---|---|---|
| <video-id>/build-a/ | looks/<id>/ | | |

Work on a copy of the prototype inside your own folder; the prototype folders under looks/ stay as they are.

## Done when

- static_check.py passes; timing_audit.mjs passes for every available voice and No voice.
- SCENES-NOTES.md lists the checks run and what they did not cover.
- When PLAN.md records generated media, the disclosure line is on screen at the end in both modes; for a loop, where PLAN.md places it (in `#stage`, on screen for the whole loop in both modes, or on the hosting page).
