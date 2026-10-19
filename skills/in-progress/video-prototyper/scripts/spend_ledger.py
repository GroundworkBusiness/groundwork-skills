#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Shared spend ledger for paid generation: append-only JSON lines with caps.

tts_generate.py and api_media.py import this module (it sits beside them). Every paid
request is reserved here, under a file lock, before it is sent, with a second cap check.
A request that never connected (the connection was refused or blocked, the host was not
found or unreachable, or the TLS handshake failed) is marked not_sent and does not count,
because nothing left the machine. Every other outcome keeps its reservation, because it
may have billed. A malformed ledger is refused, never reset. Never delete ledger lines to get
under a cap; raise a cap only with the owner's explicit yes.

Each line is one JSON object:
  {"at": "2026-01-31T12:00:00Z", "day": "2026-01-31", "id": "...", "tool": "...",
   "kind": "speech|image|video|music|other", "model": "...", "units": 1.0,
   "unit": "request|second|track|image", "est_usd": 0.05, "status": "reserved", "note": "..."}
Outcome lines refer back by id: {"ref": "<id>", "status": "completed|failed|uncertain|pending|not_sent", ...}.
Costs are estimated list prices before credits; the billing page is the real record.

Usage:
  python3 spend_ledger.py --summary media/ledger.jsonl
  python3 spend_ledger.py --reserve media/ledger.jsonl --kind image --unit image --est-usd 0.04 \
      --cap-usd-day 1 --note <request id>        (prints the reservation id)
  python3 spend_ledger.py --outcome media/ledger.jsonl --ref <id> --status completed

--reserve and --outcome record a paid item made outside the scripts (the agent tool's own
generator, or a web app), so the caps count it: reserve before making the item, and record
the outcome after.

Dependencies: Python 3.9 or later, standard library only (fcntl on macOS and Linux; a
lock file elsewhere).
Exit codes: 0 summary printed, reserved or recorded; 1 the ledger is malformed; 2 bad arguments; 3 a cap refused the reservation.
"""
import argparse
import contextlib
import datetime
import json
import math
import os
import sys
import time
import uuid

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None


class LedgerError(Exception):
    pass


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


@contextlib.contextmanager
def locked(path):
    lock_path = path + ".lock"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if fcntl:
        with open(lock_path, "a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
    else:
        deadline = time.time() + 30
        while True:
            try:
                fd = os.open(lock_path + ".x", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                if time.time() > deadline:
                    raise LedgerError("could not lock the ledger within 30 s")
                time.sleep(0.2)
        try:
            yield
        finally:
            os.close(fd)
            os.remove(lock_path + ".x")


def read(path):
    """Return every line as a dict. Raise LedgerError on any malformed line."""
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            def refuse_constant(name):
                raise LedgerError(f"ledger line {n} holds {name}; fix it by hand, never reset the ledger")
            try:
                row = json.loads(line, parse_constant=refuse_constant)
            except ValueError:
                raise LedgerError(f"ledger line {n} is not JSON; fix it by hand, never reset the ledger")
            if not isinstance(row, dict) or not ("id" in row or "ref" in row):
                raise LedgerError(f"ledger line {n} has no id or ref")
            estimate = row.get("est_usd", 0)
            if "id" in row and (isinstance(estimate, bool) or not isinstance(estimate, (int, float))
                                or not math.isfinite(estimate) or estimate < 0):
                raise LedgerError(f"ledger line {n} has an est_usd that is not a finite number of 0 or more; fix it by hand, never reset the ledger")
            rows.append(row)
    return rows


def not_sent_ids(rows):
    """Reservations released only when the request never connected."""
    return {row["ref"] for row in rows if row.get("status") == "not_sent" and "ref" in row}


def totals(rows, day=None):
    """Sum reserved estimates: (total for the day, total for the project)."""
    day_total = project_total = 0.0
    excluded = not_sent_ids(rows)
    for row in rows:
        if "id" not in row or row["id"] in excluded:
            continue
        cost = float(row.get("est_usd") or 0)
        project_total += cost
        if day and row.get("day") == day:
            day_total += cost
    return round(day_total, 6), round(project_total, 6)


def check_caps(est_usd, rows, day, cap_request=None, cap_day=None, cap_project=None):
    """Return a list of reasons the request would break a cap (empty when it fits)."""
    reasons = []
    for name, value in (("request", cap_request), ("day", cap_day), ("project", cap_project)):
        if value is not None and (not math.isfinite(value) or value < 0):
            reasons.append(f"cap {name} is not a finite number of 0 or more")
    if est_usd != est_usd or est_usd in (float("inf"), float("-inf")) or est_usd < 0:
        reasons.append("estimated cost is not a finite, non-negative number")
        return reasons
    day_total, project_total = totals(rows, day)
    if cap_request is not None and est_usd > cap_request:
        reasons.append(f"request estimate ${est_usd:.4f} is over the per-request cap ${cap_request:.4f}")
    if cap_day is not None and day_total + est_usd > cap_day:
        reasons.append(f"today ${day_total:.4f} + ${est_usd:.4f} is over the daily cap ${cap_day:.4f}")
    if cap_project is not None and project_total + est_usd > cap_project:
        reasons.append(f"project ${project_total:.4f} + ${est_usd:.4f} is over the project cap ${cap_project:.4f}")
    return reasons


def reserve(path, record, cap_request=None, cap_day=None, cap_project=None):
    """Append a reservation under the lock after a second cap check. Return its id."""
    with locked(path):
        rows = read(path)
        now = utc_now()
        day = now.date().isoformat()
        est = float(record.get("est_usd") or 0)
        reasons = check_caps(est, rows, day, cap_request, cap_day, cap_project)
        if reasons:
            raise LedgerError("; ".join(reasons))
        row = dict(record)
        row.update({"at": now.isoformat().replace("+00:00", "Z"), "day": day,
                    "id": row.get("id") or uuid.uuid4().hex[:12], "status": "reserved", "est_usd": est})
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row["id"]


def outcome(path, ref, status, **extra):
    """Append an outcome; only not_sent releases the reservation from totals."""
    with locked(path):
        read(path)
        row = {"ref": ref, "status": status, "at": utc_now().isoformat().replace("+00:00", "Z")}
        row.update(extra)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--summary", metavar="LEDGER")
    mode.add_argument("--reserve", metavar="LEDGER", help="reserve one paid item made outside the scripts (a built-in generator or a web app); prints its id")
    mode.add_argument("--outcome", metavar="LEDGER", help="append the outcome of the reservation named by --ref")
    ap.add_argument("--tool", default="built-in-generator")
    ap.add_argument("--kind", default="other", choices=["speech", "image", "video", "music", "other"])
    ap.add_argument("--model")
    ap.add_argument("--units", type=float, default=1.0)
    ap.add_argument("--unit", default="item")
    ap.add_argument("--est-usd", type=float, help="list-price estimate for this item (0 when the owner's plan includes it)")
    ap.add_argument("--cap-usd-request", type=float)
    ap.add_argument("--cap-usd-day", type=float)
    ap.add_argument("--cap-usd-project", type=float)
    ap.add_argument("--note", default="")
    ap.add_argument("--ref", help="with --outcome: the id --reserve printed")
    ap.add_argument("--status", choices=["completed", "failed", "uncertain", "pending", "not_sent"], help="with --outcome")
    args = ap.parse_args()
    if args.reserve:
        caps = (args.cap_usd_request, args.cap_usd_day, args.cap_usd_project)
        if args.est_usd is None or all(c is None for c in caps):
            print("FAIL: --reserve needs --est-usd and at least one of --cap-usd-request, --cap-usd-day or --cap-usd-project")
            return 2
        try:
            read(args.reserve)
        except LedgerError as err:
            print(f"FAIL: {err}")
            return 1
        try:
            rid = reserve(args.reserve, {"tool": args.tool, "kind": args.kind, "model": args.model, "units": args.units,
                                         "unit": args.unit, "est_usd": args.est_usd, "note": args.note}, *caps)
        except LedgerError as err:
            print(f"REFUSED: {err}")
            return 3
        print(f"reserved {rid}: ${args.est_usd:.4f} for {args.note or args.kind}; after the item, run --outcome with --ref {rid}")
        return 0
    if args.outcome:
        if not args.ref or not args.status:
            print("FAIL: --outcome needs --ref and --status")
            return 2
        try:
            outcome(args.outcome, args.ref, args.status)
        except LedgerError as err:
            print(f"FAIL: {err}")
            return 1
        print(f"recorded {args.status} for {args.ref}")
        return 0
    try:
        rows = read(args.summary)
    except LedgerError as err:
        print(f"FAIL: {err}")
        return 1
    by_day = {}
    excluded = not_sent_ids(rows)
    for row in rows:
        if "id" in row and row["id"] not in excluded:
            by_day[row.get("day", "?")] = by_day.get(row.get("day", "?"), 0.0) + float(row.get("est_usd") or 0)
    outcomes = {}
    for row in rows:
        if "ref" in row:
            outcomes[row["status"]] = outcomes.get(row["status"], 0) + 1
    for day in sorted(by_day):
        print(f"{day}  ${by_day[day]:.4f}")
    _, project = totals(rows)
    reserved = sum(1 for r in rows if "id" in r)
    print(f"total  ${project:.4f} estimated list cost across {reserved} reservation(s); not_sent: {len(excluded)} (not counted); outcomes {outcomes or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
