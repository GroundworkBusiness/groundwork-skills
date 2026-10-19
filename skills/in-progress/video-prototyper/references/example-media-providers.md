# Worked examples: music, images, clips, billing and provenance

Real providers used the way [music.md](music.md), [generated-media.md](generated-media.md) and [spend-and-credentials.md](spend-and-credentials.md) describe. Each block is dated and links the vendor's documentation. Prices, limits, model ids and endpoints change; re-check the vendor's current docs before relying on any of them. Where a line says a provider "can" or "may" do something, that behaviour was seen in use but is not documented; check it on your own first request. No account figures appear here.

## Contents

- [Lyria music through the Gemini API](#worked-example-google-lyria-music-through-the-gemini-api)
- [Image generation through the Interactions API](#worked-example-google-gemini-image-generation-through-the-interactions-api)
- [Generated video clips](#worked-example-google-veo-and-gemini-omni-clips)
- [The prepaid billing gate](#worked-example-google-gemini-api-prepaid-billing)
- [The enterprise cloud route](#worked-example-google-cloud-enterprise-route)
- [Watermarks and content credentials](#worked-example-google-synthid-and-c2pa-content-credentials)

## Worked example: Google Lyria music through the Gemini API

Checked 2026-10-15; re-check the vendor's current docs before relying on it.

Docs: https://ai.google.dev/gemini-api/docs/music-generation, https://ai.google.dev/gemini-api/docs/lyria-prompt-guide, https://ai.google.dev/gemini-api/docs/pricing

```json
{"model": "<music model id, for example lyria-3.5>", "input": "<the music prompt>", "response_format": {"type": "audio"}}
```

sent to `POST https://generativelanguage.googleapis.com/v1beta/interactions` with the key in the `x-goog-api-key` header.

- Adding a `delivery` field can be rejected for audio ("Audio delivery mode is not supported").
- A request can return HTTP 400 with no reason, and the identical body can succeed when resent. `api_media.py` prints the error's status and message and saves the body; resend once under a new reservation only when the message names no field.
- A response can carry `status: completed`, then `steps[]`: a text step holding only section markers for an instrumental, then an audio step with `mime_type: audio/mpeg` and base64 `data`. Decode `steps[].content[]` where `type` is `audio`. Docs can describe a different shape (such as a top-level audio field); parse the live response.
- Output is MP3 at 44.1 kHz. The music page says Lyria 3.5 can also return WAV by setting `response_format`, but its sample shows only `{"type": "audio"}` (checked 2026-10-16); dry-run a WAV request and read the response's `mime_type` before relying on it. A lossless source makes a better bed and provenance record. A track can fade out over its last seconds; measure it and trim the fade before looping.
- Request a model id the music page lists. The response's `model` field can name a different model from the one requested: a request for an unlisted id can come back reporting a listed one. Record both and reconcile with the billing line.
- Billed per track, at a list price per model (a short-clip model and a full-song model can differ); read it on the pricing page on the day. An older instrumental-only WAV model that takes negative prompts is not on the developer API's music page; check which platform offers it before planning on it.
- Transcribe each track; an instrumental gives only a non-speech marker.

With this skill:

```sh
python3 <skill>/scripts/api_media.py --endpoint https://generativelanguage.googleapis.com/v1beta/interactions \
  --body media/music-request.json --name bright-acoustic --out-dir music/source --key-env <VARIABLE_NAME> \
  --auth header:x-goog-api-key --kind music --prompt-field input --units 1 --unit track --unit-usd <per-track list price> \
  --price-basis "list price per track, read <date>" --ledger media/ledger.jsonl --cap-usd-request <the owner's per-track cap> \
  --types audio --log media/media-log.jsonl --dry-run
```

## Worked example: Google Gemini image generation through the Interactions API

Checked 2026-10-16; re-check the vendor's current docs before relying on it.

Docs: https://ai.google.dev/gemini-api/docs/image-generation, https://ai.google.dev/gemini-api/docs/pricing

```json
{"model": "<image model id, for example gemini-nano-banana-2.1>",
 "input": [{"type": "text", "text": "<the image prompt, ending with its exclusions>"}],
 "response_format": {"type": "image", "mime_type": "image/png", "aspect_ratio": "16:9", "image_size": "2K"}}
```

sent to `POST https://generativelanguage.googleapis.com/v1beta/interactions` with the key in the `x-goog-api-key` header.

- The page's basic REST sample sends `model` and `input` only. Other samples add `response_format` with `type: "image"`, `mime_type` (`image/png` or `image/jpeg`), `aspect_ratio` and `image_size`. The values above are the ones the samples show. `image_size` takes an uppercase K (1K, 2K, 4K; some models also 512px, written 0.5K); lowercase is rejected. The page lists aspect ratios per model; read the list for the model you send, and dry-run first.
- Response: the page shows no raw response JSON; its SDK samples read the image as base64 (`interaction.output_image.data`). `api_media.py` reads `content[]` items of type `image` with base64 `data`, the Interactions shape the music and clip examples use. Read the first live response; when the script finds no image of the wanted type, it saves the response for you to check.
- Gemini 3 image models think by default and can return up to two interim "thought images" in steps of type `thought` (read from `summary[]` in the page's SDK samples); they are not charged and are not the result (checked 2026-10-16). The final image is the last image block (the SDK's `output_image`). `api_media.py` prefers images outside thought steps and prints how many interim images it skipped. When a response holds images only inside thought steps, it keeps the last one, which the page calls the final rendered image, prints that it did, and marks its media-log record `from_thought_step: true`; look at that image before using it.
- Price: billed per image, by model and output size; read the row for the model and size you send on the pricing page on the day.

With this skill (check `--prompt-field input.0.text` against your own body in the dry run's printed body):

```sh
python3 <skill>/scripts/api_media.py --endpoint https://generativelanguage.googleapis.com/v1beta/interactions \
  --body media/image-request.json --name <id> --out-dir media/generated --key-env <VARIABLE_NAME> \
  --auth header:x-goog-api-key --kind image --types image --prompt-field input.0.text --units 1 --unit image \
  --unit-usd <per-image list price for this model and size> \
  --price-basis "list price per image, <price-page row>, <size>, read <date> at https://ai.google.dev/gemini-api/docs/pricing" \
  --ledger media/ledger.jsonl --cap-usd-request <cap> --log media/media-log.jsonl --dry-run
```

## Worked example: Google Veo and Gemini Omni clips

Checked 2026-10-15; re-check the vendor's current docs before relying on it.

Docs: https://ai.google.dev/gemini-api/docs/veo, https://ai.google.dev/gemini-api/docs/omni, https://ai.google.dev/gemini-api/docs/pricing

Request (Veo, checked 2026-10-15). Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/models/<veo model id>:predictLongRunning`, with the key in the `x-goog-api-key` header. Example ids: `veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview`, `veo-3.1-lite-generate-preview`.

```json
{"instances": [{"prompt": "<the clip prompt, ending with its exclusions>",
                "image": {"inlineData": {"mimeType": "image/png", "data": "<base64 of the first frame>"}},
                "lastFrame": {"inlineData": {"mimeType": "image/png", "data": "<base64 of the same still, for a loop>"}}}],
 "parameters": {"aspectRatio": "16:9", "resolution": "720p", "durationSeconds": "8"}}
```

Field notes: `aspectRatio` is `"16:9"` or `"9:16"`. `resolution` is `"720p"`, or `"1080p"` (8 s only); `"4k"` exists only on 3.1 and 3.1 Fast. `durationSeconds` is a string: `"4"`, `"6"` or `"8"`. `lastFrame` must be used together with `image`. The page's interpolation section says first-and-last-frame works on Veo 3.1 models only, while its parameter table lists it for every model, so label first-and-last-frame "verify on the chosen model". For a background loop, pick `durationSeconds` so the clip's length divides the video's duration ([generated media](generated-media.md#video-on-the-timeline)): `"4"` for a 20 s video; `"4"`, `"6"` or `"8"` for a 24 s video. Set `--units` to the same number. 1080p and 4k allow only `"8"`.

Flow: the start response carries the operation `name`. Poll `GET https://generativelanguage.googleapis.com/v1beta/<name>` with the same header every 10 s or so until `done` is true. The video link is at `response.generateVideoResponse.generatedSamples[0].video.uri`; download it with the key header, following redirects. Generated videos are stored on the server for 2 days, then removed (Veo page, Limitations, checked 2026-10-16). Billed per second of video, at a list price per model tier and resolution; read the rates on the pricing page on the day. Video is billed only when a video is generated. Offline, with no price page, use a worst-case per-second figure the owner sets, and say so in `--price-basis`.

```sh
python3 <skill>/scripts/api_media.py \
  --endpoint https://generativelanguage.googleapis.com/v1beta/models/<veo model id>:predictLongRunning \
  --body media/clip-request.json --name water-loop --out-dir media/generated --key-env <VARIABLE_NAME> \
  --auth header:x-goog-api-key --kind video --prompt-field instances.0.prompt --units 8 --unit second \
  --unit-usd <per-second list price for this model and resolution> \
  --price-basis "list price per second, <model id>, 720p, read <date> at https://ai.google.dev/gemini-api/docs/pricing" \
  --ledger media/ledger.jsonl --cap-usd-request <the owner's per-clip cap> --types video --log media/media-log.jsonl --dry-run
# live (the owner's yes first): the same without --dry-run prints RUNNING and the operation name (exit 4), then
python3 <skill>/scripts/api_media.py --poll https://generativelanguage.googleapis.com/v1beta/<operation name> \
  --key-env <VARIABLE_NAME> --auth header:x-goog-api-key --kind video --name water-loop --out-dir media/generated --log media/media-log.jsonl \
  --body media/clip-request.json --prompt-field instances.0.prompt --units 8 --unit second \
  --unit-usd <the same price as the start call> --price-basis "<the same basis as the start call>"
```

Request (Omni, checked 2026-10-16 on https://ai.google.dev/gemini-api/docs/omni): `POST https://generativelanguage.googleapis.com/v1beta/interactions`, with the key in the `x-goog-api-key` header. For a clip over 4 MB, add link delivery:

```json
{"model": "<omni model id, for example gemini-omni-1.1-flash>", "input": "<the clip prompt>",
 "response_format": {"type": "video", "delivery": "uri"}}
```

For first-and-last-frame input on Omni, follow the page's own image-input sample; this example adds no field beyond what the page shows.

- Omni bills per output video token, at a stated number of tokens per second for each resolution; read both on the pricing page on the day and multiply by the clip's seconds. A clip usually costs far more than a music track, so estimate each batch separately.
- Veo clips are 24 fps (Veo page, checked 2026-10-16); the Omni page states no frame rate, so read it from the clip with ffprobe. A clip can come back with an audio track although none was wanted; strip it.
- Seamless loops: pass the same still as the first and last frame. A result can be nearly, not perfectly, loopable; check the seam frame by frame.
- Omni returns the clip inline as base64 by default. For clips over about 4 MB, set `"delivery": "uri"` in `response_format`. The creation response's `content[]` item (type `video`, `mime_type` `video/mp4`) then carries the `uri` (`https://generativelanguage.googleapis.com/v1beta/files/<id>:download?alt=media`), and the file must be `ACTIVE` before it downloads: pass `--wait-file` so `api_media.py` polls `files/<id>` every 5 s until `ACTIVE`, then downloads (Omni page, checked 2026-10-16). Without `--wait-file`, a link that returns no media saves its body as `<name>-link-response.json` (another extension for a non-JSON body), never as a clip; the script exits 4 when the body's state is `PROCESSING` and 1 otherwise. The `uri` is guaranteed only in that creation response: a later `GET` of the interaction (`--poll https://generativelanguage.googleapis.com/v1beta/interactions/<id>`) returns the clip inline as base64, even for a clip created with link delivery. The key header goes only to the API's own host, and the script records the operation id; when a download fails or the file is not ready, the reservation stays uncertain and `--poll` fetches the result again without a new generation. The Omni page states no retention period (checked 2026-10-16); download at once.
- Latency runs from about 11 s to 6 minutes at peak; long jobs run as operations to poll every 10 s or so.
- Veo takes `durationSeconds` as a string, `"4"`, `"6"` or `"8"`; 1080p and 4k need `"8"`. The Omni page documents no duration parameter, so dry-run first and read the response.
- Cap Veo at 720p or 1080p (4k costs more per second and needs `"8"`). Cap Omni at 720p: its 1080p and 4k are upscaled, and the pricing page gives a per-second rate only for 720p (`resolution` takes 360p, 720p, 1080p or 4k; default 720p; checked 2026-10-16).
- The same models have `-preview` ids on the developer API and `-001` ids on the cloud platform, with regional endpoints there. Keep a per-platform table.
- Agent tools with built-in image generation can lack video generation entirely; a direct API call with a spend guard fills the gap.

## Worked example: Google Gemini API prepaid billing

Checked 2026-10-15; re-check the vendor's current docs before relying on it.

Docs: https://ai.google.dev/gemini-api/docs/billing, https://ai.google.dev/gemini-api/docs/pricing

- An API key on prepaid billing needs a paid balance above $0 before promotional credits apply; once it exists, eligible credits are used first.
- When the prepaid balance reaches $0, every key on that billing account stops (HTTP 402). Auto-reload, if on, tops it up silently.
- Budgets that only alert stop nothing.
- Usage data lags about 10 minutes; billing reports lag up to a day. Take a baseline before the first paid call and read the next day.
- Credits for the vendor's consumer creative app cannot pay for API calls, and that app has no API.
- The developer API has no free tier for the video or music models.
- A minimum deposit can unlock the API quickly, while the zero-deposit route (below) can take much longer to set up. Show the owner both early.

## Worked example: Google Cloud enterprise route

Checked 2026-10-15; re-check the vendor's current docs before relying on it.

Docs: https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps, https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start/express-mode/overview, https://docs.cloud.google.com/iam/docs/keys-create-delete

- Separate billing with per-project spend caps (monthly, counted at list price before credits, not instant; set them slightly below the real limit).
- A simple express-mode API key works only for the Gemini models in its table (text and image), not for Veo or Lyria; media models need a service-account key with one narrow role (`roles/aiplatform.user`). Service-account keys download once, the vendor warns they are a risk, and new organisations may block their creation by policy.
- Link delivery of large results needs a storage bucket, a separate charge outside the spend cap; inline delivery avoids it.
- Its pricing pages may not render for a fetch tool; use the developer API's list prices as the working estimate and check them against the test's billing line.

## Worked example: Google SynthID and C2PA content credentials

Checked 2026-10-15; re-check the vendor's current docs before relying on it.

Docs: https://deepmind.google/models/synthid/, https://ai.google.dev/gemini-api/terms, https://policies.google.com/terms/generative-ai/use-policy

- Generated music and video carry an invisible SynthID watermark in the signal, which the vendor says survives cropping, filters, frame-rate changes, noise, speed changes and lossy compression. Anyone can check a file with the SynthID Detector.
- The same files can carry a C2PA manifest in the container (for example in an ID3 frame of an MP3, or in an MP4). A re-encode or a metadata strip removes it while the watermark stays, so beds made from them carry none.
- The vendor's terms say it does not claim ownership of outputs, may generate the same or similar output for others, and holds the user responsible for use. Its prohibited-use policy bars passing generated content off as solely human-made to deceive. Read the terms for the exact model on the day.
