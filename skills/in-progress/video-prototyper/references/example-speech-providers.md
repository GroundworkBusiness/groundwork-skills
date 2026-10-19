# Worked examples: speech providers

Real providers used the way [voices.md](voices.md) describes. Each block is dated and links the vendor's documentation. Prices, limits, model ids and endpoints change; re-check the vendor's current docs before relying on any of them. Where a line says a provider "can" or "may" do something, that behaviour was seen in use but is not documented; check it on your own first request. Nothing here is a recommendation of one provider over another.

## Contents

- [Google Gemini API text-to-speech](#worked-example-google-gemini-api-text-to-speech)
- [Google AI Studio auditions by hand](#worked-example-google-ai-studio-auditions-by-hand)
- [OpenAI text-to-speech](#worked-example-openai-text-to-speech)
- [Local scratch voices](#worked-example-local-scratch-voices)

## Worked example: Google Gemini API text-to-speech

Checked 2026-10-15; re-check the vendor's current docs before relying on it.

Docs: https://ai.google.dev/gemini-api/docs/speech-generation, https://ai.google.dev/api/interactions, https://ai.google.dev/gemini-api/docs/rate-limits, https://ai.google.dev/gemini-api/docs/voice-design

Request, one per scene, through the Interactions endpoint, with the key in a header:

```text
POST https://generativelanguage.googleapis.com/v1beta/interactions
x-goog-api-key: <from the environment variable>
```

```json
{"model": "<tts model id, for example gemini-3.8-flash-tts>",
 "input": [{"type": "user_input", "content": [{"type": "text", "text": "<cued scene text>",
            "annotations": [{"type": "speech_metadata", "style": "<short style line>"}]}]}],
 "response_format": {"type": "audio"},
 "generation_config": {"speech_config": [{"voice": "<voice id>"}]}}
```

Response: the audio is base64 in `steps[]` (type `model_output`), inside `content[]` where `type` is `audio`, field `data`. Usage sits in `usage` (`total_input_tokens`, `total_output_tokens`). The decoded bytes are a complete WAV: 16-bit PCM, 24 kHz, mono. The vendor's REST sample takes the last audio block, and its SDKs' `output_audio` returns the last block (checked 2026-10-16). `tts_generate.py` does the same, logs how many parts came back, and joins them with `--join-audio-parts`.

Voices:

- About 30 prebuilt voices, by name.
- Designed voices, created in Google AI Studio from a one- or two-sentence description, get ids like `voice_<id>` and are usable by API under the same account. Designed voices can also be created by API (`POST /v1beta/voices` with `type: "prompted"` and `store` set to true, as every sample on the voice-design page sets it; the speech page describes `store` false, for replicated voices, as a stateless key that expires after 7 days, so keep `store` true for a voice the takes depend on; checked 2026-10-16). Stored `voice_...` ids are deleted after one year without use (each use resets the year), with at most 200 per project (checked 2026-10-16). Record the creation date and keep the design prompt in `voices.json`, so the voice can be recreated.
- Library voices: the speech page lists them with `GET /v1beta/voices` (checked 2026-10-16); their ids can look like `en-us-<name>`.

Delivery: about 35 recommended inline tags in angle brackets, some with two spellings (pauses, breaths, laughs), CAPS for stress, ellipses and `--` for hesitation, and a style annotation per request. Keep style lines short; the vendor names long direction as the most common cause of voice drift. Some voices may read a tag such as `<long pause>` aloud as words; transcribe every scene and regenerate a leaking scene with the tags removed.

Limits: rate limits for these models can show per project in AI Studio rather than on the rate-limits page; read your project's limit there. Set `--min-interval` to 60 divided by that per-minute limit, plus about a second (for a limit of 12 a minute, 6 s), and retry 429, 500 and 503 after 30, 60, 90 and 120 s. Pacing sets the wall time: at 12 a minute, 60 scene requests take at least five minutes. Output audio is billed per output token: read the output tokens per second of speech from `usage` on your first request, then estimate seconds x tokens per second x the output price per token, plus a small input cost. Read the price per token, and any free tier, on the pricing page on the day.

With this skill:

```sh
python3 <skill>/scripts/tts_generate.py --scenes script/scenes.json --adapter gemini-interactions \
  --model <tts model id> --voice-id <voice id> --key-env <VARIABLE_NAME> \
  --out-dir voices/<voice> --min-interval <seconds between requests> --max-requests 20 \
  --ledger media/ledger.jsonl --est-usd-per-request <estimate> --cap-usd-day <cap> --dry-run
```

Re-check: model ids, the voice list, tag list, rate limits per tier and prices.

## Worked example: Google AI Studio auditions by hand

Checked 2026-10-15; re-check the vendor's current docs before relying on it.

Docs: https://ai.google.dev/gemini-api/docs/voice-design, https://ai.google.dev/gemini-api/docs/speech-generation

The owner auditions in the web app: signs in, chooses a speech model, pastes scenes from `voice-pack.md` with their style lines, designs voices from the pack's prompts, and favourites library voices. The agent then generates the chosen voices by API, scene by scene, from the voice ids the owner reports. The shortlist is a starting point; designed and library voices can beat it, and the ear decides.

An agent can drive the same app with browser or computer-use tools, with the owner signing in. Sign-in, payment and key creation stay with the owner.

Re-check: which models the app offers for voice design, and whether designed voices stay usable by API.

## Worked example: OpenAI text-to-speech

Checked 2026-10-15; re-check the vendor's current docs before relying on it.

Docs: https://developers.openai.com/api/docs/guides/text-to-speech, https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create, https://developers.openai.com/api/docs/deprecations, https://openai.com/policies/usage-policies/

```text
POST https://api.openai.com/v1/audio/speech
Authorization: Bearer <from the environment variable>
{"model": "<dated tts model id>", "voice": "<voice>", "input": "<scene text>", "response_format": "wav", "instructions": "<delivery>"}
```

- The `instructions` field steers delivery only on the `gpt-4o-mini-tts` family; other models ignore or reject it. Pass `--instructions` to `tts_generate.py` only for those models. Pass `--instructions-file` to send a standing block; the file's text is sent with each scene's style line after it.
- About 4,096 characters per request (gpt-4o-mini-tts also caps input at 2,000 tokens); one scene per request stays well inside it.
- The usage policy requires telling listeners that the voice is AI-generated. Put the disclosure on the closing card and the page.
- Speech models carry published shutdown dates. Record the dated model id and the date checked; prefer a voice that also exists on the replacement model. For `<dated tts model id>`, choose a snapshot the deprecations page does not list for removal.
- The deprecations page lists each speech model's removal date and the replacement it names; read it on the day. When a model you use is listed, check whether its replacement is offered on /v1/audio/speech before planning retakes, keep WAV masters, and generate any retakes before the removal date.
- The docs say little about how text is read: CAPS are unreliable (a short word can be spelled out) and long dashes are read inconsistently. Use word order for stress and commas or full stops for pauses.
- A long single take, such as one recorded in the playground, can silently drop its last line. Generate scene by scene and transcribe every ending.
- `tts_generate.py` strips delivery tags and the `--` cue from the `openai-speech` body, because this voice may read them aloud. To give this provider delivery cues it reads well (here an ellipsis for the pause and no CAPS), give the scene its own variant; every variant keeps the script's words, and `cue_check.py` checks it:

```json
{"n": 2, "text_cued": "Alder Creek uses THREE bins. <short pause> The blue bin takes clean paper, cans and bottles. <short pause> The green bin takes food scraps and yard trimmings. <short pause> And the grey bin takes -- everything else.",
 "variants": {"openai-speech": "Alder Creek uses three bins... The blue bin takes clean paper, cans and bottles... The green bin takes food scraps and yard trimmings... And the grey bin takes, everything else."}}
```

With this skill (a dry run first; `--plain-all` sends every scene without tags whatever its variants hold):

```sh
python3 <skill>/scripts/tts_generate.py --scenes script/scenes.json --adapter openai-speech \
  --model <dated tts model id> --voice-id <voice> --instructions --instructions-file script/openai-instructions.txt --key-env <VARIABLE_NAME> \
  --out-dir voices/<voice> --max-requests 20 \
  --ledger media/ledger.jsonl --est-usd-per-request <estimate> --cap-usd-day <cap> --dry-run
```

A scene without its own `openai-speech` variant still sends stress capitals. Give every scene a variant, as [scenes.example.json](../assets/scenes.example.json) does, or add `--script script/script.txt --plain-all` to send each scene's canonical paragraph.

A labelled instruction block, reused for every scene so the voice stays consistent. Save it as `script/openai-instructions.txt` and pass `--instructions-file script/openai-instructions.txt`:

```text
Affect: Bright and unhurried, like a morning radio host reading the local notices.
Tone: Matter-of-fact and cheerful, with a light touch on the colour names.
Pacing: A little brisk through the lists, slowing for the last item in each.
Pronunciation: Say "Alder Creek" with equal weight on both words.
Personality: Neighbourly and practical, like a local who has put the bins out every week for years.
```

Re-check: models, voices, the `instructions` support list, limits, shutdown dates and the disclosure terms.

## Worked example: local scratch voices

Checked 2026-10-15; re-check the tool's current docs before relying on it.

Docs: `man say` on macOS; `espeak-ng --help` for eSpeak NG.

Free voices for timing work and offline test runs, through the `command` adapter:

```sh
# macOS built-in voice (writes AIFF; the script converts it to 16-bit WAV with ffmpeg)
python3 <skill>/scripts/tts_generate.py --scenes script/scenes.json --adapter command --voice-id Samantha \
  --command "say -v {voice} -o {out} -f {text_file}" --command-ext aiff --out-dir voices/scratch-local

# eSpeak NG on Linux or Windows (writes WAV)
python3 <skill>/scripts/tts_generate.py --scenes script/scenes.json --adapter command --voice-id en-us \
  --command "espeak-ng -v {voice} -w {out} -f {text_file}" --command-ext wav --out-dir voices/scratch-local
```

The `command` adapter strips delivery tags before speaking, so local voices read clean text. `say -v '?'` lists macOS voices; `espeak-ng --voices` lists eSpeak NG voices.

These tools take no style line, so a styled audition sounds the same as the plain one; run the styled pass only for voices whose tool takes direction (put `{style}` in the command for a local tool that accepts it).

Limits seen: none relevant; quality is for timing, not publishing.
