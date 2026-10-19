---
name: video-prototyper
description: "Plans, prototypes and builds explainer, tutorial, course and product videos as deterministic web pages, with optional narration, music and generated images or clips, and exports them to MP4. Use when someone wants to make or revise such a video, an animated scene or a looping background, choose a narrator voice or background music for one, prototype video looks, or sync animation to a voiceover. Works with any speech, music, image or video tool by API, by browser or locally, and stops for the owner's pick at four gates: looks, voices, music and timing."
---

# Video Prototyper

This skill makes a video as one deterministic web page per build: a 1920x1080 stage driven by a seekable timeline, optionally narrated, with music, generated images or clips, captions, and light and dark modes. One viewer page plays every build with every voice and every music bed, and an export step renders the chosen combination to MP4.

Prototyping comes first because the brief is discovered there. Goals, voices, music, length and media all change once the owner sees and hears real options, so the architecture is built to absorb change.

Requirements: Python 3.9 or later and Node 18 or later for the scripts, and ffmpeg and ffprobe for audio. The full pipeline also uses a speech-to-text tool with word timestamps and a headless browser. Each has a fallback where one exists (No voice timed from the reading estimate, `--no-stt`, the host's browser), and stage 1 probes them.

## How it works

- **Late binding.** Animation is keyed to cue ids, never to seconds. Each voice take carries its own timing file, manifests list the takes and the music beds, and one viewer switches build, voice, music, mode and captions. Requirements move (voice or none, music or none, length, media) and takes of one script can differ widely in length, so anything timed in fixed seconds gets rebuilt.
- **Four gates before the owner locks a look, a voice, a bed or the timing.** Looks, voices, music and timing each produce options side by side. The owner decides at each gate, and the pick goes in the decision log of `PLAN.md` with its reason.
- **Say only what is true of the real thing.** Use only verified counts, names and figures, and take the facts for the pictures from a named source. Label illustrative examples as illustrative in the brief, the notes and any sources line, and on screen too when a viewer could take one for a real record or when the owner asks.
- **The owner holds money, keys, sign-ins, installs, downloads and rights.** Each is its own yes. Paid generation needs an explicit yes and a cap.
- **Check in a real browser with sound on.** Agents in sandboxes often cannot open a browser, bind a port or play audio, so the host session owns pixel and audio checks, and every check report says what it did not cover.
- **Name the need.** Every step says what it needs (a speech tool, a transcriber, an audio tool, a browser). Worked examples with real tools live in the reference files.

Terms:

- **Host session**: the session that runs the local server and does the browser and audio checks, usually the main session; when it cannot, the owner runs them ([how](workflows/by-hand.md#when-an-agent-cannot-open-a-browser-bind-a-port-reach-the-network-or-write-to-git)).
- **Agent tool**: the AI tool running the skill, for example Claude Code, Codex, Grok Build, Antigravity or a chat.
- **Built-in generator**: a generator built into the agent tool, such as its own image generation, used without an API ([the built-in generator path](references/generated-media.md#without-an-api-a-built-in-generator-or-a-web-app)).
- **Take**: one voice's full narration of the script.
- **Bed**: a music file built to outlast every take at a measured loudness.
- **Title card** (the pre-roll): the opening card before narration starts: a title, plus an optional label (a short line above the title, such as "Part 1") and kicker (a subtitle under it), set with `make_cues.py --title`, `--label` and `--kicker`. Each scene's own label is separate and comes from `scenes.json`.
- **Owner**: the person directing the video; they approve each gate, make every pick, and hold money, keys, sign-ins and rights.
- **No voice**: the `none` entry every `voices.json` keeps, timed from the reading estimate.
- **Cue**: one sentence of `script/script.txt`, with an id (`c01`, `c02`, ...) shared by `cues.json` and every take's timing file.
- **Beat**: one on-screen change, keyed to an anchor `A(scene, k, f)`: cue k of that scene (counted from 0), fraction f of the way through it. A build lists its beats in its `BEATS` table as `[element id, k, f]`; a brief's beat table lists the same beats with their narration.
- **Delivery cues**: the tags, CAPS and style lines in `scenes.json` that steer a speech tool; they never change the words.
- **Text-only piece**: a video with no voice whose on-screen lines are the whole script, one cue per line; captions are off unless the owner asks for a plate.

## Stages at a glance

| # | Stage | Gate | Produces | Read |
|---|---|---|---|---|
| 1 | Intake | | `PLAN.md`: goal, picks, tool map, caps | [intake](references/intake.md) |
| 2 | Series, outline and script | | `script.txt`, `scenes.json`, estimated `cues.json`, voice pack | [script](references/script.md) |
| 3 | Look prototypes | Gate 1 | several looks of one scene, compare page | [look prototypes](references/look-prototypes.md) |
| 4 | Full build | | one build per shortlisted look, `cues.json` | [build](references/build.md) |
| 5 | Voice auditions and takes | Gate 2 | checked takes, `voices.json` | [voices](references/voices.md) |
| 6 | Alignment | | one timing file per take | [alignment](references/alignment.md) |
| 7 | Music options | Gate 3 | measured beds, `tracks.json` | [music](references/music.md) |
| 8 | Generated images and video, screen recordings (when chosen) | | picked media with provenance | [generated media](references/generated-media.md) |
| 9 | Viewer | | `viewer.html` switching everything | [viewer](references/viewer.md) |
| 10 | Timing check | Gate 4 | `qa/timing-audit.json` per build | [timing check](references/timing-check.md) |
| 11 | Review and fix | | review report, host acceptance list | [review and iterate](references/review-and-iterate.md) |
| 12 | Iterate after output | | new takes, beds, fixes | [review and iterate](references/review-and-iterate.md) |
| 13 | Export | | MP4 with the chosen voice and bed | [export](references/export.md) |

Look prototypes may run on the saved sample scene while the rest of the script is still open. One short audition may use only scenes whose words are already settled. Full takes and the voice-gate pick wait until the owner has approved the script and shortlisted the look. The timing check runs again after every new take or timing change.

A gate means: produce options, present them side by side (compare page, audition list, bed list, audit report), wait for the owner's pick, and record it with its reason in `PLAN.md`. A gate for a medium the owner chose not to use still runs as a confirmation: record "none" and what replaces it. With no voice, for example, cues are timed from the reading estimate and the timing check runs on No voice.

When the video already has a build and the request changes it (a new voice, new music, a timing fix, a new look or a script change), start at [stage 12](#12-iterate-after-output) with the existing `PLAN.md`. With no `PLAN.md` yet, copy [the template](assets/templates/PLAN.md) and fill in what the existing build shows before the first change. The prototype workflow has no iterate stage, so run stage 12's recipes by hand with every agent tool.

Commands run from `<project>/`. `<skill>` is the folder that holds this SKILL.md, wherever the agent tool installed it. A command written inline in a stage names the script and the flags that matter at that step; the full command lines, required arguments included, are in [the by-hand guide](workflows/by-hand.md), the reference file each stage links, and each script's `--help`.

Flags each `make_cues.py` call adds, by pick (the loop and text-only flags):

- Loop or text-only piece: `--target-seconds <length>` (the piece's length on the script and build calls; on a look's call, the sample scene's own length, which equals the piece's length only when the sample is the whole piece), plus `--loop` for a loop, and the [No voice pace flags](references/timing-check.md#no-voice).
- Loop or text-only piece whose Title card line in `PLAN.md` records the owner's confirmation to drop the card: `--title-card 0`.
- Captions off: `--captions off`.
- Music none: `--no-music`, or no flag when `music/tracks.json` holds an empty `tracks` list (stage 7). A look's call always carries `--no-music`.

To choose how to run it on your agent tool, see [Running it on your agent tool](#running-it-on-your-agent-tool).

## 1. Intake

Start by copying [the PLAN template](assets/templates/PLAN.md) to `<project>/PLAN.md`, and tell the owner up front that answers will change and the build absorbs that. Each step below fills a line of it.

1. Ask the owner to state the goal in their own words: who watches, what they should know or do afterward, where it plays (web page, MP4, a loop on a screen, an embed) and how long it runs. Leave the length open unless the owner sets a limit, and trim for time only to meet that limit.
2. Ask the owner to pick only what applies, one line each:
   - voice: none, owner-recorded, text-to-speech, or several to compare;
   - music: none, owner-supplied, generated, or a licensed library track;
   - visuals: code-built motion, generated images, generated video clips, screen recordings;
   - captions: on, off, burned in, or a toggle;
   - modes: light, dark, or both (for an MP4, also which mode it ships in, or one file per mode).
   What each captions pick means for `make_cues.py` and export is in [intake](references/intake.md#the-pick-list); for a text-only piece, confirm here whether captions are off (`make_cues.py --captions off`) or a plate.
3. For each tool the picks need, record how it is reached: by API (the owner places the key and the agent reads an environment variable by name), by browser or computer use driving a web app (the owner signs in, pays and creates keys; the agent never enters credentials or payment details), or locally (transcriber, audio tool, local voice). Write this tool map in `PLAN.md`.
4. Probe what is reachable before planning: run `python3 <skill>/scripts/probe_tools.py`, with `--stt-model <path>` naming the transcriber's model file when a voice or generated music needs a transcriber check (the transcriber commands that `check_takes.py` and `voice_batch.py` run name this model file). It reports the audio tool, a transcriber and its model, Node, a headless browser, local voices, and whether named key variables are set, never their values. Agent tools often have image generation but no video generation, so record what is missing and ask.
5. Agree spending: a cap per batch and per project, a dry run before every paid call, the owner's yes per batch, and a billing baseline before the first paid call. See [spend and credentials](references/spend-and-credentials.md).
6. Ask for three owner inputs and record each on its line of `PLAN.md`:
   - **6a.** Banned strings: words or characters the owner bans on screen and in narration (the Banned line). Each becomes a `--ban` argument to `static_check.py` and `cue_check.py`; nothing is banned by default. Bans match any capitalisation, and a ban that starts or ends with a letter or digit matches whole words only at that end (a ban of "ai" does not match "said"); required terms match exactly. Speech engines read the long dash inconsistently (see [script](references/script.md#writing-for-speech)), so offer it as a suggested ban (pass it as in [the by-hand guide](workflows/by-hand.md#one-agent-stage-by-stage)).
   - **6b.** Required on-screen terms, in their exact wording (the Required terms line); on full builds each becomes a `--require` argument to `static_check.py`.
   - **6c.** The title card's text: the title, and a label and kicker if wanted (the Title card line).
7. Ask for the owner's standing design rules: the art direction they apply to every video, for example how on-screen devices and interfaces are shown, how one scene hands over to the next, or which colours, type and imagery are off-limits. Record them on the Design rules line of `PLAN.md`; every look and build brief carries them.
8. Make the project folders below and fill any `PLAN.md` line still empty. When the Voice pick is none, also write `voices/voices.json` with only the `none` entry now ([template](assets/voices.json)), so the first build check finds it.

```
<project>/
  PLAN.md          intake answers, tool map, spend caps, decision log
  script/          series.md, outline.md, script.txt (canonical), scenes.json (cued), cues.json (estimate), voices-shortlist.json, voice-pack.md
  looks/           BRIEF.md, sample-script.txt, sample-scenes.json, looks.json, compare.html, <look-id>/
  voices/          voices.json, batch.json, <voice-id>/ scene files, joined takes, timing files
  music/           tracks.json, source/ (untouched originals), beds
  media/           image-requests.json, generated/, source/ (screen recordings), media-log.jsonl, ledger.jsonl
  <video-id>/      BRIEF.md, review.md, viewer.html, viewer.json, <build-id>/
                   <build-id>/qa/ audit report and frame lists
  export/
```

Serve `<project>/` so sibling folders resolve. Details: [intake](references/intake.md).

### A series in one project

- Shared: `PLAN.md`, `looks/`, `music/` and `media/`.
- Each video gets `script/<video-id>/` (its `script.txt`, `scenes.json`, `cues.json`, `voices-shortlist.json` and `voice-pack.md`; `series.md` stays in `script/`) and `voices/<video-id>/` (its `voices.json`, `batch.json` and `<voice-id>/` take folders).
- In every command for that video, read `script/` as `script/<video-id>/` and `voices/` as `voices/<video-id>/`: its `batch.json` sets `scenes`, `script`, `voices_dir` and `manifest` to those folders, and its builds' first `make_cues.py` call adds `--voices-manifest ../../voices/<video-id>/voices.json` (stage 4, step 3).
- A shared bed's `--min-seconds` covers the longest video across the series.
- When a later video joins a project whose first video used `script/` and `voices/` directly, leave the first in place and give each new video its own folders.

## 2. Series, outline and script

1. For a series, list every video first: number, title, what it covers and what it does not.
2. Outline the video being built (scene, what it teaches, what is on screen). Talk it through with the owner in the conversation: ask questions and check existing material before proposing.
3. Draft narration per scene for the ear, each with an "On screen" line and a sources line. Number the drafts. The owner approves.
4. Write `script/script.txt`, the canonical caption script: one paragraph per scene, a blank line between scenes, no markup. The aligner maps paragraph N to scene N. For a loop or text-only piece, the on-screen lines are the script: end each with `.`, `!` or `?` so it becomes its own cue ([timing check](references/timing-check.md#no-voice)).
5. Write `script/scenes.json`: the same words plus delivery cues and a short style line per scene ([example](assets/scenes.example.json)) (with no voice, `text_cued` holds the paragraph's words unchanged and `style` is empty).
6. When a voice is planned, render `voice-pack.md` for anyone auditioning by hand: `python3 <skill>/scripts/make_voice_pack.py --scenes script/scenes.json --script script/script.txt --out script/voice-pack.md`. Once stage 5 has a shortlist, copy [voices-shortlist.example.json](assets/voices-shortlist.example.json) to `script/voices-shortlist.json`, fill it in, and render again with `python3 <skill>/scripts/make_voice_pack.py --scenes script/scenes.json --script script/script.txt --out script/voice-pack.md --shortlist script/voices-shortlist.json`.
7. Run `python3 <skill>/scripts/cue_check.py --script script/script.txt --scenes script/scenes.json` with the owner's `--ban` list. Delivery cues never change the words; it prints `N of N words match`.
8. Run `python3 <skill>/scripts/make_cues.py --script script/script.txt --scenes script/scenes.json --out script/cues.json --title "<approved video title>"` (add `--label "<label>" --kicker "<kicker>"` when the owner wants them; a loop or text-only piece adds the loop and text-only flags listed under [Stages at a glance](#stages-at-a-glance)) to write the estimated cues for the whole video; it gives the No voice duration, and each build writes its own in stage 4.

Rules: write for the real viewer; use plain, unbranded example names; state only counts and facts that are true and will stay true, because a spoken number needs a full re-voice; write numbers, dates and acronyms as spoken; put perishable names on title cards, not in narration; end with an AI-disclosure card (or, for a loop, the placement the owner picks) whenever any voice, music, images or footage is generated. Details: [script](references/script.md).

## 3. Gate 1: look prototypes

1. Pick one short scene (about 20 seconds) and fix its narration and beat table. When the whole video is about the sample's length, make the sample the whole video as one scene; the full build may split it into scenes. Save the narration as `looks/sample-script.txt` (one paragraph, the same format as `script.txt`) and its title and label as a one-scene `looks/sample-scenes.json` (a one-scene file with `n`, `title`, `label` and `on_screen`, which is all `make_cues.py` reads for the sample: `{"scenes": [{"n": 1, "title": "...", "label": "...", "on_screen": "..."}]}`). The full script's `scenes.json` also carries `text_cued` and `style` (stage 2, step 5). Its `label` is the scene label; the title card's label and kicker come only from `make_cues.py --label` and `--kicker`.
2. Write one brief from [the look brief template](assets/templates/look-brief.md) to `looks/BRIEF.md`.
3. Build three to six distinct looks of that identical scene (at least two when only one tool is available), each in its own `looks/<id>/` folder (copy the template into it with `mkdir -p looks/<id> && cp -R <skill>/assets/build-template/. looks/<id>/`; the trailing `/.` copies the contents the same way on macOS and Linux), each to the [stage contract](references/stage-contract.md). Start from the runtime in [the build template](assets/build-template/index.html), keeping and replacing the parts [the stage contract lists](references/stage-contract.md#starting-from-the-template); the look itself is free.
4. Draw stand-ins and list wanted images (and any wanted clip) in the look's `image-requests.json`; generation waits for stage 8.
5. Each look ships `index.html`, `cues.json`, `LOOK.md` ([template](assets/templates/LOOK.md)), `image-requests.json` and, when a browser is available and the server is running, `frames/` (otherwise list them under what the checks did not cover; capture command in [the headless Chrome example](references/example-local-tools.md#worked-example-headless-chrome-frame-capture)). Make its cues, replace the scene, then check each look:

   ```sh
   # Captions picked off: add --captions off; add --label "<label>" --kicker "<kicker>" from PLAN.md's Title card line when it has them.
   # A loop or text-only piece: add --target-seconds <the sample's length>, --loop for a loop, --title-card 0 when PLAN.md's Title card line records the owner's confirmation, and the No voice pace flags (references/timing-check.md).
   rm looks/<id>/cues.json
   python3 <skill>/scripts/make_cues.py --script looks/sample-script.txt --scenes looks/sample-scenes.json --out looks/<id>/cues.json --title "<sample scene title>" --default-mode <light|dark> --no-voices --no-music
   # ...build the look here, then:
   python3 <skill>/scripts/sync_embed.py --build looks/<id>
   # Repeat --ban once per string on the Banned line of PLAN.md; omit it when there are no bans.
   python3 <skill>/scripts/static_check.py --page looks/<id>/index.html --level look --ban='<banned string>'
   node <skill>/scripts/timing_audit.mjs --build looks/<id>
   ```

   Run these checks after the look's scene replaces the template's. The template's two scenes point at cues the one-scene sample lacks, so on an unedited copy `static_check.py` passes and `timing_audit.mjs` fails; that is expected, not a template fault.
6. When several agents or models are available, give each a different look. The comparison then also shows which one does code-built motion well. Record that verdict in `PLAN.md` and route later motion work by it.
7. Serve the compare page and check that it answers before handing over its URL:
   - **7a.** Copy [the compare page](assets/compare.html) and [looks.json](assets/looks.json) into `looks/`, set the title in `looks.json` and list the looks.
   - **7b.** Serve the project with `serve_range.py` (port 8770 by default) and check that this server answers 200 for `looks/compare.html` before you hand over the URL, using the start, check and stop lines in [the by-hand guide](workflows/by-hand.md#looks-gate-1). A 200 counts only when this server is running. When the server runs on another port, use that port in every URL that follows, including `frame_review.py --base-url` and the export capture URLs. When it cannot bind a port or the check fails, give no URL as a ready preview and hand off as in [the by-hand guide](workflows/by-hand.md#when-an-agent-cannot-open-a-browser-bind-a-port-reach-the-network-or-write-to-git).
   - **7c.** After a 200, give the owner the compare page's URL on the port that served it (http://127.0.0.1:8770/looks/compare.html by default), [test every look at about 375 px wide](references/look-prototypes.md#the-compare-page), and stop the server once they have seen it.
8. The owner shortlists. Style is decided here; story and information get their own pass with the owner's content.
9. When a style or transition choice stays open, offer A/B pages.
10. Cross-refine: when another agent or model is available, hand each shortlisted look to a different agent or model than its author, with the brief "keep what works, fix what the owner said"; otherwise run a separate review pass in the same session with that brief.

Details: [look prototypes](references/look-prototypes.md).

## 4. Full build

1. Hold the build until the owner has given the content for this video.
2. Write `<video-id>/BRIEF.md` from [the build brief template](assets/templates/build-brief.md): approved narration by scene with "On screen" lines, facts for the pictures, the owner's rules, timing until a voice exists, the contract, and the builds table.
3. Make one build per shortlisted look, each in its own folder copied from its prototype. Copy [the SCENES-NOTES template](assets/templates/SCENES-NOTES.md) into each build folder; keep the copied `LOOK.md` unchanged as the record of the prototype (`SCENES-NOTES.md` describes the build); delete the copied `frames/` and `qa/` folders (`rm -rf <video-id>/<build-id>/frames <video-id>/<build-id>/qa`), which hold the prototype's captures and reports. A builder changes only its own folder and reads the shared folders (voices, music) without writing to them. Replace the prototype's one-scene cues and check for cues left over from the sample:

   ```sh
   # Add --label "<label>" --kicker "<kicker>" when the owner wants them.
   # Captions picked off: add --captions off; music none: add --no-music.
   # A later video in a series with its own voices/<video-id>/: add --voices-manifest ../../voices/<video-id>/voices.json
   # A loop or text-only piece: add --target-seconds <length>, --loop for a loop, --title-card 0 when PLAN.md's Title card line records the owner's confirmation, and the No voice pace flags (references/timing-check.md).
   rm <video-id>/<build-id>/cues.json
   python3 <skill>/scripts/make_cues.py --script script/script.txt --scenes script/scenes.json --out <video-id>/<build-id>/cues.json --title "<approved video title>" --default-mode <light|dark>
   # Repeat --ban once per string on the Banned line of PLAN.md; omit it when there are no bans.
   python3 <skill>/scripts/cue_check.py --script script/script.txt --scenes script/scenes.json --cues <video-id>/<build-id>/cues.json --ban='<banned string>'
   ```
4. Until a voice exists, timing comes from the estimate in `cues.json`: 2.4 words per second, a 0.45 s breath after each sentence, 0.6 s of lead before each scene and 2.5 s of hold after it (`make_cues.py --hold`). Tune these per project.
5. Write every beat as an anchor `A(scene, k, f)`: cue k of that scene (counted from 0), fraction f of the way through it. One `render(t)` computes all state from time alone; keep CSS loops, the wall clock, unseeded randomness and timers off the timeline.
6. Light and dark share one DOM and one timeline.
7. Put captions on their own plate at 44 px or more at 1080p, and keep teaching content above the caption band.
8. Keep `SCENES-NOTES.md` ([template](assets/templates/SCENES-NOTES.md)) current at the end of every pass.
9. For use from disk, run `python3 <skill>/scripts/sync_embed.py --build <video-id>/<build-id>` to embed cues and manifests. Run `python3 <skill>/scripts/static_check.py --page <video-id>/<build-id>/index.html` with the owner's `--ban` list and one `--require` per term on the Required terms line of `PLAN.md`.
10. Apply every pass to every live build until the owner drops one.

Details: [build](references/build.md), [stage contract](references/stage-contract.md) and [viewer](references/viewer.md).

## 5. Gate 2: voice auditions and takes

1. Shortlist voices: prebuilt voices, voices designed from a one- or two-sentence prompt naming permanent traits only, library voices, or the owner's own recording. For any regional-accent design, add an A/B with a neutral accent. Write the shortlist to `script/voices-shortlist.json` and re-render the voice pack (stage 2, step 6).
2. Run auditions by hand in a vendor web app, by browser or computer use (the owner signs in), or by API (`tts_generate.py --only <n,m> --plain-all --style-off`; full line in [the by-hand guide](workflows/by-hand.md#one-agent-stage-by-stage)).
3. Audition on one or two short scenes, plain first, then with style lines; check the audition folder with `python3 <skill>/scripts/check_takes.py --scenes script/scenes.json --take-dir voices/audition-<id> --stt-cmd "<transcriber command with {in}>" --only <n,m>` (quick-transcript template in [the whisper.cpp example](references/example-local-tools.md#worked-example-whispercpp-transcription)). The owner's ear decides; descriptions do not. List every audition file in `PLAN.md` as a table (voice, scene, plain or styled, path), or as a page of `<audio>` elements served with `serve_range.py`, so the owner can compare them one after another.
4. Generate full takes scene by scene, one request per scene. This avoids length limits and dropped endings, allows a style line per scene, and lets one bad scene be regenerated alone. Pace requests to the rate limit, retry with growing waits, and cap the request count.
   - **4a.** With `voice_batch.py` (generate, check, regenerate, join, align, and add to `voices.json`): copy [voice-batch.example.json](assets/voice-batch.example.json) to `voices/batch.json`, fill in the top-level placeholders (`stt_quick`, `stt_words` and `aligner_label`, which `--no-stt` does not read) and those of the voices you run, and delete the voices and cap keys you do not use (a batch of unpaid local voices needs no caps). Run `python3 <skill>/scripts/voice_batch.py --config voices/batch.json --dry-run`, get the owner's yes, then run the same command with `--merge-manifest` in place of `--dry-run`. When an API voice stays dry-run only (no budget or no key), pass `--only-voices <local voice ids>` on the live run. Then skip steps 5 and 6 and stage 6.
   - **4b.** With `tts_generate.py`, one voice at a time (two API adapters as worked examples, plus a `command` adapter for any local voice tool or, with `--paid`, any paid speech tool); then run steps 5 and 6 and stage 6 yourself.
   - **4c.** Takes made by hand (the owner's recording, or audio from a web app by hand or by browser): save one file per scene as `voices/<id>/s<N>.wav`, converting each with the audio tool to one sample rate and 16-bit PCM (for example `ffmpeg -i <in> -ac 1 -ar 24000 -c:a pcm_s16le voices/<id>/s<N>.wav`; check the real file type first). Then run steps 5 and 6 and stage 6, and write the `voices.json` entry by hand (kind `recorded`, or the vendor's kind; model, voice, created, note), starting from [the template](assets/voices.json) with its two example takes deleted, as in step 7. For a single full-length file, see [takes made by hand](references/voices.md#takes-made-by-hand).
5. Check every scene with `python3 <skill>/scripts/check_takes.py` (it needs the transcriber and its model file): tag words inserted relative to the script, and whether the ending is heard. Regenerate a leaking scene plain, keep the tagged file beside it, re-check, and cap the retries.
6. Join with `python3 <skill>/scripts/join_scenes.py --take-dir voices/<id> --out voices/<id>/<id>.wav --scenes script/scenes.json`, which writes exact scene offsets to `voices/<id>/<id>-scenes.json`.
7. Keep WAV masters. Record model id, voice, date and any known fault (`note`) per take in `voices/voices.json` (when writing it by hand, copy [the template](assets/voices.json) there and delete its two example takes, keeping the `none` entry; `voice_batch.py --merge-manifest` writes it for you). Set its `default` to the owner's pick.

"No voice" is always a manifest entry. With voice set to none, this gate records the owner's confirmation and the reading estimate; check that `voices/voices.json` holds only the `none` entry (written at stage 1, step 8; write it now if it is missing). Details: [voices](references/voices.md) and [speech provider examples](references/example-speech-providers.md).

## 6. Alignment

Give every take a timing file (`scenes[]` and `sentences[]` with start and end seconds; [example](assets/timing.example.json)) from word timestamps aligned to the canonical script with `python3 <skill>/scripts/align_words.py`. Its inputs are the transcriber's word JSON, the script, the duration and, optionally, the scene offsets from the join. It prints matched words per take and exits 3 and writes nothing when a sentence is shorter than 0.05 s, when three or more script words at the end were not heard, or when fewer than `--min-match` of the words matched (default 0.6); see [alignment](references/alignment.md#failures).

Treat sentence starts as approximate to a few hundred milliseconds. Without a transcriber, `--no-stt` spreads words by count inside the exact scene offsets and says so in the take's `method` (`voice_batch.py --no-stt` runs the whole take this way). Details: [alignment](references/alignment.md) and [local tool examples](references/example-local-tools.md).

## 7. Gate 3: music options

1. Offer at least two options, or one plus none: owner-supplied, generated, or licensed.
2. For a generated option, write two or three prompts as in [music](references/music.md#prompting-generated-music) and treat each request as a paid call: dry-run it with [api_media.py](scripts/api_media.py), using the full line under Music (gate 3) in [the by-hand guide](workflows/by-hand.md#one-agent-stage-by-stage) and the labelled worked example for [Lyria](references/example-media-providers.md#worked-example-google-lyria-music-through-the-gemini-api), get the owner's yes and the cap for the batch, then run it live. With the agent tool's own generator or a web app, follow [the built-in generator path](references/generated-media.md#without-an-api-a-built-in-generator-or-a-web-app) and save into `music/source/`.
3. When a track arrives, ask who made it, with what, and whether it is a cover, remix or derivative (a title containing "cover", "remix" or "in the style of" always raises this question). Until the owner answers, list it with `rights` set to `pending: <question>, asked <date>` and keep it out of the default, any export and any shared build; a track with no rights recorded is handled the same way. Listing it in `tracks.json` is fine for the owner's own preview: the served page marks it "(rights pending)", `sync_embed.py` embeds it as not ready, and `mix_audio.py` refuses it. Before a served build is shared beyond the owner, take its entry out of `tracks.json` until the rights are answered, then run `sync_embed.py` for every build. Building and measuring its bed may go ahead. Details: [music](references/music.md#rights-and-provenance).
4. Keep every source untouched in `music/source/`. Check generated music for vocals with the transcriber (`make_bed.py --vocals-check --stt-cmd "<transcriber command with {in}>"`, step 5); with no transcriber, listen for vocals.
5. Build each bed with `python3 <skill>/scripts/make_bed.py`, passing `--id <id> --label "<label>"` (the id becomes the track's `id` in `tracks.json`, which export's `--track-id` takes; without `--id` it is the output file's name without its extension). It measures the source (integrated loudness, peak, last 8 s), trims any fade-in head and fade-out tail, joins enough plays with a crossfade to reach `--min-seconds` (the longest video duration over every take and No voice, plus a margin of about 10 s: `duration` in `cues.json` for No voice, `__video.duration` or the duration `python3 <skill>/scripts/mix_audio.py` prints for a take), applies a static gain to about -30 LUFS, verifies, and checks each seam (short-term loudness within about 3 LU of its neighbours; a source that fades out leaves a hole at the seam).
6. In the page, play the bed at half gain under a voice (about 14 dB under speech near -22 LUFS) and full gain with no voice. Fade in over 2 s from t = 0 and out over 4 s ending on the last frame. The bed plays once from t = 0 and seeks with the video; sound starts when the viewer presses Play.
7. Present the beds side by side: add each bed to `music/tracks.json` (copy [the template](assets/tracks.json) to `music/tracks.json` once and delete its two example tracks) with `default` left at `off`, serve the project with `serve_range.py` (start, check and stop it as in [the by-hand guide](workflows/by-hand.md#looks-gate-1), checking the build's `index.html`), and let the owner switch Music in a build's own controls under the picked voice; or list the beds in `PLAN.md` as a table, or as a page of `<audio>` elements. Record the pick and its reason in `PLAN.md`.
8. Record source, rights answer with date, prompt, model, cost and watermark per track in `music/tracks.json`. For a generated track, `make_bed.py --origin generated --media-log media/media-log.jsonl` fills the generation fields from its record; for a track made without `api_media.py`, copy them from the record you wrote (see [generated media](references/generated-media.md#the-generation-record)). Set its `default` to the owner's pick (never a track whose rights are pending or not recorded), then run `sync_embed.py` for every build.

With music set to none, record the owner's confirmation in `PLAN.md` first. Then either write `music/tracks.json` with an empty `tracks` list or make each build's cues with `--no-music`, and run `sync_embed.py` for every build. Details: [music](references/music.md).

## 8. Generated images and video

Run this stage only when the owner chose generated media or screen recordings. For screen recordings alone, keep each untouched file under `media/source/` and go to step 5.

1. At stage 8, once each shortlisted look has its build folder, merge the shortlisted looks' and builds' `image-requests.json` entries into `media/image-requests.json`, the one list this stage works from and where `picked` is set; then turn its entries ([example](assets/image-requests.example.json)) into requests after the look is picked.
2. Make one small test first, on the owner's yes, within a cap. Dry-run every paid request with `python3 <skill>/scripts/api_media.py`, which keeps the spend ledger. Download results at once, because servers delete them. Without an API (the agent tool's own generator, or a web app by hand or by browser), follow [the built-in generator path](references/generated-media.md#without-an-api-a-built-in-generator-or-a-web-app).
3. When two tools are available, generate each request on both and let the owner pick per slot.
4. Pin the model; check the real file type; zoom any in-image text at the size it will show; keep production words (asset, deliverable, module) out of prompts. Set exact colours and fonts in the page code.
5. For clips, strip the audio track unless the owner keeps it (export then mixes it in; see [export](references/export.md)), make loops with the same first and last frame, and record provenance. Place clips and screen recordings on the timeline as in [generated media](references/generated-media.md#video-on-the-timeline). Watermarks survive edits; content credentials survive only in the untouched source.
6. Place each picked image as in [generated media](references/generated-media.md#placing-picked-images): keep the untouched original under `media/generated/`, set the request's `picked` in `media/image-requests.json` to it and log the pick in `PLAN.md`, replace the stand-in in every build with the image and its per-mode `blend`, then run `sync_embed.py`, `static_check.py` and `timing_audit.mjs`, and have the host check both modes.

Details: [generated media](references/generated-media.md) and [media provider examples](references/example-media-providers.md).

## 9. Viewer

Copy [viewer.html](assets/viewer.html) and [viewer.json](assets/viewer.json) into `<video-id>/`, set its title, `default_build` and builds, and check that viewer.json's `message_type` matches the builds' `cues.json`. The viewer switches build, voice (every take plus No voice), music (Off plus every bed), light or dark, and captions, and keeps its state in its URL.

Each build supports `?embed=1` and the viewer API: `voices()`, `tracks()`, `setVoice(id)` (keeps scene and fraction, resumes if playing), `setMusic`, `setMode`, `setCaptions`, `seekScene(n, f)`, `state()` and `ready`. It posts a state message to the parent on every change. A take or bed whose files are missing shows as not ready, and the page keeps working. Adding one is a manifest edit.

Serve with `python3 <skill>/scripts/serve_range.py`, which supports byte ranges so audio can seek. It binds to 127.0.0.1 unless the owner asks to test on a phone. Start, check and stop the server as in [the by-hand guide](workflows/by-hand.md#looks-gate-1), checking `<video-id>/viewer.html` before you give the owner its URL. Details: [viewer](references/viewer.md).

## 10. Gate 4: timing check

These rules hold for every voice and for No voice:

- **R1** A title card of about 3.5 s comes before any narration. Music still starts at t = 0. A loop or text-only piece may drop the card (`make_cues.py --title-card 0`) with the owner's recorded confirmation; the card element stays in the page and the runtime keeps it hidden.
- **R2** Nothing is on screen before the narration says it. Each narration-tied element first shows within a window from 0.3 s before its sentence (or key phrase) starts to 0.5 s after. Quoted lines appear as spoken.
- **R3** Scenes open nearly empty (label and background) and build.
- **R4** Elements hold until the narration moves past them and clear at a scene change or a replacement, never mid-sentence.
- **R5** Prove it per voice. Tag every narration-tied element with `data-cue` and run `node <skill>/scripts/timing_audit.mjs --build <video-id>/<build-id>` for every build. It writes `qa/timing-audit.json` and exits non-zero on any violation. After a new take, a timing fix or a script change, add `--strict`: an unavailable manifest voice then exits non-zero. Without `--strict`, that gap prints `INCOMPLETE` and exits 0.
- **Opening frame.** After the title card, nothing overlaps or is clipped, in both modes, at 1920x1080 and inside the viewer.

Then the host looks at t = 0, the end of the title card, every scene start and every take's last line. With no voice, the audit uses the estimated cues in `cues.json`: each sentence lasts its words at `make_cues.py`'s `--wps` (2.4 by default), and R4 keeps each element up at least that long. For text-only pieces, rerun `make_cues.py` for every build with a lower `--wps`, then `sync_embed.py` and `timing_audit.mjs`, until the owner, watching once at full length, says it reads well; the audit prints the shortest visible span. The owner signs off. Details: [timing check](references/timing-check.md).

## 11. Review and fix

1. One reviewer checks every build against R1 to R5, the opening frame, the stage and viewer contracts and the notes files, using [the review checklist](assets/templates/review-checklist.md). It changes no build file and writes its findings only to `<video-id>/review.md` (on Claude Code's prototype workflow it returns them in the review stage's result instead). With one session, run the review as a separate pass before changing any file.
2. Only when the review finds something, one strong model makes the fixes to every build. With one model, that session makes the fixes.
3. The host runs the acceptance list in a real browser with sound: every voice plays with its own captions (hidden at load when captions are off), every bed stays in sync after a seek, Off is silent, nothing sounds before Play, `setVoice` while playing keeps playing, embed hides the duplicated controls, the console shows no errors other than 404s for takes or beds listed as not ready, narrow widths work, and the opening frame is clean.
4. Owner notes that arrive while a builder is busy go in a written note ([change brief template](assets/templates/change-brief.md)) that the builder reads on its next turn and the reviewer also reads.

A builder's report of "programmatic checks pass, browser unverified" is normal; the host closes the gap. Details: [review and iterate](references/review-and-iterate.md).

## 12. Iterate after output

Most owners keep changing things after the first output. Each recipe ends with the timing check for every voice. The commands are in the Iterate block of [the by-hand guide](workflows/by-hand.md#one-agent-stage-by-stage); the full recipes are in [review and iterate](references/review-and-iterate.md#iteration-recipes):

- **New voice:** audition it as in stage 5, steps 2 and 3 (optional for a scratch voice), add its entry to `voices/batch.json`, run `voice_batch.py --only-voices <id>` with `--dry-run` and then with `--merge-manifest` after the owner's yes for a paid voice (add `--no-stt` when there is no transcriber), and run `sync_embed.py` per build. A take made by hand (kind `recorded`, or audio from a web app) skips `voice_batch.py`: save its scenes and run the lines in [stage 5, step 4c](#5-gate-2-voice-auditions-and-takes), write its `voices.json` entry by hand, then run `sync_embed.py` per build.
- **New music:** handle rights as in stage 7, step 3, build and measure the bed, add it to `tracks.json`, and rerun `make_cues.py` with `--tracks-manifest ../../music/tracks.json` for any build made with `--no-music`.
- **Timing fix:** move the anchor, never a seconds value.
- **New look or build:** snapshot first, and keep the earlier version selectable.
- **Script change:** edit `script.txt` and `scenes.json` together, check that every changed scene's beats still point at the right cue, and renumber the `data-cue` ids in every scene from the first changed sentence onward (cue ids run across the whole script; BEATS `k` indices count within a scene), and renumber `scenes.json` and the take folders' scene files when a scene is added or removed ([review and iterate](references/review-and-iterate.md#iteration-recipes)). For a take made by hand, re-record or re-export only the changed scenes as `voices/<id>/s<N>.wav` and rerun step 4c's check, join, transcribe and align lines.

After any of these, run `sync_embed.py` for every build used from disk and `timing_audit.mjs --strict` for every build, and update each build's `SCENES-NOTES.md` (takes and durations, tracks and their rights state, moved anchors, checks run). When `sync_embed.py` reports a bed shorter than the longest video, rebuild that bed from its untouched source with the `--min-seconds` it prints and update its `tracks.json` measurements (keep the rights fields).

When an MP4 was already delivered, run stage 13 again for each delivered combination of build, voice, bed, mode and captions, and keep the earlier file under a dated name.

Record each change in the decision log as "time, subject, decision, because". Details: [review and iterate](references/review-and-iterate.md).

## 13. Export

Capture frames by seeking `?render=1` pages with any headless browser; the Playwright example in [export](references/export.md#frames) also writes `export/clips.json`, which the mix needs when a clip keeps its audio. When voice and music are both none and no clip keeps its audio, skip the mix and encode without an audio track (`-an`; the line is in [export](references/export.md#loops)). Otherwise mix the audio with `python3 <skill>/scripts/mix_audio.py` from the `cues.json` music and voice blocks (voice delayed by the pre-roll, bed gain and fades as in the page). With a bed, pass `--bed music/<bed>.mp3 --tracks music/tracks.json --track-id <bed-id>` so its rights are checked; full line in [export](references/export.md). Then encode, and compare the MP4 with the viewer at every scene start. Treat the procedure as unproven on a new setup: check the first export frame by frame and by ear. Details: [export](references/export.md).

## Running it on your agent tool

- Any agent tool, one session: follow the stages in order. With several agents available, fan out the look round, the builds, the per-voice checks and the audits; fan-out is optional, and every gate comes back to the owner.
- Claude Code with the Workflow tool: run [the prototype workflow](workflows/prototype.js) one stage per call (looks, build, takes, audit or review), after the owner's go for that stage. Pass its absolute path as `scriptPath` and `{stage, project, skill_dir, ...}` as `args` (listed at the top of the file; `cue_flags` carries the make_cues.py flags the owner's picks need, and `fixer_model` routes the review stage's final fixer; for a later video in a series, pass `script_dir` and `voices_dir` as `script/<video-id>` and `voices/<video-id>`). It makes no paid calls and generates no speech or music, so voice generation, music beds, gate picks and export run by hand. Its takes stage needs a transcriber (`stt_quick` and `stt_words` in `args`); without one, process the takes by hand with `--no-stt` as in [stage 6](#6-alignment) (`voice_batch.py --no-stt --merge-manifest` for a batch voice).
- Any other agent tool (for example Codex, Grok Build, Antigravity, a single chat, or Claude Code without the Workflow tool): follow [the by-hand guide](workflows/by-hand.md).

## Files

References:

- [intake.md](references/intake.md): goal questions, pick list, tool map, browser and local paths, decision log format.
- [script.md](references/script.md): series and outline tables, writing for speech, script and `scenes.json` formats, cue-check normalisation.
- [look-prototypes.md](references/look-prototypes.md): choosing concepts, briefs, `LOOK.md`, compare page, shortlist, design checklist, sample beat table.
- [stage-contract.md](references/stage-contract.md): the technical contract every look and build meets.
- [build.md](references/build.md): build brief, `cues.json`, anchors, retiming, clock and sync, take edge cases.
- [voices.md](references/voices.md): voice kinds, design prompts, style lines, auditions, scene-by-scene generation, checks, cost.
- [alignment.md](references/alignment.md): word timestamps, the algorithm, timing file format, failures and caveats.
- [music.md](references/music.md): options, prompt pattern, bed recipe, seam check, page mixing, `tracks.json`, rights.
- [generated-media.md](references/generated-media.md): stand-ins, requests, image and clip gotchas, generation records, provenance.
- [timing-check.md](references/timing-check.md): R1 to R5, opening frame, audit spec, determinism, host checks.
- [viewer.md](references/viewer.md): layout, manifests, URL parameters, API, state messages, serving.
- [review-and-iterate.md](references/review-and-iterate.md): roles, change briefs, review and acceptance, iteration recipes.
- [export.md](references/export.md): frame capture, mixing, encoding, loops, export checks.
- [spend-and-credentials.md](references/spend-and-credentials.md): owner-placed keys, spend guard, ledger, billing preflight.
- [example-speech-providers.md](references/example-speech-providers.md): worked examples for two speech APIs, a web app and local voices.
- [example-media-providers.md](references/example-media-providers.md): worked examples for music, images, clips, billing and provenance.
- [example-local-tools.md](references/example-local-tools.md): worked examples for the transcriber, audio tool, server test and headless capture.

Scripts (Python 3.9 or later with the standard library, unless noted):

Audio tools: `make_bed.py`, `mix_audio.py` and `voice_batch.py` need ffmpeg and ffprobe; `check_takes.py` needs ffmpeg; `join_scenes.py` uses ffmpeg to measure loudness (skipped with a note without it) and to convert scenes whose formats differ; `tts_generate.py` uses ffmpeg to convert a tool's non-WAV output; `align_words.py` uses ffprobe when `--duration` is not given; `api_media.py` uses ffprobe when it is present.

- [serve_range.py](scripts/serve_range.py): local static server with byte ranges; `--self-test`.
- [probe_tools.py](scripts/probe_tools.py): reports reachable tools and whether key variables are set.
- [cue_check.py](scripts/cue_check.py): cued words match the canonical script; banned strings.
- [make_voice_pack.py](scripts/make_voice_pack.py): renders the voice pack for hand auditions.
- [make_cues.py](scripts/make_cues.py): writes the estimated `cues.json` from the script.
- [tts_generate.py](scripts/tts_generate.py): scene-by-scene speech with pacing, retries, caps and dry run.
- [check_takes.py](scripts/check_takes.py): tag leaks, endings and match rate per scene (needs a transcriber).
- [join_scenes.py](scripts/join_scenes.py): joins scene files with a gap and writes exact offsets.
- [align_words.py](scripts/align_words.py): word timestamps to a timing file; fails on a missing ending.
- [voice_batch.py](scripts/voice_batch.py): generate, check, regenerate, join and align per voice.
- [make_bed.py](scripts/make_bed.py): music bed with trims, crossfades, loudness target, seam and vocals checks.
- [sync_embed.py](scripts/sync_embed.py): embeds cues and manifests for use from disk.
- [static_check.py](scripts/static_check.py): contract checks on a page.
- [timing_audit.mjs](scripts/timing_audit.mjs): the R1 to R5 audit for every voice and mode (Node 18 or later).
- [frame_review.py](scripts/frame_review.py): capture list for the host, with an optional capture command.
- [api_media.py](scripts/api_media.py): guarded paid generation call with dry run and generation log.
- [spend_ledger.py](scripts/spend_ledger.py): the shared spend ledger and caps; `--reserve` and `--outcome` for paid items made outside the scripts.
- [mix_audio.py](scripts/mix_audio.py): export mix of voice and bed.

Assets and templates:

- [build-template/](assets/build-template/index.html): a working build implementing the stage and viewer contracts, with its [cues.json](assets/build-template/cues.json).
- [compare.html](assets/compare.html) and [looks.json](assets/looks.json): the look comparison page.
- [viewer.html](assets/viewer.html) and [viewer.json](assets/viewer.json): the parent viewer.
- [voices.json](assets/voices.json), [tracks.json](assets/tracks.json), [voice-batch.example.json](assets/voice-batch.example.json), [voices-shortlist.example.json](assets/voices-shortlist.example.json), [timing.example.json](assets/timing.example.json), [scenes.example.json](assets/scenes.example.json), [image-requests.example.json](assets/image-requests.example.json): data formats.
- [timing-audit.js](assets/timing-audit.js): the audit core, also pasteable into a browser console.
- Templates: [PLAN.md](assets/templates/PLAN.md), [look-brief.md](assets/templates/look-brief.md), [LOOK.md](assets/templates/LOOK.md), [build-brief.md](assets/templates/build-brief.md), [SCENES-NOTES.md](assets/templates/SCENES-NOTES.md), [change-brief.md](assets/templates/change-brief.md), [review-checklist.md](assets/templates/review-checklist.md).

Workflows: [prototype.js](workflows/prototype.js) for Claude Code's Workflow tool, [by-hand.md](workflows/by-hand.md) for every other agent tool and for Claude Code without that tool.
