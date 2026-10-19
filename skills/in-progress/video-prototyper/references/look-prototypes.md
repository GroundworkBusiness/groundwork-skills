# Look prototypes (gate 1)

How to decide the look on a small, identical sample before building the whole video. Templates: [look-brief.md](../assets/templates/look-brief.md), [LOOK.md](../assets/templates/LOOK.md), [compare.html](../assets/compare.html) and [looks.json](../assets/looks.json).

## Contents

- [Why one short identical scene](#why-one-short-identical-scene)
- [The sample scene](#the-sample-scene)
- [Choosing concepts](#choosing-concepts)
- [Spreading looks across agents](#spreading-looks-across-agents)
- [What each look ships](#what-each-look-ships)
- [The compare page](#the-compare-page)
- [Shortlist, routing and cross-refinement](#shortlist-routing-and-cross-refinement)
- [Design checklist](#design-checklist)

## Why one short identical scene

The same sample in every look makes the look the only variable. About 20 seconds is long enough to show type, motion, light and captions, and short enough to build several in parallel. Fixed narration and a shared beat table let the compare page scrub every look to the same time. The prototype decides style; story and information get their own pass once the owner has given the content. When the whole video is about the sample's length, make the sample the whole video as one scene; the full build may split it into scenes.

## The sample scene

Save your own video's sample scene, not this example, as `looks/sample-script.txt` (one paragraph) with its one-scene `looks/sample-scenes.json`, as in [SKILL.md stage 3, step 1](../SKILL.md#3-gate-1-look-prototypes). Make each look's `cues.json` from it with make_cues.py, so the static check, the timing audit and the compare page run on the sample scene alone.

An example only, for the invented "Three bins" curbside-sorting explainer used throughout this skill (its narration differs from [scenes.example.json](../assets/scenes.example.json) and the build template), as a five-beat table:

| Beat | Anchor | Narration | On screen |
|---|---|---|---|
| 1 | `A(1, 0, 0)` | Alder Creek sorts its rubbish into three bins. | Three empty bins roll in from the right and stop at the kerb. |
| 2 | `A(1, 1, 0)` | Blue is for clean paper, cans and bottles. | The blue lid flips open; a can, a bottle and a flattened box drop in. |
| 3 | `A(1, 2, 0)` | Green is for food scraps and yard trimmings. | Apple peels and a handful of leaves tumble into green. |
| 4 | `A(1, 3, 0)` | Grey takes whatever is left, like a greasy pizza box. | The box drops toward blue, bounces off the lid, and lands in grey. |
| 5 | `A(1, 4, 0)` | Next, which day each bin goes out. | The bins roll back out; a wall calendar slides into view. |

All facts are invented for the example and labelled illustrative. Beats are anchors on these cues, as in the full build, so the full build retimes the same look to every voice take.

## Choosing concepts

Pick concepts far apart, so the comparison teaches something. Examples:

- chalk drawings on a slate board, rubbed out and redrawn between beats;
- a flat isometric diorama of toy-like blocks;
- a hand-inked comic strip, with panels and speech balloons;
- shapes that assemble tile by tile from a pixel mosaic;
- watercolour washes that bleed in behind loose ink lines;
- split-screen data panels, like a control-room wall.

Every look supports light and dark on one timeline. Each may choose its own default mode; the compare page can override it.

## Spreading looks across agents

When several agents or models are available, give each a different look; build three to six distinct looks to the same spec, and at least two when only one tool is available. The compare page then doubles as a test of which agent or model does code-built motion well. Record the verdict in `PLAN.md` and route later motion work to the winner.

Every look starts from the runtime in [the build template](../assets/build-template/index.html) (what to keep and what to replace is listed at the top of [the stage contract](stage-contract.md#starting-from-the-template)) and meets [the stage contract](stage-contract.md); the look itself is free.

## What each look ships

- `index.html`, self-contained.
- `cues.json`, made from `looks/sample-script.txt` with `make_cues.py --no-voices --no-music` (delete the template's copy first; the script keeps an existing file's title card and message type). Add `--label "<label>" --kicker "<kicker>"` from the Title card line of `PLAN.md` when it has them. A loop or text-only piece also adds `--target-seconds <the sample's length>`, `--loop` for a loop, `--title-card 0` when the Title card line of `PLAN.md` records the owner's confirmation, and the [No voice pace flags](timing-check.md#no-voice) (`--wps`, `--breath`, `--lead`, `--hold`); captions picked off add `--captions off`.
- `LOOK.md`: concept; palette per mode with hex values and computed contrast ratios for each text role and for captions on their plate; type; motion signature with a staging table; how it carries across a series; what it borrows; on-screen facts and their sources; playback and rendering notes; what was checked and **what the checks do not prove**; open questions for the owner.
- `image-requests.json` with drawn stand-ins (no generated images).
- `frames/` when a browser is available: stills at each beat and mid-beat in both modes, named `frames/<voice>/<mode>-t<SSS.SS>.png` (voice `none` for a look), as [frame_review.py](../scripts/frame_review.py) writes them.

Sandboxed agents often cannot launch a browser. They still run [static_check.py](../scripts/static_check.py) and [timing_audit.mjs](../scripts/timing_audit.mjs), list what they could not check, and the host renders the frames.

## The compare page

Copy [compare.html](../assets/compare.html) and [looks.json](../assets/looks.json) into `looks/`, list each look (`id`, `label`, `folder`, `builder`), and serve the project with [serve_range.py](../scripts/serve_range.py).

- Every look is a real 1920x1080 page in an iframe, scaled to its tile, so the true layout shows.
- Play all, Pause all, one scrub bar that seeks every look, and a mode override (each look's default, all light, all dark).
- Looks not built yet show as not ready, so the page can go to the owner before every agent finishes.
- The builder label can be hidden when the page is shared beyond the owner.
- For frame-exact comparison, scrub; Play all runs each look on its own clock.

Also open every look at about 375 px wide, in a desktop browser's responsive or device mode, or through a same-origin test page saved in `looks/` that holds the look's own page in a 375 px wide iframe (`<iframe src="<look-id>/index.html" width="375" height="812"></iframe>`, one per look) opened or captured at a normal window size. The compare page loads every look at 1920x1080 and scales the tile, so `compare.html` in a narrow iframe does not test a look's own scaling or its controls. A look that breaks its scaling in a small window fails the contract.

## Shortlist, routing and cross-refinement

1. The owner watches the looks side by side, opens any one with its controls and its `LOOK.md`, and shortlists.
2. Record the shortlist, the reasons, and the routing verdict in `PLAN.md`.
3. When a style or transition choice stays open, build A/B pages and let the owner pick.
4. Cross-refine: when another agent or model is available, give each shortlisted look to a different agent or model than its author, with "keep what works, fix what the owner said fell short"; otherwise run a separate review pass in the same session with that brief.
5. Hold the full build until the owner has walked through the content for the video.

## Design checklist

- The owner's standing design rules (the Design rules line in `PLAN.md`) hold for every look.
- Names of products, buttons and screens are spelled as the real thing spells them, and two different things never share one name.
- Examples are everyday ones a viewer recognises at a glance.
- No figures (prices, counts, dates) in viewer-facing copy unless true and approved.
- Captions stay legible on their plate in both modes; decorative lines may be low contrast if they carry no words.
- Ambient motion is a function of time, never an independent loop.
