# Intake

The questions to ask before planning, how to map each need to a reachable tool, and how to keep decisions on record. The plan template is [PLAN.md](../assets/templates/PLAN.md).

## Contents

- [The goal](#the-goal)
- [The pick list](#the-pick-list)
- [The tool map](#the-tool-map)
- [Browser and computer use](#browser-and-computer-use)
- [Local tools](#local-tools)
- [Expect the answers to change](#expect-the-answers-to-change)
- [The decision log](#the-decision-log)

## The goal

Ask the owner to state it in their own words:

- Who watches, and what they already know.
- What they should know or do afterward.
- Where it plays: a web page, an MP4, a loop on a screen, an embed, a page section triggered on scroll. A scroll-triggered section hosts the same `?embed=1` build in an iframe and calls `play()` through the viewer API when it scrolls into view and `pause()` when it leaves.
- How long it runs. Set no limit unless the owner sets one; trim content for time only to meet a limit the owner set.

Before scripting, also collect: the points that must be said, where each fact comes from, the words and characters banned on screen and in narration (the Banned line of `PLAN.md`), audience wording, which names stay out of the narration, and the owner's standing design rules (art direction every video keeps). The full checklist is in [script.md](script.md#outline).

## The pick list

The owner picks only what applies, one line each:

| Medium | Options |
|---|---|
| Voice | none; owner-recorded; text-to-speech; several to compare |
| Music | none; owner-supplied; generated; licensed library |
| Visuals | code-built motion; generated images; generated video clips; screen recordings |
| Captions | On: the page shows the plate by default (`--captions on`, or no flag); capture the MP4 with `cc=on`. Burned in: the same files as on, naming an MP4 whose captions cannot be turned off; no caption file ships. Toggle: keep the owner's page default (`--captions on` or `off`), capture with `cc=off`, and ship the WebVTT file from [export](export.md). Off: add `--captions off` to every `make_cues.py` call, capture with `cc=off`, and ship no WebVTT. |
| Modes | light; dark; both. For an MP4, record which mode it ships in, or one file per mode. |

A medium set to none still gets its gate as a confirmation: record "none" and what replaces it.

## The tool map

For every need the picks create, record the tool, how it is reached, whether the probe found it, and who acts:

| Need | Tool | Reach | Probed | Who acts |
|---|---|---|---|---|
| Speech | a speech API | API: the owner places the key; the agent reads the variable by name | key set | owner creates the key and pays |
| Voice auditions | the provider's web app | browser or computer use | n/a | owner signs in |
| Transcriber | a local speech-to-text tool | local | yes | agent |
| Audio | an audio tool (ffmpeg in the examples) | local | yes | agent |
| Timing audit | Node 18 or later | local | yes | agent |
| Frame capture | a headless browser | local | yes | agent or host |

Run [probe_tools.py](../scripts/probe_tools.py) before planning. It reports the audio tools, a transcriber, Node, a headless browser, local voices, and whether each named key variable is set, never its value. Agent tools often have image generation but no video generation; record what is missing and ask how the owner wants to fill it. Installs and model downloads are the owner's yes, each named with its source and size.

## Browser and computer use

Some providers are easiest through their web app: voice design, a voice library, a music or clip studio. An agent with browser or computer-use tools can drive the app, with these limits:

- The owner signs in, pays, accepts terms and creates keys. The agent never types a password, a key or payment details.
- Downloads may land in the app's own folder rather than the usual downloads folder; search by modification time.
- Check every downloaded file's real type; an export named `.png` can be another format.
- Consumer-app credits and API credits are usually separate systems; one cannot pay for the other.
- The same work by hand is always an option: give the owner the voice pack or the prompt list and collect the results.

## Local tools

The local path keeps test runs and early iterations free: a local voice (the `command` adapter of [tts_generate.py](../scripts/tts_generate.py)), a local transcriber, an audio tool, Node and a headless browser. Worked examples are in [example-local-tools.md](example-local-tools.md).

## Expect the answers to change

Say this to the owner up front. Any of these can move once real options exist, for example:

- no voice becomes one voice, then several to compare;
- no music becomes one bed, then a second option;
- a length target is dropped, or the content grows past it;
- generated media goes from "maybe" to parked to live;
- the destination grows from a web page to an MP4, a loop, or an embed.

The architecture absorbs it: cue anchors instead of seconds, timing files per take, manifests for takes and beds, and one viewer.

## The decision log

Keep it at the end of `PLAN.md`, one line per decision, so the owner, the host and every agent read the same record:

```text
2026-01-31 14:05, looks, shortlist the chalk and diorama looks, because the owner found both easiest to read at phone size
```

Format: time, subject, decision, because. Record every gate pick, every spend approval with its cap, every rights answer with its date, and every routing verdict (which agent or model did code-built motion well).
