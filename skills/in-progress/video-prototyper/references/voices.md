# Voices (gate 2)

How to shortlist, audition and generate narration, and how to check every take before it reaches a build. Provider-specific details are in [example-speech-providers.md](example-speech-providers.md).

## Contents

- [When](#when)
- [Voice kinds](#voice-kinds)
- [Design prompts](#design-prompts)
- [Style lines and delivery cues](#style-lines-and-delivery-cues)
- [Auditions](#auditions)
- [Full takes, scene by scene](#full-takes-scene-by-scene)
- [The check loop](#the-check-loop)
- [Joining and records](#joining-and-records)
- [Model lifetimes and disclosure](#model-lifetimes-and-disclosure)
- [Cost](#cost)
- [Scratch voices](#scratch-voices)

## When

Look prototypes may run on the saved sample scene while the rest of the script is still open. One short audition may use only scenes whose words are already settled. Full takes and the voice-gate pick wait until the owner has approved the script and shortlisted the look. A voice generated before the words are final is paid for twice.

## Voice kinds

| Kind | What it is | Notes |
|---|---|---|
| prebuilt | A named voice the provider ships | Confirm it works on the exact model before shortlisting. |
| library | A voice from a provider's shared library | Usable by id like a prebuilt voice. |
| designed | A voice made from a short text description | Created in the provider's web app or by API; some providers delete designed voices left unused (see the speech examples). |
| recorded | The owner (or a speaker) reading the script | Treat like any take: check the ending, align. See [takes made by hand](#takes-made-by-hand). |
| local | A voice tool on this machine | For timing work and scratch takes; not for publishing unless the owner says so. |

Choose by ear, never from descriptions. Vendor descriptions are thin and voice counts on vendor pages often disagree.

## Design prompts

One or two sentences naming permanent traits only: age range, gender if relevant, timbre, texture, accent, baseline pace. Situational emotion belongs in each scene's style line, not the design. Two examples:

```text
A calm male narrator in his late 50s. Deep, slightly gravelly timbre, neutral accent, slow and deliberate delivery.
A lively female presenter in her late 20s. Light, crisp timbre, neutral accent, brisk but clear delivery.
```

For any regional accent, also generate the prompt with a neutral accent and let the owner compare; a strong accent prompt can sound exaggerated.

## Style lines and delivery cues

- A style line per scene of a few words ("steady, with a lift on each colour name"). Long direction is a common cause of voice drift; when a voice changes character, shorten or empty the line.
- Inline tags (pauses, breaths), CAPS for stress, ellipses and `--` for hesitation are provider conventions. Keep them in `scenes.json`, never in `script.txt` or the captions. Per provider, a convention may be documented, ignored or harmful (one provider documents CAPS as stress; another can spell out a capitalised short word).
- Prefer a sentence break or a comma over a long-pause tag; some voices read tags aloud.
- When a scene sounds overdone, remove its breath tags before anything else, and then the pauses inside lists.

## Auditions

Test order:

1. Plain first: two short scenes (one should be the closing scene, which also tests the ending), no tags and an empty style line, three or four voices.
2. Add style lines to the favourites and compare with step 1 (for voices that take a style line; a local voice with none skips it, and the report says so).
3. The owner picks. Record the pick and the reason in `PLAN.md`.

Three ways to run them:

- **By hand in the provider's web app.** Give the owner `voice-pack.md` from [make_voice_pack.py](../scripts/make_voice_pack.py): the model, a shortlist, design prompts, how the delivery cues work, the test order, each scene's Plain and Cued text, and what to do when something goes wrong. The owner signs in, pastes, listens, designs and saves voices; the agent collects the voice ids afterwards.
- **By browser or computer use.** The agent drives the same web app; the owner signs in, pays and creates keys. Check each downloaded file's real type.
- **By API.** Run [tts_generate.py](../scripts/tts_generate.py) with `--only` on the audition scenes and `--plain-all --style-off` for the plain pass (no tags, no style line). The plain pass uses `--script script/script.txt`. Check the audition folder with [check_takes.py](../scripts/check_takes.py) `--only` on the same scenes, so the scenes not auditioned are not reported missing.

List every audition file in `PLAN.md` as a table (voice, scene, plain or styled, path), or as a page of `<audio>` elements served with `serve_range.py`, so the owner can compare them one after another.

## Full takes, scene by scene

Generate one request per scene. It avoids per-request length limits, prevents the silently dropped ending that long single reads produce, allows a style line per scene, and lets one bad scene be regenerated instead of the whole take. A resume skips a scene only when its generation record matches the words, voice and model; a mismatch is left in place until `--only` and `--force`.

- Pace requests to the provider's rate limit (`--min-interval`: 60 divided by the per-minute limit, plus about a second; for a limit of 12 a minute, 6 s) and retry 429, 500 and 503 with growing waits (`--backoff`, `--max-retries`).
- Cap the run (`--max-requests`, which counts every attempt, retries included) and record spend in the shared ledger; see [spend-and-credentials.md](spend-and-credentials.md). A live API run, or a paid tool behind the `command` adapter with `--paid`, needs `--ledger`, an explicit `--est-usd-per-request` (finite, 0 or more; 0 suits a free local endpoint) and at least one of `--cap-usd-request`, `--cap-usd-day` or `--cap-usd-project`; without them it exits before reading any key.
- Dry-run first (`--dry-run`): it prints every request in full and the estimated list cost, checks the caps and --max-requests, reads no key and creates nothing. The spend caps are checked against the ledger. `--dry-run-out FILE` keeps the requests as JSON lines.
- [voice_batch.py](../scripts/voice_batch.py) runs generate, check, regenerate, join, transcribe and align for several voices; one voice failing does not stop the others. Run it with `--config voices/batch.json --merge-manifest` so each finished take lands in `voices.json`; config format in [voice-batch.example.json](../assets/voice-batch.example.json). When an API voice stays dry-run only (no budget or no key), pass `--only-voices <local voice ids>` on the live run. max_requests applies to each generation call, and each regeneration round is a new call, so one voice can make up to (1 + --max-regens) x max_requests attempts; the USD caps bound the whole batch through the ledger.
- When neither worked-example adapter fits the provider, wrap the vendor's CLI, or a short script that reads the key from the environment, in the `command` adapter with `--paid --ledger ... --est-usd-per-request ...` and a cap; the pacing, retries, caps and ledger then apply. For an OpenAI-compatible speech endpoint, the worked-example route is `--adapter openai-speech --endpoint <url>`.

### Takes made by hand

The owner's recording, or audio from a web app saved by hand or by browser:

1. Save one file per scene as `voices/<id>/s<N>.wav`, converting each with the audio tool to one sample rate and 16-bit PCM (for example `ffmpeg -i <in> -ac 1 -ar 24000 -c:a pcm_s16le voices/<id>/s<N>.wav`). Check the real file type first.
2. Check every scene with [check_takes.py](../scripts/check_takes.py), join with [join_scenes.py](../scripts/join_scenes.py), transcribe the joined take to word JSON, and align it with [align_words.py](../scripts/align_words.py) and `--scene-offsets`.
3. Write the `voices.json` entry by hand (start from [the template](../assets/voices.json) with its two example takes deleted and the `none` entry kept, as in [SKILL.md stage 5, step 7](../SKILL.md#5-gate-2-voice-auditions-and-takes)): kind `recorded` (or the vendor's kind), model, voice, created, note.

A single full-length file: convert it to `voices/<id>/<id>.wav`, transcribe it to word JSON, run `align_words.py` without `--scene-offsets` (it still exits 3 on a missing ending), listen to the ending, and write the entry by hand. The runnable lines are under [Voices (gate 2) in the by-hand guide](../workflows/by-hand.md#voices-gate-2).

With a single full-length file and no transcriber, find the pauses between scenes with the silence detector in [the local tools examples](example-local-tools.md#worked-example-ffmpeg-and-ffprobe), cut the file at them into `voices/<id>/s<N>.wav` with the audio tool, then follow the per-scene route (`join_scenes.py`, then `align_words.py --no-stt --scene-offsets`) and listen to every scene's ending.

## The check loop

[check_takes.py](../scripts/check_takes.py) transcribes every scene (16 kHz mono) and reports:

- **Tag leaks**: tag words inserted relative to the script. Detection is by diff, not by searching for the words, so a script that legitimately says "pause" raises no alarm. Move the scene aside (`--move-leaks` keeps it as `s<N>-tagged.wav` for comparison), regenerate it without tags but with its style line (`tts_generate.py --plain-scenes N`), and re-check.
- **Ending heard**: at least two of the scene's last three words appear in the transcript.
- **Match rate**: matched script words over all script words; a scene below 0.85 (`check_takes.py --min-match`) is regenerated.

Loop check, regenerate, check until clean or a retry cap (two rounds by default), then stop and report. A tag-heavy script needs more plain re-takes.

## Joining and records

- [join_scenes.py](../scripts/join_scenes.py) joins `s1..sN` with a fixed gap (0.6 s by default) at the source rate and writes exact scene offsets, which the aligner uses to pin scene boundaries. Run it as `python3 <skill>/scripts/join_scenes.py --take-dir voices/<id> --out voices/<id>/<id>.wav --scenes script/scenes.json`.
- Keep WAV masters. Editing and mixing a lossy file compresses twice, and a provider may retire the model that made the take.
- Record each take in `voices.json`: kind, vendor, dated model id, voice id, design prompt, creation date, scenes regenerated plain, integrated loudness (`loudness_lufs`, which `join_scenes.py` measures and prints), and any known fault in `note`. A take with a fault stays selectable and labelled.
- Takes from different tools differ in level; apply one static gain to about -22 LUFS when the owner hears jumps between voices.

## Model lifetimes and disclosure

- Providers publish shutdown dates for speech models. Record the dated model id, never an alias. When choosing between equal voices, prefer one that also exists on the provider's replacement model.
- Some providers require telling listeners that the voice is AI-generated. Put a disclosure line on the closing card of every video (it can be watched away from its page; for a loop, where PLAN.md places it, see [script](script.md#disclosure-card)) and on the hosting page. The owner decides the final wording.

## Cost

Estimate before generating: audio seconds x the provider's output units per second x the current price per unit, plus a small input cost. Look the price up on the provider's page on the day; never quote one from memory. Read the real figure from the billing page the next day.

## Scratch voices

A local voice (the `command` adapter) gives free takes for timing and layout work before any paid voice exists, and lets test runs work offline. It goes through the same check, join and align steps, so the pipeline is proven before money is spent. A local voice gives the same audio for the same text, so a scene the transcriber mishears fails the same way on every try; `voice_batch.py` stops after the first identical regeneration and says so. Listen to the scene: when it reads correctly, try a larger transcriber model or another installed voice.
