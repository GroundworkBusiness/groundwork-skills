# Viewer

One page that switches build, voice, music, mode and captions, and the contract each build meets so the viewer can drive it. The parent page is [viewer.html](../assets/viewer.html) with [viewer.json](../assets/viewer.json); the build side is in [the build template](../assets/build-template/index.html).

## Contents

- [Folder layout](#folder-layout)
- [Manifests](#manifests)
- [Build URL parameters](#build-url-parameters)
- [The viewer API](#the-viewer-api)
- [State messages](#state-messages)
- [The parent page](#the-parent-page)
- [Availability](#availability)
- [Serving](#serving)

## Folder layout

```
<project>/
  voices/voices.json          takes and their timing files
  music/tracks.json           beds
  <video-id>/
    viewer.html, viewer.json  the parent page
    build-a/index.html        cues.json points to ../../voices/voices.json and ../../music/tracks.json
    build-b/index.html
```

Serve `<project>/` so the relative paths resolve. For a series, each video keeps its script in `script/<video-id>/` and its takes in `voices/<video-id>/`: `voices.json` there, with the `<voice-id>/` take folders under it. That video's builds make their cues with `--voices-manifest ../../voices/<video-id>/voices.json`.

## Manifests

`voices.json` ([template](../assets/voices.json)) lists every take plus No voice. Fields: `id`, `label`, `kind` (`none`, `prebuilt`, `library`, `designed`, `recorded`, `local`), `vendor`, `model` (a dated id), `voice`, `audio` and `timing` (paths relative to the manifest), `created`, `regenerated_plain` (scenes whose current files were sent without tags), `regenerated` (ending-only regenerations that kept tags, added up over every run), `loudness_lufs` (the take's integrated loudness from `join_scenes.py`), and `note` (a known fault, shown in the build's control bar). Label voices from `kind` and `vendor`, never by parsing a provider string.

`tracks.json` ([template](../assets/tracks.json)) lists every bed with its measurements, source, rights and provenance. Page defaults `gain_with_voice`, `gain_no_voice`, `fade_in` and `fade_out` sit at the top; a track's own non-null values override them. Validate on load: unique ids, gains and fades finite and not negative.

Adding a take or a bed is a manifest edit. Run [sync_embed.py](../scripts/sync_embed.py) afterwards for use from disk.

## Build URL parameters

| Parameter | Meaning |
|---|---|
| `?t=<s>` | Open paused at a time, applied after the selected take loads. |
| `?mode=light` or `dark` | Look mode. |
| `?voice=<id>` | Take. Default: the manifest default. An unavailable id falls back to the default, then to No voice. |
| `?music=off` or `<id>` | Bed. Default: the manifest default. |
| `?cc=on` or `off` | Captions, default from `cues.json`'s `captions_default`, else on. `?captions=0` also turns them off; `?cc` wins when both are given. The viewer passes `cc` only once a choice is made, so a build opens on its own default. |
| `?embed=1` | Inside the viewer: hide the voice, music, mode and caption controls; keep play, time, timeline and scene buttons; fit the stage with no page scroll. |
| `?render=1` | Hide every control; never start sound. |
| `?vo=1` | Opt in to an unlisted `vo.wav` or `vo.mp3` in the page's folder. |
| `?loop=1` or `?loop=0` | Wrap playback to 0 at the end, or stop there. Default: the `loop` field of `cues.json` (`make_cues.py --loop`). |

## The viewer API

Builds add these to the base API in [stage-contract.md](stage-contract.md). Return types are fixed so every build behaves the same:

| Member | Contract |
|---|---|
| `voices()` | `[{id, label, available}]` in manifest order, including No voice. |
| `tracks()` | `[{id, label, available}]` with Off first. |
| `setVoice(id)` | Promise resolving to `state()`. Keeps the current scene and how far through it playback is; resumes if it was playing, stays paused if paused; a newer call wins over an older pending one. Rejects with an Error for an unknown or unavailable id, keeping the current take. |
| `setMusic(idOrOff)` | Promise resolving to `state()`. Replaces the bed without moving the playhead; Off keeps the gain at 0 while the video plays on. Rejects for an unknown or unavailable id. |
| `setMode(m)` | Applies live; returns `state()`. |
| `setCaptions(on)` | Applies live; returns `state()`. |
| `seekScene(n, f)` | Scene 1..N, fraction 0..1; returns `state()`. |
| `state()` | `{voice, music, mode, cc, t, scene, sceneFraction, playing, duration}`; `scene` is a number from 1. |
| `refresh()` | Re-reads the manifests (served only) and posts an availability message when something changed. |
| `timeline()` | Diagnostics: pre-roll, duration, sentences and scene windows in video time. |
| `timingWarnings` | The active take's repairs, as text. |
| `diagnostics()` | Voice and music element times, paused flags, the current music level, and whether Web Audio is in use. |

One meaning per name: no member returns a string id in one place and a number in another.

## State messages

Whenever the voice, music, mode, captions or scene (while playing) changes, and on play, pause, a seek from the build's own controls (scrub, keys, scene buttons) or `seekScene`, loop (a looping build wrapping to 0) and availability, a build posts `{type: '<message_type>', reason, ...state()}` to `window.parent` with target origin `location.origin`. The `message_type` comes from `cues.json` and matches `viewer.json`. From `file://` the origin is null, so builds send no messages there. The public `seek(t)` posts nothing, because capture, the audits and the compare page call it once per frame; a parent that calls it reads `state()` afterwards.

## The parent page

- A build switcher (buttons with `aria-pressed`), voice and music selects filled from the build's own `voices()` and `tracks()`, light or dark, captions, and a status line. One iframe with `allow="autoplay"`.
- State lives in the viewer's URL (`build`, `voice`, `music`, `mode`, `cc`) and is written back with `history.replaceState`, so a link reproduces the view.
- The iframe loads `<build>/index.html?embed=1&voice=..&music=..&mode=..&cc=..`.
- On load it awaits `__video.ready`. After a build switch it calls `seekScene` with the saved scene and fraction; when the old build was playing it says "Press Play to continue", because browsers block a silent resume.
- A control change calls the API method; when the call fails, the viewer reloads the iframe with the new settings and says so.
- It accepts messages only from `location.origin` with the expected `type`, and syncs its controls from them.
- Every 15 s it calls `refresh()` so takes that finish rendering become selectable.

## Availability

A take is available when both its audio and its timing file exist, the timing has the right scene and sentence counts, and, when both cues.json and the timing file record a `source_words_sha256`, those hashes match. A bed is available when its file exists. A track whose rights are pending (`rights` starts with "pending") or not recorded (null or empty) is held back: the served local preview still lists it so the owner can answer, labels it "(rights pending)" or "(rights not recorded)", starts such a default on Off and warns; from disk, `sync_embed.py` embeds it as not ready and its default is Off. Served, the build fetches each timing file and sends a HEAD request for each audio file; from disk, `sync_embed.py` decides. Unavailable entries show disabled with "(not ready)". A listed take whose files are missing produces a 404 in the console; that is expected until the files land.

## Serving

- Use a server that answers byte ranges with 206, or audio cannot seek: [serve_range.py](../scripts/serve_range.py). Python's built-in `http.server` ignores ranges. Check with a range request (see [example-local-tools.md](example-local-tools.md)).
- Bind 127.0.0.1. Bind the network address only when the owner asks to test on a phone. To test on a phone, run `serve_range.py --host 0.0.0.0` (or the machine's LAN address) and open `http://<LAN address>:8770/<video-id>/viewer.html` on the phone; stop the server afterwards.
- A scroll-triggered section hosts the same `?embed=1` build in an iframe and calls `play()` through the viewer API when it scrolls into view and `pause()` when it leaves.
- From `file://`, a media element routed through Web Audio plays silence in some browsers, so builds use the element's volume there and Web Audio only when served. Keep media on the same origin as the page.
- Browser device emulation can show compositing faults that real phones do not. Confirm on a real phone before deep debugging.
