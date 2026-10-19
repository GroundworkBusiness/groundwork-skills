# Running the stages by hand

Every stage in [SKILL.md](../SKILL.md), for any agent tool other than Claude Code with the Workflow tool: for example Codex, Grok Build, Antigravity, a single chat, or Claude Code without that tool. Every step is a plain instruction, a script call or a page to open; fan-out is optional and every gate comes back to the owner.

## Contents

- [One agent, stage by stage](#one-agent-stage-by-stage)
- [Several sessions in parallel](#several-sessions-in-parallel)
- [Passing owner notes to a busy agent](#passing-owner-notes-to-a-busy-agent)
- [When an agent cannot open a browser, bind a port, reach the network or write to git](#when-an-agent-cannot-open-a-browser-bind-a-port-reach-the-network-or-write-to-git)
- [The host's audit and browser pass](#the-hosts-audit-and-browser-pass)
- [Notes per agent tool](#notes-per-agent-tool)

## One agent, stage by stage

On Windows PowerShell: use `python` (or `py`) for `python3`; put each continued command on one line; run each side of an `a && b` line as its own command (Windows PowerShell 5.1 has no `&&`); write `mkdir -p <dir>` as `New-Item -ItemType Directory -Force <dir>`, `cp -R <src>/. <dst>/` as `Copy-Item -Recurse -Force <src>/* <dst>/`, and `rm -rf <a> <b>` as `Remove-Item -Recurse -Force -ErrorAction SilentlyContinue <a>, <b>`; copy one file per `Copy-Item`; and start the server in a second terminal (the `nohup`, `sleep`, `kill` and `curl` lines below are macOS and Linux only). Or run the blocks in Git Bash or WSL.

When the request changes a video that already has a build (a new voice, new music, a timing fix, a new look, a script change), go to [stage 12 of SKILL.md](../SKILL.md#12-iterate-after-output) and the recipes in [review and iterate](../references/review-and-iterate.md#iteration-recipes).

Follow the stages in [SKILL.md](../SKILL.md) in order. Two overlaps are allowed: look prototypes may run on the saved sample scene while the rest of the script is still open, and one short audition may use only scenes whose words are settled; full takes and the voice-gate pick wait until the owner has approved the script and shortlisted the look. At each gate, stop, show the options, and wait for the owner's pick before the next stage. Commands run from `<project>/`. `<skill>` is the folder that holds the skill's SKILL.md (the parent of this `workflows/` folder), wherever the agent tool installed it. Replace the angle-bracket placeholders with project values (for `<transcriber command with {in}>`, see the quick-transcript template in [the whisper.cpp example](../references/example-local-tools.md#worked-example-whispercpp-transcription)); quote paths containing spaces. For a second or later video in a series, use that video's own `script/<video-id>/` and `voices/<video-id>/` folders in every command below and add `--voices-manifest ../../voices/<video-id>/voices.json` to each build's first `make_cues.py` call ([SKILL.md, A series in one project](../SKILL.md#a-series-in-one-project)).

### Bans and required terms

Repeat `--ban` once per string on the Banned line of `PLAN.md`. To ban the long dash (U+2014), pass the character itself, for example `--ban="$(python3 -c 'print(chr(0x2014))')"`, or paste it between the quotes. A value that starts with an ASCII hyphen goes in the `--ban=<value>` form. A `--` in `script.txt` is always caught by `cue_check.py`, so it needs no ban. On builds only, repeat `--require` once per term on the Required terms line, on `static_check.py` (`cue_check.py` has no `--require`). Bans match any capitalisation, and a ban that starts or ends with a letter or digit matches whole words only at that end (a ban of "ai" does not match "said"); required terms match exactly.

### Loop and text-only flags

Each `make_cues.py` call adds the flags listed for the owner's picks in [SKILL.md, Stages at a glance](../SKILL.md#stages-at-a-glance).

### Intake

Fill `PLAN.md` and probe the tools needed for the owner's picks, following [intake](../references/intake.md).

```sh
python3 <skill>/scripts/probe_tools.py --stt-model <path to the transcriber's model file> --key-env <VARIABLE_NAME>
# voice none: mkdir -p voices, copy <skill>/assets/voices.json to voices/voices.json and keep only the none entry (default none)
```

### Script

Use the approved words and [script guidance](../references/script.md) to write the script, voice pack and estimated cues. For a loop or text-only piece, use the [No voice pace flags](../references/timing-check.md#no-voice).

```sh
python3 <skill>/scripts/cue_check.py --script script/script.txt --scenes script/scenes.json --ban='<banned string>'
python3 <skill>/scripts/make_voice_pack.py --scenes script/scenes.json --script script/script.txt --out script/voice-pack.md
# a loop or text-only piece: add the loop and text-only flags (above); add --label "<label>" --kicker "<kicker>" from PLAN.md's Title card line when it has them
python3 <skill>/scripts/make_cues.py --script script/script.txt --scenes script/scenes.json --out script/cues.json --title "<title>"
```

### Looks (gate 1)

Per look, copy `<skill>/assets/build-template/` to `looks/<id>/`, then make its cues and replace the template's two scenes, BEATS table and scene CSS with the look's one sample scene ([Starting from the template](../references/stage-contract.md#starting-from-the-template)). The sample lives in `looks/sample-script.txt` and `looks/sample-scenes.json`; an unedited copy fails the timing audit by design. Use the [No voice pace flags](../references/timing-check.md#no-voice) when needed. 8770 is the default port. When the server runs on another port, use that port in every URL below. After checking the preview answers 200, show the comparison, stop for the owner's shortlist and record it in `PLAN.md`; if the check fails, use [the host fallback](#when-an-agent-cannot-open-a-browser-bind-a-port-reach-the-network-or-write-to-git).

```sh
mkdir -p looks/<id> && cp -R <skill>/assets/build-template/. looks/<id>/
cp <skill>/assets/templates/LOOK.md looks/<id>/LOOK.md   # fill it in as the look takes shape
# write looks/<id>/image-requests.json from <skill>/assets/image-requests.example.json (an empty list when the look wants no images)
# a loop or text-only piece: add the loop and text-only flags (above); add --label "<label>" --kicker "<kicker>" from PLAN.md's Title card line when it has them; captions picked off: add --captions off
rm looks/<id>/cues.json; python3 <skill>/scripts/make_cues.py --script looks/sample-script.txt --scenes looks/sample-scenes.json --out looks/<id>/cues.json --title "<title>" --default-mode <light|dark> --no-voices --no-music
# ...build the look here, then:
python3 <skill>/scripts/sync_embed.py --build looks/<id>
python3 <skill>/scripts/static_check.py --page looks/<id>/index.html --level look --ban='<banned string>'
node <skill>/scripts/timing_audit.mjs --build looks/<id>
cp <skill>/assets/compare.html <skill>/assets/looks.json looks/   # set title, then list each look (id, label, folder, builder) in looks.json
nohup python3 <skill>/scripts/serve_range.py --dir . --port 8770 >.preview.log 2>&1 & echo $! > .preview.pid   # macOS and Linux; or start it as the agent tool's own background job
sleep 1; if kill -0 "$(cat .preview.pid)" 2>/dev/null && grep -q '^Serving ' .preview.log; then curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8770/looks/compare.html; else cat .preview.log; fi   # macOS and Linux
# a 200 counts only when this server is running; port in use: start again with another --port and use that port in every URL; cannot bind: follow "When an agent cannot ... bind a port" below; anything else: cat .preview.log, give no URL (an empty log: wait a second and run the check again)
# without curl, or on Windows: check that the terminal (or .preview.log) shows Serving <this project's path> first, then: python3 -c "import urllib.request as u; print(u.urlopen('http://127.0.0.1:8770/looks/compare.html').status)"
# In a second terminal (required on Windows PowerShell): python3 <skill>/scripts/serve_range.py --dir . --port 8770   # check that the terminal shows Serving <this project's path> first
# Once the owner has seen the page, stop the server the way it was started: started with nohup, run kill "$(cat .preview.pid)"; started in a second terminal, press Ctrl+C in that terminal; started as the agent tool's background job, stop that job.
# After a 200, the owner opens http://127.0.0.1:8770/looks/compare.html
```

### Build

Per build folder, replace the look's one-scene cues with the whole video's, following [build](../references/build.md). For a loop or text-only piece, use the [No voice pace flags](../references/timing-check.md#no-voice).

```sh
mkdir -p <video-id>/<build-id> && cp -R looks/<look-id>/. <video-id>/<build-id>/
rm -rf <video-id>/<build-id>/frames <video-id>/<build-id>/qa   # the prototype's captures and reports
cp <skill>/assets/templates/SCENES-NOTES.md <video-id>/<build-id>/SCENES-NOTES.md
# a loop or text-only piece: add the loop and text-only flags (above); add --label "<label>" --kicker "<kicker>" from PLAN.md's Title card line when it has them; captions picked off: add --captions off; music none: add --no-music
# A later video in a series with its own voices/<video-id>/: add --voices-manifest ../../voices/<video-id>/voices.json
rm <video-id>/<build-id>/cues.json; python3 <skill>/scripts/make_cues.py --script script/script.txt --scenes script/scenes.json --out <video-id>/<build-id>/cues.json --title "<title>" --default-mode <light|dark>
python3 <skill>/scripts/cue_check.py --script script/script.txt --scenes script/scenes.json --cues <video-id>/<build-id>/cues.json --ban='<banned string>'
# voice none: voices/voices.json (none only) is written at intake
python3 <skill>/scripts/sync_embed.py --build <video-id>/<build-id>
python3 <skill>/scripts/static_check.py --page <video-id>/<build-id>/index.html --ban='<banned string>' --require='<required term>'
node <skill>/scripts/timing_audit.mjs --build <video-id>/<build-id>
```

### Voices (gate 2)

Audition one or two settled scenes per shortlisted voice, plain first, then with style lines, following [voices](../references/voices.md). Stop for the owner's pick by ear and record it in `PLAN.md` before full takes. For voice none, check that `voices/voices.json` holds only the `none` entry (written at intake; write it now as described there if it is missing), run `sync_embed.py` for every build, and skip the remaining Voices commands. For hand-made takes, use the [whisper.cpp transcription example](../references/example-local-tools.md#worked-example-whispercpp-transcription) and [alignment](../references/alignment.md).

```sh
cp <skill>/assets/voices-shortlist.example.json script/voices-shortlist.json   # fill in the shortlist, then:
python3 <skill>/scripts/make_voice_pack.py --scenes script/scenes.json --script script/script.txt --out script/voice-pack.md --shortlist script/voices-shortlist.json
python3 <skill>/scripts/tts_generate.py --scenes script/scenes.json --script script/script.txt --adapter <adapter> --voice-id <id> \
  --out-dir voices/audition-<id> --only <n,m> --plain-all --style-off --dry-run
#   API adapters also need --model <model-id>; local adapters need --command "<command template>" --command-ext <ext> (copy both from the voice's entry in <skill>/assets/voice-batch.example.json, or from the speech-provider examples in references/example-speech-providers.md).
#   then live, after the owner's yes: add --key-env <VARIABLE_NAME> for an API, --ledger,
#   --est-usd-per-request and a cap for a paid tool, drop --dry-run;
#   repeat without --plain-all --style-off into voices/audition-<id>-styled
python3 <skill>/scripts/check_takes.py --scenes script/scenes.json --take-dir voices/audition-<id> \
  --stt-cmd "<transcriber command with {in}>" --only <n,m>
# Check the styled audition folder too; with no transcriber, listen to both endings.
# Full takes, after the owner picks voices at the audition: dry run, the owner's yes, then the batch
# config: copy <skill>/assets/voice-batch.example.json to voices/batch.json, fill in the top-level placeholders
# (stt_quick, stt_words, aligner_label; not read with --no-stt) and those of the voices you run, and delete the voices and cap keys you do not use (a batch of unpaid local voices needs no caps)
python3 <skill>/scripts/voice_batch.py --config voices/batch.json --dry-run
# the dry run prints every request in full; the request file it names is temporary. To keep one voice's requests as JSON lines, run its tts_generate.py line (as under the audition commands above, without --only, --plain-all and --style-off) with --dry-run --dry-run-out voices/<id>-dry-run.jsonl
python3 <skill>/scripts/voice_batch.py --config voices/batch.json --merge-manifest
# an API voice that stays dry-run only: add --only-voices <local voice ids>

# No transcriber: python3 <skill>/scripts/voice_batch.py --config voices/batch.json --no-stt --merge-manifest
# then listen to every scene's ending and record it in the note.

# Takes made by hand (the owner's recording, or audio from a web app by hand or by browser): save one file per
# scene as voices/<id>/s<N>.wav, converted to one sample rate and 16-bit PCM (check the real file type first):
#   ffmpeg -i <in> -ac 1 -ar 24000 -c:a pcm_s16le voices/<id>/s<N>.wav
# then check, join, transcribe and align, and write the voices.json entry by hand (kind recorded, or the vendor's kind; start from <skill>/assets/voices.json with its two example takes deleted and the none entry kept, as in SKILL.md stage 5, step 7):
#   python3 <skill>/scripts/check_takes.py --scenes script/scenes.json --take-dir voices/<id> --stt-cmd "<transcriber command with {in}>"
#   continue only when check_takes.py exits 0 (2: regenerate the scenes it names; 1: the check did not run, so fix the transcriber first)
#   python3 <skill>/scripts/join_scenes.py --take-dir voices/<id> --out voices/<id>/<id>.wav --scenes script/scenes.json
#   ffmpeg -i voices/<id>/<id>.wav -ar 16000 -ac 1 voices/<id>/<id>-16k.wav
#   whisper-cli -m <model-dir>/<model-file> -f voices/<id>/<id>-16k.wav -ml 1 -sow -ojf -np -of voices/<id>/<id>-words   # word times, as in the whisper.cpp example; add -ng if it aborts at model load
#   python3 <skill>/scripts/align_words.py --script script/script.txt --words voices/<id>/<id>-words.json --format whisper-cpp \
#     --voice <id> --audio voices/<id>/<id>.wav --scene-offsets voices/<id>/<id>-scenes.json --out voices/<id>/<id>-timing.json
# A single full-length file: convert it to voices/<id>/<id>.wav, run the 16 kHz conversion and the word command, then
#   python3 <skill>/scripts/align_words.py --script script/script.txt --words voices/<id>/<id>-words.json --format whisper-cpp \
#     --voice <id> --audio voices/<id>/<id>.wav --out voices/<id>/<id>-timing.json
# (without --scene-offsets it still exits 3 on a missing ending); listen to the ending.
```

### Music (gate 3)

Prepare options and record their rights, following [music](../references/music.md) and the [Lyria worked example](../references/example-media-providers.md#worked-example-google-lyria-music-through-the-gemini-api). Dry-run paid requests and get the owner's yes before live generation. Show the beds side by side, stop for the owner's pick, and record it in `PLAN.md`. For music none, record the owner's confirmation, then either run `mkdir -p music`, copy [the manifest template](../assets/tracks.json) to `music/tracks.json` and delete its two example tracks (an empty `tracks` list), or make each build's cues with `--no-music`. Run `sync_embed.py` for every build, and skip the remaining Music commands.

```sh
cp <skill>/assets/tracks.json music/tracks.json   # once: delete the two example tracks, paste each entry make_bed.py prints, fill in the rights fields
# <s>: the longest video duration over every take and No voice, plus about 10 s. No voice: duration in a build's
# cues.json; a take: the duration this prints (or the longest video sync_embed.py prints):
# python3 <skill>/scripts/mix_audio.py --cues <video-id>/<build-id>/cues.json --voice-audio voices/<v>/<v>.wav --timing voices/<v>/<v>-timing.json --out export/duration-check.wav
# A generated option: one request per prompt, dry run first; live after the owner's yes (drop --dry-run)
python3 <skill>/scripts/api_media.py --endpoint <endpoint> --body media/<id>-request.json --name <id> --out-dir music/source \
  --key-env <VARIABLE_NAME> --auth <bearer|header:<header name>> --kind music --types audio \
  --prompt-field <dotted path to the prompt in your body> --units 1 --unit track \
  --unit-usd <list price> --price-basis "<price-page row, date read>" --ledger media/ledger.jsonl --cap-usd-request <cap> \
  --log media/media-log.jsonl --dry-run
# first bracket: a track made with api_media.py (fills its generation fields from the media log); second bracket: any generated track, when a transcriber is available (otherwise listen for vocals); see references/music.md; for a track made with api_media.py, <file> is the name its saved line printed (<id>-1.<ext>)
python3 <skill>/scripts/make_bed.py --src music/source/<file> --out music/<id>-bed.mp3 --min-seconds <s> --id <id> --label "<label>" [--origin generated --media-log media/media-log.jsonl] [--vocals-check --stt-cmd "<transcriber command with {in}>"]
```

### Generated media

Only when generated media or screen recordings were chosen (screen recordings alone: keep each untouched file under `media/source/` and place it as in SKILL.md stage 8, step 5; skip the commands below): once each shortlisted look has its build folder, merge the shortlisted looks' and builds' `image-requests.json` into `media/image-requests.json`; dry-run one request per entry and get the owner's yes before live generation. For a clip entry (`"kind": "video"`), use `--kind video --types video --units <seconds> --unit second`; a live start prints RUNNING and the operation name (exit 4). For polling with `api_media.py --poll`, see [the provider examples](../references/example-media-providers.md#worked-example-google-veo-and-gemini-omni-clips). For a built-in generator or web app, use [Without an API](../references/generated-media.md#without-an-api-a-built-in-generator-or-a-web-app): keep the same folders and media-log record, reserve paid items with `spend_ledger.py --reserve`, and close them with `--outcome`.

```sh
python3 <skill>/scripts/api_media.py --endpoint <endpoint> --body media/<id>-request.json --name <id> --out-dir media/generated \
  --key-env <VARIABLE_NAME> --auth <bearer|header:<header name>> --kind image --types image \
  --prompt-field <dotted path to the prompt in your body, e.g. input.0.text> --units 1 --unit image \
  --unit-usd <list price> --price-basis "<price-page row, size, date read>" --ledger media/ledger.jsonl --cap-usd-request <cap> \
  --log media/media-log.jsonl --dry-run
# live, after the owner's yes: the same without --dry-run; then place each pick as in SKILL.md stage 8, step 6
```

### Viewer

Copy and configure the viewer, then sync every build for use from disk ([viewer](../references/viewer.md)).

```sh
cp <skill>/assets/viewer.html <skill>/assets/viewer.json <video-id>/   # set title and default_build, list each build in viewer.json; message_type must match the builds' cues.json
python3 <skill>/scripts/sync_embed.py --build <video-id>/<build-id>     # after any manifest change, for use from disk
```

### Timing (gate 4)

Run per build, adding `--strict` after a new take, timing fix or script change ([timing check](../references/timing-check.md)). Show the audit and frames, stop for the owner's sign-off, and keep the gate unsigned while any voice is incomplete.

```sh
node <skill>/scripts/timing_audit.mjs --build <video-id>/<build-id>
python3 <skill>/scripts/frame_review.py --build <video-id>/<build-id> --base-url http://127.0.0.1:8770/<video-id>/<build-id>/index.html
```

### Review and fix (stage 11)

Read every build against the Reviewer sections of [the review checklist](../assets/templates/review-checklist.md), and write the findings to `<video-id>/review.md` before changing any build file. With one session, this is a separate pass. Only when it lists findings, apply them to every live build, then rerun the `sync_embed.py` and `static_check.py` lines under Build and `timing_audit.mjs --strict` for every build. Then run [the host's audit and browser pass](#the-hosts-audit-and-browser-pass).

### Iterate (stage 12)

For a video that already has a build, use [the iteration recipes](../references/review-and-iterate.md#iteration-recipes). Audition a new voice first as under Voices (gate 2), then add it to `voices/batch.json`; a scratch voice may skip the audition. After a new voice or bed, run the `sync_embed.py` and `timing_audit.mjs --strict` lines at the end of Iterate. If an MP4 was delivered, export each delivered combination again and retain the earlier file under a dated name. A take made by hand (kind `recorded`, or audio from a web app) skips `tts_generate.py` and `voice_batch.py`. Re-record or re-export the new or changed scenes as `voices/<id>/s<N>.wav`, run the Takes made by hand lines under [Voices (gate 2)](#voices-gate-2) (SKILL.md stage 5, step 4c), and update its `voices.json` entry by hand. Then run `sync_embed.py` per build and `timing_audit.mjs --strict`. After each change, update each build's `SCENES-NOTES.md` (takes and durations, tracks and their rights state, moved anchors, checks run).

```sh
python3 <skill>/scripts/voice_batch.py --config voices/batch.json --only-voices <id> --dry-run
python3 <skill>/scripts/voice_batch.py --config voices/batch.json --only-voices <id> --merge-manifest   # after the owner's yes for a paid voice; add --no-stt when there is no transcriber
# New music: ask the composition-rights question on arrival; a cover, remix or "in the style of" stays rights "pending: ..."
python3 <skill>/scripts/make_bed.py --src music/source/<file> --out music/<id>-bed.mp3 --min-seconds <s> --id <id> --label "<label>" [--origin generated --media-log media/media-log.jsonl] [--vocals-check --stt-cmd "<transcriber command with {in}>"]
# a build made with --no-music (music.manifest null in its cues.json) lists only Off until it points at the manifest:
python3 <skill>/scripts/make_cues.py --script script/script.txt --scenes script/scenes.json --out <video-id>/<build-id>/cues.json --tracks-manifest ../../music/tracks.json
# Script change: edit script/script.txt and script/scenes.json first
# a sentence added or removed: renumber data-cue in that scene and every later scene of every build before the audit
python3 <skill>/scripts/cue_check.py --script script/script.txt --scenes script/scenes.json --ban='<banned string>'
# per build: make_cues.py keeps the build's title card, pace, music, voices, message type, default mode, loop, captions default and target length; give --wps, --breath, --lead or --hold only to change the pace
python3 <skill>/scripts/make_cues.py --script script/script.txt --scenes script/scenes.json --out <video-id>/<build-id>/cues.json
python3 <skill>/scripts/cue_check.py --script script/script.txt --scenes script/scenes.json --cues <video-id>/<build-id>/cues.json --ban='<banned string>'
# per voice: regenerate only the changed scenes, dry run first (a take made by hand: re-record those scenes and use the Takes made by hand lines under Voices (gate 2) instead of the next two commands)
python3 <skill>/scripts/tts_generate.py --scenes script/scenes.json --script script/script.txt --adapter <adapter> --voice-id <id> \
  --out-dir voices/<voice> --only <n,m> --force --dry-run   # plus the take's --model and --key-env (API) or --command and --command-ext (local); for a paid voice add --ledger, --est-usd-per-request and a cap, then drop --dry-run after the owner's yes
# check, join and align the whole take (unchanged scenes are kept) and update voices.json
python3 <skill>/scripts/voice_batch.py --config voices/batch.json --only-voices <voice> --merge-manifest   # add --no-stt when there is no transcriber
python3 <skill>/scripts/sync_embed.py --build <video-id>/<build-id>
# When sync_embed.py reports a bed shorter than the longest video, rebuild that bed from its untouched source with the --min-seconds it prints and update its tracks.json measurements, keeping the rights fields.
node <skill>/scripts/timing_audit.mjs --build <video-id>/<build-id> --strict
```

### Export

Capture the frames as in [export](../references/export.md#frames) (its Playwright example also writes `export/clips.json`), then mix the chosen audio and encode. With voice and music both none and no clip audio kept, skip `mix_audio.py` and encode with `-an` ([Loops](../references/export.md#loops)).

```sh
python3 <skill>/scripts/mix_audio.py --cues <video-id>/<build-id>/cues.json --voice-audio voices/<voice>/<voice>.wav --timing voices/<voice>/<voice>-timing.json --bed music/<bed>.mp3 --tracks music/tracks.json --track-id <bed-id> [--clips export/clips.json] --out export/mix.wav   # --clips when a clip keeps its audio; write it from __video.clips(); <bed-id> is the bed's id in music/tracks.json
```

## Several sessions in parallel

Give each look, or each build, its own session and its own folder:

1. Write the brief once (`looks/BRIEF.md` or `<video-id>/BRIEF.md`) and give every session the same brief plus its folder name and concept. Name each session's task in one line: a look session copies `<skill>/assets/build-template/` into its folder and does SKILL.md stage 3, steps 3 to 5 (cues from `looks/sample-script.txt`, then `sync_embed.py`, `static_check.py --level look` and `timing_audit.mjs` on its folder); a build session does stage 4, steps 3 to 9 for its folder. Neither runs intake, a gate, the server, or any voice, music or paid step. A look session captures `frames/` only when the host has said its server is running, and at which URL (http://127.0.0.1:8770 by default); otherwise it skips `frames/` and lists them under what its checks did not cover.
2. Paste this shared preamble into every session, replacing placeholders:

   > You are working on a video-prototyper project at <absolute project path>, using the skill at <absolute skill path>. Read <skill>/SKILL.md, then the references this brief names. Read <project>/PLAN.md for the goal, picks, copy rules and design rules. Write only inside <your folder>. Never type, print or copy a key. Make no paid calls. Never edit <project>/voices or <project>/music. Run the commands from <project>/ with <skill> replaced by the path above. If you cannot open a browser, bind a port, play audio or reach the network, say so in your final message.

3. Each session writes only inside its own folder and reads the shared folders (`script/`, `voices/`, `music/`) without writing to them.
4. Each session's final message lists: the files it wrote, the checks it ran with their results, what its checks did not cover, and its open questions.
5. The host re-runs `static_check.py` and `timing_audit.mjs` on each returned folder (the commands under Looks (gate 1) and Build above), then fills `looks.json` (or `viewer.json`) and shows the owner.

When sessions run on different models or providers, the look round also shows which one does code-built motion well. Record the verdict in `PLAN.md` and send later motion work there. For the full build, hand each shortlisted look to a different session than the one that made it.

Sessions on other agent tools (for example Codex, Grok Build or Antigravity) can each run the Python and Node scripts directly; none of them needs Claude Code's Workflow tool. In Claude Code, the [prototype workflow](prototype.js) (the Workflow tool, with `scriptPath` and `args`, one stage per call) runs the same fan-out from one call per stage.

## Passing owner notes to a busy agent

Some sessions accept messages mid-run; many do not. When the owner says something while a session is busy:

1. Write it to a short note in that session's folder or the run folder, from [the change brief template](../assets/templates/change-brief.md): what the owner said or showed, the ask, the done-when checks, "also give this to the reviewer".
2. Hand it over when the session next takes a turn, or start the next pass with it.
3. Give the same note to the reviewer.

## When an agent cannot open a browser, bind a port, reach the network or write to git

Sandboxed sessions often cannot launch a browser, bind a local port, play audio, reach the network or write a `.git` folder. That is normal:

- The session runs the programmatic checks (`static_check.py`, `timing_audit.mjs`, `serve_range.py --self-test`), writes the frame list with `frame_review.py`, and returns "programmatic checks pass, browser unverified" with the list of what it could not check.
- The host session runs the server, captures and looks at the frames, listens, and makes any git commits. When the main session is itself sandboxed, it prints the `serve_range.py` command, the URL to open and the Host section of the review checklist. The owner runs them in their own terminal and browser and reports what they saw. The session does not wait for another agent session.
- Paid and API steps (`tts_generate.py` and `api_media.py` live runs, and `voice_batch.py` with API voices) need outbound network. Installs and downloads need it too, each after the owner's yes: the `brew install` lines and the transcriber's model file in [the local tool examples](../references/example-local-tools.md), and `npm install playwright` and `npx playwright install chromium` in [export](../references/export.md). Run them from a session that has the network, or from the owner's terminal. "STOP: nothing reached the endpoint" means the call never left the machine; nothing was spent. A TLS certificate failure prints its own STOP line; with a python.org Python on macOS, set `SSL_CERT_FILE=/etc/ssl/cert.pem` ([the example](../references/example-local-tools.md#worked-example-python-https-on-macos)).

## The host's audit and browser pass

After every build pass, new take or timing fix:

1. Run `node <skill>/scripts/timing_audit.mjs --build <video-id>/<build-id>` for every build (add `--strict` after a new take, a timing fix or a script change); read `qa/timing-audit.json`.
2. Serve the project with `serve_range.py`, check that `<video-id>/viewer.html` answers 200 (as in the Looks commands above), and open it.
3. Work through the Host section of [the review checklist](../assets/templates/review-checklist.md) with sound on: every voice, every bed, Off, play and pause, a voice switch while playing, a build switch, embed mode, the opening frame in both modes, every take's last line, narrow width, the console.
4. For a second opinion on timing in the real browser, open the build's own page (`<video-id>/<build-id>/index.html` on the same server, not the viewer), paste [timing-audit.js](../assets/timing-audit.js) into that page's console and run `videoTimingAudit.inBrowser().then(r => console.log(r.status, r.failures))`. The viewer's own console has no `__video`, because the build runs inside its iframe.
5. Report what was verified and what was not, and record the owner's sign-off in `PLAN.md`.

## Notes per agent tool

On an agent tool without a skill installer, put the whole `video-prototyper/` folder, with SKILL.md inside, in any folder: unzip the skill's ZIP where one is offered, or copy the folder from its repository. That folder is `<skill>`. Start each session by telling it to read `<skill>/SKILL.md` (the preamble above does this); a chat without tools gets the files as in the last bullet below.

- **Claude Code**: the workflow covers the fan-out; the main session stays the host. Subagents may run sandboxed; give the browser pass to the main session.
- **Codex**: start each session in `<project>/` (so the commands' paths resolve) and tell it which folder it owns; ask each to report what its sandbox blocked. Sandboxed sessions may start with the network off. A paid step needs the network: add `-c sandbox_workspace_write.network_access=true` to a `--sandbox workspace-write` session (codex-cli 0.162.1, checked 2026-10-16; the configuration reference describes it as "Allow outbound network access inside the workspace-write sandbox"), or run the paid steps from the owner's terminal. When the main session cannot bind a port or open a browser, it hands the server command, the URL and the Host checklist to the owner ([see above](#when-an-agent-cannot-open-a-browser-bind-a-port-reach-the-network-or-write-to-git)). Worked example (codex-cli 0.162.1, checked 2026-10-16): a headless session is `codex exec -C <project> --sandbox workspace-write --skip-git-repo-check -o "<absolute path to the session's folder>/final-message.md" "<preamble + task>"`; `--skip-git-repo-check` lets it run in a project folder that is not a git repository. `-o` writes the session's last message to that file, so the host reads each session's report from its own folder.
- **Grok Build**: the same pattern; a headless session prints its final message to stdout; a status file exists only if the session wrote one. When the main session cannot bind a port or open a browser, it hands the server command, the URL and the Host checklist to the owner ([see above](#when-an-agent-cannot-open-a-browser-bind-a-port-reach-the-network-or-write-to-git)). Worked example (grok 1.0.50, checked 2026-10-16): `grok --cwd <project> --sandbox workspace --always-approve --prompt-file <path to a file holding the preamble + task>` runs a headless single-turn session that can run the skill's scripts and prints its final message to stdout. `grok --help` also lists `-p "<preamble + task>"` for an inline prompt (not the form checked); keep the quoted prompt directly after `-p`. `grok --help` lists `--sandbox <PROFILE>` without naming its profiles; `workspace` is the profile this example was checked with (grok 1.0.50, 2026-10-16). If your version rejects it, check Grok Build's own documentation for the current profile names.
- **Antigravity**: the same pattern. Whichever session can open a real browser with sound runs the host's browser pass. When the main session cannot bind a port or open a browser, it hands the server command, the URL and the Host checklist to the owner ([see above](#when-an-agent-cannot-open-a-browser-bind-a-port-reach-the-network-or-write-to-git)). Worked example (agy 1.4.0, checked 2026-10-16): from `<project>/`, a headless session is `agy --mode accept-edits --add-dir <project> --add-dir <skill> --prompt "<preamble + task>"`, which prints its final response and puts both folders in its workspace; in the desktop app, open `<project>` as the workspace and add the skill folder; `--mode accept-edits` let a headless session run the skill's scripts (agy 1.4.0, 2026-10-16); `--mode plan` does not run them.

Flags change between versions; check each tool's `--help` before relying on them.

- **Any single chat without tools**: the agent gives each file's path and full contents in a code block; the owner saves them, runs the commands, and pastes the output back. The owner first puts the whole `video-prototyper/` folder in a local folder, from the skill's ZIP where one is offered or copied from its repository; that folder, which holds SKILL.md, is `<skill>` in every command. Before each stage, upload or paste SKILL.md, this guide and the reference file that stage links into the chat (or use the chat's own skill upload where it has one); a chat without tools cannot open `<skill>/SKILL.md` from a path.
