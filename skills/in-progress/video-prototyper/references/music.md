# Music (gate 3)

How to offer music options, turn each into a bed that works under every take, mix it in the page, and record its rights. The bed builder is [make_bed.py](../scripts/make_bed.py); the manifest is [tracks.json](../assets/tracks.json).

## Contents

- [Options](#options)
- [Prompting generated music](#prompting-generated-music)
- [Checks on the source](#checks-on-the-source)
- [The bed](#the-bed)
- [Mixing in the page](#mixing-in-the-page)
- [The manifest](#the-manifest)
- [Rights and provenance](#rights-and-provenance)

## Options

Offer at least two, or one plus none:

| Option | Fits when | Watch for |
|---|---|---|
| Owner-supplied | The owner has a track they made or licensed | Who made it, with what, and whether it is a cover or derivative. |
| Generated | A bespoke bed is wanted quickly and cheaply | Non-determinism, vocals, watermarks, the vendor's terms. |
| Licensed library | A known, cleared track is needed | The licence's scope (web, broadcast, paid ads) and attribution. |
| None | Text-only explainers, or narration that must stand alone | Record the owner's confirmation. |

## Prompting generated music

Every bed prompt carries these, in any order:

- no vocals or singing;
- a length;
- what it plays under (spoken narration);
- the instruments;
- a tempo, with no drums or percussion;
- a constant level: no build, no drop, no ending and no fade-out.

For example:

```text
Use: background for a spoken how-to video. Instruments: nylon-string guitar, glockenspiel and upright bass. Tempo: 92 BPM; no drums, no percussion. Vocals: none. Length: about 2 min 30 s. Level: constant from the first bar to the last, with no intro build, no outro and no fade.
```

- The same prompt gives a different track each time. Generate two or three and pick by ear; keep every source.
- Many music models cannot continue a track; loop in the edit instead.
- When stitching clips, state the same key and tempo in every prompt.
- Requests naming a specific artist's voice or copyrighted lyrics are usually blocked.
- Record which model made which track; models differ in length per request, output format and whether they take negative prompts.
- Send each prompt with [api_media.py](../scripts/api_media.py) `--kind music`, dry run first, under [the spend guard](spend-and-credentials.md#the-spend-guard). Worked example: [example-media-providers.md](example-media-providers.md#worked-example-google-lyria-music-through-the-gemini-api).

## Checks on the source

- Keep every source byte for byte in `music/source/`. The bed is a derivative.
- Measure integrated loudness, true peak, and the loudness of the last 8 s (a quiet tail means the track fades out).
- Generated music can contain vocals even when the prompt says instrumental. Transcribe it (`--vocals-check` with `--stt-cmd`) and expect only non-speech markers.

## The bed

A bed is one file longer than the video with any take, at a fixed measured loudness, so the page only seeks it and one gain rule fits every track. Set `--min-seconds` to the longest video duration over every take and No voice, plus a margin of about 10 s. For No voice the duration is `duration` in `cues.json`; for a take it is the page's `__video.duration`, or the duration `mix_audio.py` prints. Both already include the pre-roll and the tail, and the fade-out ends inside them.

1. Trim any fade-in head and fade-out tail. `auto` keeps the stretch whose short-term loudness stays within 1.5 LU of the track's steady middle level. A steady edge is kept; `--trim-head` and `--trim-tail` override auto. A crossfade between two fading ends leaves an audible hole at the seam.
2. Join enough plays with an equal-power crossfade (6 s by default) to pass `--min-seconds`.
3. Apply one static gain so the bed lands near -30 LUFS integrated. A static gain keeps the music's own dynamics; a fixed, measured level makes the page gains mean the same thing for every track.
4. Encode (MP3 at 192 kbps or WAV) with metadata and cover art removed.
5. Verify: loudness within 1 LU of the target, peak below -1 dBFS, length at least `--min-seconds`.
6. Seam check: short-term loudness within 2 s of each seam must stay within 3 LU of the music 5 to 15 s either side. A failure means more tail to trim or a steadier section to loop.

```sh
python3 <skill>/scripts/make_bed.py --src music/source/bright-acoustic-1.mp3 --out music/bright-acoustic-bed.mp3 \
  --min-seconds 260 --id bright-acoustic --label "Bright acoustic" --origin generated --media-log media/media-log.jsonl \
  --vocals-check --stt-cmd "<transcriber> -m <model-file> -f {in} -np -nt"
```

`--src` is the path `api_media.py` printed on its `saved` line (`<name>-<n>.<ext>`); keep that name, because `--media-log` finds the track's record by it. With `--origin generated`, `--media-log` fills the entry's generation fields from the track's record in the media log (it prints a NOTE when the log has none). It prints a `tracks.json` entry with `rights` empty (or `pending: ...` when the title or file name says cover, remix or "in the style of"); record the owner's answer as in [Rights and provenance](#rights-and-provenance). Until then the track is not ready from disk and cannot be exported.

## Mixing in the page

- The bed plays from video t = 0 (including the title card) and seeks with the video. The voice starts after the pre-roll.
- Level at time t: `(off ? 0 : (voice is none ? gain_no_voice : gain_with_voice)) x clamp(t / fade_in) x clamp((duration - t) / fade_out)`. Defaults: 0.5 under a voice (about -36 LUFS, about 14 dB under speech near -22 LUFS), 1.0 with no voice, 2 s fade in, 4 s fade out ending on the last frame.
- Route the element through a gain node when served, with a second gain stage for 0.15 s ramps on play and pause (no clicks), pausing the element about 170 ms after the ramp.
- Create or resume the audio context on the first Play; browsers keep it silent until a user gesture.
- From `file://`, set the element's `volume` instead: a media element routed through Web Audio plays silence there in some browsers.
- While playing, re-sync when the bed drifts more than 0.25 s from the timeline; while paused, snap within 0.05 s. Past the bed's end, pause it. The bed never loops in the page.
- No sound before Play, in render mode, or on a paused selection change.

## The manifest

Top-level defaults (`gain_with_voice`, `gain_no_voice`, `fade_in`, `fade_out`) and per-track overrides when not null. Per track: `id`, `label`, `file`, `seconds`, `loudness_lufs`, `peak_dbfs`, `source_file`, `origin`, `generated_with` (the endpoint or tool), `requested_model`, `reported_model`, `generated_on`, `prompt`, `cost_list_usd`, `rights`, `rights_cleared_by`, `rights_cleared_on`, `watermark`, `content_credentials_in_source`, `vocals_checked`, `seam_check`, and `bed` (plays, crossfade, trims, gain and each seam's measurement, as make_bed.py prints them). The viewer and the rights record are then one file, and adding a bed never touches page code.

## Rights and provenance

- Ask who made an owner-supplied track, with what, and whether it is a cover, remix or derivative. Embedded tags (artist, title, date) are leads, not proof. Record the answer and the date.
- A title containing "cover", "remix" or "in the style of" raises a composition-rights question, even when the recording is the owner's own. Ask the composition-rights question as soon as the track arrives. Building and measuring the bed may go ahead, because it is local. Until the owner answers, list the track with `rights` set to `pending: <question>, asked <date>`, keep it out of the default and out of any export or shared build, and carry the question in the report. The served local preview still plays it so the owner can answer; `sync_embed.py` embeds it as not ready and `mix_audio.py` refuses to export it. Before a served build is shared beyond the owner, take the track's entry out of `tracks.json` until the rights are answered, then run `sync_embed.py` for every build. A track with no rights recorded (null, as `make_bed.py` prints them for a track it does not flag) is handled the same way. The served page adds "(rights pending)" or "(rights not recorded)" to the label, so keep the label itself plain.
- For generated music, read the vendor's terms for the exact model on the day (ownership, exclusivity, commercial use) and record a summary with the date.
- Generated files can carry an invisible watermark in the signal (which survives edits and re-encoding) and a content-credentials manifest in the container (which a re-encode strips). Keep the untouched source as the provenance record; never point to the bed as evidence.
- When any voice, music, images or footage is generated, the video carries a disclosure line on its closing card and on the hosting page; for a loop or a piece without a closing card, where PLAN.md places it (see [script](script.md#disclosure-card)).
