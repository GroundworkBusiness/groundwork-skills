#!/usr/bin/env python3
"""Read Claude Code's saved transcripts, and no other format.

This script reads the JSON Lines transcript Claude Code saves for a session or
for one of its subagents, and nothing else: it holds the one piece of
host-specific reading the skill needs, so ao.py and git_lanes.py stay
host-neutral. It lists a transcript's turns, or writes a range of turns as a
context packet for agent-orchestrate.

    python3 claude_transcript.py TRANSCRIPT --list
    python3 claude_transcript.py TRANSCRIPT --turns A-B --out FILE --name NAME --about TEXT
                                 [--revision N] [--with-tool-output]

Requires Python 3.9 or later. Standard library only, so it runs under
`python3 -I`. It reads TRANSCRIPT as UTF-8, one JSON object per line, and skips
a line that is not valid UTF-8 or not a JSON object, counting the lines it
skipped. It makes no network call and writes nothing but --out.

WHERE THE TRANSCRIPT IS
-----------------------
    ~/.claude/projects/<project folder, every / replaced by ->/<session id>.jsonl
    ~/.claude/projects/<project folder>/<session id>/subagents/agent-<agentId>.jsonl

The first is a session's main chat; the session id is the UUID in the
session's scratchpad path. The second is one subagent's own transcript, the
file its spawn result's output_file links to.

WHICH KIND OF FILE
------------------
The script tells the two apart by structure. A subagent's file is one whose
first user or assistant line carries "isSidechain": true and an "agentId"; the
script then reads the lines carrying that agentId. Any other file is a main
chat, read from its lines whose "isSidechain" is not true. In a main chat,
the user's messages are "user" and the model's are "orchestrator". A message
the user typed while the model worked is an "attachment" line of type
"queued_command" whose "origin" "kind" is "human", its text in "prompt". In a
subagent's file the orchestrator speaks: the spawn message first, then each
message it sent, so those turns are "orchestrator", and the model's own are
"agent". A message to a stopped agent is a user line whose "origin" "kind" is
"coordinator", marked "isMeta"; a message to a running agent is an
"attachment" line of type "queued_command" with that origin, its text in
"prompt".

TURNS
-----
A turn starts at a genuine user message and runs to the next one. A user line
is genuine when "type" is "user", it belongs to the file's own lines (above),
"isMeta" and "isCompactSummary" are not true, and its content holds text
rather than only tool results. Where the line carries "origin", its "kind"
must be "human"; where it carries none, its text must not open with
<command-name>, <local-command-stdout>, <local-command-caveat> or
<task-notification>, which mark host-made lines. A queued message, the user's
in a main chat or the orchestrator's in a subagent's file, also starts a turn,
and so does a coordinator user line, though it is marked "isMeta"; a summary
line never does. A line with no "origin" whose whole text is
[Request interrupted by user] or [Request interrupted by user for tool use] is
the host's mark that the user stopped a turn: it starts no turn, and a packet
shows it as one line where it fell. Lines before the first genuine user
message form a turn of their own when the model wrote text or called a tool
there; that turn's speaker is the model, the orchestrator in a main chat and
the agent in a subagent's file. A turn takes the time of its first line.

COMPACTION POINTS
-----------------
A line with "type" "system" and "subtype" "compact_boundary" marks a point
where the live chat was replaced by a summary. The summary line after it
("isCompactSummary": true) is not a turn. The turns before the point stay in
the file. A compaction point that comes before the line opening the first turn
is shown before turn 1, even when other lines sit between them: the file then
holds no turns from before it, as in a session continued after the context
limit, which starts a new file.

WHAT A PACKET HOLDS
-------------------
For each turn: each speaker's text, one line per tool call, "(used NAME:
DESCRIPTION)", with only the description field of the call's input, when it
has one, one line where an agent's completion notice arrived, and one where
the user interrupted. In a subagent's file the spawn message, which opens it,
shows as one line: it holds the standing text and the earlier agent's own
task, which its successor gets in its own form. Left out: thinking,
attachment lines other than the queued messages above, every other field of a
tool call's input, the text of completion notices, and tool result bodies,
which carry file contents and are where secrets sit. --with-tool-output adds
the result bodies. Source names the transcript by its file name without
.jsonl: the session id, or agent-<agentId> for a subagent's file. Any closing
packet tag, in any case, is written with a space after its <, so the packet
cannot end early inside a spawn message.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

PACKET_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
RESERVED_NAMES = frozenset(["claude", "agents", "gemini"])  # each NAME.md loads as instructions
HOST_TAGS = ("<command-name>", "<local-command-stdout>", "<local-command-caveat>",
             "<task-notification>")
COMMAND_RE = re.compile(r"<command-name>\s*(.*?)\s*</command-name>", re.S)
ARGS_RE = re.compile(r"<command-args>\s*(.*?)\s*</command-args>", re.S)
RANGE_RE = re.compile(r"\s*([0-9]+)\s*(?:-\s*([0-9]+)\s*)?")
CLOSE_TAG_RE = re.compile(r"</(packet)", re.I)
# The host's lines when the user stops a turn; a line is one only when its whole text matches.
INTERRUPTED = ("[Request interrupted by user]", "[Request interrupted by user for tool use]")
SPAWN_LINE = ("(The spawn message: the standing text, any packets, the roles and the agent's task. "
              "It is left out here; the agent's task file holds its task.)")
PREVIEW = 100


class Failure(Exception):
    """One error, worded as 'where: problem. Fix: fix'."""


def problem(where: str, what: str, fix: str) -> str:
    return f"{where}: {what}. Fix: {fix}"


# ---------------------------------------------------------------- reading

def read_records(path: Path) -> tuple[list, int]:
    """Every JSON object line of the transcript, and the count of lines skipped."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raise Failure(problem(str(path), "no such file",
                              "pass a session's transcript, ~/.claude/projects/<project folder "
                              "with / replaced by ->/<session id>.jsonl, or a subagent's, "
                              "<session id>/subagents/agent-<agentId>.jsonl in that folder"))
    except IsADirectoryError:
        raise Failure(problem(str(path), "is a directory", "pass the .jsonl file itself"))
    except OSError as exc:
        raise Failure(problem(str(path), f"cannot be read ({exc.strerror})",
                              "check the path and its permissions"))
    records, skipped = [], 0
    for number, line in enumerate(raw.split(b"\n"), 1):
        if not line.strip():
            continue
        try:
            text = line.decode("utf-8-sig" if number == 1 else "utf-8")
            record = json.loads(text)
        except (UnicodeDecodeError, ValueError):
            skipped += 1
            continue
        if not isinstance(record, dict):
            skipped += 1
            continue
        records.append(record)
    return records, skipped


def text_of(content) -> str:
    """The text in a message's content: a string, or the text blocks of a list."""
    if isinstance(content, str):
        return content
    parts = []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif block.get("type") == "image":
                parts.append("(image)")
    return "\n\n".join(p for p in parts if p.strip())


def readable_command(text: str) -> str:
    """Show a slash-command line as the command the user typed."""
    name = COMMAND_RE.search(text)
    if not name:
        return text
    args = ARGS_RE.search(text)
    return (name.group(1) + (" " + args.group(1) if args and args.group(1) else "")).strip()


class Kind:
    """Which transcript a file is, which of its lines are its own, and who speaks.

    A subagent's file: its first user or assistant line carries "isSidechain"
    true and an "agentId", and its own lines carry that agentId. Its user
    messages come from the orchestrator and its model is the agent. Any other
    file is a main chat: its own lines are those whose "isSidechain" is not
    true, its user messages are the user's and its model is the orchestrator.
    """

    def __init__(self, records: list) -> None:
        self.agent_id = None
        for record in records:
            if record.get("type") in ("user", "assistant"):
                agent = record.get("agentId")
                if record.get("isSidechain") is True and isinstance(agent, str) and agent:
                    self.agent_id = agent
                break
        self.subagent = self.agent_id is not None
        self.asker = "orchestrator" if self.subagent else "user"
        self.model = "agent" if self.subagent else "orchestrator"

    def owns(self, record: dict) -> bool:
        if self.subagent:
            return record.get("agentId") == self.agent_id
        return record.get("isSidechain") is not True

    def label(self) -> str:
        return f"a subagent's transcript, agent {self.agent_id}" if self.subagent else "a main chat"


def is_interruption(record: dict, text: str) -> bool:
    """The host's mark that the user stopped a turn: no origin, and the whole text is one of
    INTERRUPTED. A message that only starts with that text is the user's own."""
    return record.get("origin") is None and text.strip() in INTERRUPTED


def is_genuine_user(record: dict, kind: Kind) -> bool:
    if record.get("type") != "user" or not kind.owns(record):
        return False
    message = record.get("message")
    if not isinstance(message, dict):
        return False
    if record.get("isCompactSummary") is True:
        return False
    origin = record.get("origin")
    if kind.subagent and isinstance(origin, dict) and origin.get("kind") == "coordinator":
        # The orchestrator's message to a stopped agent: marked isMeta, but a message it sent.
        return bool(text_of(message.get("content")).strip())
    if record.get("isMeta") is True:
        return False
    content = message.get("content")
    if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result"
                                         for b in content):
        return False
    text = text_of(content)
    if not text.strip() or is_interruption(record, text):
        return False
    if isinstance(origin, dict):
        return origin.get("kind") == "human"
    return not text.lstrip().startswith(HOST_TAGS)


def result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    return text_of(content)


def events_of(records: list, kind: Kind) -> list:
    """The transcript's own lines as a flat list of events, in file order.

    Each event is a tuple: ("user", time, text) for a genuine user message,
    whoever its speaker is, ("say", time, text) for the model's text,
    ("tool", time, name, description), ("result", time, name, text),
    ("notice", time) for an agent's completion notice, ("interrupt", time) where
    the user stopped a turn, or ("compact", time). A message that arrived while
    the model worked, a queued_command attachment, is a ("user", time, text)
    event too: the user's in a main chat, the orchestrator's in a subagent's
    file.
    """
    events = []
    tool_names: dict = {}
    for record in records:
        if not kind.owns(record):
            continue
        rtype = record.get("type")
        when = record.get("timestamp") if isinstance(record.get("timestamp"), str) else ""
        if rtype == "system" and record.get("subtype") == "compact_boundary":
            events.append(("compact", when))
            continue
        attachment = record.get("attachment")
        if rtype == "attachment" and isinstance(attachment, dict):
            if attachment.get("type") == "queued_command":
                origin = attachment.get("origin")
                sender = origin.get("kind") if isinstance(origin, dict) else None
                text = text_of(attachment.get("prompt"))
                if sender == ("coordinator" if kind.subagent else "human") and text.strip():
                    # A message that arrived while the model worked: the user's in a main
                    # chat, the orchestrator's in a subagent's file.
                    events.append(("user", when, text))
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if rtype == "user":
            origin = record.get("origin") if isinstance(record.get("origin"), dict) else {}
            if is_genuine_user(record, kind):
                events.append(("user", when, readable_command(text_of(content))))
            elif is_interruption(record, text_of(content)):
                events.append(("interrupt", when))
            elif origin.get("kind") == "task-notification" or (
                    isinstance(content, str) and content.lstrip().startswith("<task-notification>")):
                events.append(("notice", when))
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        name = tool_names.get(block.get("tool_use_id"), "a tool")
                        events.append(("result", when, name, result_text(block)))
        elif rtype == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text" and isinstance(block.get("text"), str) and block["text"].strip():
                    events.append(("say", when, block["text"]))
                elif btype in ("tool_use", "server_tool_use"):
                    name = block.get("name") if isinstance(block.get("name"), str) else "a tool"
                    tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
                    desc = tool_input.get("description")
                    tool_names[block.get("id")] = name
                    events.append(("tool", when, name, desc if isinstance(desc, str) else ""))
                elif btype and btype.endswith("_tool_result"):
                    name = tool_names.get(block.get("tool_use_id"), "a tool")
                    events.append(("result", when, name, result_text(block)))
    return events


def turns_of(events: list, kind: Kind) -> tuple:
    """Group events into turns, and return them with the compaction points
    that come before the first turn.

    Each turn is {number, time, who, start, events}, where start is the event
    that opens it: a genuine user message, or for a leading turn of the
    model's own its first text or tool call. A compaction point that comes
    before the first turn's start, whatever comes between, is returned apart,
    so it shows before turn 1. One inside a turn's events sits where it falls
    in the file.
    """
    turns: list = []
    lead: list = []
    for event in events:
        if event[0] == "user":
            turns.append({"time": event[1], "who": kind.asker, "start": event, "events": [event]})
        elif turns:
            turns[-1]["events"].append(event)
        else:
            lead.append(event)
    start = next((i for i, e in enumerate(lead) if e[0] in ("say", "tool")), len(lead))
    early = [e for e in lead[:start] if e[0] == "compact"]
    if start < len(lead):
        rest = [e for e in lead[:start] if e[0] != "compact"] + lead[start:]
        turns.insert(0, {"time": lead[start][1], "who": kind.model, "start": lead[start],
                         "events": rest})
    if kind.subagent:
        # The first genuine user message of a subagent's file is its spawn message.
        for turn in turns:
            if turn["who"] == kind.asker:
                turn["spawn"] = True
                break
    for number, turn in enumerate(turns, 1):
        turn["number"] = number
    return turns, early


# ---------------------------------------------------------------- output

def one_line(text: str, width: int = PREVIEW) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= width else flat[:width - 3].rstrip() + "..."


def short_time(stamp: str) -> str:
    """2026-10-13T18:31:05.123Z as 2026-10-13T18:31:05Z; unknown as a dash."""
    if not stamp:
        return "-"
    match = re.match(r"([0-9-]{10}T[0-9:]{8})", stamp)
    return (match.group(1) + "Z") if match and stamp.endswith(("Z", "z")) else (
        match.group(1) if match else stamp)


def preview(turn: dict) -> str:
    if turn.get("spawn"):
        return "(the spawn message)"
    for event in turn["events"]:
        if event is turn["start"] and event[0] == "user":
            return one_line(event[2])
        if event[0] == "say":
            return one_line(event[2])
    return "(tool calls only)"


def cmd_list(path: Path) -> int:
    records, skipped = read_records(path)
    kind = Kind(records)
    turns, early = turns_of(events_of(records, kind), kind)
    points = sum(1 for t in turns for e in t["events"] if e[0] == "compact") + len(early)
    print(f"Turns in {path} ({kind.label()}): {len(turns)}; compaction points: {points}; "
          f"malformed lines skipped: {skipped}")
    count = 0

    def marker(event, leading: bool = False) -> None:
        nonlocal count
        count += 1
        what = ("before turn 1: this file holds no turns from before it" if leading else
                "the chat before this line was replaced by a summary")
        print(f"{'--':>5}  {short_time(event[1]):20}  compaction point {count}, {what}")

    for event in early:
        marker(event, leading=True)
    for turn in turns:
        for event in turn["events"]:
            if event is turn["start"]:
                print(f"{turn['number']:>5}  {short_time(turn['time']):20}  {turn['who']:12}  "
                      f"{preview(turn)}")
            elif event[0] == "compact":
                marker(event)
    if skipped:
        print(f"claude_transcript.py: note: skipped {skipped} malformed lines", file=sys.stderr)
    return 0


def render(turns: list, kind: Kind, with_output: bool) -> str:
    asker, model = kind.asker.capitalize() + ":\n", kind.model.capitalize() + ":\n"
    out = []
    for turn in turns:
        out.append(f"## Turn {turn['number']}, {short_time(turn['time'])}")
        out[-1] = ("\n" if len(out) > 1 else "") + out[-1]
        speaker = None
        for event in turn["events"]:
            what = event[0]
            if what == "compact":
                out.append("(Compaction point: the live chat was replaced by a summary here.)")
                speaker = None
            elif what == "user":
                text = SPAWN_LINE if turn.get("spawn") and event is turn["start"] else event[2].strip()
                out.append(asker + text)
                speaker = "asker"
            elif what == "say":
                text = event[2].strip()
                out.append(text if speaker == "model" else model + text)
                speaker = "model"
            elif what == "tool":
                line = f"(used {event[2]}: {one_line(event[3], 200)})" if event[3] else f"(used {event[2]})"
                out.append(line if speaker == "model" else model + line)
                speaker = "model"
            elif what == "interrupt":
                out.append("(The user interrupted the work here.)")
                speaker = None
            elif what == "notice":
                out.append("(An agent's completion notice arrived here.)")
                speaker = None
            elif what == "result" and with_output:
                out.append(f"(output of {event[2]}:)\n" + event[3].rstrip())
    return "\n\n".join(out).rstrip() + "\n"


def parse_range(text: str, count: int) -> tuple:
    match = RANGE_RE.fullmatch(text or "")
    fix = (f"run --list to see the {count} turns, then pass --turns A-B with 1 <= A <= B <= {count}"
           if count else "this transcript has no turns yet; pass another transcript")
    if not match:
        raise Failure(problem(f"--turns {text}", "is not a range of turns", fix))
    first = int(match.group(1))
    last = int(match.group(2)) if match.group(2) else first
    if not (1 <= first <= last <= count):
        raise Failure(problem(f"--turns {text}", f"is outside the transcript's {count} turns", fix))
    return first, last


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def cmd_turns(path: Path, args) -> int:
    for flag, value in (("--out", args.out), ("--name", args.name), ("--about", args.about)):
        if not value:
            raise Failure(problem(flag, "is missing", "--turns needs --out FILE, --name NAME and "
                                                     "--about TEXT"))
    name = args.name
    if not PACKET_NAME_RE.fullmatch(name) or name in RESERVED_NAMES:
        raise Failure(problem(f"--name {name}", "is not a packet name",
                              "use lowercase letters, digits and hyphens, starting with a letter "
                              "or a digit, other than claude, agents and gemini, such as grounding"))
    about = " ".join(args.about.split())
    out = Path(os.path.abspath(os.path.expanduser(args.out)))
    if out.name != f"{name}.md":
        raise Failure(problem(f"--out {out}", f"is not named {name}.md",
                              f"write packet {name} as packets/{name}.md in the run's folder"))
    real, skill = Path(os.path.realpath(out)), Path(os.path.realpath(SKILL_DIR))
    if skill in real.parents:
        raise Failure(problem(str(out), "is inside the skill folder",
                              "write packets in the run's folder, outside the skill"))
    if args.revision < 1:
        raise Failure(problem(f"--revision {args.revision}", "is below 1",
                              "pass 1 for a new packet, and add 1 at each update"))
    records, skipped = read_records(path)
    kind = Kind(records)
    turns, early = turns_of(events_of(records, kind), kind)
    first, last = parse_range(args.turns, len(turns))
    chosen = turns[first - 1:last]
    span = f"turn {first}" if first == last else f"turns {first}-{last}"
    # The file's name without .jsonl: the session id, or agent-<agentId>.
    source = f"{span} of transcript {path.stem}"
    about = CLOSE_TAG_RE.sub(r"< /\1", about)
    header = (f"# Packet: {name}\nRevision: {args.revision}\nAbout: {about}\n"
              f"Source: {source}\nKept: no\n")
    note = ("Tool output is included." if args.with_tool_output else
            "Tool output is left out; each tool call shows as one line.")
    if early and first == 1:
        note += " This transcript begins at a compaction point and holds no turns from before it."
    body = CLOSE_TAG_RE.sub(r"< /\1", render(chosen, kind, args.with_tool_output))
    text = header + "\n" + note + "\n\n" + body
    try:
        write_atomic(out, text)
    except OSError as exc:
        raise Failure(problem(str(out), f"cannot be written ({exc.strerror})",
                              "pass a path in a folder you can write, such as the run's packets/"))
    print(f"Wrote packet {name}, revision {args.revision}, to {out}: {span}, "
          f"{len(text.encode('utf-8'))} bytes, "
          f"{'with' if args.with_tool_output else 'without'} tool output; "
          f"malformed lines skipped: {skipped}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claude_transcript.py", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Read Claude Code's saved transcripts, a session's or a subagent's, and no "
                    "other format: list a transcript's turns, or write a range of them as a "
                    "context packet.",
        epilog="Exit 0 on success; 1 with one error on stderr naming the fix.")
    parser.add_argument("transcript", metavar="TRANSCRIPT",
                        help="~/.claude/projects/<project folder with / replaced by ->/<session id>.jsonl, "
                             "or <session id>/subagents/agent-<agentId>.jsonl in that folder")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true",
                      help="print one line per turn and one per compaction point")
    mode.add_argument("--turns", metavar="A-B", help="write turns A to B as a packet")
    parser.add_argument("--out", metavar="FILE", help="the packet file, packets/NAME.md")
    parser.add_argument("--name", metavar="NAME", help="the packet's name")
    parser.add_argument("--about", metavar="TEXT",
                        help="one plain sentence: what this context is and why agents get it")
    parser.add_argument("--revision", metavar="N", type=int, default=1,
                        help="the packet's revision (default 1; add 1 at each update)")
    parser.add_argument("--with-tool-output", action="store_true",
                        help="include tool result bodies, which are left out by default")
    return parser


def main(argv: list | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass
    args = build_parser().parse_args(argv)
    path = Path(os.path.abspath(os.path.expanduser(args.transcript)))
    try:
        return cmd_list(path) if args.list else cmd_turns(path, args)
    except Failure as exc:
        sys.stdout.flush()
        print(f"claude_transcript.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
