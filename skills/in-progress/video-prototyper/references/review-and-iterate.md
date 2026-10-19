# Review, fix and iterate

Who checks what, how changes reach busy builders, and the recipes for the changes owners make after the first output. Templates: [change-brief.md](../assets/templates/change-brief.md) and [review-checklist.md](../assets/templates/review-checklist.md).

## Contents

- [Roles](#roles)
- [Change briefs](#change-briefs)
- [Notes for a busy builder](#notes-for-a-busy-builder)
- [Review](#review)
- [Final fixes](#final-fixes)
- [Host acceptance](#host-acceptance)
- [Iteration recipes](#iteration-recipes)
- [Snapshots and live builds](#snapshots-and-live-builds)

## Roles

Responsibilities, not headcount: one person and one agent can hold every role.

| Role | Does |
|---|---|
| Owner | States the goal; approves each gate; makes every pick; holds money, keys, sign-ins, installs, downloads and rights; judges by eye and ear. |
| Host (the main session; when it cannot serve or open a browser, the owner runs the server and the browser and sound checks it prints) | Writes briefs; runs the server; generates and aligns takes, builds beds, writes manifests and the viewer; runs every check a sandboxed agent cannot (real browser, sound, pixels, the server); checks vendor claims on the vendor's own pages; takes the billing baseline. |
| Builders | Build only inside their own folder to one spec; run programmatic checks; keep notes current; list wanted images instead of generating them; return one line per scene, their open questions, and what their checks did not cover. |
| Reviewer | Changes no build file; checks every build against the rules, the contracts and the notes, and writes its findings to `<video-id>/review.md` (on the prototype workflow, returns them in the review stage's result). |
| Final fixer | One strong model, only when the review finds something; fixes every build. |

## Change briefs

Each pass gives each builder a brief: numbered requirements, a "Done when" list of checks with expected results, the reason in one line, and constraints (keep the contracts working; change only your own folder; fix timing by moving anchors). When the brief answers something the owner saw, include the concrete observation: the voice, the time on screen and the time the words were spoken, so the builder can reproduce it.

## Notes for a busy builder

Some agents can be messaged mid-run; many cannot. When the owner says something while a builder is busy, write it to a short note in the builder's folder or the run folder: what the owner said, what a screenshot shows, the ask, and "also give this to the reviewer". The builder reads it on its next turn; the reviewer reads it too.

## Review

After builders return, one reviewer, who changes no build file, checks every build against [the review checklist](../assets/templates/review-checklist.md): R1 to R5 and the opening frame, the stage and viewer contracts, the audit and static-check reports, and the notes files against the pages. Stale notes are a finding.

A builder's report of "programmatic checks pass, browser unverified" is normal and expected from a sandbox. It is a partial result, not a failure; the host closes the gap.

## Final fixes

Only when the review finds something, one strong model makes the fixes to every live build, then the audit and static check run again for every voice.

## Host acceptance

In a real browser with sound, on the range server: every item under "Host" in [the review checklist](../assets/templates/review-checklist.md). The defects that builders' own checks miss are exactly these: text seconds ahead of the voice, a full scene on screen at t = 0, an opening that overlaps or clips, a voice switch that leaves playback paused, audio that cannot seek. Read voice, music and timeline times side by side with `__video.diagnostics()` in the build page's console (open the build's `index.html`, or from the viewer's console run `document.getElementById('frame').contentWindow.__video.diagnostics()`).

Each report says what was verified and what was not.

## Iteration recipes

Most owners keep changing things after the first output. Each recipe ends with the timing audit for every voice and a host look at the changed scenes.

**New voice.** Audition or design it on one or two short scenes (optional for a scratch voice), then take one route:

- With [voice_batch.py](../scripts/voice_batch.py), which does every step below: add the voice's entry to `voices/batch.json` (copy an existing entry; a local voice needs `command` and `command_ext`), dry-run it with `voice_batch.py --config voices/batch.json --only-voices <id> --dry-run`, then run it with `--merge-manifest` after the owner's yes for a paid voice (add `--no-stt` when there is no transcriber, then listen to every ending).
- Step by step: generate scene by scene with [tts_generate.py](../scripts/tts_generate.py), dry run first and live only after the owner's yes for a paid voice; check with [check_takes.py](../scripts/check_takes.py); regenerate leaking scenes plain; join with [join_scenes.py](../scripts/join_scenes.py); transcribe and align with [align_words.py](../scripts/align_words.py); add it to `voices.json`.
- Made by hand (kind `recorded`, or audio from a web app): save one file per scene as `voices/<id>/s<N>.wav`, run the check, join, transcribe and align lines of [SKILL.md stage 5, step 4c](../SKILL.md#5-gate-2-voice-auditions-and-takes) (the Takes made by hand comments under [Voices (gate 2) in the by-hand guide](../workflows/by-hand.md#voices-gate-2)), and write its `voices.json` entry by hand.

Then run [sync_embed.py](../scripts/sync_embed.py) for every build used from disk. When it reports a bed shorter than the longest video, rebuild that bed from its untouched source with the `--min-seconds` it prints and update its `tracks.json` measurements (keep the rights fields). No page code changes.

**New music.** Keep the source untouched. Ask the composition-rights question as soon as the track arrives (a "cover" in the title is one such question). Building and measuring the bed may go ahead, because it is local ([make_bed.py](../scripts/make_bed.py)). Until the owner answers, list the track with `rights` set to `pending: <question>, asked <date>`, keep it out of the default and out of any export or shared build, and carry the question in the report. Then add the printed entry to `tracks.json` and record its rights as above. Before a served build is shared beyond the owner, take a pending track's entry out of `tracks.json` until the rights are answered, then run `sync_embed.py` for every build. In each build whose `cues.json` has `music.manifest` null (made with `--no-music`), rerun [make_cues.py](../scripts/make_cues.py) for that build with `--tracks-manifest ../../music/tracks.json` first; it keeps the rest of the file. Without this the build lists only Off. Sync for disk use and re-audit every voice with `--strict`.

**Timing fix.** Find the element and its anchor; move the anchor (cue index within its scene, fraction), never a seconds value; when the element belongs to a key phrase, set the same fraction in `data-cue-at`. Re-audit every voice.

**New look or build.** Snapshot first. Copy the closest build, keep the earlier one selectable in `viewer.json`, and apply the same contract.

**Script change.**

1. Edit `script.txt` and `scenes.json` together. To add or remove a scene, renumber `scenes.json` so `n` runs 1 to N again. Run [cue_check.py](../scripts/cue_check.py). A wording change that keeps the sentence counts still makes the old take stale.
2. Rewrite every build's `cues.json` with [make_cues.py](../scripts/make_cues.py) (it keeps each build's title card, pace, music, voices, message type, mode, loop, captions default and target length).
3. When a sentence is added or removed, the id of every later cue shifts by that count. In each build, renumber the `data-cue` attribute on every element in the changed scene and every later scene to its new id (clips anchored by `data-cue` too). The BEATS `k` indices count within a scene; in unchanged scenes they stay as they are, and in a changed scene check each one still points at the right sentence. An audit line reading "sits in scene N but its sentence is in scene M", or R2 lines for a scene nobody edited, mean the ids shifted this way.
4. When a scene was added or removed: in each take folder, move a removed scene's `s<N>.wav` and `s<N>.json` aside and rename every pair whose number changed to its new number (start from the last scene when numbers go up); their generation records still match their words, so only new or edited scenes are generated. A leftover `s<N>.wav` past the last scene is ignored with a warning; move it aside.
5. Regenerate only the changed scenes (`tts_generate.py` with the take's own `--scenes`, `--adapter`, `--voice-id` and `--out-dir`, plus `--model` and `--key-env` (API) or `--command` and `--command-ext` (local) as in `voices/batch.json`, plus `--only <n,m> --force`, after the dry run and the owner's yes for a paid voice).
6. Check, join and align the whole take (`voice_batch.py --only-voices <voice> --merge-manifest` (plus `--no-stt` with no transcriber) does all three), then run `sync_embed.py`. When `sync_embed.py` reports a bed shorter than the longest video, rebuild that bed from its untouched source with the `--min-seconds` it prints and update its `tracks.json` measurements (keep the rights fields).
   For a take made by hand, steps 5 and 6 are: re-record or re-export the changed scenes as `voices/<id>/s<N>.wav`, rerun the check, join, transcribe and align lines of [SKILL.md stage 5, step 4c](../SKILL.md#5-gate-2-voice-auditions-and-takes), and update its `voices.json` entry by hand; then run `sync_embed.py`.
7. Audit every voice with `--strict`.

When an MP4 was already delivered, run stage 13 again for each delivered combination of build, voice, bed, mode and captions, and keep the earlier file under a dated name.

Record each change in the decision log as "time, subject, decision, because", and update each build's `SCENES-NOTES.md` (takes and durations, tracks and their rights state, moved anchors, checks run), since stale notes are a finding.

## Snapshots and live builds

- Snapshot a build before a polish round so the earlier version can be kept if the owner prefers it.
- Apply every pass to every live build until the owner drops one, even when one is preferred.
- Shared folders (voices, music) are written only by the host, never from a build folder.
