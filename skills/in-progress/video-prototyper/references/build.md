# Full build

How a full build is briefed, timed and kept retimable. The runtime is in [the build template](../assets/build-template/index.html); the contract is in [stage-contract.md](stage-contract.md).

## Contents

- [The build brief](#the-build-brief)
- [cues.json](#cuesjson)
- [Anchors](#anchors)
- [Retiming strategies](#retiming-strategies)
- [Clock and sync](#clock-and-sync)
- [Take edge cases](#take-edge-cases)
- [From disk and served](#from-disk-and-served)
- [Notes file](#notes-file)
- [Rules of thumb](#rules-of-thumb)

## The build brief

Write one brief for the whole video before any builder starts, from [the build brief template](../assets/templates/build-brief.md):

1. The approved narration, scene by scene, each with an "On screen" line saying what the picture shows beat by beat.
2. The owner's standing rules: audience wording, plain example names, which names may appear and where, facts never to state, the owner's length limit, or no limit, copied from `PLAN.md`.
3. Facts for the pictures: the true parts, order and grouping each scene depicts, so builders do not invent.
4. Timing until a voice exists.
5. The technical contract.
6. The required notes file.
7. A builds table: folder, which prototype it starts from, which builder, which look.

Hold the build until the owner has given the content for this video; the full video runs much longer than the prototype scene and its story needs the owner's input. Each picture carries the narration's meaning beat by beat: when the voice says three bins line up, three bins visibly line up. When the narration leans on a comparison, add a word on screen that stops viewers taking it literally.

## cues.json

[make_cues.py](../scripts/make_cues.py) writes it from `script.txt` and `scenes.json`. Every sentence of the script becomes one cue, and its id (`c01`, `c02`, ...) matches the sentence ids [align_words.py](../scripts/align_words.py) writes into every take's timing file, so a take's sentences map one to one onto the cues.

Shortened to scene 1's first cue; the full file is [cues.json](../assets/build-template/cues.json) (two scenes, seven cues).

```json
{
  "schema_version": 1,
  "title": "Three bins",
  "status": "estimated",
  "message_type": "video:state",
  "default_mode": "light",
  "pace": {"words_per_second": 2.4, "breath_after_sentence_s": 0.45, "scene_lead_s": 0.6, "scene_hold_s": 2.5},
  "title_card": {"duration_s": 3.5, "label": "Part 1", "title": "Three bins", "kicker": "Curbside sorting in Alder Creek"},
  "tail_s": 6.0,
  "duration": 40.45,
  "music": {"manifest": "../../music/tracks.json", "default": "off",
            "gain_with_voice": 0.5, "gain_no_voice": 1.0, "fade_in": 2.0, "fade_out": 4.0},
  "voices": {"manifest": "../../voices/voices.json", "default": "none"},
  "scenes": [
    {"id": "s1", "n": 1, "title": "First week", "label": "Week one", "start": 0.6, "end": 14.0,
     "on_screen": "A kitchen counter fills with four everyday items; a question appears.",
     "cues": [{"id": "c01", "start": 0.6, "end": 6.433, "text": "It's your first week in Alder Creek, and the kitchen counter is filling up."}]}
  ]
}
```

Cue times are narration time: seconds after the title card. They are estimates that serve No voice; recorded takes replace them at runtime. The `music` and `voices` blocks stay in this file so the export mix reads the same settings the page uses. Regenerate the file after any script change; `make_cues.py` keeps the title card, pace, music, voices, message type, default mode, loop, captions default and target length.

The estimate defaults (2.4 words per second, 0.45 s breath, 0.6 s lead, 2.5 s hold; flags `--wps`, `--breath`, `--lead` and `--hold`) give a calm reading pace. Real takes vary widely in pace; plan from the measured take.

## Anchors

Write every beat as an anchor `A(scene, k, f)`: cue k of the scene (from 0), fraction f of the way through it, read from the active timing. In the template a beat table lists `[element id, k, f]` plus an optional options object, for example `['s2-blue', 1, 0]` and `['s1-ask', 2, 0, {type: true}]` per scene, and one `render(t)` turns the table into state:

- A reveal starts 0.15 s before its anchor and runs 0.4 s, so the element is readable as its words arrive.
- `{type: true}` types the element's `data-type` text across its sentence, so quoted lines appear as spoken.
- `{until: [k, f]}` clears the element when a later beat replaces it.
- Scene windows: a scene starts after the previous scene's last sentence ends (or 0.6 s before its own first sentence, whichever is later) and cross-fades over 0.4 s.

Because anchors read the active timing, every voice retimes the whole picture with no code change. Write every reveal as an anchor.

## Retiming strategies

Anchors on the active timing are the only strategy: cues and take sentences map one to one, anchors read the active list, and every beat stays on its words for every voice. When the cue list and a take's sentences differ, the cues or the take are stale: check that `script.txt` and `scenes.json` were edited together (`cue_check.py`), rerun `make_cues.py` from the current script, renumber `data-cue` from the first changed sentence, regenerate or re-record only the changed scenes, and align again, as in [SKILL.md stage 12](../SKILL.md#12-iterate-after-output). Retime by moving anchors, never seconds.

## Clock and sync

- Video time t = pre-roll (the title card) + take time. Duration = pre-roll + the later of (last sentence end + tail) and the take's audio length.
- While the voice plays, its media clock drives the picture, but only while it agrees with the wall clock within 0.5 s and is not seeking; otherwise a `performance.now()` anchor drives it. No voice uses the wall clock only.
- Play, pause and seek re-sync voice and music. Correct music drift above 0.25 s while playing; snap within 0.05 s while paused.
- Nothing sounds on load, on seek, on a paused selection change, or in render mode.
- At the end the clock stops and Play restarts from 0. A loop (`"loop": true` in `cues.json`, written by `make_cues.py --loop`) wraps to 0 and keeps playing instead, and its last scene clears over the video's last second so the end matches the start. When the tail after the last sentence is under 1 s, the fade takes the tail, and it still starts only after the last sentence ends. `?loop=1` or `?loop=0` overrides only the playback wrap; the last scene clears only with `"loop": true`.

## Take edge cases

The template repairs these at load and lists each as a timing warning (on the API as `timingWarnings` and in the control bar). [timing_audit.mjs](../scripts/timing_audit.mjs) applies the same repairs when it computes expected times, and `sync_embed.py`, `mix_audio.py` and `frame_review.py` use them when they compute a take's length.

| Case | Repair |
|---|---|
| A take silently dropped its last line (trailing sentences shorter than 0.05 s) | Give each a silent slot 0.3 s after the previous sentence, sized by word count at 2.4 words per second; show no caption; note "last line not in the audio". The owner decides: regenerate the ending or keep the slot. Record the fault as a `note` in `voices.json`. |
| A zero-length sentence mid-take | Widen it up to the next sentence's start. |
| Sentence starts out of order | Clamp each start to at least the previous one. |
| Last sentence ends after the audio | Keep the data; warn. |
| Touching scene boundaries | `seekScene(n, f)` adds a microsecond and clamps f below 1, so the requested scene shows. |
| A take listed before its files exist | Show it as not ready; see [viewer.md](viewer.md). |

Never edit shared timing files from a build folder; fix them at the source (regenerate, re-align) or handle them in the page.

## From disk and served

Served over HTTP, the page fetches `cues.json`, the voice manifest and each take's timing, and the music manifest, with `cache: 'no-store'`. From `file://` it cannot read its neighbours, so [sync_embed.py](../scripts/sync_embed.py) embeds copies into `<script type="application/json">` blocks (`cue-data`, `voice-data`, `music-data`). Run it after any change to cues, manifests or takes. It marks a take available only when its audio and timing exist, the timing has the right scene and sentence counts, and the timing's `source_words_sha256` matches the one in `cues.json` when both record it.

## Notes file

Keep `SCENES-NOTES.md` ([template](../assets/templates/SCENES-NOTES.md)) current at the end of every pass: how to open it, timing, music, the shared viewer, scenes beat by beat, checks run, decisions, open questions. A reviewer checks the notes against the page, so stale notes are a finding.

## Rules of thumb

- Give every builder the same `cues.json` and estimate; two builders inventing two schemas cannot share takes.
- Keep estimated cues sentence-sized; a 30-word sentence makes a three-line caption.
- The picture holds a tail (6 s by default) after the last spoken sentence so the closing card stays readable.
- Use plain example names; draw quantities as marks or bars rather than digits unless the number is true and approved.
- Apply every pass to every live build until the owner drops one.
