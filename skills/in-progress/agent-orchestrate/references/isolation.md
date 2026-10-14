# Where each agent works

Isolation conventions differ per repository, and a fixed rule would be wrong somewhere. So this is
a preflight, not a policy: read what the repository is, then pick from what it supports. Read this
file before choosing a tier for any agent that writes, and again when its branch closes.

## Contents

- The preflight
- Preflight fields
- Worktree fields
- The three tiers
- When an agent gets its own branch
- Agents per branch
- How a branch closes
- Traps that fail silently
- The repository's own conventions

## The preflight

Run the read-only git reader from the skill folder, once per repository the run touches, with the
path of any folder inside it:

```text
python3 scripts/git_lanes.py REPO
```

It prints one JSON object with three parts: `preflight` (what the repository supports), `worktrees`
(every working tree and what it carries) and `lanes` (one per branch, for the graph view in
[widgets.md](widgets.md)). It fetches nothing, writes nothing and leaves the index untouched, so it
is safe to run at any moment. Add `--full` when branches close or a squash needs confirming; squash
detection is the one slow check.

Outside a git repository the preflight is short, and tier `none` is the only choice:

```json
{
  "schema_version": 1,
  "repo": "/home/dev/notes",
  "preflight": {
    "is_repo": false,
    "tiers_available": ["none"],
    "tiers_blocked": ["not a git repository: isolation is path-disjoint slices only"]
  },
  "worktrees": [],
  "lanes": []
}
```

## Preflight fields

Inside a repository the preflight carries every field below.

- `is_repo`: true when the path is inside a git working tree. When false, the preflight carries
  only `is_repo`, `tiers_available` and `tiers_blocked`.
- `head_branch`: the branch checked out where you ran the reader, which is the work in front of
  you. Empty when HEAD is detached.
- `trunk`: the branch work integrates into, from the remote's HEAD, else a local `main`, `master`
  or `trunk`, else the current branch. `--trunk NAME` sets it. Each lane's ahead and behind counts
  are measured against it.
- `commits`: the number of commits reachable from HEAD. Zero rules out every worktree tier.
- `remote`: the URL of the reported remote, with any user name and password removed. Empty when the
  repository has no remote.
- `remote_name`: the reported remote: `origin` when it exists, else the push default, else the
  first listed.
- `remote_head`: the remote's default branch as this clone records it, such as `origin/main`.
  Empty when the clone has no record of it.
- `size_mb`: the size of the git object store in MB, loose and packed objects together, not the
  working tree. Worktrees share one object store, so this does not grow per agent; it is for
  information.
- `origin_head`: the same as `remote_head` when the reported remote is named `origin`, else empty.
- `commits_not_on_remote_default`: the number of commits on HEAD that `remote_head` lacks, an
  integer. A worktree based on the remote's default branch starts without those commits, so a
  count above zero is work in progress that an agent there would not see. Null when `remote_head`
  is empty, since there is nothing to count against. The reader reads git alone and no host's
  settings; how each host picks the base of a new worktree is in its SOP
  ([Claude](hosts/claude-code.md), [OpenAI](hosts/openai.md)).
- `worktreeinclude`: true when the repository root has a `.worktreeinclude` file, which some hosts
  read to copy named gitignored files into a new worktree.
- `worktreeinclude_note`: one line on what a new worktree will lack when there is no such file.
- `tiers_available`: the tiers this repository supports. Offer only these in the plan.
- `tiers_blocked`: each tier it cannot support, with the reason. Show these in the plan as
  unavailable, so the reader learns what is impossible here and why.
- `worktrees_locked`: paths of locked worktrees, each held by another tool or session.
- `worktrees_prunable`: paths of registered worktrees whose directory no longer exists.

## Worktree fields

Each entry in `worktrees` describes one working tree, the main one first.

- `path`: the absolute path of the working tree.
- `branch`: the branch checked out there. Empty when HEAD is detached.
- `head`: the short commit id of its HEAD.
- `detached`: true when HEAD is detached.
- `locked`: true when the tree is locked. Some hosts lock an agent's worktree while the agent runs,
  which makes the lock a second sign of a live agent.
- `prunable`: true when the directory is gone and only the registration remains.
- `note`: the reason given with the lock or the prunable state, when there is one.
- `dirty_count`: the number of changed and untracked paths in the tree. Null when the status query
  fails.
- `dirty`: true when `dirty_count` is above zero. Null when the directory is gone or the status
  query fails or times out, which means unknown rather than clean.
- `error`: present when a query on this tree failed, saying which and what is unknown as a result.
- `rebased`: commits that this tree's own reflog records as the result of a rebase. It is local
  evidence and expires with the reflog, so an empty list means not recorded.

## The three tiers

**none**: no worktree. The agent works in place, in the project folder, on whatever branch is
checked out, and the orchestrator commits (`may_commit` false). Nothing enforces the boundary, so
the scope is the boundary: give each agent paths no other agent in its stage can reach. It fits
work outside a git repository, every read-only agent (researchers and reviewers with an empty
scope), several writing agents with separate, path-disjoint responsibilities on the current branch,
a lone writing agent with a low-risk change, a slice whose scope lies in gitignored paths, which git
never commits, so there is nothing to commit afterwards, a repository with no commits, and any host
without per-agent isolation. It is the default outside a git repository
(`default_tier.outside_git_repo`).

**ephemeral**: a worktree made for this agent on its own branch, removed once the branch closes.
It fits a writing agent that runs beside other writing agents, or whose change should land only
after review. It is the default inside a git repository (`default_tier.in_git_repo`).

**session**: a worktree kept after the agent finishes, so a later session can resume in the same
tree on the same branch. It fits long-running work, an experiment someone will inspect before
deciding its fate, and any slice a person will come back to.

For a writing agent on the ephemeral or session tier, create the worktree yourself before you
write its task, with `git -C REPO worktree add -b BRANCH PATH BASE`, where REPO is the repository
the agent's slice is in, naming the base explicitly. You, the orchestrator, run these commands and
the clean-up below; the user approves the plan and each merge. Then set the task's `workdir` to
`PATH`, and point its `scope` and `done_when` checks at absolute paths inside it. A host's own
isolation option makes the worktree only at the spawn, after the task is written, so the task
cannot name it; the host SOP says where that route still fits. Put worktrees you create outside the
main working tree, such as in a sibling folder, so they never show up there as untracked files.

## When an agent gets its own branch

An agent that writes inside a git repository gets a branch of its own, and with it a worktree,
when one of the situations in `branch_when` holds and that situation is turned on in config:

- **parallel_slice**: the slice runs beside other writing agents in the same repository.
- **risky_change**: the change could break shared work, so it lands only after review.
- **long_running**: the work spans more than one stage or sitting and needs its own line of
  history.
- **experiment**: the outcome is uncertain and the work may be thrown away.
- **hotfix**: an urgent fix that lands on its own, apart from work in progress.

Each situation gives the branch a kind: `parallel_slice`, `risky_change` and `long_running` give a
`feature` branch, `experiment` an `experiment` branch, and `hotfix` a `hotfix` branch. Record the
situation on the agent's roster row as `branch_reason` and the kind as `branch_kind`; the kind picks
how the branch closes and lands. An agent that only reads needs no branch. A writing agent with no
situation that holds, or whose situation is turned off, works at tier `none` on the current branch,
and its slice shares no path with any other agent in its stage.

Before giving a writing agent a worktree, check with `git -C REPO check-ignore -q PATH` every path
its work will produce, including paths inside a folder in its scope, writing a folder with a
trailing slash, such as `notes/`; the command exits 0 when git ignores the path. A slice with an
ignored deliverable runs at tier `none`.

An agent on a worktree tier works in one repository, since a task carries one `workdir` and one
`branch`. Give a slice that spans repositories one agent per repository, or run it at tier `none`,
where you commit in each repository.

Name each branch `<kind>/<agent>`, such as `feature/export-api`, unless the repository has a
convention of its own.

## Agents per branch

On the ephemeral and session tiers, a writing agent works on exactly one branch, and by default a
branch carries one agent at a time (`agents.per_branch`, default `1`). Git enforces part of this on
its own: a branch can be checked out in only one worktree at a time. At tier `none`, agents share
the checked-out branch with path-disjoint scopes, and the orchestrator owns every commit and branch
change. An agent and the agents it spawns count as one writer on its branch: it coordinates them,
and their scopes lie inside its own.

**A shared branch** is the opt-in for more: `agents.per_branch` above `1` lets that many writing
agents work on one worktree branch at once, and so in one working tree. It is the riskier mode,
since nothing but their scopes keeps them apart. Inside that tree they follow the tier `none` rules:
scopes that share no path, checked by the plan's collision verdict; `may_commit` false for each of
them; and you commit each accepted slice yourself. Give each the same `workdir` and `branch`, and
mark the branch as shared in the plan. Every agent on a shared branch carries the same
`branch_kind`, `integrate` and `lands`; settle a difference in the plan before launch. At close, a
missing or differing `lands` among them means ask. The branch closes once, after every agent on it
has returned and each slice is accepted.

A later agent may continue a branch once the agent before it has returned `done`, or `partial` with
its work accepted, such as a builder fixing a reviewer's findings on the same branch. A parked agent
keeps its branch until you release it. Only the orchestrator sees across branches, so it decides
every hand-over between agents on one branch.

## How a branch closes

Every branch closes by one method and lands one way, both set by its kind: take the method from
`branch_kinds.<kind>.integrate` and the landing from `branch_kinds.<kind>.lands` for the agent's
`branch_kind`. Both ship as `merge` and `ask` for every kind. Show them for each agent in the plan
and record them on its roster row as `integrate` and `lands`; a different value for one agent is a
plan-time choice the user sees.

- **merge**: merge the branch with a merge commit, keeping its history (`git merge --no-ff BRANCH`).
- **squash**: land the branch as one commit on the target (`git merge --squash BRANCH`, then
  commit).
- **rebase_ff**: rebase the branch onto the target inside its own worktree
  (`git -C PATH rebase TARGET`), then fast-forward the target (`git merge --ff-only BRANCH`).
- **discard**: close the branch without integrating it. The return and its `report` carry what was
  learned.

Close each branch in this order:

1. **Review.** Check the return with `ao.py check`, read its `files`, `assumed` and `next`, and
   re-run a `done_when` check where the result matters. A reviewer's `revise` verdict goes back to
   the branch before it closes.
2. **Get the go.** A branch whose roster `lands` is `auto` lands after review without asking. For
   `ask`, show the user the branch in the summary view (the review's verdict, `files`, `assumed`
   and the method) and integrate on their go. The same go covers the commit you make for an
   accepted slice at tier `none` inside a repository, since it lands on the branch in front of the
   user. The plan may set `lands` to `auto` for a branch whose work touches no production code,
   such as notes, docs or test data, and the user's go on the plan covers it. When a row carries no
   `lands`, ask.
3. **Integrate** into the branch the agent's branch was based on, from the working tree where that
   branch is checked out (`git -C REPO worktree list` shows it), using the method above with
   `git -C TREE`. Confirm that tree's current branch is the target first. When no working tree has
   the target checked out, check it out in the repository's main working tree.
4. **Confirm** with `python3 scripts/git_lanes.py REPO --trunk TARGET --full`, where TARGET is
   the branch you integrated into. After `merge` or `rebase_ff` the fate must read `merged`; after
   `squash`, `squashed`, with the `proof` behind it. A `rebased` fate alone is not proof of
   integration. After `discard`, skip this step and confirm the return holds everything worth
   keeping.
5. **Clean up.** For ephemeral, remove the worktree with `git -C REPO worktree remove PATH`, then
   delete the branch with `git -C REPO branch -d BRANCH`, which deletes a merged branch and refuses
   one that is not; a squashed or discarded branch is never an ancestor of the target, so it takes
   `git -C REPO branch -D BRANCH`, after you confirm the return holds everything worth keeping. For
   session, keep the worktree and the branch, and write where they are in the roster row's
   `summary`.
6. **Record** the outcome on the roster row.

Close branches one at a time, in stage order. When an integration conflicts, resolve it before the
next branch closes. Two slices from one stage that conflict were not disjoint, which is worth
noting against the plan.

## Traps that fail silently

Each of these ends with an agent working on the wrong thing and nothing reporting an error.

**A new worktree may start from the remote's default branch instead of the current work.** Some
hosts base a new worktree on the remote's default branch, fetching it first, rather than on the
branch in front of you. An agent in that worktree never sees the work in progress, including
commits not yet pushed, and the loss appears only at integration. Each host SOP
([Claude](hosts/claude-code.md), [OpenAI](hosts/openai.md)) says how its host picks the base and how to
point it at the current work. Read `commits_not_on_remote_default` in the preflight: above zero, a
worktree based on the remote's default branch misses that many commits, so point the host at the
current branch, or create the worktree yourself and name the current branch as its base.

**A worktree carries no gitignored files.** A new worktree is a fresh checkout, so environment
files, virtual environments and installed dependencies are absent, and an agent that needs to run
anything starts broken. Give the agent a setup step in its task, as its first `done_when` check or
in `notes`, and expect it to spend time on it. Where the host copies named ignored files into a new
worktree (the `worktreeinclude` field), the host SOP says how. Nothing written to an ignored path
comes back either: git never commits it, neither `git status` nor the reader's `dirty` shows it, and
`git worktree remove` deletes it without a warning.

**Uncommitted work does not travel.** A worktree checks out a commit, so staged changes, unstaged
changes and untracked files in the main working tree are not in it. Commit what the agent needs
before the spawn, with the user's go when the work is theirs, or run that slice at tier `none`.

**A locked or prunable worktree belongs to its owner.** A locked tree is held by another tool or
session: leave it as it is, and plan around its branch. A prunable one is a registration whose
directory is gone: report it in the plan, and leave the pruning to the repository's owner.
`git worktree list --porcelain` is the view that shows both, and the reader reports them in
`worktrees_locked` and `worktrees_prunable`.

## The repository's own conventions

Follow the convention a repository already has. Read its existing worktrees and where they live, its
branch names, its `.gitignore`, and whether it has a `.worktreeinclude`, and match what you find.
Where there is no convention, propose one in the plan and use ephemeral worktrees meanwhile.

Write a durable convention (an include file, a host setting, a `.gitignore` entry) only when the
user asks for it. These outlive the run, and a run leaves behind only configuration somebody chose.

## Related

- [SKILL.md](../SKILL.md): the run checklist, where the tier is chosen per agent.
- [git_lanes.py](../scripts/git_lanes.py): the reader behind the preflight and the graph.
- [config.md](config.md): `branch_when`, `branch_kinds`, `agents.per_branch` and `default_tier`.
- [defaults.json](../config/defaults.json): their shipped values.
- [protocol.md](protocol.md): the `tier`, `workdir`, `branch` and `may_commit` fields on a task, and
  `branch_reason`, `branch_kind`, `integrate` and `lands` on a roster row.
- [widgets.md](widgets.md): the plan view's tier column and the branch graph.
- [hosts/claude-code.md](hosts/claude-code.md) and [hosts/openai.md](hosts/openai.md): how each host makes a
  worktree and picks its base.
