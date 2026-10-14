#!/usr/bin/env python3
"""Effective settings, message checks, status logs, roster and spawn package for agent-orchestrate.

The skill's one deterministic helper. Every command prints JSON on stdout,
except package, which prints the spawn message as text. A printed object that
is not itself a message carries "schema_version": 1. Errors go to stderr,
one per line, naming the path and the fix, and the exit status is 1. The
script makes no network call and never writes inside the skill folder: status
and roster files live wherever the caller points, normally the session's
temporary working space, and config set writes only the user or project
override files.

    python3 ao.py config [--project DIR] [--explain]
    python3 ao.py config set --layer user|project [--project DIR] [--reset KEY]... [PATCH]
    python3 ao.py check FILE                (FILE may be - for stdin)
    python3 ao.py status append FILE --agent NAME --event EVENT --summary TEXT
    python3 ao.py status read FILE [--threshold TEXT]
    python3 ao.py roster set FILE --row JSON
    python3 ao.py roster show FILE
    python3 ao.py package TASK_FILE [--out FILE] [--packets DIR]
    python3 ao.py packets DIR

Requires Python 3.9 or later. Standard library only. The script finds the
skill folder through its own location, so it runs from any directory.

CONFIG LAYERS
-------------
The shipped files config/defaults.json and config/models.json form the
baseline document; their nulls are values (no cap, host default). On top of
it, as RFC 7396 merge patches and in this order:

    user     ${XDG_CONFIG_HOME:-~/.config}/agent-orchestrate/config.json, models.json
    project  <DIR or the git root of the working directory>/.agent-orchestrate/
             config.json, models.json   (the working directory when not in git)

In an override a null deletes the key. Every override file carries
"schema_version": 1. The merged result is validated against
schemas/config.schema.json and checked for completeness: every key in the
shipped files must still be set. A deleted key whose shipped value is null
reads as null again, because null is that key's unset value; deleting any
other shipped key is an error naming the file that deleted it.

config set takes PATCH as JSON text or as @FILE. It sends each top-level key
to the override file whose shipped counterpart carries it (models.json for
the model settings, config.json for the run settings), and refuses a key the
shipped files do not carry, at any depth. Each part is merged into that
layer's file key by key. A null is stored only for a key whose shipped value
is null, where it overrides the layers below with that value; a null for any
other key is refused. --reset KEY, a dotted key, removes that key from the
layer's file, so the layer below shows through, and drops an object it
leaves empty. The effective config is then built with the new content in
memory and checked exactly as config checks it. Only when every check passes
are the files written, each through a temporary file in the same folder and
os.replace; a failed replace puts back the files already replaced. The
--explain output follows.

CHECKS
------
check routes a message by its `kind` to `$defs/<kind>` in
schemas/protocol.schema.json. The validator implements exactly the keywords
the schemas use and refuses a schema holding any other, so a rule it cannot
enforce fails loudly. On top of the schema it enforces the rules the schema
cannot express: absolute paths, non-empty roles, done_when and options, an
ask's default naming one of its options, milestone present for
before_milestone, at most three `did` items, asks present exactly when a
return is blocked, RFC 3339 UTC timestamps, packet names and each packet
listed once, layers_below 0 on a fork, plain text in every access sentence and
reason, edit only with a scope and spawn only with layers_below, a request
notice's id, need, why and meanwhile, an ask on a request carrying trigger
permission, and the consistency of the shared enums across both schemas. A threshold line's wording is checked against the
task's threshold by `status read --threshold`, the one place that holds both.

check also accepts text whose last fenced json block is the message (an
agent's final reply), and JSON Lines files: each line is checked, and
roster_row lines are first folded per agent as `roster show` folds them.

PACKETS
-------
A context packet is a Markdown file, packets/NAME.md in the run's folder,
opening with a header that package and packets parse:

    # Packet: NAME
    Revision: 1
    About: one plain sentence saying what this context is and why agents get it
    Source: where it came from, in words
    Kept: no

The header ends at the first blank line; the body follows and must not be
empty. NAME follows the rule for a task's packets, claude and agents refused;
Revision is ASCII digits, 1 or more; no closing packet tag appears in any
case. package places each packet the task lists after the standing text, in
the task's order, so agents given the same packets open with the same text.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROTOCOL_SCHEMA = SKILL_DIR / "schemas" / "protocol.schema.json"
CONFIG_SCHEMA = SKILL_DIR / "schemas" / "config.schema.json"
SHIPPED_CONFIG = (SKILL_DIR / "config" / "defaults.json",
                  SKILL_DIR / "config" / "models.json")
STANDING = SKILL_DIR / "assets" / "standing.md"

# File names hosts load as project instructions, compared in lower case. A saved
# spawn message must never take one of them.
LOADED_NAMES = frozenset(["claude.md", "claude.local.md", "agents.md", "agents.override.md"])

OVERRIDE_FILES = ("config.json", "models.json")
USER_FOLDER = "agent-orchestrate"        # inside the user config folder
PROJECT_FOLDER = ".agent-orchestrate"    # inside the project root
SCHEMA_VERSION = 1

# The keywords the validator implements. A schema using any other keyword is
# refused when it loads, so an unimplemented rule never passes silently.
KEYWORDS = frozenset([
    "$schema", "$id", "$defs", "$ref", "$comment", "title", "description",
    "type", "properties", "required", "additionalProperties", "enum",
    "enumDescriptions", "const", "items", "default", "minimum",
])
JSON_TYPES = ("object", "array", "string", "integer", "number", "boolean", "null")
TYPE_WORDS = {"object": "an object", "array": "an array", "string": "a string",
              "integer": "an integer", "number": "a number",
              "boolean": "true or false", "null": "null"}

# Enums defined in both schemas, which must stay identical, and the subset
# whose enumDescriptions must match as well.
SHARED_ENUMS = ("tier", "integrate", "model_tier", "branch_when", "branch_kind", "lands", "role")
SHARED_DESCRIPTIONS = ("tier", "integrate", "model_tier", "branch_kind", "lands")

# Path fields typed as string-or-null rather than through $defs/absolute_path.
# Fields that use that $ref are checked wherever the ref appears.
NULLABLE_PATHS = {"task": ("workdir", "ao_script", "spawn_file"), "return": ("report",),
                  "roster_row": ("workdir",)}

TIMESTAMP_RE = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})")
WINDOWS_ABSOLUTE_RE = re.compile(r"[A-Za-z]:/")
FENCE_RE = re.compile(r"```json[ \t]*\r?\n(.*?)\r?\n[ \t]*```", re.S)

# Context packets: packets/NAME.md in the run's folder, opening with a header.
PACKET_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
RESERVED_PACKET_NAMES = frozenset(name[:-3] for name in LOADED_NAMES if name.endswith(".md")
                                  and "." not in name[:-3])
PACKET_TITLE_RE = re.compile(r"# Packet: (\S+)[ \t]*")
PACKET_FIELDS = ("Revision", "About", "Source", "Kept")
PACKET_HEADER_EXAMPLE = ("# Packet: NAME / Revision: 1 / About: one plain sentence / "
                         "Source: where it came from, in words / Kept: no, one per line, "
                         "then a blank line and the body")


# ---------------------------------------------------------------- errors

class Failure(Exception):
    """One or more errors, each already worded as 'where: problem. Fix: fix'."""

    def __init__(self, lines: list[str]) -> None:
        super().__init__("\n".join(lines))
        self.lines = list(lines)


def problem(where: str, what: str, fix: str) -> str:
    """One error line: the location, what is wrong, and how to fix it."""
    return f"{where}: {what}. Fix: {fix}"


def located(where: str, pointer: str) -> str:
    """A file or label plus a JSON pointer inside it."""
    return f"{where} at {pointer or '(root)'}"


def note(text: str) -> None:
    """Print an informational line to stderr without failing the command."""
    print(f"ao.py: note: {text}", file=sys.stderr)


# ---------------------------------------------------------------- JSON I/O

class DuplicateKey(ValueError):
    pass


class BadConstant(ValueError):
    pass


def _reject_duplicates(pairs: list) -> dict:
    """object_pairs_hook that refuses an object holding the same key twice."""
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise DuplicateKey(f"duplicate key {key!r}")
        obj[key] = value
    return obj


def _reject_constant(name: str) -> None:
    """parse_constant hook that refuses NaN and Infinity, which JSON lacks."""
    raise BadConstant(f"{name} is not a JSON value")


def parse_json(text: str, where: str):
    """Parse one JSON document, refusing duplicate keys, NaN and Infinity."""
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicates,
                          parse_constant=_reject_constant)
    except DuplicateKey as exc:
        raise Failure([problem(where, str(exc), "keep one of the two entries and delete the other")])
    except BadConstant as exc:
        raise Failure([problem(where, str(exc), "write a number, or null")])
    except json.JSONDecodeError as exc:
        raise Failure([problem(f"{where}, line {exc.lineno} column {exc.colno}",
                               f"not valid JSON ({exc.msg})",
                               "correct the JSON syntax at that position")])


def read_text(path: Path, missing_fix: str) -> str:
    """Read a UTF-8 text file (a byte-order mark is tolerated)."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise Failure([problem(str(path), "no such file", missing_fix)])
    except IsADirectoryError:
        raise Failure([problem(str(path), "is a directory, not a file", "pass the path of a file")])
    except UnicodeDecodeError:
        raise Failure([problem(str(path), "is not UTF-8 text", "save the file as UTF-8")])
    except OSError as exc:
        raise Failure([problem(str(path), f"cannot be read ({exc.strerror})",
                               "check the path and its permissions")])


def load_json_file(path: Path, missing_fix: str):
    return parse_json(read_text(path, missing_fix), str(path))


def print_json(value) -> None:
    sys.stdout.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def absolute(raw: str) -> Path:
    """The absolute, normalised form of a path given on the command line."""
    return Path(os.path.abspath(os.path.expanduser(raw)))


def writable_path(raw: str) -> Path:
    """A file path the script may append to: never inside the skill folder."""
    path = absolute(raw)
    real = Path(os.path.realpath(path))
    skill = Path(os.path.realpath(SKILL_DIR))
    if real == skill or skill in real.parents:
        raise Failure([problem(str(path), "is inside the skill folder, which ao.py never writes to",
                               "keep status and roster files in the session's temporary working "
                               "space, outside the skill, and pass that path")])
    if path.is_dir():
        raise Failure([problem(str(path), "is a directory",
                               "pass a file path inside it, such as run/roster.jsonl")])
    return path


def append_line(path: Path, record: dict) -> None:
    """Append one JSON Lines record, first ending any unterminated last line."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lead = ""
        if path.exists() and path.stat().st_size > 0:
            with open(path, "rb") as fh:
                fh.seek(-1, os.SEEK_END)
                if fh.read(1) != b"\n":
                    lead = "\n"
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(lead + json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise Failure([problem(str(path), f"cannot be written ({exc.strerror})",
                               "pass a path in a folder you can write, such as the "
                               "session's temporary working space")])


def load_jsonl(path: Path) -> tuple[list, list[str]]:
    """Every non-blank line of a JSON Lines file as (line number, value)."""
    records, errors = [], []
    text = read_text(path, "check the path")
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        try:
            records.append((number, parse_json(raw, f"{path}:{number}")))
        except Failure as exc:
            errors.extend(exc.lines)
    return records, errors


# ---------------------------------------------------------------- JSON values

def json_type(value) -> str:
    """The JSON type name of a parsed value. A bool is never an integer here."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def is_type(value, name: str) -> bool:
    """True when `value` has JSON type `name`; 1.0 counts as an integer."""
    kind = json_type(value)
    if name == "integer":
        return kind == "integer" or (kind == "number" and float(value).is_integer())
    if name == "number":
        return kind in ("integer", "number")
    return kind == name


def same_json(a, b) -> bool:
    """JSON equality: true and 1 differ, 1 and 1.0 match."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if json_type(a) in ("integer", "number") and json_type(b) in ("integer", "number"):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_json(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same_json(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def pointer_join(pointer: str, token) -> str:
    """Extend an RFC 6901 JSON pointer by one key or index."""
    return pointer + "/" + str(token).replace("~", "~0").replace("/", "~1")


def pointer_of(path: tuple) -> str:
    out = ""
    for key in path:
        out = pointer_join(out, key)
    return out


def path_of(pointer: str) -> tuple:
    if not pointer:
        return ()
    return tuple(t.replace("~1", "/").replace("~0", "~") for t in pointer.split("/")[1:])


def first_sentence(text: str) -> str:
    return text.split(". ")[0].rstrip(".") if text else ""


def is_absolute(text: str) -> bool:
    """True for /posix/paths and C:/windows/paths written with forward slashes."""
    return text.startswith("/") or bool(WINDOWS_ABSOLUTE_RE.match(text))


def parse_timestamp(text: str):
    """Parse an RFC 3339 date-time. Returns an aware datetime, or None."""
    match = TIMESTAMP_RE.fullmatch(text)
    if not match:
        return None
    year, month, day, hour, minute, second = (int(g) for g in match.groups()[:6])
    zone = match.group(7)
    try:
        if zone in ("Z", "z"):
            offset = timedelta(0)
        else:
            sign = -1 if zone[0] == "-" else 1
            offset = sign * timedelta(hours=int(zone[1:3]), minutes=int(zone[4:6]))
        # A leap second (60) is valid RFC 3339; datetime stops at 59.
        return datetime(year, month, day, hour, minute, 59 if second == 60 else second,
                        tzinfo=timezone(offset))
    except ValueError:
        return None


def now_stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- schemas

def audit_schema(node, root: dict, path: Path, pointer: str, errors: list[str]) -> None:
    """Refuse keywords the validator does not implement, and malformed ones."""
    where = located(str(path), pointer)
    if not isinstance(node, dict):
        errors.append(problem(where, "a schema must be a JSON object",
                              "replace it with an object such as {\"type\": \"string\"}"))
        return
    for key in node:
        if key not in KEYWORDS:
            errors.append(problem(where, f"keyword {key!r} is not one ao.py implements",
                                  "use only " + ", ".join(sorted(KEYWORDS))
                                  + ", or teach ao.py the keyword first"))
    kind = node.get("type")
    if kind is not None:
        single = isinstance(kind, str) and kind in JSON_TYPES
        pair = (isinstance(kind, list) and len(kind) == 2 and "null" in kind
                and kind[0] != kind[1] and all(k in JSON_TYPES for k in kind))
        if not (single or pair):
            errors.append(problem(where + "/type", f"{json.dumps(kind)} is not a supported type",
                                  "use one JSON type name, or a two-item list of a type and \"null\""))
    ref = node.get("$ref")
    if ref is not None:
        target = ref[len("#/$defs/"):] if isinstance(ref, str) and ref.startswith("#/$defs/") else None
        if target is None or target not in root.get("$defs", {}):
            errors.append(problem(where + "/$ref", f"{json.dumps(ref)} does not resolve",
                                  "point it at an existing local definition, #/$defs/<name>"))
    if "additionalProperties" in node and not isinstance(node["additionalProperties"], bool):
        errors.append(problem(where + "/additionalProperties", "must be true or false",
                              "set it to true; schema-valued additionalProperties is not supported"))
    required = node.get("required")
    if required is not None and not (isinstance(required, list)
                                     and all(isinstance(r, str) for r in required)):
        errors.append(problem(where + "/required", "must be a list of property names",
                              "list the required property names as strings"))
    if "minimum" in node and json_type(node["minimum"]) not in ("integer", "number"):
        errors.append(problem(where + "/minimum", "must be a number",
                              "set it to the smallest value allowed, such as 0 or 1"))
    enum = node.get("enum")
    if enum is not None and not isinstance(enum, list):
        errors.append(problem(where + "/enum", "must be a list", "list the allowed values"))
    descriptions = node.get("enumDescriptions")
    if descriptions is not None:
        count = len(descriptions) if isinstance(descriptions, list) else -1
        if not isinstance(enum, list) or count != len(enum):
            errors.append(problem(where + "/enumDescriptions",
                                  f"has {max(count, 0)} entries for "
                                  f"{len(enum) if isinstance(enum, list) else 0} enum values",
                                  "give exactly one description per enum value, in the same order"))
    properties = node.get("properties")
    if properties is not None:
        if not isinstance(properties, dict):
            errors.append(problem(where + "/properties", "must be an object",
                                  "map each property name to its schema"))
        else:
            for name, sub in properties.items():
                audit_schema(sub, root, path, pointer_join(pointer_join(pointer, "properties"), name), errors)
    if "items" in node:
        audit_schema(node["items"], root, path, pointer_join(pointer, "items"), errors)
    definitions = node.get("$defs")
    if definitions is not None:
        if not isinstance(definitions, dict):
            errors.append(problem(where + "/$defs", "must be an object",
                                  "map each definition name to its schema"))
        else:
            for name, sub in definitions.items():
                audit_schema(sub, root, path, pointer_join(pointer_join(pointer, "$defs"), name), errors)


def load_schemas() -> tuple[dict, dict]:
    """Load and audit both schemas, then check the enums they share."""
    restore = "restore the file from the skill's repository; ao.py reads it from the schemas folder"
    errors: list[str] = []
    protocol = load_json_file(PROTOCOL_SCHEMA, restore)
    config = load_json_file(CONFIG_SCHEMA, restore)
    for path, doc in ((PROTOCOL_SCHEMA, protocol), (CONFIG_SCHEMA, config)):
        audit_schema(doc, doc, path, "", errors)
    if errors:
        raise Failure(errors)

    pdefs, cdefs = protocol.get("$defs", {}), config.get("$defs", {})
    for name in SHARED_ENUMS:
        mine, theirs = cdefs.get(name, {}).get("enum"), pdefs.get(name, {}).get("enum")
        if mine != theirs:
            errors.append(problem(located(str(CONFIG_SCHEMA), f"/$defs/{name}/enum"),
                                  f"{json.dumps(mine)} differs from {json.dumps(theirs)} in "
                                  f"{PROTOCOL_SCHEMA.name} /$defs/{name}/enum",
                                  "make the two lists identical, value for value and in order"))
    for name in SHARED_DESCRIPTIONS:
        mine = cdefs.get(name, {}).get("enumDescriptions")
        theirs = pdefs.get(name, {}).get("enumDescriptions")
        if mine != theirs:
            errors.append(problem(located(str(CONFIG_SCHEMA), f"/$defs/{name}/enumDescriptions"),
                                  f"differs from {PROTOCOL_SCHEMA.name} /$defs/{name}/enumDescriptions",
                                  "copy the descriptions across so both schemas say the same thing"))
    kinds = pdefs.get("kind", {}).get("enum") or []
    for kind in kinds:
        if kind not in pdefs:
            errors.append(problem(located(str(PROTOCOL_SCHEMA), "/$defs/kind/enum"),
                                  f"kind {kind!r} has no definition at /$defs/{kind}",
                                  "add the definition, or remove the kind from the enum"))
    if errors:
        raise Failure(errors)
    return protocol, config


# ---------------------------------------------------------------- validator

class Validator:
    """Validate a value against the audited keyword subset of a schema.

    Each finding is (JSON pointer, what is wrong, how to fix it). A rule
    registered under a definition name runs on every value that definition
    validates, wherever its $ref appears, so nested messages get their rules.
    """

    def __init__(self, root: dict, rules: dict | None = None) -> None:
        self.defs = root.get("$defs", {})
        self.rules = rules or {}

    def validate(self, value, schema: dict, pointer: str = "") -> list[tuple]:
        found: list[tuple] = []
        self._walk(value, schema, pointer, found)
        return found

    def _walk(self, value, schema: dict, pointer: str, found: list) -> None:
        ref = schema.get("$ref")
        if ref is not None:
            # Keywords beside a $ref are annotations here (only description).
            name = ref[len("#/$defs/"):]
            self._walk(value, self.defs[name], pointer, found)
            rule = self.rules.get(name)
            if rule is not None:
                rule(value, pointer, found)
            return

        kind = schema.get("type")
        if kind is not None:
            allowed = [kind] if isinstance(kind, str) else list(kind)
            if not any(is_type(value, t) for t in allowed):
                fix = "write " + " or ".join(TYPE_WORDS[t] for t in allowed)
                if "enum" in schema:
                    fix += ": one of " + ", ".join(str(v) for v in schema["enum"])
                elif schema.get("description"):
                    fix += f" ({first_sentence(schema['description'])})"
                found.append((pointer, f"expected {' or '.join(allowed)}, got {json_type(value)}", fix))
                return

        if "const" in schema and not same_json(value, schema["const"]):
            want = json.dumps(schema["const"])
            found.append((pointer, f"must be {want}, got {json.dumps(value)}", f"set it to {want}"))
        if "enum" in schema and not any(same_json(value, v) for v in schema["enum"]):
            found.append((pointer, f"{json.dumps(value)} is not an allowed value",
                          "use one of " + ", ".join(str(v) for v in schema["enum"])))
        if ("minimum" in schema and json_type(value) in ("integer", "number")
                and value < schema["minimum"]):
            found.append((pointer, f"{json.dumps(value)} is below the minimum of {schema['minimum']}",
                          f"use {schema['minimum']} or more"))

        if isinstance(value, dict):
            properties = schema.get("properties", {})
            for name in schema.get("required", []):
                if name not in value:
                    hint = first_sentence(properties.get(name, {}).get("description", ""))
                    found.append((pointer, f"missing required field {name!r}",
                                  f"add {json.dumps(name)}" + (f" ({hint})" if hint else "")))
            for name, sub in properties.items():
                if name in value:
                    self._walk(value[name], sub, pointer_join(pointer, name), found)
            if schema.get("additionalProperties") is False:
                for name in value:
                    if name not in properties:
                        found.append((pointer_join(pointer, name), "is not an allowed field",
                                      "remove it or check its spelling"))

        if isinstance(value, list) and "items" in schema:
            for index, item in enumerate(value):
                self._walk(item, schema["items"], pointer_join(pointer, index), found)


# ---------------------------------------------------------------- code rules
# The rules the schemas leave to code. Each takes (value, pointer, found) and
# runs after the schema walk of the definition it is registered under.

def rule_absolute_path(value, pointer: str, found: list) -> None:
    if isinstance(value, str) and not is_absolute(value):
        found.append((pointer, f"{json.dumps(value)} is not an absolute path",
                      "write the full path from the filesystem root with forward slashes, "
                      "such as /home/me/run/status.jsonl or C:/run/status.jsonl"))


def rule_timestamp(value, pointer: str, found: list) -> None:
    if not isinstance(value, str):
        return
    parsed = parse_timestamp(value)
    example = ("write it like 2026-10-02T12:54:00+00:00, as "
               "datetime.now(timezone.utc).isoformat(timespec=\"seconds\") prints it")
    if parsed is None:
        found.append((pointer, f"{json.dumps(value)} is not an RFC 3339 date-time", example))
    elif parsed.utcoffset() != timedelta(0):
        found.append((pointer, f"{json.dumps(value)} is not in UTC", example))


def check_nullable_paths(kind: str, value: dict, pointer: str, found: list) -> None:
    for name in NULLABLE_PATHS.get(kind, ()):
        if name in value:
            rule_absolute_path(value[name], pointer_join(pointer, name), found)


def rule_packet_name(value, pointer: str, found: list) -> None:
    if not isinstance(value, str):
        return
    if not PACKET_NAME_RE.fullmatch(value):
        found.append((pointer, f"{json.dumps(value)} is not a packet name",
                      "use lowercase letters, digits and hyphens, starting with a letter or a "
                      "digit, such as grounding or api-contract"))
    elif value in RESERVED_PACKET_NAMES:
        found.append((pointer, f"{json.dumps(value)} would make {value}.md, a name hosts load as "
                               "project instructions",
                      "choose another name, such as " + value + "-notes"))


def blank(value) -> bool:
    """True for a string holding no text; other types are left to the schema."""
    return isinstance(value, str) and not value.strip()


def needs_text(value: dict, pointer: str, found: list, fields: tuple, fix: str) -> None:
    """Each named field, when present as a string, holds some text."""
    for name in fields:
        if blank(value.get(name)):
            found.append((pointer_join(pointer, name), "is empty", fix))


def rule_path_reason(value, pointer: str, found: list) -> None:
    if isinstance(value, dict):
        needs_text(value, pointer, found, ("why",),
                   "say in a plain phrase why the agent needs this path")


def rule_access(value, pointer: str, found: list) -> None:
    if not isinstance(value, dict):
        return
    needs_text(value, pointer, found, ("summary", "held_by"),
               "write one plain sentence a person can read")
    tools = value.get("tools")
    if isinstance(tools, list):
        if not tools:
            found.append((pointer_join(pointer, "tools"), "must not be empty",
                          "list what the agent may use, from read, edit, shell, web and spawn"))
        seen = set()
        for index, tool in enumerate(tools):
            if not isinstance(tool, str):
                continue  # the schema walk reports a tool that is not a string
            if tool in seen:
                found.append((pointer_join(pointer_join(pointer, "tools"), index),
                              f"names {json.dumps(tool)} twice", "list each capability once"))
            seen.add(tool)
    network = value.get("network")
    if isinstance(network, dict):
        needs_text(network, pointer_join(pointer, "network"), found, ("why",),
                   "say in a plain phrase why the agent may or may not reach the network")


def rule_notice(value, pointer: str, found: list) -> None:
    if not isinstance(value, dict) or value.get("reason") != "request":
        return
    fixes = {"id": "add \"id\", the agent name plus a counter unique in the run, such as export-api-2",
             "need": "add \"need\": one plain sentence saying what more access the agent needs",
             "why": "add \"why\": why the slice needs it",
             "meanwhile": "add \"meanwhile\": what the agent keeps doing while it waits"}
    for name, fix in fixes.items():
        if name not in value:
            found.append((pointer, f"a request is missing {name!r}", fix))
        elif not isinstance(value[name], str) or not value[name].strip():
            found.append((pointer_join(pointer, name), "must hold some text", fix))
    if value.get("continuing") is False:
        found.append((pointer_join(pointer, "continuing"),
                      "is false, but a request never stops the agent",
                      "set continuing to true; with nothing left to do, park with an ask whose "
                      "trigger is permission and whose request_id names this request"))


def unique_packets(value: dict, pointer: str, found: list, by_name: bool) -> None:
    """A packet appears once in a list, by name (packet_ref objects) or as itself."""
    packets = value.get("packets")
    if not isinstance(packets, list):
        return
    seen = set()
    for index, item in enumerate(packets):
        name = item.get("name") if by_name and isinstance(item, dict) else item
        if not isinstance(name, str):
            continue
        if name in seen:
            found.append((pointer_join(pointer_join(pointer, "packets"), index),
                          f"names packet {json.dumps(name)} twice",
                          "list each packet once"))
        seen.add(name)


def rule_task(value, pointer: str, found: list) -> None:
    if not isinstance(value, dict):
        return
    if isinstance(value.get("roles"), list) and not value["roles"]:
        found.append((pointer_join(pointer, "roles"), "must not be empty",
                      "list at least one role, such as [\"builder\"]"))
    if isinstance(value.get("done_when"), list) and not value["done_when"]:
        found.append((pointer_join(pointer, "done_when"), "must not be empty",
                      "add at least one {\"check\": ..., \"expect\": ...} that proves the work"))
    unique_packets(value, pointer, found, by_name=False)
    layers = value.get("layers_below")
    above_zero = is_type(layers, "integer") and layers > 0
    if value.get("fork") is True and above_zero:
        found.append((pointer_join(pointer, "layers_below"),
                      f"is {layers} on a fork, which spawns no agents of its own",
                      "set layers_below to 0, or set fork to false"))
    access = value.get("access")
    tools = access.get("tools") if isinstance(access, dict) else None
    if isinstance(tools, list):
        where = pointer_join(pointer_join(pointer, "access"), "tools")
        if "edit" in tools and isinstance(value.get("scope"), list) and not value["scope"]:
            found.append((where, "lists edit while scope is empty",
                          "give the task the paths it may change in scope, or take edit out"))
        if "spawn" in tools and not above_zero:
            found.append((where, "lists spawn while layers_below is 0 or absent",
                          "set layers_below to the smaller of agents.max_layers and the host's "
                          "nesting cap, minus 1, or take spawn out"))
    check_nullable_paths("task", value, pointer, found)


def rule_ask(value, pointer: str, found: list) -> None:
    if not isinstance(value, dict):
        return
    options = value.get("options")
    if isinstance(options, list):
        if not options:
            found.append((pointer_join(pointer, "options"), "must not be empty",
                          "offer at least one choice, such as {\"id\": \"A\", \"label\": \"...\"}"))
        ids = [o.get("id") for o in options if isinstance(o, dict)]
        default = value.get("default")
        if options and isinstance(default, str) and default not in ids:
            found.append((pointer_join(pointer, "default"),
                          f"{json.dumps(default)} is not the id of any option",
                          "set it to one of the option ids: "
                          + ", ".join(str(i) for i in ids)))
    if "request_id" in value and value.get("trigger") != "permission":
        found.append((pointer_join(pointer, "trigger"),
                      "must be permission on an ask that parks on a request",
                      "set trigger to permission, or remove request_id"))
    milestone = value.get("milestone")
    if value.get("need_by") == "before_milestone" and not (
            isinstance(milestone, str) and milestone.strip()):
        found.append((pointer_join(pointer, "milestone"),
                      "is required when need_by is before_milestone",
                      "add \"milestone\" worded as in the status file, or set need_by to now"))


def rule_return(value, pointer: str, found: list) -> None:
    if not isinstance(value, dict):
        return
    did = value.get("did")
    if isinstance(did, list) and len(did) > 3:
        found.append((pointer_join(pointer, "did"), f"has {len(did)} items, more than 3",
                      "merge them into three one-line items or fewer"))
    status = value.get("status")
    asks = value.get("asks")
    has_asks = isinstance(asks, list) and len(asks) > 0
    if status == "blocked" and not has_asks:
        found.append((pointer_join(pointer, "asks"), "status is blocked but asks is missing or empty",
                      "add the open question as an ask, or set status to partial"))
    if status in ("done", "partial") and has_asks:
        found.append((pointer_join(pointer, "asks"), f"carries asks while status is {status}",
                      "set status to blocked, or remove the asks"))
    check_nullable_paths("return", value, pointer, found)


def rule_answer(value, pointer: str, found: list) -> None:
    if isinstance(value, dict):
        unique_packets(value, pointer, found, by_name=True)


def rule_roster_row(value, pointer: str, found: list) -> None:
    if isinstance(value, dict):
        unique_packets(value, pointer, found, by_name=True)
        check_nullable_paths("roster_row", value, pointer, found)


RULES = {
    "absolute_path": rule_absolute_path,
    "timestamp": rule_timestamp,
    "packet_name": rule_packet_name,
    "path_reason": rule_path_reason,
    "access": rule_access,
    "task": rule_task,
    "ask": rule_ask,
    "answer": rule_answer,
    "notice": rule_notice,
    "return": rule_return,
    "roster_row": rule_roster_row,
}


def check_message(protocol: dict, message, where: str, expect: str | None = None) -> list[str]:
    """Error lines for one message: the root schema, then $defs/<kind>, then the rules."""
    if not isinstance(message, dict):
        return [problem(located(where, ""), f"expected a JSON object, got {json_type(message)}",
                        "send one JSON object holding schema_version and kind")]
    validator = Validator(protocol, RULES)
    found = validator.validate(message, protocol, "")
    kind = message.get("kind")
    kinds = protocol["$defs"]["kind"]["enum"]
    if expect is not None and kind != expect:
        found.append(("/kind", f"expected kind {json.dumps(expect)} here, got {json.dumps(kind)}",
                      f"pass a {expect} message, with \"kind\": \"{expect}\""))
    elif isinstance(kind, str) and kind in kinds:
        found += validator.validate(message, {"$ref": f"#/$defs/{kind}"}, "")
    seen, lines = set(), []
    for pointer, what, fix in found:
        if (pointer, what) not in seen:
            seen.add((pointer, what))
            lines.append(problem(located(where, pointer), what, fix))
    return lines


# ---------------------------------------------------------------- merge patch

def merge_patch(target, patch):
    """RFC 7396: apply `patch` to `target`; a null in the patch deletes the key."""
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)
    result = copy.deepcopy(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result


def overlay(base: dict, extra: dict) -> dict:
    """Deep-merge `extra` into `base`, keeping nulls as values (shipped files)."""
    out = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = overlay(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def leaves(doc: dict, prefix: tuple = ()):
    """Yield (path, value) for every leaf; an empty object counts as a leaf."""
    for key, value in doc.items():
        path = prefix + (key,)
        if isinstance(value, dict) and value:
            yield from leaves(value, path)
        else:
            yield path, value


def has_path(doc, path: tuple) -> bool:
    for key in path:
        if not isinstance(doc, dict) or key not in doc:
            return False
        doc = doc[key]
    return True


def restore_null(doc: dict, path: tuple) -> bool:
    """Set `path` to null, creating missing parents. False if a parent is not an object."""
    node = doc
    for key in path[:-1]:
        if key not in node:
            node[key] = {}
        elif not isinstance(node[key], dict):
            return False
        node = node[key]
    node[path[-1]] = None
    return True


def fold_rows(records: list) -> tuple[dict, list[str]]:
    """Fold roster lines per agent as merge patches, in file order."""
    rows: dict = {}
    errors: list[str] = []
    for where, record in records:
        agent = record.get("agent") if isinstance(record, dict) else None
        if not isinstance(agent, str) or not agent:
            errors.append(problem(located(where, "/agent"), "a roster line must name its agent",
                                  "add \"agent\" with the agent's short name, or delete the line"))
            continue
        rows[agent] = merge_patch(rows.get(agent, {}), record)
    return rows, errors


# ---------------------------------------------------------------- config

class Layer:
    """One config file: its layer name, path and content (without $schema)."""

    def __init__(self, name: str, path: Path, doc: dict, is_patch: bool) -> None:
        self.name, self.path, self.doc, self.is_patch = name, path, doc, is_patch


def source_of(path: tuple, layers: list[Layer]) -> tuple[Layer | None, str]:
    """The last layer that set, deleted or replaced the key at `path`."""
    for layer in reversed(layers):
        node = layer.doc
        for depth, key in enumerate(path):
            if not isinstance(node, dict) or key not in node:
                break
            node = node[key]
            if layer.is_patch and node is None:
                return layer, "deleted"
            if layer.is_patch and depth < len(path) - 1 and not isinstance(node, dict):
                return layer, "replaced"
        else:
            return layer, "set"
    return None, ""


def project_root(option: str | None) -> Path:
    """--project DIR, else the nearest folder above the working directory holding .git."""
    if option:
        root = absolute(option)
        if not root.is_dir():
            raise Failure([problem(str(root), "--project is not a directory",
                                   f"pass the folder that holds {PROJECT_FOLDER}/, "
                                   "usually the repository root")])
        return root
    cwd = Path.cwd().resolve()
    for folder in (cwd, *cwd.parents):
        if (folder / ".git").exists():
            return folder
    return cwd


def user_folder() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or ""
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / USER_FOLDER


def check_config_file(doc, path: Path, config_schema: dict, shipped: bool) -> list[str]:
    """Each file is an object with schema_version 1; shipped files validate in full."""
    if not isinstance(doc, dict):
        return [problem(located(str(path), ""), f"expected a JSON object, got {json_type(doc)}",
                        "wrap the settings in one object with \"schema_version\": 1")]
    errors = []
    if not same_json(doc.get("schema_version"), SCHEMA_VERSION):
        got = (f"got {json.dumps(doc['schema_version'])}" if "schema_version" in doc
               else "it is missing")
        errors.append(problem(located(str(path), "/schema_version"),
                              f"must be {SCHEMA_VERSION}, and {got}",
                              f"set \"schema_version\": {SCHEMA_VERSION} at the top level"))
    if shipped:
        for pointer, what, fix in Validator(config_schema).validate(doc, config_schema, ""):
            errors.append(problem(located(str(path), pointer), what, fix))
    return errors


SHIPPED_FIX = "restore it from the skill's repository; the shipped config files are part of the skill"


def layer_folder(name: str, root: Path) -> Path:
    """The folder holding one override layer's config.json and models.json."""
    return user_folder() if name == "user" else root / PROJECT_FOLDER


def resolve_config(root: Path, config_schema: dict, replacements: dict | None = None) -> tuple:
    """Merge and check every layer; return (effective, layers, files, restored).

    `replacements` maps an override file's path to the content to use in place
    of the file on disk, so config set checks new content exactly as config
    checks the files.
    """
    replacements = replacements or {}
    layers: list[Layer] = []
    files: list[dict] = []
    errors: list[str] = []

    # Baseline: the shipped files combined as documents, nulls kept as values.
    base: dict = {}
    for path in SHIPPED_CONFIG:
        doc = load_json_file(path, SHIPPED_FIX)
        errors += check_config_file(doc, path, config_schema, shipped=True)
        if isinstance(doc, dict):
            doc = {k: v for k, v in doc.items() if k != "$schema"}
            base = overlay(base, doc)
            layers.append(Layer("skill", path, doc, is_patch=False))
        files.append({"layer": "skill", "file": str(path), "found": True})

    # Overrides: RFC 7396 merge patches, user then project.
    effective = copy.deepcopy(base)
    for name in ("user", "project"):
        folder = layer_folder(name, root)
        for filename in OVERRIDE_FILES:
            path = folder / filename
            found = path in replacements or path.is_file()
            files.append({"layer": name, "file": str(path), "found": found})
            if not found:
                continue
            if path in replacements:
                doc = replacements[path]
            else:
                doc = load_json_file(path, "check the path")
            problems = check_config_file(doc, path, config_schema, shipped=False)
            errors += problems
            if isinstance(doc, dict):
                doc = {k: v for k, v in doc.items() if k != "$schema"}
                effective = merge_patch(effective, doc)
                layers.append(Layer(name, path, doc, is_patch=True))
    if errors:
        raise Failure(errors)

    # Completeness: every shipped key stays set. A deleted key whose shipped
    # value is null reads as null, its unset value.
    restored = set()
    for path, value in leaves(base):
        if has_path(effective, path):
            continue
        if value is None and restore_null(effective, path):
            restored.add(path)
            continue
        layer, how = source_of(path, layers)
        cause = f"{layer.path} {how} it" if layer is not None and layer.is_patch else "an override removed it"
        errors.append(problem(f"effective config at {pointer_of(path)}",
                              f"is missing, so the config is incomplete ({cause})",
                              "remove that null or replacement from the override, or give the key "
                              "a value; every key in the shipped files must stay set"))

    for pointer, what, fix in Validator(config_schema).validate(effective, config_schema, ""):
        layer, _ = source_of(path_of(pointer), layers)
        origin = f" (from {layer.path})" if layer is not None else ""
        errors.append(problem(f"effective config at {pointer or '(root)'}{origin}", what, fix))
    if errors:
        raise Failure(errors)
    return effective, layers, files, restored


def explain_config(root: Path, resolved: tuple) -> dict:
    """The --explain document: the files looked for and every leaf with its layer."""
    effective, layers, files, restored = resolved
    rows = []
    for path, value in leaves(effective):
        layer, _ = source_of(path, layers)
        row = {"key": ".".join(path), "value": value,
               "layer": layer.name if layer else "", "file": str(layer.path) if layer else ""}
        if path in restored:
            row["note"] = "deleted by a null in this file; reads as null, its unset value"
        rows.append(row)
    return {"schema_version": SCHEMA_VERSION, "project_root": str(root), "files": files,
            "leaves": rows}


def cmd_config(args) -> int:
    if getattr(args, "action", None) == "set":
        return cmd_config_set(args)
    _, config_schema = load_schemas()
    root = project_root(args.project)
    resolved = resolve_config(root, config_schema)
    print_json(explain_config(root, resolved) if args.explain else resolved[0])
    return 0


def config_routes() -> tuple[dict, dict]:
    """Each settable top-level key and the override file it goes to, and the settings.

    A key goes to the file whose shipped counterpart carries it, so the
    routes follow the shipped files as keys are added. The settings are the
    shipped files combined, nulls kept as values, without schema_version and
    $schema: the keys config set accepts, at every depth.
    """
    routes: dict = {}
    settings: dict = {}
    for shipped, filename in zip(SHIPPED_CONFIG, OVERRIDE_FILES):
        doc = load_json_file(shipped, SHIPPED_FIX)
        if isinstance(doc, dict):
            doc = {k: v for k, v in doc.items() if k not in ("schema_version", "$schema")}
            for key in doc:
                routes[key] = filename
            settings = overlay(settings, doc)
    return routes, settings


def allowed_beside(shipped: dict) -> str:
    return "use one of " + ", ".join(sorted(shipped)) + ", or check its spelling"


def check_patch_keys(patch: dict, shipped: dict, path: tuple, where: str, errors: list) -> None:
    """Refuse a key the shipped files lack, at any depth, and a null they do not ship.

    Only a key whose shipped value is null may be set to null: config set
    stores that null, which overrides the layers below. Any other null is a
    removal, which --reset makes.
    """
    for key, value in patch.items():
        sub = path + (key,)
        if key not in shipped:
            errors.append(problem(located(where, pointer_of(sub)), "is not a setting",
                                  allowed_beside(shipped)))
        elif value is None and shipped[key] is not None:
            errors.append(problem(located(where, pointer_of(sub)),
                                  "is null, which config set stores only for a setting whose "
                                  "shipped value is null",
                                  f"use --reset {'.'.join(sub)} to remove it from this layer's "
                                  "file, so the layer below shows through"))
        elif isinstance(value, dict) and isinstance(shipped[key], dict):
            check_patch_keys(value, shipped[key], sub, where, errors)


def reset_path(key: str, settings: dict) -> tuple:
    """The path of a --reset KEY, a dotted key the shipped files carry."""
    where = f"--reset {key}"
    path = tuple(key.split("."))
    node = settings
    for depth, name in enumerate(path):
        if not isinstance(node, dict):
            parent = ".".join(path[:depth])
            raise Failure([problem(located(where, pointer_of(path[:depth + 1])), "is not a setting",
                                   f"{parent} holds no keys; reset {parent} itself")])
        if name not in node:
            raise Failure([problem(located(where, pointer_of(path[:depth + 1])), "is not a setting",
                                   allowed_beside(node))])
        node = node[name]
    return path


def remove_path(doc: dict, path: tuple) -> bool:
    """Delete the key at `path` from `doc`; False when `doc` does not hold it."""
    node = doc
    for key in path[:-1]:
        node = node.get(key) if isinstance(node, dict) else None
    if isinstance(node, dict) and path[-1] in node:
        del node[path[-1]]
        return True
    return False


def prune_emptied(doc: dict, before) -> None:
    """Drop objects a reset emptied by removing their keys."""
    for key in list(doc):
        value = doc[key]
        if isinstance(value, dict):
            old = before.get(key) if isinstance(before, dict) else None
            prune_emptied(value, old)
            if not value and isinstance(old, dict) and old:
                del doc[key]


def put_back(path: Path, mode: int, previous) -> None:
    """Restore a replaced file's previous bytes, or remove a file that was new."""
    if previous is None:
        os.unlink(path)
        return
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(previous)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_files_atomically(docs: list) -> None:
    """Write each (path, doc) as UTF-8 JSON through a temporary file and os.replace.

    Every temporary file is written, and each target's previous bytes or its
    absence kept, before any replace, so a failure while writing leaves every
    target file as it was. When a replace fails, the files already replaced
    are put back, and a file that cannot be put back is named in the error.
    """
    staged: list = []
    replaced: list = []
    current = None
    try:
        mask = os.umask(0)
        os.umask(mask)
        for path, doc in docs:
            current = path
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_file():
                mode, previous = stat.S_IMODE(path.stat().st_mode), path.read_bytes()
            else:
                mode, previous = 0o666 & ~mask, None
            fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
            staged.append((tmp, path, mode, previous))
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp, mode)
        for tmp, path, mode, previous in staged:
            current = path
            os.replace(tmp, path)
            replaced.append((path, mode, previous))
    except OSError as exc:
        for tmp, *_ in staged:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        lines = [problem(str(current), f"cannot be written ({exc.strerror or exc})",
                         "make that folder writable, or point the layer at a folder you can "
                         "write: XDG_CONFIG_HOME for the user layer, --project for the "
                         "project layer")]
        for path, mode, previous in reversed(replaced):
            try:
                put_back(path, mode, previous)
            except OSError as undo:
                lines.append(problem(str(path), "was changed by this save and could not be put "
                                                f"back ({undo.strerror or undo})",
                                     "check its content, then run config set again with the "
                                     "values it should hold"))
        raise Failure(lines)


def cmd_config_set(args) -> int:
    _, config_schema = load_schemas()
    root = project_root(args.project)
    resets = args.reset or []
    if args.patch is None:
        if not resets:
            raise Failure([problem("PATCH", "is missing",
                                   "pass a JSON object such as '{\"agents\": {\"per_branch\": 2}}', "
                                   "or --reset KEY to remove a key from the layer's file")])
        where, patch = "--reset", {}
    elif args.patch.startswith("@"):
        source = absolute(args.patch[1:])
        where = str(source)
        text = read_text(source, "pass @ followed by the path of a file holding the JSON patch")
        patch = parse_json(text, where)
    else:
        where = "PATCH"
        patch = parse_json(args.patch, where)
    if not isinstance(patch, dict):
        raise Failure([problem(where, f"expected a JSON object, got {json_type(patch)}",
                               "pass one object such as '{\"agents\": {\"per_branch\": 2}}'")])

    # Route each top-level key to its file; schema_version and $schema are not routed.
    routes, settings = config_routes()
    parts: dict = {}
    errors: list[str] = []
    for key, value in patch.items():
        if key == "$schema":
            continue
        if key == "schema_version":
            if not same_json(value, SCHEMA_VERSION):
                errors.append(problem(located(where, "/schema_version"),
                                      f"must be {SCHEMA_VERSION}, got {json.dumps(value)}",
                                      "leave schema_version out; config set writes it"))
            continue
        if key in routes:
            parts.setdefault(routes[key], {})[key] = value
    settable = {k: v for k, v in patch.items() if k not in ("$schema", "schema_version")}
    check_patch_keys(settable, settings, (), where, errors)

    # Each reset names a setting, and no key PATCH sets.
    paths: list = []
    for key in resets:
        try:
            path = reset_path(key, settings)
        except Failure as exc:
            errors += exc.lines
            continue
        for leaf, _ in leaves(settable):
            if leaf[:len(path)] == path or path[:len(leaf)] == leaf:
                errors.append(problem(f"--reset {key}", "names a key PATCH also sets",
                                      "pass each key in PATCH or in --reset, not both"))
                break
        paths.append((key, path))
    if errors:
        raise Failure(errors)

    # Each value the patch sets must be valid on its own, so a value a higher
    # layer hides is never written invalid. The nulls left here are stored.
    stripped = overlay({"schema_version": SCHEMA_VERSION}, patch)
    for pointer, what, fix in Validator(config_schema).validate(stripped, config_schema, ""):
        errors.append(problem(located(where, pointer), what, fix))
    if errors:
        raise Failure(errors)

    folder = layer_folder(args.layer, root)
    real, skill = Path(os.path.realpath(folder)), Path(os.path.realpath(SKILL_DIR))
    if real == skill or skill in real.parents:
        raise Failure([problem(str(folder), "is inside the skill folder, which ao.py never writes to",
                               "pass --project the root of the project the run works in")])
    replacements: dict = {}
    for filename in OVERRIDE_FILES:
        path = folder / filename
        part = parts.get(filename)
        removing = [(key, p) for key, p in paths if routes[p[0]] == filename]
        if part is None and not removing:
            continue
        if path.is_file():
            before = load_json_file(path, "check the path")
        else:
            before = {"schema_version": SCHEMA_VERSION}
        if not isinstance(before, dict):
            raise Failure(check_config_file(before, path, config_schema, shipped=False))
        after = copy.deepcopy(before)
        removed = False
        for key, p in removing:
            if remove_path(after, p):
                removed = True
            else:
                note(f"--reset {key}: {path} does not set it, so there is nothing to reset")
        if part is not None:
            after = overlay(after, part)
        prune_emptied(after, before)
        if part is not None or removed:
            replacements[path] = after
    if not replacements:
        note(f"{where}: changes no setting, so nothing was written")

    # The same checks config runs, on the new content held in memory.
    resolve_config(root, config_schema, replacements)
    write_files_atomically(list(replacements.items()))
    print_json(explain_config(root, resolve_config(root, config_schema)))
    return 0


# ---------------------------------------------------------------- check

def cmd_check(args) -> int:
    protocol, _ = load_schemas()
    if args.file == "-":
        where = "stdin"
        try:
            text = sys.stdin.buffer.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            raise Failure([problem(where, "is not UTF-8 text", "send UTF-8 text")])
    else:
        where = str(absolute(args.file))
        text = read_text(absolute(args.file), "check the path of the message file")

    # One JSON document is the usual case.
    try:
        message = parse_json(text, where)
    except Failure as first:
        message, failure = None, first
    else:
        errors = check_message(protocol, message, where)
        if errors:
            raise Failure(errors)
        print_json({"schema_version": SCHEMA_VERSION, "valid": True, "file": where,
                    "kind": message["kind"]})
        return 0

    # An agent's reply: the last fenced json block is the message.
    blocks = FENCE_RE.findall(text)
    if blocks:
        label = f"{where} (last json block)"
        message = parse_json(blocks[-1], label)
        errors = check_message(protocol, message, label)
        if errors:
            raise Failure(errors)
        print_json({"schema_version": SCHEMA_VERSION, "valid": True, "file": where,
                    "kind": message["kind"]})
        return 0

    # A JSON Lines file: status lines one by one, roster rows folded per agent.
    lines = [(n, raw) for n, raw in enumerate(text.splitlines(), 1) if raw.strip()]
    if len(lines) < 2:
        raise failure
    errors, kinds, roster = [], set(), []
    for number, raw in lines:
        label = f"{where}:{number}"
        try:
            record = parse_json(raw, label)
        except Failure:
            raise failure
        kind = record.get("kind") if isinstance(record, dict) else None
        kinds.add(str(kind))
        if kind == "roster_row":
            roster.append((label, record))
        else:
            errors += check_message(protocol, record, label)
    rows, fold_errors = fold_rows(roster)
    errors += fold_errors
    for agent, row in rows.items():
        errors += check_message(protocol, row, f"{where}, folded row for {agent!r}", expect="roster_row")
    if errors:
        raise Failure(errors)
    print_json({"schema_version": SCHEMA_VERSION, "valid": True, "file": where,
                "lines": len(lines), "kinds": sorted(kinds)})
    return 0


# ---------------------------------------------------------------- status

def cmd_status_append(args) -> int:
    protocol, _ = load_schemas()
    path = writable_path(args.file)
    line = {"schema_version": SCHEMA_VERSION, "kind": "status_line", "agent": args.agent,
            "at": now_stamp(), "event": args.event, "summary": args.summary}
    errors = check_message(protocol, line, "new status line", expect="status_line")
    if errors:
        raise Failure(errors)
    append_line(path, line)
    print_json(line)
    return 0


def cmd_status_read(args) -> int:
    protocol, _ = load_schemas()
    path = absolute(args.file)
    numbered, errors = [], []
    if not path.exists():
        note(f"{path}: no status file yet, read as empty; the agent's first status line creates it")
    else:
        records, errors = load_jsonl(path)
        for number, record in records:
            problems = check_message(protocol, record, f"{path}:{number}", expect="status_line")
            if problems:
                errors += problems
            else:
                numbered.append((number, record))
    lines = [record for _, record in numbered]

    if args.threshold is None:
        print_json(lines)
    else:
        # The rule that a threshold line repeats the task's threshold exactly
        # is enforced here, where the line and the threshold meet.
        matched = [r for r in lines if r["event"] == "threshold" and r["summary"] == args.threshold]
        mismatched = []
        for number, record in numbered:
            if record["event"] == "threshold" and record["summary"] != args.threshold:
                mismatched.append(record)
                where = located(f"{path}:{number}", "/summary")
                said = (f"threshold line says {json.dumps(record['summary'])}, not the "
                        f"task's threshold {json.dumps(args.threshold)}")
                # Status files are append-only, so a misworded line stays once a
                # correct one follows it. An exact match settles the threshold, and
                # the misworded line is then reported as a note, not an error.
                if matched:
                    note(f"{where}: {said}; another line matches exactly, so the threshold counts as crossed")
                else:
                    errors.append(problem(where, said,
                                          "append a threshold line worded exactly as the task's threshold"))
        print_json({"schema_version": SCHEMA_VERSION, "threshold": args.threshold,
                    "threshold_crossed": bool(matched),
                    "crossed_at": matched[0]["at"] if matched else None,
                    "mismatched": mismatched, "lines": lines})
    if errors:
        raise Failure(errors)
    return 0


# ---------------------------------------------------------------- roster

def cmd_roster_set(args) -> int:
    protocol, _ = load_schemas()
    patch = parse_json(args.row, "--row")
    if not isinstance(patch, dict):
        raise Failure([problem("--row", f"expected a JSON object, got {json_type(patch)}",
                               "pass one object such as '{\"agent\": \"docs\", \"state\": \"spawned\"}'")])
    patch = {"schema_version": SCHEMA_VERSION, "kind": "roster_row", **patch}
    agent = patch.get("agent")
    if not isinstance(agent, str) or not agent.strip():
        raise Failure([problem("--row at /agent", "is missing or empty",
                               "name the agent with its short name from the task, as \"agent\"")])
    path = writable_path(args.file)
    records, errors = load_jsonl(path) if path.exists() else ([], [])
    if errors:
        raise Failure(errors + [problem(str(path), "holds lines that are not valid JSON",
                                        "repair or delete those lines, then set the row again")])

    # Validate the row as it will read after this patch, then append the patch.
    current: dict = {}
    for _, record in records:
        if isinstance(record, dict) and record.get("agent") == agent:
            current = merge_patch(current, record)
    folded = merge_patch(current, patch)
    errors = check_message(protocol, folded, f"roster row for {agent!r} after this set",
                           expect="roster_row")
    if errors:
        raise Failure(errors)
    append_line(path, patch)
    print_json(folded)
    return 0


def cmd_roster_show(args) -> int:
    protocol, _ = load_schemas()
    path = absolute(args.file)
    if not path.exists():
        note(f"{path}: no roster yet, read as empty; the first roster set creates it")
        print_json([])
        return 0
    records, errors = load_jsonl(path)
    rows, fold_errors = fold_rows([(f"{path}:{n}", r) for n, r in records])
    errors += fold_errors
    current = []
    for agent, row in rows.items():
        problems = check_message(protocol, row, f"{path}, folded row for {agent!r}",
                                 expect="roster_row")
        if problems:
            errors += problems
        else:
            current.append(row)
    print_json(current)
    if errors:
        raise Failure(errors)
    return 0


# ---------------------------------------------------------------- package

def without_related(text: str) -> str:
    """Drop a trailing '## Related' section: its links are relative to the
    skill folder and do not resolve inside a spawn message."""
    lines = text.splitlines()
    headings = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if headings and lines[headings[-1]].strip() == "## Related":
        lines = lines[:headings[-1]]
    return "\n".join(lines).rstrip()


def roles_block(protocol: dict, roles: list) -> str:
    """A short Markdown list of the task's roles, each with its description.

    The text comes from protocol.schema.json $defs/role (enum zipped with
    enumDescriptions), so the schema stays the one source of role text. Roles
    appear once each, in the task's order.
    """
    role = protocol["$defs"].get("role", {})
    described = dict(zip(role.get("enum") or [], role.get("enumDescriptions") or []))
    names = list(dict.fromkeys(roles))
    missing = [name for name in names if not described.get(name)]
    if missing:
        raise Failure([problem(located(str(PROTOCOL_SCHEMA), "/$defs/role/enumDescriptions"),
                               "has no description for " + ", ".join(missing),
                               "give every role in $defs/role/enum a description, in the same order")])
    lines = ["## Your role" if len(names) == 1 else "## Your roles", ""]
    lines += [f"- `{name}`: {described[name]}" for name in names]
    return "\n".join(lines)


def parse_packet(path: Path, text: str, expected: str | None = None) -> dict:
    """Read one packet file: its header fields and its body.

    The header is the title line `# Packet: NAME`, then one `Field: value`
    line for each of Revision, About, Source and Kept, ending at the first
    blank line. Everything after it is the body, which must hold some text.
    """
    where = str(path)
    fix = "open the file with this header: " + PACKET_HEADER_EXAMPLE
    if not text.strip():
        raise Failure([problem(where, "is empty", "write the packet's header and body, or remove "
                                                  "the packet from the task's packets")])
    lines = text.splitlines()
    title = PACKET_TITLE_RE.fullmatch(lines[0])
    if not title:
        raise Failure([problem(where + ", line 1", "is not a packet title", fix)])
    name = title.group(1)
    stem = path.name[:-3] if path.name.endswith(".md") else path.name
    if name != stem:
        raise Failure([problem(where + ", line 1", f"names packet {json.dumps(name)} in a file named "
                                                   f"{path.name}",
                               f"make the title '# Packet: {stem}', or rename the file {name}.md")])
    if expected is not None and name != expected:
        raise Failure([problem(where, f"is packet {json.dumps(name)}, not {json.dumps(expected)}",
                               f"write the packet {expected} as {expected}.md")])
    named: list = []
    rule_packet_name(name, "", named)
    if named:
        raise Failure([problem(where + ", line 1", what, fix) for _, what, fix in named])
    fields: dict = {}
    end = None
    for number, line in enumerate(lines[1:], 2):
        if not line.strip():
            end = number
            break
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or key not in PACKET_FIELDS:
            raise Failure([problem(f"{where}, line {number}",
                                   f"{json.dumps(line[:60])} is not a header field",
                                   "use only Revision, About, Source and Kept in the header, then "
                                   "a blank line before the body")])
        if key in fields:
            raise Failure([problem(f"{where}, line {number}", f"repeats the {key} field",
                                   "keep one of the two lines")])
        fields[key] = value
    errors = []
    for key in PACKET_FIELDS:
        if not fields.get(key):
            errors.append(problem(where, f"the header has no {key} value", fix))
    revision = fields.get("Revision", "")
    # ASCII digits only: str.isdigit() also accepts digits such as a superscript two,
    # which int() then refuses.
    if revision and not (re.fullmatch(r"[0-9]+", revision) and int(revision) >= 1):
        errors.append(problem(where, f"Revision {json.dumps(revision)} is not a whole number "
                                     "of 1 or more",
                              "write Revision: 1 for a new packet, and add 1 at each update"))
    if fields.get("Kept") and fields["Kept"] not in ("yes", "no"):
        errors.append(problem(where, f"Kept {json.dumps(fields['Kept'])} is not yes or no",
                              "write Kept: no for a packet of this run only, Kept: yes once it is "
                              "copied to the project's .agent-orchestrate/packets/"))
    if errors:
        raise Failure(errors)
    body = "\n".join(lines[end:]) if end is not None else ""
    if not body.strip():
        raise Failure([problem(where, "has a header and no body",
                               "write the context below the header, after one blank line")])
    if "</packet" in text.lower():
        raise Failure([problem(where, "contains a closing packet tag, which would end the packet "
                                      "early in the spawn message",
                               "reword that line so it holds no </packet, in any case")])
    return {"name": name, "revision": int(revision), "about": fields["About"],
            "source": fields["Source"], "kept": fields["Kept"] == "yes",
            "bytes": len(text.encode("utf-8")), "file": where, "text": text.strip("\n")}


def packets_folder(task_path: Path, option: str | None) -> tuple[Path, list[Path]]:
    """The folder package reads packets from, and every folder it looked in.

    --packets DIR wins. Otherwise packets/ beside the task file, then packets/
    in the folder above it, the run's folder when task files sit in tasks/.
    """
    if option:
        folder = absolute(option)
        return folder, [folder]
    tried = [task_path.parent / "packets", task_path.parent.parent / "packets"]
    for folder in tried:
        if folder.is_dir():
            return folder, tried
    return tried[0], tried


def packets_block(task: dict, task_path: Path, option: str | None) -> tuple[str, list[str]]:
    """The packets to place after the standing text, and any error lines."""
    names = task.get("packets") or []
    if not names:
        return "", []
    folder, tried = packets_folder(task_path, option)
    errors: list[str] = []
    parts = []
    for name in names:
        path = folder / f"{name}.md"
        if not path.is_file():
            looked = " and ".join(str(f) for f in tried)
            errors.append(problem(str(path), f"packet {json.dumps(name)} is missing (looked in {looked})",
                                  f"write it as packets/{name}.md in the run's folder, pass "
                                  "--packets DIR, or remove it from the task's packets"))
            continue
        try:
            packet = parse_packet(path, read_text(path, "check the path"), expected=name)
        except Failure as exc:
            errors += exc.lines
            continue
        parts.append(f"<packet name=\"{name}\" revision=\"{packet['revision']}\">\n"
                     f"{packet['text']}\n</packet>")
    if errors:
        return "", errors
    heading = ("## Context packets\n\nThe orchestrator gave you this context before your task, in "
               "this order.")
    return heading + "\n\n" + "\n\n".join(parts), []


def cmd_packets(args) -> int:
    load_schemas()
    folder = absolute(args.folder)
    if not folder.is_dir():
        note(f"{folder}: no packets folder yet, read as empty; the first packet written there "
             "creates it")
        print_json({"schema_version": SCHEMA_VERSION, "folder": str(folder), "packets": []})
        return 0
    errors: list[str] = []
    found = []
    for path in sorted(folder.glob("*.md")):
        try:
            packet = parse_packet(path, read_text(path, "check the path"))
        except Failure as exc:
            errors += exc.lines
            continue
        packet.pop("text")
        found.append(packet)
    print_json({"schema_version": SCHEMA_VERSION, "folder": str(folder), "packets": found})
    if errors:
        raise Failure(errors)
    return 0


def cmd_package(args) -> int:
    protocol, _ = load_schemas()
    path = absolute(args.task_file)
    task = load_json_file(path, "pass the path of the task file written for this agent")
    errors = check_message(protocol, task, str(path), expect="task")
    named = task.get("task_file") if isinstance(task, dict) else None
    if isinstance(named, str) and is_absolute(named) and \
            os.path.realpath(named) != os.path.realpath(path):
        errors.append(problem(located(str(path), "/task_file"),
                              f"names {named}, not the file being packaged",
                              f"set \"task_file\" to \"{path}\" so the agent re-reads this file"))
    out = None
    if args.out is not None:
        try:
            out = writable_path(args.out)
        except Failure as exc:
            errors += exc.lines
        else:
            if out.name.lower() in LOADED_NAMES:
                errors.append(problem(str(out), "is a name hosts load as project instructions",
                                      "name the file after the agent, such as AGENT-spawn.md"))
            if os.path.realpath(out) == os.path.realpath(path):
                errors.append(problem(str(out), "is the task file itself",
                                      "save the spawn message beside it, such as AGENT-spawn.md"))
            spawn = task.get("spawn_file") if isinstance(task, dict) else None
            if isinstance(spawn, str) and is_absolute(spawn) and \
                    os.path.realpath(spawn) != os.path.realpath(out):
                errors.append(problem(located(str(path), "/spawn_file"),
                                      f"names {spawn}, not the --out file {out}",
                                      f"set \"spawn_file\" to \"{out}\" so the agent re-reads that file"))
    if not STANDING.is_file():
        errors.append(problem(str(STANDING),
                              "is missing; the spawn message starts with the standing instructions "
                              "in this file",
                              "write assets/standing.md in the skill folder, or restore it from the "
                              "skill's repository, then package again"))
    packets = ""
    if not errors:
        # Only a valid task is read for packets, so its packets list is well formed.
        packets, problems = packets_block(task, path, args.packets)
        errors += problems
    if errors:
        raise Failure(errors)
    standing = without_related(
        read_text(STANDING, "restore assets/standing.md from the skill's repository"))
    body = json.dumps(task, indent=2, ensure_ascii=False)
    # Standing text, then packets, so agents given the same packets in the same
    # order open with the same text; the roles block and the task differ per agent.
    message = (standing.rstrip("\n") + "\n\n" + (packets + "\n\n" if packets else "")
               + roles_block(protocol, task["roles"])
               + "\n\n<task>\n```json\n" + body + "\n```\n</task>\n")
    if out is not None:
        # Written here as UTF-8 rather than through shell redirection, which some
        # shells re-encode (Windows PowerShell 5.1 writes UTF-16LE).
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(message)
        except OSError as exc:
            raise Failure([problem(str(out), f"cannot be written ({exc.strerror})",
                                   "pass a path in a folder you can write, such as the "
                                   "session's temporary working space")])
    sys.stdout.write(message)
    return 0


# ---------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    raw = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(
        prog="ao.py", formatter_class=raw,
        description=__doc__.split("\n")[0],
        epilog="Run 'ao.py COMMAND --help' for one command. Exit 0 on success; "
               "1 with errors on stderr, each naming the path and the fix.")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)

    config = commands.add_parser(
        "config", formatter_class=raw, help="print the effective settings, or change one with set",
        description="Merge the shipped config files with the user and project overrides "
                    "(RFC 7396; a null deletes a key), validate the result and print it.\n\n"
                    "user:    ${XDG_CONFIG_HOME:-~/.config}/agent-orchestrate/{config,models}.json\n"
                    "project: <DIR>/.agent-orchestrate/{config,models}.json\n\n"
                    "Run 'ao.py config set --help' to change a setting in one of those files.")
    config.add_argument("--project", metavar="DIR",
                        help="project root (default: the git root of the working directory, "
                             "else the working directory)")
    config.add_argument("--explain", action="store_true",
                        help="print every leaf with the layer and file it came from")
    config.set_defaults(func=cmd_config)
    config_actions = config.add_subparsers(dest="action", metavar="ACTION")
    config_set = config_actions.add_parser(
        "set", help="change settings in the user or project file",
        description="Merge PATCH into the chosen layer's override files and print the --explain "
                    "output. Top-level keys reviewed, roles, role_agents and providers go to "
                    "models.json, every other setting to config.json; a key the shipped files "
                    "do not carry, at any depth, is refused. Each part merges key by key. A "
                    "null is stored only for a setting whose shipped value is null "
                    "(agents.max_active, role_agents.*, providers.*.*.model and .effort), and "
                    "overrides the layers below with that null; a null for any other key is "
                    "refused. --reset KEY removes KEY from the layer's file, so the layer below "
                    "shows through. The effective config is checked with the new content "
                    "first; on any error nothing is written. Files are written atomically as "
                    "UTF-8, and a failed write puts back the files it already replaced.")
    config_set.add_argument("--layer", required=True, choices=("user", "project"),
                            help="user: ${XDG_CONFIG_HOME:-~/.config}/agent-orchestrate/; "
                                 "project: <DIR>/.agent-orchestrate/")
    config_set.add_argument("--project", metavar="DIR", default=argparse.SUPPRESS,
                            help="project root (default: the git root of the working directory, "
                                 "else the working directory)")
    config_set.add_argument("--reset", action="append", metavar="KEY", default=None,
                            help="a dotted key, such as roles.reviewer, to remove from the "
                                 "layer's file; repeat it for more keys")
    config_set.add_argument("patch", metavar="PATCH", nargs="?", default=None,
                            help="a JSON object, or @FILE to read it from FILE; optional with "
                                 "--reset")

    check = commands.add_parser(
        "check", help="validate one message against the protocol schema",
        description="Validate a task, ask, answer, notice, return, status_line or roster_row "
                    "by its kind, plus the rules the schema leaves to code. Also accepts a "
                    "reply whose last fenced json block is the message, and JSON Lines "
                    "status or roster files.")
    check.add_argument("file", metavar="FILE", help="the message file, or - to read stdin")
    check.set_defaults(func=cmd_check)

    status = commands.add_parser("status", help="append to or read an agent's status file",
                                 description="An agent's status file holds one status_line "
                                             "per line (JSON Lines).")
    status_actions = status.add_subparsers(dest="action", metavar="ACTION", required=True)
    append = status_actions.add_parser(
        "append", help="append one status line",
        description="Append one status_line, stamped with the current UTC time, and print it.")
    append.add_argument("file", metavar="FILE", help="the agent's status file")
    append.add_argument("--agent", required=True, metavar="NAME", help="the agent's short name")
    append.add_argument("--event", required=True, metavar="EVENT",
                        help="a status_event from protocol.schema.json, such as milestone or threshold")
    append.add_argument("--summary", required=True, metavar="TEXT",
                        help="what just became true; for a threshold, the task's threshold exactly")
    append.set_defaults(func=cmd_status_append)
    read = status_actions.add_parser(
        "read", help="print a status file as a JSON array",
        description="Print the status lines as a JSON array. With --threshold, print an "
                    "object with threshold_crossed, true when a threshold line with exactly "
                    "that summary exists, and the lines. A misworded threshold line is an "
                    "error until a line with exactly that summary exists, and a note after.")
    read.add_argument("file", metavar="FILE", help="the agent's status file")
    read.add_argument("--threshold", metavar="TEXT", help="the task's threshold wording")
    read.set_defaults(func=cmd_status_read)

    roster = commands.add_parser("roster", help="set or show rows of the run's roster",
                                 description="The roster is a JSON Lines file of roster_row "
                                             "records, appended and folded per agent.")
    roster_actions = roster.add_subparsers(dest="action", metavar="ACTION", required=True)
    roster_set = roster_actions.add_parser(
        "set", help="validate and append a partial row",
        description="Append a partial roster_row for one agent. The row as it reads after "
                    "the patch must be valid; a null deletes a field. Prints that row.")
    roster_set.add_argument("file", metavar="FILE", help="the roster file")
    roster_set.add_argument("--row", required=True, metavar="JSON",
                            help="a JSON object holding at least \"agent\"")
    roster_set.set_defaults(func=cmd_roster_set)
    roster_show = roster_actions.add_parser(
        "show", help="print the current rows",
        description="Fold the rows per agent as merge patches, in file order, and print "
                    "the current rows as a JSON array.")
    roster_show.add_argument("file", metavar="FILE", help="the roster file")
    roster_show.set_defaults(func=cmd_roster_show)

    package = commands.add_parser(
        "package", help="print the spawn message for one task",
        description="Validate TASK_FILE as a task, then print assets/standing.md without "
                    "its trailing Related section, each packet the task lists (in its "
                    "order, each in a <packet> element with its header), a short block "
                    "describing each of the task's roles (from protocol.schema.json), and "
                    "a <task> element holding the task as one fenced json block. With "
                    "--out, also save it to FILE as UTF-8. A missing, empty or headerless "
                    "packet is an error, and nothing is written.")
    package.add_argument("task_file", metavar="TASK_FILE", help="the task file to send")
    package.add_argument("--out", metavar="FILE",
                         help="save the message here too, as UTF-8: the task's spawn_file")
    package.add_argument("--packets", metavar="DIR",
                         help="read the task's packets from DIR (default: packets/ beside the "
                              "task file, else packets/ in the folder above it)")
    package.set_defaults(func=cmd_package)

    packets = commands.add_parser(
        "packets", help="list the context packets in a folder",
        description="Read every NAME.md packet in DIR and print, for each, its name, revision, "
                    "about, source, kept and size in bytes, for the packets view. A packet "
                    "whose header does not parse is named on stderr, and the exit status is 1.")
    packets.add_argument("folder", metavar="DIR",
                         help="a run's packets/ folder, or a project's .agent-orchestrate/packets/")
    packets.set_defaults(func=cmd_packets)
    return parser


def main(argv: list[str] | None = None) -> int:
    # Write UTF-8 even where the console default is another encoding.
    for stream in (sys.stdout, sys.stderr):
        if (getattr(stream, "encoding", "") or "").lower().replace("-", "") != "utf8":
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, ValueError, OSError):
                pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Failure as exc:
        sys.stdout.flush()
        for line in exc.lines:
            print(f"ao.py: {line}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
