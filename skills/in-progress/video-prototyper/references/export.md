# Export to MP4

How to render the chosen build, voice and bed into a video file. The page is deterministic (`seek(t)` sets the exact state for any t), so export is: capture frames by seeking, mix the audio the way the page plays it, encode, and compare with the viewer. Check the first export on any new setup frame by frame and by ear before relying on the procedure.

## Contents

- [Inputs](#inputs)
- [Audio](#audio)
- [Frames](#frames)
- [Encode](#encode)
- [Loops](#loops)
- [Checks](#checks)

## Inputs

- The chosen build folder, voice id, bed id (or Off), mode (as recorded at intake; export once per mode when the MP4 ships in both), and captions on or off.
- The build's `cues.json`, the take's timing file, `tracks.json`.
- Duration = pre-roll + the later of (last sentence end + tail) and the take's audio length: the same rule the page uses, and what `__video.duration` reports.

## Audio

[mix_audio.py](../scripts/mix_audio.py) mixes from the same settings the page uses: the voice delayed by the title card, the bed from t = 0 at `gain_with_voice` (or `gain_no_voice`), a fade in over `fade_in` seconds and out over the last `fade_out` seconds, per-track overrides from `tracks.json`, and any stage clip that keeps its audio (`data-audio="keep"`).

```sh
python3 <skill>/scripts/mix_audio.py --cues <video-id>/<build-id>/cues.json \
  --voice-audio voices/<voice>/<voice>.wav --timing voices/<voice>/<voice>-timing.json \
  --bed music/<bed>.mp3 --tracks music/tracks.json --track-id <bed-id> \
  [--clips export/clips.json] --out export/mix.wav [--target-lufs -16]
```

Pass `--clips export/clips.json` when any clip keeps its audio (written from `window.__video.clips()`, as in the Playwright example below); when a clip keeps its audio, run the capture before this mix. It prints the duration and the measured loudness. `--target-lufs` normalises the whole mix for a delivery platform's loudness target. `<bed-id>` is the bed's `id` in `music/tracks.json`, the --id given to make_bed.py.

## Frames

Serve the project ([serve_range.py](../scripts/serve_range.py)) as in [the by-hand guide's Looks block](../workflows/by-hand.md#looks-gate-1), and use the port it serves on (8770 by default) in the capture URLs below. Capture `index.html?voice=<id>&music=off&render=1&mode=<m>&cc=<on|off>&t=<seconds>` at 1920x1080 for every frame time `k / fps`. Wait for `__video.ready` before each capture.

The simplest capture needs no packages: one headless browser process per frame (command in [example-local-tools.md](example-local-tools.md)). Treat it as a low-rate diagnostic. It is slow (around a second a frame), and a screenshot taken on page load cannot await `__video.ready`, so a frame can miss fonts or data. `--virtual-time-budget` (for example 3000 ms) gives the page time to settle before the shot, but check its frames against the viewer at the same times. The Playwright example below awaits `ready` and is the route for a real export.

Each export captures into a fresh folder, so frames left from an earlier, longer capture never extend the file, and encodes exactly the number of frames it captured. Old frame folders stay for the owner to remove.

Before capturing, open the same URL once without `render=1` and run `__video.state()` in the page's console: `voice` must be the voice you will mix. An unavailable take falls back to the default voice, then to No voice, with no message.

The loop is bash; on Windows run it in Git Bash or WSL.

```sh
# <duration>: the page's __video.duration for the chosen voice, in seconds
F=export/frames-<voice>-<mode>-<cc>-$(date +%Y%m%d-%H%M%S)   # a fresh folder per export
mkdir -p "$F"
i=0
LOOP=0   # 1 for a loop: t = duration equals t = 0, so it is left out
for t in $(python3 -c "d = <duration>; ks = range(round(d*30)) if $LOOP else range(int(d*30) + 1); print(' '.join(f'{k/30:.4f}' for k in ks))"); do
  # cc: the export's caption choice; captions are burned in when on
  "<chrome binary>" --headless=new --hide-scrollbars --window-size=1920,1080 --virtual-time-budget=<ms> \
    --screenshot=$(printf "$F/f%05d.png" $i) \
    "http://127.0.0.1:8770/<video-id>/<build-id>/index.html?voice=<id>&music=off&render=1&mode=<mode>&cc=<on|off>&t=$t"
  i=$((i+1))
done
echo "captured $i frames into $F; encode with -frames:v $i"
```

Worked example (Playwright for Node, labelled; check its current docs at https://playwright.dev/docs/library and https://playwright.dev/docs/browsers): one browser page, one load, then seek and screenshot per frame, which is much faster for long videos. Save it as `export-frames.mjs` in `<project>/`. With the owner's yes (an install: name the package and its source, npm), run `npm install playwright` in `<project>/`. The library needs a browser: with Chrome or Edge already installed (the tool probe reports it), launch with `chromium.launch({ channel: 'chrome' })` (or `'msedge'`), which needs no download; otherwise run `npx playwright install chromium`, a browser download that needs the owner's yes. Then run `node export-frames.mjs`.

```js
// npm install playwright, after the owner's yes (an export-time dependency; the skill's scripts do not need it)
import { chromium } from 'playwright';
import fs from 'node:fs';
const LOOP = false; // true for a loop: leave out t = duration, which equals t = 0
const F = `export/frames-<voice>-<mode>-<cc>-${new Date().toISOString().replace(/[-:]/g, '').slice(0, 15)}`; // a fresh folder per export
await fs.promises.mkdir(F, { recursive: true });
// Chrome or Edge installed: channel 'chrome' (or 'msedge') needs no download.
// Otherwise run `npx playwright install chromium` first (the owner's yes) and call chromium.launch() with no channel.
const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
// cc: the export's caption choice; captions are burned in when on
await page.goto('http://127.0.0.1:8770/<video-id>/<build-id>/index.html?voice=<id>&music=off&render=1&mode=<mode>&cc=<on|off>');
await page.evaluate(() => window.__video.ready);
const st = await page.evaluate(() => window.__video.state());
if (st.voice !== '<id>' || st.mode !== '<mode>') {
  throw new Error(`page fell back to voice ${st.voice}, mode ${st.mode}; check the take's files and voices.json`);
}
const clips = await page.evaluate(() => (window.__video.clips ? window.__video.clips() : []));
await fs.promises.writeFile('export/clips.json', JSON.stringify(clips, null, 2));
const duration = await page.evaluate(() => window.__video.duration);
const last = LOOP ? Math.round(duration * 30) - 1 : Math.floor(duration * 30);
for (let k = 0; k <= last; k++) {
  await page.evaluate(t => window.__video.seek(t), k / 30);
  await page.evaluate(() => (window.__video.frameReady ? window.__video.frameReady() : Promise.resolve()));
  await page.screenshot({ path: `${F}/f${String(k).padStart(5, '0')}.png` });
}
await browser.close();
console.log(`captured ${last + 1} frames into ${F}; encode with -frames:v ${last + 1}`);
```

## Encode

```sh
# <frames folder> and <N>: the folder and the frame count the capture step printed
ffmpeg -framerate 30 -i <frames folder>/f%05d.png -i export/mix.wav -frames:v <N> \
  -c:v libx264 -pix_fmt yuv420p -movflags +faststart -c:a aac -b:a 192k -shortest export/<video-id>.mp4
```

`yuv420p` keeps the file playable everywhere; `+faststart` lets it start before it fully downloads. Captions are burned in when the frames were captured with `cc=on`; for a separate caption file, use the same cue source as the WebVTT file below.

For a toggle, ship a WebVTT file: one cue per sentence, from the take's timing file (`sentences[]`) for a voice, or from `cues.json` (`scenes[].cues[]`, flattened) for No voice; for either source use its `text`, `start` and `end`, adding the pre-roll (`title_card.duration_s` in `cues.json`) to both times. Capture the frames with `cc=off`, then ship the `.vtt` beside the MP4 or mux it with `ffmpeg -i export/<video-id>.mp4 -i export/<video-id>.vtt -c copy -c:s mov_text export/<video-id>-cc.mp4`. For example, with a 3.5 s pre-roll and the first sentence of [timing.example.json](../assets/timing.example.json), timed 0.00 to 4.01 s:

```
WEBVTT

00:00:03.500 --> 00:00:07.510
It's your first week in Alder Creek, and the kitchen counter is filling up.
```

## Loops

For a muted loop on a screen: capture with no voice and music off, skip `mix_audio.py` when voice and music are both none and no clip keeps its audio, and encode without an audio track (`-an`).

- Design the end state to equal the start: with `make_cues.py --loop` the page clears the last scene by the end, so t = duration paints the same frame as t = 0 (or cross-fade the last second into the first).
- Capture k = 0 to duration x fps - 1 and encode exactly duration x fps frames. The state at t = duration equals the state at t = 0, so leave that time out of the capture; the last captured frame is k = duration x fps - 1. Make the duration a whole number of frames (`make_cues.py --target-seconds`).
- In the bash loop set `LOOP=1`; in the Playwright example set `LOOP = true`.
- Check the seam by playing the file on repeat and stepping across the join frame by frame.

```sh
# <N> = duration x 30, the count the capture step printed
ffmpeg -framerate 30 -i <frames folder>/f%05d.png -frames:v <N> -c:v libx264 -pix_fmt yuv420p -movflags +faststart -an export/<video-id>.mp4
```

## Checks

- After `ready`, `__video.state().voice` equals the voice that was mixed. An unavailable take falls back to the default or to No voice without any message.
- The MP4's duration equals the page's `__video.duration` for that voice (pre-roll plus the later of the last sentence end plus the tail, and the take's audio length), within one frame.
- Frames at every scene start match the viewer at the same time and settings ([frame_review.py](../scripts/frame_review.py) lists those times).
- The mix's loudness is as printed; the peak stays below -1 dBFS; no clipping.
- Burned-in captions match the take's sentences, or the `cues.json` cues for No voice.
- Toggle: the WebVTT file ships beside the MP4 or muxed into it, one cue per sentence, offset by the pre-roll.
- Every take's last line is heard.
- For a loop, the frame count is N = duration x fps, captured at k / fps for k = 0 to N - 1, leaving out t = duration; the state at t = duration equals the state at t = 0; play the file on repeat and step across the seam frame by frame to check that motion is continuous. Identical adjacent frames at the seam are fine when the design holds still there.
- A generated-media disclosure line is on the closing card, or where `PLAN.md` records it for a loop, when any voice, music, images or footage is generated.
