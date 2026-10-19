# Generated images and video

How to bring generated images and clips into a build without losing control of cost, quality or provenance. Run this stage only when the owner chose generated media or screen recordings; screen recordings use [Video on the timeline](#video-on-the-timeline). Provider examples: [example-media-providers.md](example-media-providers.md).

## Contents

- [Stand-ins first](#stand-ins-first)
- [From requests to prompts](#from-requests-to-prompts)
- [Paired generation](#paired-generation)
- [Without an API: a built-in generator or a web app](#without-an-api-a-built-in-generator-or-a-web-app)
- [Images](#images)
- [Placing picked images](#placing-picked-images)
- [Video clips](#video-clips)
- [Video on the timeline](#video-on-the-timeline)
- [The generation record](#the-generation-record)
- [Provenance and disclosure](#provenance-and-disclosure)

## Stand-ins first

Looks and builds draw stand-ins and list wanted images in `image-requests.json` ([example](../assets/image-requests.example.json)). Generation waits until the look is picked, so the look is judged on motion and type, and the owner chooses the generator with the look in hand. At stage 8, once each shortlisted look has its build folder, merge the shortlisted looks' and builds' `image-requests.json` entries into `media/image-requests.json`, the one list this stage works from and where `picked` is set. A wanted clip is listed the same way, with `"kind": "video"` and its length, loop and audio needs in `where`. An entry without `kind` is an image.

## From requests to prompts

1. Each request has `id`, `prompt`, `size`, `where` and a per-mode `blend`.
2. Write prompts that describe the picture. Keep production words (asset, deliverable, module, workflow) out: generators turn instruction nouns into on-screen headings.
3. End every prompt with its exclusions: no text, no people, no logos, as the slot needs.
4. Make one small test first, on the owner's yes, within a cap. Dry-run it with [api_media.py](../scripts/api_media.py), which prints the request and the estimated list cost and writes nothing. Then run it live.
5. Download every result at once; some servers delete generated media within days.

## Paired generation

When two tools are available, generate each request on both with its own `--name` per tool (for example `<id>-<tool>`) and let the owner pick per slot. Name the winner as the style lead for later prompts and record it in `PLAN.md`.

## Without an API: a built-in generator or a web app

When the image or clip tool is the agent tool's own generator, or a web app that the owner drives (or the agent drives by browser, with the owner signed in):

1. State the estimate: the price per image or clip from the plan or price page, or 'included in the owner's plan'.
2. Get the owner's yes and the cap. When the tool charges per item, reserve each item before making it: `python3 <skill>/scripts/spend_ledger.py --reserve media/ledger.jsonl --kind <image|video|music> --unit <image|second|track> --est-usd <estimate> --cap-usd-day <cap> --cap-usd-project <cap> --note <request id>`. For a clip, pass `--units <seconds> --unit second`, as the API route does; `--est-usd` is the whole clip's estimate. It checks the caps under the ledger's lock, exits 3 when a cap would be passed, and prints the reservation id.
3. Save each result at once under `media/generated/`, or `music/source/` for audio, keeping the file as the tool gave it, and check its real file type. A built-in generator may write into the agent tool's own folder rather than the project: copy the file from the path its result names, or find it there by modification time. When the tool only shows the result in the chat, ask the owner to save it into `media/generated/` (or `music/source/`).
4. Append one line to `media/media-log.jsonl` with the fields of [the generation record](#the-generation-record). Set `endpoint` to `built-in-generator` or `web-app: <app name>`, and set each field the tool does not report to null.
5. For a reserved item, record its outcome: `python3 <skill>/scripts/spend_ledger.py --outcome media/ledger.jsonl --ref <id> --status completed` (or `failed`), so the caps keep counting it.

A file the owner saves by hand from a web app goes in the same place and gets the same log line.

## Images

- Pin the model. An "auto" choice hides which model ran, so results cannot be reproduced.
- Check the real file type of every export with a file-type tool; an image named `.png` can be another format.
- Magnify every piece of in-image text several times over at its final display size; the same words can come out clean when large and broken when small. Editing the prompt can correct a misspelt word; a malformed letterform needs a new generation or text drawn in code.
- Density or detail controls in some apps raise the error rate in text; prefer the standard setting for images with words.
- Exact colours and typefaces are not honoured by generators. Brand-exact colour and type come from code or a designed template rendered to PNG.
- A generator's workspace usually cannot see earlier ones, so asking it to "match the earlier style" fails; describe the qualities instead.
- Record which model made which image; models differ in text, lettering and photoreal strength, and those strengths change between versions.

## Placing picked images

1. Keep the untouched original under `media/generated/`.
2. Set the request's `picked` in `media/image-requests.json` to that path, and log the pick in `PLAN.md`.
3. In each build, replace the stand-in with an `<img>` or a CSS background referencing `../../media/generated/<file>` (a build folder sits two levels below the project), and apply the request's per-mode `blend`.
4. Run `sync_embed.py`, `static_check.py` and `timing_audit.mjs` for each build; the host then checks both modes in a real browser.

## Video clips

- Many agent tools have image generation but no video generation. Probe first; a direct API call with a spend guard fills the gap.
- Generated clips often carry an audio track even when none is wanted. Prompt "no dialogue, no music", then strip the audio in the edit.
- Loops: pass the same still as the first and last frame where the model supports it. Ping-pong (forward then reversed) is a fallback, though the reversal shows. Check the seam frame by frame.
- Large results may come back as a link instead of inline data; download it before it expires.
- Duration and resolution parameter formats vary and are sometimes undocumented; dry-run first and read the response.
- Latency ranges from seconds to minutes; jobs may run as long operations. Poll every 10 s or so ([api_media.py](../scripts/api_media.py) `--poll`), and never resubmit a job that may have billed.
- Cap at a resolution with a published price; upscaled resolutions sometimes have none.
- The same model can have different ids and locations on different platforms. Keep one table per platform and use each id only on its own platform.
- One request makes one clip. Prompts have a length cap; keep them short and concrete.

## Video on the timeline

Clips and screen recordings use the same placement.

- Keep the file under `media/`. Leave the untouched original under `media/generated/` for a generated clip, or `media/source/` for a screen recording.
- Strip the audio unless the owner wants it kept, and record the choice. A screen recording is footage. A generated clip follows the disclosure line under Provenance.
- A background clip that runs the whole video goes in the `data-bg` layer with no `data-cue`: it is anchored at t = 0 and is not narration-tied. With `data-loop` it repeats; make its length divide the video's duration (a 4 s clip loops five times in 20 s). The export mix plays a clip's kept audio once, so keep a looping clip's audio stripped.
- Place the in-point with a cue anchor `A(scene, k, f)`, not a baked second. On the `<video>`: `data-clip`, `data-cue`, optional `data-cue-at`, `data-in` (source in-point, seconds) and `data-rate` (default 1). `data-audio="keep"` leaves the audio; otherwise `render(t)` mutes the element. Export mixes kept clip audio through `__video.clips()` and `mix_audio.py --clips`.
- In `render(t)`, set `currentTime` to the source in-point plus `(t - anchor time) × rate`, clamped to the file (with `data-loop`, wrapped over it instead). The page plays each clip at its rate while its scene is visible and pauses it otherwise. While playing, re-sync only when it drifts more than about 0.1 s. While paused, or under `?render=1`, set it exactly and wait for `seeked`.
- `__video.frameReady()` resolves when every stage `<video>` has decoded the current frame, and at once when there is none. The export example awaits it after every seek. A look does not need a video element.

## The generation record

[api_media.py](../scripts/api_media.py) appends one line per file to `media/media-log.jsonl`:

```json
{"created_at": "2026-01-31T12:00:00Z", "name": "pool-loop", "kind": "video", "out": "media/generated/pool-loop-1.mp4",
 "mime": "video/mp4", "bytes_written": 3100000, "endpoint": "<endpoint>", "requested_model": "<id sent>", "reported_model": "<id returned>",
 "operation": "<operation id>", "prompt": "...", "estimated_cost": {"usd": 0.9, "units": 6, "unit": "second", "unit_usd": 0.15, "basis": "<price page and date>"},
 "watermark": "<vendor watermark>", "content_credentials": "unchecked", "ledger_id": "...", "duration_s": 6.0, "resolution": "1280x720", "has_audio": false}
```

The response can report a different model than the one requested; record both and reconcile against the billing line the next day.

## Provenance and disclosure

- Generated files can carry two provenance layers: an invisible watermark in the signal, which survives cropping, re-encoding and speed changes, and a content-credentials manifest in the container, which any re-encode or metadata strip removes. Keep the untouched original as the provenance record; derivatives are not evidence.
- Decide deliberately whether published derivatives should carry content credentials.
- Anyone can check a file with the vendor's detector, so disclose. When any voice, music, images or footage is generated, the closing card and the hosting page carry one plain disclosure line; the owner decides the wording. For a loop or a piece without a closing card, show the line small for the whole loop: directly in `#stage`, outside every `[data-scene]` and outside `[data-bg]`, with no `data-cue` (see [the stage contract](stage-contract.md#hooks-the-timing-audit-reads)), or on the hosting page and beside the screen, as the owner decides.
- Keep every visible AI label in the export.
