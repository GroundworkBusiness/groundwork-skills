# Stage contract

The technical contract every look prototype and every full build meets. [The build template](../assets/build-template/index.html) implements all of it; start from that runtime and change the scenes.

## Contents

- [Starting from the template](#starting-from-the-template)
- [The page](#the-page)
- [The stage](#the-stage)
- [Controls](#controls)
- [The base API](#the-base-api)
- [URL parameters](#url-parameters)
- [Captions](#captions)
- [Images](#images)
- [Hooks the timing audit reads](#hooks-the-timing-audit-reads)
- [Viewer extensions](#viewer-extensions)
- [Capturing frames](#capturing-frames)
- [Checks](#checks)

## Starting from the template

Copy the template into the look's or build's folder, then:

- **Keep** the runtime script, the `window.__video` API, the controls, the audio code and the title card element (`data-title-card` with `tc-label`, `tc-title` and `tc-kicker`, which the runtime fills, and keeps hidden when `title_card.duration_s` is 0).
- **Replace** the scene CSS, the `<section data-scene>` blocks, the `BEATS` table, the mode branch in `renderBeat`, and, when the look has them, the `data-bg` background layer (a stage layer outside the scenes, always visible) and the `ambient(t, duration)` hook that `render(t)` calls on every frame.
- **Regenerate** `cues.json`: delete the copied one and run [make_cues.py](../scripts/make_cues.py) from `looks/sample-script.txt` for a look, or from `script/script.txt` for a full build.

## The page

- A single self-contained `index.html` in each look or build folder, with inline CSS and JS.
- The timeline, `render(t)` and `window.__video` live in a classic inline `<script>` that boots with no external globals: the timing audit runs only the page's inline classic scripts (it skips `src` scripts and rejects inline `type="module"`). At most two external scripts (`<script src>`) from a public CDN, each pinned to an exact version, may add optional enhancements behind a check that the global exists. Most looks need none.
- Web fonts are allowed; keep local fallbacks in every `font-family`, because sandboxed builders and offline previews cannot always fetch them.
- No autoplay. Sound starts only after the viewer presses Play.

## The stage

- A 1920x1080 frame, scaled uniformly to fit the window and letterboxed: `scale = min(width / 1920, height / 1080)`, applied as `translate(-50%, -50%) scale(s)` from a centred origin.
- The stage keeps its scale at every window size, including a 375 px wide phone and the small tiles of the compare page.
- Light and dark are one DOM and one timeline. A mode restyles type, colour, lighting and how things enter; timing never changes with it.

## Controls

- Outside the frame: play and pause, time, a scrub bar with every scene marked (click a scene to jump), captions on or off, light or dark.
- Keyboard, while no control has focus: Space toggles play, Left and Right move 0.5 s, Home and End seek to the start and the end.
- Controls wrap at 375 px wide.
- `?render=1` hides every control.

## The base API

`window.__video` exposes:

| Member | Contract |
|---|---|
| `duration` | Total length in seconds, including the title card and the tail. |
| `time` | Current time, read-only. |
| `playing` | Whether the clock runs, read-only. |
| `ready` | A promise that resolves after the data and fonts have loaded and the first frame has been painted. Await it before any call or capture. |
| `seek(t)` | Sets every element to the state it has at time t. One pure function of t: no wall clock, no `Date`, no unseeded randomness, no timers, no dependence on frame timing. Seeks in any order (forward, reverse, shuffled) give the same state. Clamps: `seek(-10)` gives 0, a time past the end gives `duration`, `seek(NaN)` gives 0. It posts no state message. |
| `frameReady()` | Optional. A promise that resolves when every stage `<video>` has decoded the frame for the current time, and at once when there is none. Export awaits it after every seek. |
| `clips()` | Optional; required when any stage `<video data-clip>` keeps its audio. Returns `[{file, in, rate, start, end}]` (plus `loop: true` for a `data-loop` clip): the file relative to the page, the in-point in seconds, the rate, and the video-time span the clip plays. Export writes it to `export/clips.json` for `mix_audio.py --clips`. |
| `play()` | Starts the clock. At the end, restarts from 0. With `"loop": true` in `cues.json` (or `?loop=1`), playback wraps to 0 at the end and keeps playing. |
| `pause()` | Holds the time. |
| `mode(name)` | Sets `light` or `dark`. An unsupported name leaves the mode unchanged. `mode()` with no argument returns the current mode. |

Playing past the end stops at `duration` and cancels the frame loop; the play button then reads Replay. A loop (`"loop": true`, written by `make_cues.py --loop`, or `?loop=1`) wraps to 0 instead; `?loop=0` turns the wrap off. With `"loop": true` the last scene fades out over the video's last second (never before its last sentence ends), so the stage holds only the background at t = duration.

Ambient motion (particles, drifting light) is a function of scene time with a seeded generator, or of video time in the `ambient(t, duration)` hook, so it is part of the deterministic state. For a loop, ambient motion repeats a whole number of times per duration, so t = duration paints the same frame as t = 0. The playback clock is the only code that reads `performance.now()`.

## URL parameters

| Parameter | Meaning |
|---|---|
| `?t=9.5` | Opens paused at the given time. |
| `?mode=light` or `?mode=dark` | Look mode. |
| `?render=1` | Hide every control and never start sound, for frame capture. |
| `?vo=1` | Opt in to an unlisted `vo.wav` (then `vo.mp3`) in the page's folder, played against the estimated timing. Without it the page requests no such file. |
| `?loop=1` or `?loop=0` | Wrap playback to 0 at the end, or stop there. Default: the `loop` field of `cues.json`. |

They combine: `?render=1&t=8&mode=dark`. Builds add the viewer parameters in [viewer.md](viewer.md).

## Captions

- Drawn in the page on a plate of their own, one cue for each sentence, matching the canonical script exactly (or the take's own sentences).
- At least 44 px at 1080p; the template uses 48 px with a line height of 1.22. High contrast on the plate in both modes.
- Keep teaching content above the caption band, so captions never cover the picture.
- Typographic apostrophes in captions.
- A caption shows from its sentence's start until the next sentence in the same scene starts. A scene's last caption clears at the earlier of the scene change and one second after its sentence ends. A sentence the take does not contain (a dropped ending) shows no caption.

## Images

While prototyping, draw a stand-in and list each wanted image in `image-requests.json` (or clip, with `"kind": "video"`):

```json
{"id": "counter-texture",
 "prompt": "Soft, out-of-focus kitchen counter surface in morning light. No text, no people, no logos, no objects.",
 "size": "1920x1080",
 "where": "Background layer behind scene 1",
 "blend": {"light": "multiply at 25% opacity", "dark": "screen at 7% opacity"},
 "stand_in": "flat gradient"}
```

End every prompt with its exclusions, and give the blend per mode. A full example: [image-requests.example.json](../assets/image-requests.example.json).

## Hooks the timing audit reads

[timing_audit.mjs](../scripts/timing_audit.mjs) runs the page's own script against a small DOM stand-in, so the page sets visibility in a way the stand-in can read:

- `render(t)` sets visibility through inline styles only: `opacity`, `display`, `visibility`, or the `hidden` attribute. Stylesheet rules are invisible to the audit. An element the script never touches counts as fully visible.
- The timeline core uses only basic DOM calls: `getElementById`, `querySelector`, `querySelectorAll` with simple selectors, `createElement`, `appendChild`, `textContent`, `style`, attributes and `classList`. Layout calls (`getBoundingClientRect`, `ResizeObserver`), Web Audio and `requestAnimationFrame` stay outside `render(t)` and are guarded.
- Markers:

| Attribute | Meaning |
|---|---|
| `data-title-card` | The title card element. |
| `data-scene="n"` | A scene container, numbered from 1. |
| `data-label` | The scene label, the one piece of text allowed on screen before narration. |
| `data-cue="c07"` | The sentence this element belongs to; ids come from [make_cues.py](../scripts/make_cues.py). |
| `data-cue-at="0.4"` | Optional: the element belongs to a key phrase 40 percent of the way through its sentence. |
| `data-captions` | The caption container. |
| `data-clip` | On a `<video>`: `render(t)` drives it from the timeline. Optional `data-in` (source in-point, seconds), `data-rate` (default 1) and `data-audio="keep"` (otherwise the element is muted). The anchor is `data-cue` and `data-cue-at`; a clip in the `data-bg` layer with no `data-cue` is anchored at t = 0, plays for the whole video and is not narration-tied. |
| `data-loop` | On a `data-clip` video: the source time wraps, `in + ((t - anchor) x rate) mod (clip length - in)`, so a background clip repeats. Make its length divide the video's duration. |
| `data-bg` | The background layer: outside the scenes, always visible, not narration-tied. |

Every piece of text inside a scene sits under a `data-cue` or `data-label` element. Text that stays up for the whole video and is not tied to narration, such as a whole-loop AI disclosure line in a corner, sits directly in `#stage`, outside every `[data-scene]` and outside `[data-bg]`, with no `data-cue`. `render(t)` leaves it alone, the audit's coverage and loop checks read only scenes and tagged elements, and R2 to R4 do not apply to it. Keep it clear of the caption band and readable in both modes.

## Viewer extensions

Full builds also implement the viewer API (`voices()`, `tracks()`, `setVoice`, `setMusic`, `setMode`, `setCaptions`, `seekScene`, `state()`), the parameters `?voice`, `?music`, `?cc` and `?embed=1`, and state messages to the parent. See [viewer.md](viewer.md).

## Capturing frames

Await `__video.ready`, call `pause()`, set the mode, then `seek(t)` and await `frameReady()` (when the page provides it) for each frame. Seeks may come in any order. For headless capture, load `index.html?render=1&mode=<m>&t=<seconds>` at 1920x1080. Name frames `frames/<voice>/<mode>-t<SSS.SS>.png` (voice `none` for a look) so they sort, as [frame_review.py](../scripts/frame_review.py) writes them. It writes the list and can run a capture command. Two separate renders of the same t can differ at the sub-pixel level when compositor hints such as `will-change` let positions vary; remove those hints before comparing bytes.

## Checks

- [static_check.py](../scripts/static_check.py) checks the API, forbidden time sources, external scripts, caption size and markers.
- [timing_audit.mjs](../scripts/timing_audit.mjs) checks R1 to R5 and seek determinism for every voice and mode.
- Neither proves layout, fonts, overlap or sound. The host checks those in a real browser, and every look's `LOOK.md` says what its checks did not prove.
