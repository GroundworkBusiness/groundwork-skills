# Timing check (gate 4)

The rules that keep the picture from running ahead of the narration, the automated audit that proves them for every voice, and what the host still checks by eye.

## Contents

- [Why](#why)
- [The rules](#the-rules)
- [The opening frame](#the-opening-frame)
- [The audit](#the-audit)
- [No voice](#no-voice)
- [Seek determinism](#seek-determinism)
- [What the host checks](#what-the-host-checks)

## Why

When text appears before the narrator says it, viewers read instead of listen and the voice becomes noise. A build can look right with one take and run seconds ahead with another, because takes of one script differ widely in pace. So the rules hold for every voice and are proved per voice, by measuring what is painted after each seek rather than trusting the scheduled times.

## The rules

| Rule | Statement | Audit failure |
|---|---|---|
| R1 Title card | Each take, and No voice, begins with a title card (about 3.5 s: the title, plus the label and kicker when set) before any narration. The voice starts after the card; music still begins at t = 0 and fades in. A loop or text-only piece may drop the card (`--title-card 0`) with the owner's confirmation in `PLAN.md`. | With a card kept: the card is not visible at its midpoint; any scene, narration-tied element or caption is visible during the card; the card is still visible 0.5 s after it ends. |
| R2 Nothing before its words | Each narration-tied element first shows within a window from 0.3 s before its sentence (or key phrase) starts to 0.5 s after, in the active voice's timing. It is readable (opacity 0.5) within 0.5 s. Quoted lines appear as spoken. | First visible more than 0.3 s early or 0.5 s late; never visible; first readable more than 0.5 s late. |
| R3 Scenes open nearly empty | Each scene starts with its label and background, then builds. Nothing from later sentences is pre-placed. | At a scene's start, an element whose window has not opened is visible, or a caption shows before the scene's first sentence. |
| R4 Hold and clear | An element remains on screen while the narration is still on it, and leaves at a scene change or when a later beat takes its place, never mid-sentence. A loop (`"loop": true` in `cues.json`) ends with the stage cleared, as it starts. | The element is gone at its own sentence's end minus 1 ms; a scene is still visible after its clear deadline; for a loop, a scene or tagged element is still visible at t = duration. |
| R5 Prove it per voice | Tag every narration-tied element with `data-cue`; run the audit for every voice and both modes. | Untagged text in a scene; a tag naming no sentence; a tag in the wrong scene; fewer tagged elements than the minimum; any console error. |

Key phrases: when an element belongs to a phrase inside its sentence (the third item of a spoken list), mark it `data-cue-at="0.5"` and anchor its reveal at the same fraction. The audit expects it at sentence start + 0.5 x sentence length.

## The opening frame

After the title card, the first scene composes in with nothing overlapping or clipped: headings fully visible, lists complete or deliberately faded, panels clear of headings, nothing frozen mid-motion. Check both modes at 1920x1080 and inside the viewer iframe. The audit cannot see layout, so this is a host check.

## The audit

[timing_audit.mjs](../scripts/timing_audit.mjs) (Node 18 or later, no packages, no browser or sockets) runs the page's own inline script in a sandbox with a small DOM stand-in and mocked media, and applies [the audit core](../assets/timing-audit.js):

```sh
node <skill>/scripts/timing_audit.mjs --build <video-id>/<build-id>
```

Run it from `<project>/`. After a new take, a timing fix or a script change, add `--strict`.

- For every voice in the manifest (missing files recorded as `available: false`) and both modes, it boots the page with `?voice=<id>&mode=<m>&render=1&music=off`.
- It computes expected times from the timing files and `cues.json` directly (with the documented take repairs), checks that the page agrees, and checks the duration rule.
- Sampling: every 0.25 s over the whole duration, every scene edge, 0.01 s steps from 0.35 s before to 0.6 s after every expected time, and each sentence end minus 1 ms.
- At each sample it seeks and reads effective opacity: the product of inline opacity up the ancestor chain, 0 under `display: none`, `visibility: hidden` or `hidden`. First visible means opacity 0.01; first readable means 0.5.
- It writes `qa/timing-audit.json`: per voice and mode the worst early, late and readable offsets, the failures and a status, plus the limits of the check, and for No voice each tagged element's visible span (`visible_spans`; it prints the shortest). It exits 1 on any failure.

A manifest voice whose files are missing is reported as unavailable. Without `--strict` the run ends with an `INCOMPLETE` line and exits 0; with `--strict` it exits 1. Gate 4 stays unsigned while any voice is incomplete. A configured voices manifest that does not exist counts the same way: only No voice is audited and the run ends `INCOMPLETE`.

The page hooks it relies on are listed in [stage-contract.md](stage-contract.md#hooks-the-timing-audit-reads).

To check a real browser too, paste [timing-audit.js](../assets/timing-audit.js) into the console of a build and run `videoTimingAudit.inBrowser().then(r => console.log(r.status, r.failures))`. It uses computed styles and the page's own `__video.timeline()`.

## No voice

With No voice the audit uses the estimated cues: each sentence lasts its words at `make_cues.py`'s `--wps` (2.4 by default), and R4 keeps each element up at least that long. For text-only pieces, rerun `make_cues.py` with a lower `--wps` for every build, then `sync_embed.py` and the audit, until the owner, watching once at full length, says it reads well. The audit reports each element's visible span and prints the shortest; that is a report, not a rule.

Loops and text-only pieces: `script.txt` holds the on-screen lines, one paragraph per scene. End every on-screen line with `.`, `!` or `?` in `script.txt`, even when the screen shows it without: make_cues.py makes one cue per sentence, so unpunctuated lines merge into one cue.

- **One on-screen line per scene.** `--hold` (the hold after the scene's last line) and `--lead` (the lead into each scene) set the pace. With `--target-seconds`, the tail lands on the last line, so raise `--hold` until the printed times are even.
- **Every line in one scene.** `--breath` (the gap after each line) sets the pace. When the full build splits the lines into scenes, check the pace again on the full build's cues.
- **Both layouts:**
  - `make_cues.py --wps` sets the reading speed.
  - `--target-seconds <length>` reaches the owner's length. It sets the tail and fails when the lines need more time at this pace.
  - With `--target-seconds` or `--loop`, make_cues.py prints each line's longest time on screen, until its scene clears. For an element that a later beat clears with `{until: [k, f]}`, the audit's `visible_spans` in `qa/timing-audit.json` are the real figures.
  - `--title-card 0` drops the card only with the owner's confirmation recorded in `PLAN.md`. Keep its element in the page; the runtime keeps it hidden.
  - `--loop`: the page clears the last scene over the video's last second so the last state equals the first, and the audit checks that nothing is left at t = duration (see [export.md](export.md#loops)). When the tail after the last sentence is under 1 s, the fade takes the tail, and it still starts only after the last sentence ends.

## Seek determinism

The audit seeks a probe set forward, then in reverse, then shuffled, and compares a signature of every tagged element's opacity, the caption and the title card. Any difference fails, because a page that depends on its seek history cannot be captured to MP4 reliably. For a stricter check in a real browser, capture the same `?render=1&t=` twice and compare the PNG bytes.

## What the host checks

The audit covers timing logic. The host covers what it cannot see, in a real browser with sound:

- t = 0, the end of the title card, every scene start, and every take's last line, in both modes. [frame_review.py](../scripts/frame_review.py) writes the URLs and a "should show" note for each.
- Overlap, clipping, fonts and contrast at 1920x1080, inside the viewer, and at about 375 px wide.
- That every take's last line is heard.

The owner signs off on the gate after seeing the audit report and the host's notes.
