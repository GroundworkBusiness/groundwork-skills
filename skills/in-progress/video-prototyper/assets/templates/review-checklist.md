# Review checklist

The reviewer reads every build, its notes and its audit reports, and changes no build file. Its findings go to `<video-id>/review.md`; on Claude Code's prototype workflow, the reviewer writes nothing and returns them in the review stage's result. The host runs the acceptance list in a real browser with sound.

## Reviewer: timing rules

- [ ] R1: every voice and No voice begins with a title card of about 3.5 s, unless PLAN.md records the owner's confirmation that this loop or text-only piece drops it; narration starts after any card; music starts at t = 0.
- [ ] R2: nothing appears before its words; each narration-tied element first shows within 0.3 s before to 0.5 s after its sentence or key phrase.
- [ ] R2: quoted lines appear as spoken.
- [ ] R3: each scene opens with its label and background, plus at most its first sentence's element and caption; nothing from a later sentence shows before its words.
- [ ] R4: elements hold until the narration moves past them; nothing clears mid-sentence.
- [ ] R5: every narration-tied element has data-cue; qa/timing-audit.json passes for every available voice in both modes.
- [ ] Gate 4 stays unsigned while the audit prints INCOMPLETE; after a new take, a timing fix or a script change, `timing_audit.mjs --strict` exited 0 for every build.
- [ ] Reveals use anchors A(scene, k, f); no seconds values in beat code (a loop's final clear comes from `make_cues.py --loop`).

## Reviewer: contracts and notes

- [ ] Stage contract: API members, URL parameters, deterministic seek, controls outside the frame, no autoplay.
- [ ] Viewer contract: voices(), tracks(), setVoice keeps scene and fraction and resumes, setMusic, setMode, setCaptions, seekScene, state(), ready, state messages to location.origin.
- [ ] Missing takes and beds show as not ready.
- [ ] static_check.py passes.
- [ ] SCENES-NOTES.md matches the page (timing, title card, music, checks run).
- [ ] On-screen facts match the build brief; illustrative content is labelled in the brief and notes (on screen where a viewer could take it for a real record); no invented counts or names presented as real.
- [ ] Banned strings absent from captions and cards.
- [ ] Every term on the Required terms line of PLAN.md appears on screen with its exact wording in each full build (static_check.py --require passes).
- [ ] The owner's design rules in PLAN.md are met.
- [ ] When `media/image-requests.json` sets `picked` for a request: that file is in place in every live build, with the request's per-mode blend, and its stand-in is gone. A request with no pick yet (no owner's yes to generate, or no file chosen) keeps its stand-in and is listed in the review as pending, not as a failure.
- [ ] When PLAN.md records any generated voice, music, image or footage: the Disclosure line from PLAN.md appears word for word on the closing card of every build, in both modes (for a loop, where PLAN.md places it).

## Host: acceptance in a real browser, sound on

- [ ] Captions on, burned in or toggle: every voice plays with its own captions. Captions off: the plate is hidden at load and `setCaptions(true)` shows it. Not-ready takes are disabled.
- [ ] Every bed stays within 0.25 s of the timeline while playing, and within 0.05 s while paused, after seeking about two-thirds of the way through (60 s or later on a long video) (in the build page's console, `__video.diagnostics()`: open the build's own `index.html` on the same server, or from the viewer's console run `document.getElementById('frame').contentWindow.__video.diagnostics()`; compare `t` with `musicTime`).
- [ ] Seek into every clip or recording: the frame matches the timeline in the viewer and in the export.
- [ ] Music Off and ?music=off are silent; fades at start and end; no clicks.
- [ ] Nothing sounds before Play.
- [ ] setVoice while playing keeps the scene and fraction and keeps playing.
- [ ] ?embed=1 hides the voice, music, mode and caption controls; no inner scroll.
- [ ] Switching builds in the viewer keeps the scene and fraction.
- [ ] Opening frame: title card first (unless PLAN.md records it dropped). At the card's end, the first scene's label and background show, plus its first element and caption only if its first sentence starts at once. With no card, t = 0 shows the background only (plus any whole-video line outside the scenes), and the scene label shows by about 0.4 s. No overlap or clipping, in both modes, at 1920x1080 and inside the viewer.
- [ ] Every take's last line is on screen and heard.
- [ ] The disclosure line is readable at the end of every voice (or for the whole loop), in both modes.
- [ ] The console shows no errors other than 404s for takes or beds listed as not ready.
- [ ] Narrow width (about 375 px): controls wrap, no horizontal page scroll.
- [ ] A range request to the server returns 206.
- [ ] Loop: t = 0 and t = duration paint the same frame, and the frame before t = duration flows into t = 0.
