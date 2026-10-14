#!/usr/bin/env python3
"""Branch lanes, worktrees and isolation preflight for one repository, as JSON.

Read-only: every git call is a query, run with optional locks disabled so that
even `git status` leaves the index file untouched. Nothing is fetched, written,
checked out or pruned, and no network call is made. The orchestrator renders
the output, one object carrying "schema_version": 1; this script only reports.

    python3 git_lanes.py <repo> [--full] [--trunk NAME] [--limit N]

--full adds squash detection, the one expensive signal. Run it at integration,
or to confirm a suspected squash, rather than on a mid-run report.

Requires Python 3.9 or later and git on PATH. Standard library only.

BRANCH FATE, AND THE PROOF FOR EACH
-----------------------------------
Each fate names the command that proves it, because the three are not equally
knowable and a fate without its evidence is a guess.

  merged    git for-each-ref --merged=<trunk> refs/heads
            Ancestry. Cheap, exact, always on. Read through for-each-ref
            because `git branch` output marks a branch checked out in another
            worktree with "+", which a name match then misses.

  squashed  git diff <merge-base>..<branch> | git patch-id --stable, compared
            against the patch-ids of trunk commits since the merge-base.
            Patch identity. Capped at SQUASH_SCAN trunk commits, since a squash
            normally lands within a few commits of the merge-base and an
            unbounded scan is slow on a long trunk. When the cap truncates the
            scan the lane says so rather than reporting a clean "open".

  rebased   git reflog --no-abbrev --date=iso, lines containing "rebase (finish)"
            or "rebase -i (finish)".
            Local evidence only, read per working tree: a linked worktree keeps
            its own HEAD reflog, so the reader opens the reflog inside each
            worktree. A reflog belongs to one clone and expires (90 days by
            default), so absence means "not recorded", never "did not happen".

Two detectors that look right give wrong answers, which is why neither is used:
`git cherry` never matches a squash, because the squash collapses N commits and
every one of them reports '+'; and a plain `git diff <trunk> <branch>` gives a
false negative as soon as unrelated work lands on trunk.

GIT COMMANDS BEHIND EACH FIELD
------------------------------
Every query runs as `git --no-optional-locks -c core.fsmonitor=false -C <path> ...`;
without --no-optional-locks a plain `git status` rewrites the index. Where this
script cannot run, the same commands give the same fields by hand.

  is_repo                        git rev-parse --git-dir             (exits 128 outside a repository)
  worktrees, locked, prunable    git worktree list --porcelain
  dirty, dirty_count             git status --porcelain              (in each worktree)
  rebased                        git reflog --no-abbrev --date=iso   (in each worktree)
  lanes (one per branch)         git for-each-ref --format=%(refname:lstrip=2) refs/heads
  ahead, behind                  git rev-list --left-right --count <trunk>...refs/heads/<branch>
  base                           git merge-base <trunk> refs/heads/<branch>
  commits                        git log -n<limit> --date=iso-strict <base>..refs/heads/<branch>
  trunk                          see REMOTES below
  commits_not_on_remote_default  git rev-list --count refs/remotes/<remote_head>..HEAD
  fate, proof                    see BRANCH FATE above

When the worktree list, the branch list or the merged list fails or times out,
the script exits 1 rather than report an empty inventory, which would read as
clean. Two probes read git's exit code instead: the repository check takes exit
128 as "not a git repository", and the trunk check
(git rev-parse --verify --quiet <trunk>^{commit}) takes exit 1 as "no commit
yet, nothing merged". Any other failure of either, a timeout included, also
exits 1.

REMOTES
-------
Any remote name works, and so does no remote. The reader reports one remote:
"origin" when it exists, else the `remote.pushDefault` remote, else the first
listed. Trunk comes from that remote's HEAD, else a local main, master or trunk
branch, else the current branch. Remote URLs are printed with any user name and
password removed.

ISOLATION PREFLIGHT
-------------------
The preflight block reports which isolation tiers (none, ephemeral, session)
this repository can support, so a plan offers only what is possible.

It reads git alone and no host's settings. commits_not_on_remote_default
counts the commits on HEAD that the remote's default branch lacks, as this
clone records that branch (remote_head), and is null when the clone records
none. A worktree based on that branch starts without those commits. How each
host picks the base of a new worktree is in that host's SOP, under
references/hosts/.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

COMMIT_LIMIT = 40   # commits listed per lane: enough to draw a lane, few enough to read; --limit overrides
SQUASH_SCAN = 120
TIMEOUT = 20        # seconds per git query, so one stuck call (a slow network disk, a huge tree) cannot
                    # hang the report; a query that times out counts as failed
TIERS = ["none", "ephemeral", "session"]
SCHEMA_VERSION = 1

# Prepended to every git call. --no-optional-locks stops `git status` from
# refreshing the index and writing it back; core.fsmonitor=false stops a status
# call from starting a filesystem-monitor daemon that would create a socket
# inside the repository.
GIT_GLOBAL = ["--no-optional-locks", "-c", "core.fsmonitor=false"]

# The same switch as an environment variable, which also reaches any git
# process that git starts on its own, such as a submodule status.
GIT_ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")

GIT = ""


def fail(message: str) -> None:
    """Print an error naming the problem and the fix to stderr, then exit 1."""
    print(f"git_lanes.py: {message}", file=sys.stderr)
    sys.exit(1)


def run(repo: Path, *args: str, stdin: str | None = None,
        env: dict | None = None) -> subprocess.CompletedProcess | None:
    """Run one read-only git query in `repo`. Returns the finished process with
    its exit code, or None when git times out or cannot start.

    Output is decoded with surrogateescape so bytes that are not UTF-8 survive
    a round trip into `git patch-id` unchanged.
    """
    io = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
    try:
        return subprocess.run([GIT, *GIT_GLOBAL, "-C", str(repo), *args],
                              capture_output=True, text=True,
                              errors="surrogateescape", timeout=TIMEOUT,
                              env=env or GIT_ENV, **io)
    except (subprocess.TimeoutExpired, OSError):
        return None


def query(repo: Path, *args: str, stdin: str | None = None) -> str | None:
    """run(), as stdout, or None when git fails or times out, so a caller can
    tell a failed query from empty output."""
    p = run(repo, *args, stdin=stdin)
    return p.stdout if p is not None and p.returncode == 0 else None


def unknown(repo: Path, args: tuple, p: subprocess.CompletedProcess | None,
            what: str) -> None:
    """Exit 1 for a probe whose failure leaves `what` unknown."""
    why = "timed out" if p is None else (p.stderr.strip().splitlines() or
                                         [f"exit {p.returncode}"])[0]
    fail(f"git {' '.join(args)} failed in {repo} ({why}), so {what} is unknown. "
         "Run that command there to see why, then run this again.")


def g(repo: Path, *args: str, stdin: str | None = None) -> str:
    """query(), with a failure read as empty output. Use it only where empty is
    the safe reading, such as a ref that does not exist."""
    out = query(repo, *args, stdin=stdin)
    return "" if out is None else out


def must(repo: Path, *args: str) -> str:
    """query() for an inventory that must not read as empty when git fails."""
    out = query(repo, *args)
    if out is None:
        fail(f"git {' '.join(args)} failed or timed out in {repo}, so the worktree and "
             "branch state is unknown. Run that command there to see why, then run this "
             "again. The git command behind each field is listed in this script's header.")
    return out


def ref_exists(repo: Path, ref: str) -> bool:
    return g(repo, "rev-parse", "--verify", "--quiet", ref).strip() != ""


def is_repo(path: Path) -> bool:
    """True inside a git repository. Outside one, git exits 128 and says "not a
    git repository"; any other failure, a timeout included, exits 1 here."""
    args = ("rev-parse", "--git-dir")
    p = run(path, *args, env=dict(GIT_ENV, LC_ALL="C"))   # untranslated message
    if p is not None and p.returncode == 0:
        return True
    if p is not None and p.returncode == 128 and "not a git repository" in p.stderr:
        return False
    unknown(path, args, p, "whether this is a git repository")
    return False


def toplevel(repo: Path) -> Path:
    """The root of the working tree that holds `repo`, or `repo` when bare."""
    top = g(repo, "rev-parse", "--show-toplevel").strip()
    return Path(top) if top else repo


def head_branch(repo: Path) -> str:
    return g(repo, "branch", "--show-current").strip()


def commit_count(repo: Path) -> int:
    out = g(repo, "rev-list", "--count", "HEAD").strip()
    return int(out) if out.isdigit() else 0


# ---------------------------------------------------------------- remotes

def remote_names(repo: Path) -> list[str]:
    return g(repo, "remote").split()


def pick_remote(repo: Path, names: list[str]) -> str:
    """The remote this report describes: origin, else pushDefault, else the first."""
    if not names:
        return ""
    if "origin" in names:
        return "origin"
    push = g(repo, "config", "--get", "remote.pushDefault").strip()
    return push if push in names else names[0]


def remote_head(repo: Path, remote: str) -> str:
    """`<remote>/<branch>` that the remote's HEAD points at, or "" when unset."""
    if not remote:
        return ""
    full = g(repo, "symbolic-ref", "--quiet", f"refs/remotes/{remote}/HEAD").strip()
    return full[len("refs/remotes/"):] if full.startswith("refs/remotes/") else ""


def redact_url(url: str) -> str:
    """Drop any user name and password from a URL such as https://user:pw@host/x."""
    return re.sub(r"^([A-Za-z][A-Za-z0-9+.-]*://)[^/@]*@", r"\1", url)


# ---------------------------------------------------------------- trunk

def detect_trunk(repo: Path, remote: str, rhead: str, override: str) -> str:
    """Trunk name: the override, the remote's HEAD, a usual name, or HEAD's branch.

    A remote HEAD maps to the local branch of the same name when one exists, and
    otherwise to the remote-tracking branch itself.
    """
    if override:
        return override
    if rhead and ref_exists(repo, f"refs/remotes/{rhead}"):
        name = rhead[len(remote) + 1:]
        return name if ref_exists(repo, f"refs/heads/{name}") else rhead
    for name in ("main", "master", "trunk"):
        if ref_exists(repo, f"refs/heads/{name}"):
            return name
    return head_branch(repo) or "HEAD"


def full_ref(repo: Path, name: str) -> str:
    """The unambiguous ref for a branch or remote-tracking name, else `name`.

    Git resolves a bare name to a tag before a branch, so queries use the full
    ref wherever one exists.
    """
    for ref in (f"refs/heads/{name}", f"refs/remotes/{name}"):
        if ref_exists(repo, ref):
            return ref
    return name


# ---------------------------------------------------------------- size

def pack_size_mb(repo: Path) -> float:
    """Repository size as git measures it, in MB: loose objects plus packs.

    Measures git objects rather than the working tree, which can include
    installed dependencies. Sums loose and packed sizes because a repository
    that has never been packed reports size-pack 0 while holding every object
    loose.
    """
    total = 0.0
    for line in g(repo, "count-objects", "-vH").splitlines():
        key, _, val = line.partition(":")
        if key not in ("size", "size-pack"):
            continue
        num = re.match(r"([\d.]+)\s*([KMG]i?B|bytes)", val.strip())
        if not num:
            continue
        n, unit = float(num.group(1)), num.group(2)
        total += {"bytes": n / 1e6, "KiB": n / 1024, "MiB": n,
                  "GiB": n * 1024}.get(unit, n)
    return total


# ---------------------------------------------------------------- worktrees

def worktrees(repo: Path) -> list[dict]:
    """Every working tree of this repository, with what each one is carrying.

    `git worktree list --porcelain` is the only view that reports `locked` and
    `prunable`. A locked tree is held by another tool or session; a prunable
    one is a registration whose directory no longer exists.
    """
    out, cur, rows = must(repo, "worktree", "list", "--porcelain"), {}, []
    for line in out.splitlines():
        if not line.strip():
            if cur:
                rows.append(cur)
                cur = {}
            continue
        key, _, val = line.partition(" ")
        if key == "worktree":
            cur = {"path": val, "branch": "", "head": "", "locked": False,
                   "prunable": False, "detached": False, "note": ""}
        elif key == "HEAD":
            cur["head"] = val[:9]
        elif key == "branch":
            cur["branch"] = val[len("refs/heads/"):] if val.startswith("refs/heads/") else val
        elif key == "detached":
            cur["detached"] = True
        elif key == "locked":
            cur["locked"] = True
            cur["note"] = val
        elif key == "prunable":
            cur["prunable"] = True
            cur["note"] = val
    if cur:
        rows.append(cur)

    for w in rows:
        p = Path(w["path"])
        if w["prunable"] or not p.is_dir():
            w["dirty"] = None      # unknown rather than clean: the directory is gone
            w["dirty_count"] = 0
            w["rebased"] = []
            continue
        status = query(p, "status", "--porcelain")
        if status is None:     # unknown, never clean: clean-up decisions rest on this field
            w["dirty"] = None
            w["dirty_count"] = None
            w["error"] = "git status failed or timed out, so dirty is unknown"
        else:
            w["dirty_count"] = len([l for l in status.splitlines() if l.strip()])
            w["dirty"] = w["dirty_count"] > 0
        w["rebased"] = rebased_shas(p)
    return rows


def rebased_shas(tree: Path) -> list[str]:
    """Commits this working tree's own reflog records as the result of a rebase."""
    shas = []
    for line in g(tree, "reflog", "--no-abbrev", "--date=iso").splitlines():
        low = line.lower()
        if "rebase (finish)" in low or "rebase -i (finish)" in low:
            parts = line.split()
            if parts:
                shas.append(parts[0])
    return shas


# ---------------------------------------------------------------- lanes

def patch_id(repo: Path, diff_text: str) -> str:
    if not diff_text.strip():
        return ""
    out = g(repo, "patch-id", "--stable", stdin=diff_text).split()
    return out[0] if out else ""


def trunk_patch_ids(repo: Path, trunk_ref: str, since: str) -> tuple[dict, bool]:
    shas = g(repo, "rev-list", f"-n{SQUASH_SCAN}", f"{since}..{trunk_ref}").split()
    truncated = len(shas) >= SQUASH_SCAN
    ids = {}
    for sha in shas:
        pid = patch_id(repo, g(repo, "show", sha))
        if pid:
            ids[pid] = sha
    return ids, truncated


def lane(repo: Path, branch: str, trunk: str, trunk_ref: str, merged: set,
         rebased: set, dirty_by_branch: dict, full: bool, limit: int) -> dict:
    ref = f"refs/heads/{branch}"
    is_trunk = ref == trunk_ref
    tip = g(repo, "rev-parse", ref).strip()
    base = g(repo, "merge-base", trunk_ref, ref).strip()
    counts = g(repo, "rev-list", "--left-right", "--count",
               f"{trunk_ref}...{ref}").split()
    behind, ahead = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)

    rng = f"{base}..{ref}" if base and not is_trunk else ref
    commits = []
    raw = g(repo, "log", f"-n{limit}", "--date=iso-strict",
            "--format=%H%x1f%s%x1f%ad%x1f%an", rng)
    for line in raw.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            commits.append({"sha": parts[0][:9], "subject": parts[1],
                            "when": parts[2], "author": parts[3],
                            "rebased": parts[0] in rebased})

    row = {"branch": branch, "tip": tip[:9], "base": base[:9], "ahead": ahead,
           "behind": behind, "commits": commits,
           "dirty": dirty_by_branch.get(branch, False),
           "trunk": is_trunk}

    if is_trunk:
        row["fate"], row["proof"] = "trunk", "this is the trunk"
        return row
    if branch in merged:
        row["fate"] = "merged"
        row["proof"] = f"ancestry: git for-each-ref --merged={trunk} refs/heads"
        if tip in rebased:
            row["proof"] += "; this machine's reflog records a rebase before it landed"
        return row
    if full and ahead > 0 and base:
        pid = patch_id(repo, g(repo, "diff", f"{base}..{ref}"))
        if pid:
            ids, truncated = trunk_patch_ids(repo, trunk_ref, base)
            hit = ids.get(pid)
            if hit:
                row["fate"] = "squashed"
                row["proof"] = ("patch identity: the combined diff matches trunk "
                                "commit " + hit[:9])
                return row
            if truncated:
                row["fate"] = "open"
                row["proof"] = (f"{ahead} ahead, {behind} behind {trunk}; squash scan "
                                f"covered only the newest {SQUASH_SCAN} trunk commits")
                return row
    if tip in rebased:
        row["fate"] = "rebased"
        row["proof"] = ("this machine's reflog records a 'rebase (finish)' at this tip; "
                        "local evidence only")
        return row
    row["fate"] = "open"
    row["proof"] = f"{ahead} ahead, {behind} behind {trunk}"
    if not full:
        row["proof"] += "; squash not checked (run with --full)"
    return row


# ---------------------------------------------------------------- preflight

def not_on_remote_default(repo: Path, rhead: str, commits: int) -> int | None:
    """Commits on HEAD that the remote's default branch lacks.

    `rhead` is that branch as this clone records it, such as origin/main. None
    when the clone records no default branch for the remote, since there is
    then nothing to count against.
    """
    if not rhead or not ref_exists(repo, f"refs/remotes/{rhead}"):
        return None
    if not commits:
        return 0
    out = g(repo, "rev-list", "--count", f"refs/remotes/{rhead}..HEAD").strip()
    return int(out) if out.isdigit() else None


def preflight(repo: Path, top: Path, trunk: str, remote: str, rhead: str,
              wts: list[dict]) -> dict:
    head = head_branch(repo)
    commits = commit_count(repo)
    size = round(pack_size_mb(repo), 1)
    url = redact_url(g(repo, "remote", "get-url", remote).strip()) if remote else ""

    if commits == 0:
        tiers = ["none"]
        blocked = ["ephemeral, session: the repository has no commits, and a "
                   "worktree needs one"]
    else:
        tiers, blocked = list(TIERS), []

    has_include = (top / ".worktreeinclude").is_file()
    return {
        "is_repo": True,
        "head_branch": head,
        "trunk": trunk,
        "commits": commits,
        "remote": url,
        "remote_name": remote,
        "remote_head": rhead,
        "size_mb": size,
        "origin_head": rhead if remote == "origin" else "",
        "commits_not_on_remote_default": not_on_remote_default(repo, rhead, commits),
        "worktreeinclude": has_include,
        "worktreeinclude_note": "" if has_include else
            "no .worktreeinclude: a new worktree carries no gitignored files, so "
            "env files and installed dependencies will be absent",
        "tiers_available": tiers,
        "tiers_blocked": blocked,
        "worktrees_locked": [w["path"] for w in wts if w["locked"]],
        "worktrees_prunable": [w["path"] for w in wts if w["prunable"]],
    }


# ---------------------------------------------------------------- main

def build(repo: Path, trunk_override: str, full: bool, limit: int) -> dict:
    top = toplevel(repo)
    remotes = remote_names(repo)
    remote = pick_remote(repo, remotes)
    rhead = remote_head(repo, remote)
    trunk = detect_trunk(repo, remote, rhead, trunk_override)
    trunk_ref = full_ref(repo, trunk)
    wts = worktrees(repo)

    rebased = set()
    dirty_by_branch = {}
    for w in wts:
        rebased.update(w.get("rebased") or [])
        if w.get("branch"):
            dirty_by_branch[w["branch"]] = w.get("dirty")    # None stays unknown

    # lstrip=2 gives the branch name without refs/heads/ and never adds the
    # "heads/" prefix that refname:short uses when a tag shares the name.
    fmt = "--format=%(refname:lstrip=2)"
    # In a repository with no commits the trunk resolves to nothing: rev-parse
    # --verify --quiet exits 1, --merged would fail, and nothing is merged. Any
    # other failure, a timeout included, leaves the merged list unknown.
    args = ("rev-parse", "--verify", "--quiet", f"{trunk_ref}^{{commit}}")
    p = run(repo, *args)
    if p is None or p.returncode not in (0, 1):
        unknown(repo, args, p, "which branches are merged")
    trunk_ok = p.returncode == 0 and p.stdout.strip() != ""
    if not trunk_ok and trunk_override:
        fail(f"--trunk {trunk_override} names no commit in {repo}. Pass an existing "
             "branch, such as the one the agent's branch was based on.")
    merged = set(must(repo, "for-each-ref", fmt, f"--merged={trunk_ref}",
                      "refs/heads").splitlines()) if trunk_ok else set()
    names = [n for n in must(repo, "for-each-ref", fmt, "refs/heads").splitlines() if n]
    trunk_name = trunk_ref[len("refs/heads/"):] if trunk_ref.startswith("refs/heads/") else ""
    if trunk_name in names:
        names.remove(trunk_name)
        names.insert(0, trunk_name)

    lanes = [lane(repo, n, trunk, trunk_ref, merged, rebased, dirty_by_branch,
                  full, limit) for n in names]

    return {
        "schema_version": SCHEMA_VERSION,
        "repo": str(repo),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trunk": trunk,
        "squash_checked": full,
        "preflight": preflight(repo, top, trunk, remote, rhead, wts),
        "worktrees": wts,
        "lanes": lanes,
    }


def main() -> int:
    global GIT
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--full", action="store_true",
                    help="add squash detection (patch-id); use at integration, not mid-run")
    ap.add_argument("--trunk", default="", help="override trunk detection")
    ap.add_argument("--limit", type=int, default=COMMIT_LIMIT,
                    help=f"commits per lane (default {COMMIT_LIMIT})")
    a = ap.parse_args()

    GIT = shutil.which("git") or ""
    if not GIT:
        fail("git not found on PATH. Install git, or add the folder holding it to PATH.")
    repo = Path(a.repo).expanduser().resolve()
    if not repo.is_dir():
        fail(f"not a directory: {repo}. Pass the path of a folder inside a git "
             "working tree.")
    if not is_repo(repo):
        print(json.dumps({
            "schema_version": SCHEMA_VERSION, "repo": str(repo), "preflight": {
                "is_repo": False, "tiers_available": ["none"],
                "tiers_blocked": ["not a git repository: isolation is path-disjoint "
                                  "slices only"]},
            "worktrees": [], "lanes": []}, indent=2))
        return 0

    print(json.dumps(build(repo, a.trunk, a.full, a.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
