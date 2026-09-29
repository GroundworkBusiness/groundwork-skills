#!/usr/bin/env python3
"""Turn a WebVTT caption file, such as a Microsoft Teams meeting transcript, into plain text
with one line per speaker turn, and check that the text kept every spoken word.

Usage:
    python3 vtt_to_text.py FILE                        print the transcript
    python3 vtt_to_text.py FILE --check                compare word counts
    python3 vtt_to_text.py FILE --check --copy COPY    check a prepared copy instead

Each output line reads "[HH:MM:SS] Speaker: text". Every text line of every cue is kept.
Teams splits most cues over two or more lines and tags only the first with <v Speaker>, so a
line with no tag belongs to the voice tagged before it in the same cue. Consecutive cues by one
speaker merge into a single turn that keeps the first cue's start time. A cue with no <v> tag
at all is labelled "Unknown" and kept as its own turn, because the file does not say who spoke
it. Inline tags are removed and character references such as &amp; are decoded. A line that
starts with a digit is spoken text unless it is a timing line or a cue identifier.

--check prints three word counts on one line, then PASS or STOP:
    raw          words in the file's text lines, found by a plain line filter that shares no
                 parsing code with the converter, so the check can catch the converter
    copy         words in the converted text, or in COPY, leaving out each line's timestamp
                 and speaker label
    tagged_only  words on the lines that begin with a <v> tag, which is all that a reading of
                 the tagged lines alone would get
It passes only when copy equals raw exactly. A word is a run of characters between spaces once
tags are removed and references decoded; a <v> or </v> tag also separates words. COPY can be
this script's own output or "Speaker: text" lines that use the speaker names as the file
writes them.

Exit status:
    0  printed the transcript, or the check passed
    1  usage error, a file could not be read, or the output was cut off
    2  STOP: the copy does not hold the same number of words as the raw file
    3  not a WebVTT file (another extension, or no WEBVTT header), so this step does not apply:
       read the file as it is

Python 3.9 or later, standard library only. Reads FILE and COPY; writes only to stdout and
stderr.
"""

from __future__ import annotations

import argparse
import errno
import html
import os
import re
import sys
from pathlib import Path

UNKNOWN = "Unknown"
EXIT_OK, EXIT_ERROR, EXIT_STOP, EXIT_NOT_VTT = 0, 1, 2, 3

# Text rules shared by both counts: how one line of cue text becomes words.
VOICE_TAG = re.compile(r"<v(?:\.[^\s>]*)?(?:[ \t\f]+([^>]*))?>|</v\s*>")
ANY_TAG = re.compile(r"<[^>]*>")

# File structure.
SIGNATURE = re.compile(r"WEBVTT(?:[ \t].*)?$")
SKIPPED_BLOCK = re.compile(r"(?:NOTE|STYLE|REGION|WEBVTT)(?:[ \t].*)?$")
START_TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:[.,]\d+)?\s*-->")
COPY_TIMESTAMP = re.compile(r"\[\d+(?::\d{1,2}){1,2}(?:[.,]\d+)?\]\s*")


class NotWebVTT(Exception):
    """The input is not a WebVTT file, so this step does not apply to it."""


def clean(text: str) -> str:
    """Cue text to plain text: drop tags first, then decode character references."""
    return html.unescape(ANY_TAG.sub("", text))


def voice_name(annotation: str | None) -> str | None:
    """The speaker named by a <v> tag, with references decoded and spaces collapsed."""
    name = " ".join(html.unescape(annotation or "").split())
    return name or None


def clock(seconds: int) -> str:
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# --- The converter -------------------------------------------------------------------------

def split_lines(text: str) -> list[str]:
    """WebVTT ends a line with CRLF, CR or LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def start_seconds(timing: str) -> int | None:
    match = START_TIME.match(timing)
    if not match:
        return None
    hours, minutes, secs = match.groups()
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(secs)


def collect_cues(lines: list[str]) -> list[list]:
    """Group the file into cues the way a WebVTT parser collects blocks.

    Returns [start_seconds, text_lines] pairs in file order. The header runs from the first
    line to the first blank line or timing line. A block ends at a blank line, and a timing
    line after a block's first two lines starts a new block. A block whose first or second
    line is a timing line is a cue, and a first line above the timing line is its identifier.
    NOTE, STYLE and REGION blocks are skipped. A block of text with no timing line (a blank
    line inside a cue) is kept and joined to the cue before it.
    """
    cues: list[list] = []
    total = len(lines)
    pos = 1                                     # lines[0] is the WEBVTT line
    while pos < total and lines[pos].strip() and "-->" not in lines[pos]:
        pos += 1                                # rest of the header
    last_start = 0
    while pos < total:
        if not lines[pos].strip():
            pos += 1
            continue
        first = pos
        block: list[str] = []
        while pos < total and lines[pos].strip():
            line = lines[pos].strip()
            opens_block = not block or (len(block) == 1 and "-->" not in block[0])
            if "-->" in line and not opens_block:
                break                           # this timing line starts the next block
            block.append(line)
            pos += 1
        if "-->" in block[0]:
            timing_at = 0
        elif len(block) > 1 and "-->" in block[1]:
            timing_at = 1                       # block[0] is the cue identifier
        elif SKIPPED_BLOCK.match(block[0]):
            continue
        else:
            if not cues:
                cues.append([0, []])
            cues[-1][1].extend(block)
            continue
        start = start_seconds(block[timing_at])
        if start is None:
            print(f"vtt_to_text: line {first + timing_at + 1}: no start time in "
                  f"{block[timing_at]!r}; the turn keeps the previous one", file=sys.stderr)
            start = last_start
        last_start = start
        cues.append([start, block[timing_at + 1:]])
    return cues


class Turn:
    __slots__ = ("start", "speaker", "cue", "parts")

    def __init__(self, start: int, speaker: str | None, cue: int, text: str):
        self.start, self.speaker, self.cue, self.parts = start, speaker, cue, [text]

    def prefix(self) -> str:
        label = self.speaker if self.speaker is not None else UNKNOWN
        return f"[{clock(self.start)}] {label}: "

    def line(self) -> str:
        return self.prefix() + " ".join(self.parts)


def build_turns(cues: list[list]) -> list[Turn]:
    """Attribute every piece of cue text to a speaker and merge consecutive pieces."""
    turns: list[Turn] = []
    for number, (start, text_lines) in enumerate(cues):
        speaker = None                          # the voice tagged most recently in this cue
        for line in text_lines:
            pieces = []
            pos = 0
            for tag in VOICE_TAG.finditer(line):
                pieces.append((speaker, line[pos:tag.start()]))
                if tag.group(0).startswith("<v"):
                    speaker = voice_name(tag.group(1))
                pos = tag.end()
            pieces.append((speaker, line[pos:]))
            for who, piece in pieces:
                text = " ".join(clean(piece).split())
                if not text:
                    continue
                last = turns[-1] if turns else None
                if last and last.speaker == who and (who is not None or last.cue == number):
                    last.parts.append(text)
                else:
                    turns.append(Turn(start, who, number, text))
    return turns


def convert(text: str) -> list[Turn]:
    return build_turns(collect_cues(split_lines(text)))


# --- The check -----------------------------------------------------------------------------

def raw_counts(text: str) -> tuple[int, int, set]:
    """Count the file's words with a plain line filter that shares no parsing code with the
    converter above, so the check can catch the converter.

    Keeps every line except blank lines, timing lines (any line holding "-->"), the header,
    cue identifiers (a block's first line when the next line is a timing line), and the lines
    of NOTE, STYLE and REGION blocks. Returns (raw, tagged_only, speaker names).
    """
    lines = re.split(r"\r\n|\r|\n", text)
    raw = tagged_only = 0
    voices: set = set()
    total = len(lines)
    i = 1
    while i < total and lines[i].strip() and "-->" not in lines[i]:
        i += 1                                  # header
    at_block_start, skipping = True, False
    for j in range(i, total):
        line = lines[j].strip()
        if not line:
            at_block_start, skipping = True, False
            continue
        if "-->" in line:
            at_block_start, skipping = False, False
            continue
        if at_block_start:
            at_block_start = False
            if j + 1 < total and "-->" in lines[j + 1]:
                continue                        # cue identifier
            if SKIPPED_BLOCK.match(line):
                skipping = True
        if skipping:
            continue
        words = len(clean(VOICE_TAG.sub(" ", line)).split())
        raw += words
        if line.startswith("<v"):
            tagged_only += words
        for tag in VOICE_TAG.finditer(line):
            name = voice_name(tag.group(1)) if tag.group(0).startswith("<v") else None
            if name:
                voices.add(name)
    return raw, tagged_only, voices


def own_copy_words(turns: list[Turn]) -> int:
    """Words in the converter's own output, each line read without its known prefix."""
    return sum(len(turn.line()[len(turn.prefix()):].split()) for turn in turns)


def copy_words(text: str, voices: set) -> int:
    """Words in a prepared copy, leaving out a leading [timestamp] and speaker label."""
    labels = sorted(set(voices) | {UNKNOWN}, key=len, reverse=True)
    total = 0
    for line in re.split(r"\r\n|\r|\n", text):
        line = line.strip()
        stamp = COPY_TIMESTAMP.match(line)
        if stamp:
            line = line[stamp.end():]
        for label in labels:
            head = label + ":"
            if line.startswith(head) and (len(line) == len(head) or line[len(head)].isspace()):
                line = line[len(head):]
                break
        total += len(line.split())
    return total


def words(count: int) -> str:
    return f"{count} word" if count == 1 else f"{count} words"


def run_check(path: Path, copy_path: Path | None) -> int:
    text = read_webvtt(path)
    raw, tagged_only, voices = raw_counts(text)
    if copy_path is None:
        copy = own_copy_words(convert(text))
    else:
        copy = copy_words(read_text(copy_path), voices)
    print(f"raw={raw} copy={copy} tagged_only={tagged_only}")
    if copy == raw:
        if raw:
            lost = 100.0 * (raw - tagged_only) / raw
            print(f"PASS: the copy holds every word of the raw file. A reading of the tagged "
                  f"lines alone would lose {lost:.1f}% of them.")
        else:
            print("PASS: the file holds no spoken text, and neither does the copy.")
        return EXIT_OK
    gap = raw - copy
    if gap > 0:
        problem = f"the copy is {words(gap)} short of the raw file"
    else:
        problem = f"the copy has {words(-gap)} more than the raw file"
    print(f"STOP: {problem}. Do not write from it; fix the conversion and run the check again.")
    return EXIT_STOP


# --- Files and the command line ------------------------------------------------------------

def read_text(path: Path) -> str:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return text[1:] if text.startswith("\ufeff") else text


def read_webvtt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(path))
    if path.suffix.lower() != ".vtt":
        raise NotWebVTT(f"{path.name} is not a .vtt file. This step converts WebVTT captions "
                        f"only; read the file as it is.")
    text = read_text(path)
    if not SIGNATURE.match(re.split(r"\r\n|\r|\n", text, maxsplit=1)[0]):
        raise NotWebVTT(f"{path.name} does not begin with WEBVTT, so it is not a WebVTT file. "
                        f"Read it as it is, or export the captions again.")
    return text


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse exits 2 on a usage error; 2 is reserved for STOP.
        self.print_usage(sys.stderr)
        self.exit(EXIT_ERROR, f"{self.prog}: error: {message}\n")


def _arguments() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="vtt_to_text.py",
        description="Turn a WebVTT caption file into one line per speaker turn, and check "
                    "that no spoken word was lost.",
        epilog="exit status: 0 printed, or check passed; 1 usage error or unreadable file; "
               "2 STOP, the copy does not match the raw file; 3 not a WebVTT file, so read "
               "it as it is")
    parser.add_argument("file", help="the .vtt caption file")
    parser.add_argument("--check", action="store_true",
                        help="print raw, copy and tagged_only word counts; exit 0 only when "
                             "copy equals raw, otherwise 2 with a STOP line")
    parser.add_argument("--copy", metavar="COPY",
                        help="with --check: count this prepared copy instead of converting "
                             "FILE again")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    args = _arguments().parse_args(argv)
    path = Path(args.file)
    try:
        if args.check or args.copy:
            return run_check(path, Path(args.copy) if args.copy else None)
        lines = [turn.line() for turn in convert(read_webvtt(path))]
        if lines:
            sys.stdout.write("\n".join(lines) + "\n")
            sys.stdout.flush()
        return EXIT_OK
    except NotWebVTT as err:
        print(f"vtt_to_text: {err}", file=sys.stderr)
        return EXIT_NOT_VTT
    except BrokenPipeError:
        # The reader stopped early, as `| head` does; silence the rest of the output.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return EXIT_ERROR
    except OSError as err:
        print(f"vtt_to_text: cannot read {err.filename or path}: {err.strerror or err}",
              file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
