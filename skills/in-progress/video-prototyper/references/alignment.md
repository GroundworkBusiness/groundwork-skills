# Alignment

How every take gets its timing file, which every build reads at runtime. The script is [align_words.py](../scripts/align_words.py); the format is shown in [timing.example.json](../assets/timing.example.json).

## Contents

- [Word timestamps](#word-timestamps)
- [The algorithm](#the-algorithm)
- [The timing file](#the-timing-file)
- [Failures](#failures)
- [Caveats](#caveats)
- [Without a transcriber](#without-a-transcriber)

## Word timestamps

Any speech-to-text tool that gives per-word start and end times works. The aligner reads three formats:

| `--format` | Shape |
|---|---|
| `whisper-cpp` | Full JSON: `transcription[]` with `text` and `offsets.from` and `offsets.to` in milliseconds (one word per segment). |
| `words` | `{"words": [{"word", "start", "end"}]}` or `{"segments": [{"words": [...]}]}`, seconds. |
| `list` | `[{"word", "start", "end"}]` or `[[word, start, end], ...]`, seconds. |

Transcribe the joined take resampled to 16 kHz mono. Bracketed non-speech markers such as `[music]` are dropped. Commands for one transcriber are in [example-local-tools.md](example-local-tools.md).

## The algorithm

1. Read the canonical `script.txt`. Paragraphs are scenes. Sentences are split on `.`, `!`, `?` or an ellipsis followed by whitespace or the end; an ellipsis followed by a lowercase word continues the sentence. The split matches [make_cues.py](../scripts/make_cues.py), so sentence ids (`c01`, `c02`, ...) match the build's cue ids.
2. Normalise script and heard words the same way: lowercase, drop `<tags>`, fold curly apostrophes, replace everything outside `a-z`, `0-9` and the apostrophe with a space, split, trim edge apostrophes.
3. Align with `difflib.SequenceMatcher` (no junk heuristic). Matched script words copy the heard times.
4. Unmatched script words are interpolated linearly between their nearest matched neighbours, or clamped to the nearest known time at either end.
5. With `--scene-offsets` from the join, every word is pinned inside its scene's exact range, which stops interpolation from leaking across the gap between scenes.
6. A sentence starts at its first word's start and ends at its last word's end. A scene spans its sentences; `end_with_pause` is the next scene's start (the last scene's is the file length).
7. It prints `matched N of M words` and each scene's range; with `--no-stt` it prints `no-stt spread of M words` and writes `matched` as null.

## The timing file

Shortened to its first scene and first sentence; the full file is [timing.example.json](../assets/timing.example.json) (two scenes, seven sentences, all 60 words).

```json
{
  "schema": 1,
  "voice": "scratch-local",
  "file": "scratch-local.wav",
  "duration": 20.058,
  "method": "word timestamps from <transcriber, version, model> aligned to the script; all 60 script words matched; scene boundaries pinned to the join offsets",
  "matched": 60,
  "words": 60,
  "scenes": [{"scene": 1, "start": 0.0, "end": 9.703, "end_with_pause": 10.4}],
  "sentences": [{"id": "c01", "scene": 1, "text": "It's your first week in Alder Creek, and the kitchen counter is filling up.", "start": 0.0, "end": 4.01}]
}
```

Times are seconds from the start of the take. Pass the transcriber's name, version and model with `--aligner-label` so `method` says how the file was made.

## Failures

The aligner exits 3 and writes nothing when:

- any sentence is shorter than 0.05 s (its words were probably never spoken);
- three or more script words at the end were not heard (a dropped ending);
- fewer than `--min-match` of the words matched (default 0.6), which usually means the wrong script or a bad take.

Then listen to the end of the take, regenerate or re-record the scene, and align again. When the owner chooses to keep the take, `--allow-missing-ending` writes the file with the problem in `warnings`; record the fault as the take's `note` in `voices.json`, and the page shows the missing line in a silent slot.

Clean takes usually match nearly every script word; misses are words the transcriber merged or misheard, and interpolation covers them. A count well below a voice's siblings is worth a listen.

## Caveats

- Some transcribers make word times contiguous, so silence is absorbed into neighbouring words. Treat sentence starts as approximate to a few hundred milliseconds. For tighter sync, locate real pauses with a silence detector (example in [example-local-tools.md](example-local-tools.md)) or use a forced aligner.
- An ellipsis followed by a capital letter starts a new caption sentence. Use ellipses mid-sentence (followed by lowercase) when the pause should not split the caption.
- A script change after alignment changes sentence counts; [sync_embed.py](../scripts/sync_embed.py) and the page then mark the take not ready until it is re-aligned.

## Without a transcriber

`--no-stt --scene-offsets <take>-scenes.json` spreads each scene's words evenly inside its exact offsets. Scene boundaries are exact; sentence times inside a scene are approximate. The `method` says so. Use it for owner recordings when no transcriber is available, and expect R2 to need wider manual checks.

For a single full-length file, cut it into scene files first as in [voices.md](voices.md#takes-made-by-hand).
