# Transcripts

A caption file is not ready to read as it is. Convert it, check the copy against the file, and
write the recap from the copy only once the check passes. Notes, `.txt`, `.md` and `.docx`
transcripts skip this step.

## Why a `.vtt` needs converting

Microsoft Teams splits most cues over two or more lines and puts the `<v Speaker>` tag on the
first line only:

```text
00:00:03.140 --> 00:00:07.848
<v Lee, Jordan>If we can make this simple
enough, I think people will use it,</v>
```

A reading that keeps only the tagged lines still looks like a clean transcript, and it loses a
third to nearly half of the words. A filter that skips every line starting with a digit, to drop
cue numbers and timings, also drops spoken lines such as "40 hours a month."

## Convert and check

```sh
python3 <skill>/scripts/vtt_to_text.py meeting.vtt > <scratch>/meeting-transcript.txt
python3 <skill>/scripts/vtt_to_text.py meeting.vtt --check --copy <scratch>/meeting-transcript.txt
```

The first command writes one line per speaker turn, `[HH:MM:SS] Speaker: text`, and keeps every
line of every cue. The second prints three word counts:

- `raw`: the words in the file's text lines, counted by a plain line filter that shares no code
  with the converter, so a conversion that drops lines cannot pass
- `copy`: the words in the prepared copy, without its timestamps and speaker labels
- `tagged_only`: what a reading of the tagged lines alone would get

| Exit | Prints | What to do |
| --- | --- | --- |
| 0 | `PASS` | `copy` equals `raw` exactly. Read the copy, all the way to its last line. |
| 2 | `STOP` | Write nothing. Fix the conversion and run the check again. |
| 3 | not a `.vtt` file | The step does not apply. Read the file as it is. |

The script needs Python 3.9 or later and nothing else. Without code execution, read every line
of every cue yourself, including the lines with no tag, and never skip a line because it starts
with a digit.

## Keep the copy and the counts out of the recap

- The prepared copy is a working file. Keep it in a scratch folder, where it can be rebuilt from
  the `.vtt` at any time, and leave the original transcript as it is.
- The counts are working notes. Put them in your own notes or the Internal Working Notes, never
  in the recap (Keep your working out of it, in SKILL.md).
- Call a transcript poorly captured only after the check has passed and the copy still reads
  broken, and then say what is actually missing, such as a gap in the timestamps or a late
  start. A lossy conversion produces the same symptoms.
