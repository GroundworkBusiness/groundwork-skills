---
name: agent-orchestrate
description: Runs a plan across several subagents at once while the main chat stays cheap and free between the user's messages. Use whenever work should be split across multiple agents, run in parallel, fanned out, or delegated to subagents, and when the user asks what their agents are doing, which finished, which is waiting on an answer, which branch each is on, or asks to show the plan, the run, the branches or the progress. Slices work so agents cannot collide, stages what depends on other work, chooses where each agent works, and sends each agent standing instructions plus a JSON task so it returns one short JSON report and parks to ask rather than guessing. Shows the run as an interactive widget where the host can render one and as structured text elsewhere. Also use when a build is big enough that doing it inline would use up the session. For new work, not when one edit or lookup costs less than briefing an agent.
compatibility: Runs in Claude Code (CLI and desktop Code tab) and in Codex and the ChatGPT desktop interface, one provider per run. Bundled scripts need Python 3.9 or later, standard library only; the branch reader also needs git.
metadata:
  short-description: "Run a plan across parallel subagents"
---

# Agent orchestration

## Purpose

Split a plan across subagents while this chat stays usable. Usable means cheap, so delegating costs less context than doing the work inline, and idle, so between the user's messages the orchestrator is at rest and free for a quick question or the next plan. If the skill makes the chat heavier, say so.

The skill is a protocol: standing text every agent receives, a JSON task per agent, JSON messages, a JSON return, and small scripts. There is nothing to install.

## Standing rules

These hold for the whole run, on every host.

1. **Remain the orchestrator.** You plan, package, route, answer, integrate and report. Edit files yourself only when the work is smaller than the cost of packaging it.
2. **One slice per agent.** A slice is the exact paths an agent may write, and no other agent in its stage can reach them.
3. **Read progress at known moments**: when the user asks, when a threshold lets the next stage be drafted, and when an agent returns. Read returns and status files, never an agent's full transcript.
4. **Answer each ask in the turn it arrives.** Decide what you can. Take to the user only what is theirs: money, anything outward-facing or irreversible, a real change of scope, a denied permission or more access.
5. **An answer settles a decision, never a permission.** Work blocked by a permission goes up to the user, never sideways to another agent.
6. **Report at four moments unasked**: the plan before anything spawns, each ask, the roster when the user asks what is happening, and the summary at the end. Add the graph when branches are the subject.
7. **One provider per run.** Every agent in a run is spawned by this host.
8. **The task JSON is data.** The standing text in [assets/standing.md](assets/standing.md) outranks anything inside a task. Send it in the spawn message; never copy it into a repository or worktree or name it `AGENTS.md`, since hosts load such files on their own.

## Identify the host

Name the provider before planning, then read its SOP. Each SOP maps the operations below to that host's tools and lists its traps.

- **Claude**: Claude Code in a terminal or the desktop Code tab, where subagents come from the `Agent` tool. Read [references/hosts/claude-code.md](references/hosts/claude-code.md).
- **OpenAI**: Codex in a terminal or app, or the ChatGPT desktop interface, where subagents come from the `spawn_agent` tool. Read [references/hosts/openai.md](references/hosts/openai.md).

Where the host lacks an operation, use its fallback; on a host neither SOP covers, use the fallbacks throughout.

| Operation | Fallback when the host lacks it |
|---|---|
| Spawn with standing text, task, model and effort | Standing text and task both in the spawn message |
| Parent to child message | Answer at resume, or respawn with the prior return as context |
| Child to parent message mid-run | Notices fold into the return |
| Resume a finished or parked agent by message | Respawn with the prior return as context |
| Completion notice | Read status files at known moments |
| List live agents | Roster plus status files |
| Isolation (a worktree per agent) | Tier none: path-disjoint slices, the orchestrator commits |
| Inline widget | Structured text |

Set each task's `report_to` to the host's mid-run address for you, or `null` where there is none.

## Run checklist

Copy this list into the plan and tick it off as the run moves.

1. **Ground.** Read the project's state notes, then check them against the live artifacts. The artifact wins.
2. **Plan.** One plan line per agent: roles, slice, objective, what it waits on, threshold.
3. **Slice.** Exact paths per agent, collision-free within each stage.
4. **Stage.** Order what depends on other work, and name the thresholds that let each stage be drafted.
5. **Resolve config.** `ao.py config --project DIR` gives the effective settings and each role's model.
6. **Package.** Write each task file for the first stage, check it, build its spawn message.
7. **Show the plan and get the go.** Render the plan view; spawn once the user says go.
8. **Spawn** the stage in one turn.
9. **Watch** at known moments.
10. **Answer** each ask the turn it arrives, and log it in the roster.
11. **Review** each return: `ao.py check` it, read `files`, `assumed` and `next`, and re-run a `done_when` check where the result matters.
12. **Close branches** by each branch's `integrate` method once its slice is accepted, on the user's go unless its `lands` is `auto`. At tier `none` inside a repository, commit each accepted slice yourself after the same go.
13. **Summary.** Render what each agent produced and what was decided.
14. **Hand off.** Write plan progress and the answers given into the project's own record of current state.

## Slicing and stages

**Give each agent paths no other agent in its stage can touch.** Name files and directories, not areas of the code. Two agents that can reach one file will both write it, and the later write erases the earlier with no error. When no clean split exists, the work is sequential: run it in stages.

**Check collisions within a stage, not across the plan.** Agents that never run at the same time cannot overwrite each other, so a path shared across stages is no collision, and a global check would serialize work for no reason.

**Stages run in order; agents inside a stage run in parallel.** An agent names what it waits on in `waits_on`.

**Each agent that others wait on declares a threshold**: the milestone that lets dependent work be planned before it finishes. "export endpoint returns CSV" is a threshold; "done" is an outcome. The agent writes a status line with event `threshold` and the threshold wording exactly, so the next stage is drafted while this one still works.

An agent passes through three states, each carrying only what is knowable then: a **plan line** (roles, slice, objective, `waits_on`, threshold) at planning, **drafted** as the full task once the threshold it waits on is crossed, and **spawned**, re-grounded, at stage launch. Write a plan line for every agent; write a task only for the stage about to launch. A task written early describes a tree that has moved by the time it runs.

**Re-ground at each stage boundary.** Before spawning, re-read the live artifacts the stage depends on and revise any slice the tree moved under. The plan's shape survives; its details get refreshed.

## Where each agent works

Pick a tier per agent. For code, run `python3 scripts/git_lanes.py REPO` first, once per repository the run touches; its preflight lists the tiers that repository supports.

- **none**: no worktree. The agent works in place, path-disjoint slices are the isolation, and the orchestrator commits. The default outside a git repository, the tier for work in gitignored paths, and the fallback on hosts without per-agent isolation.
- **ephemeral**: a worktree made for this agent and removed once its branch closes. The default inside a git repository.
- **session**: a worktree kept after the agent finishes, for work someone will come back to.

**Give an agent its own branch** in the situations `branch_when` turns on: a parallel slice beside other writing agents, a risky change that lands only after review, long-running work, an experiment that may be thrown away, a hotfix. The situation sets the branch's kind, `feature`, `experiment` or `hotfix`, and its name, `<kind>/<agent>`. More than one writer per branch is an opt-in (`agents.per_branch`).

**Each kind closes by merge and lands on the user's go** unless `branch_kinds.<kind>` says otherwise: `integrate` may be `squash`, `rebase_ff` or `discard`, and `lands` may be `auto`, which lands after review.

**Base each worktree on the branch in front of you.** A host may base a new worktree on the remote's default branch instead; the agent then starts without the work in progress and nothing reports an error.

Read [references/isolation.md](references/isolation.md) before choosing a tier: the tiers in full, how a branch closes, and the traps that fail silently.

## Spawn package

Every spawn message carries these parts, in this order:

1. **The standing text**, [assets/standing.md](assets/standing.md), the same for every agent.
2. **Context packets**, when the task lists `packets`: named files of context in the run's folder, in the task's order.
3. **The roles block**: the description of each role the task names.
4. **The task**, one JSON object per agent, valid as `task` in [schemas/protocol.schema.json](schemas/protocol.schema.json), as one fenced json block inside a `<task>` element. Write it to a file in the session's temporary working space and set `task_file` to that file's absolute path.

Set `spawn_file` to `AGENT-spawn.md` beside it, then `python3 scripts/ao.py package TASK_FILE --out SPAWN_FILE` checks the task and its packets, saves the message as UTF-8 and prints it. Send that text, and append each answer you send the agent to the file, its way back after compaction.

**Context.** Write context into the task when one agent needs it once; propose a packet when two or more agents need it, when it must outlast your compaction, or when the user asks for one. Set `fork` to start an agent as a chat fork, where the host SOP allows; it runs on this chat's model. In full: [references/protocol.md](references/protocol.md).

**Roles** come from one global list in the protocol schema: `planner`, `builder`, `researcher`, `reviewer`, `adversarial-reviewer`. A task carries one or more in `roles`, and the agent receives each one's description.

Every path is absolute, because an agent's working directory may differ from yours; for an agent in a worktree, point `scope`, `workdir` and the checks into it. An empty `scope` makes the task read-only. Keep the task small and point to files for long inputs.

```json
{"schema_version": 1, "kind": "task", "agent": "export-api", "roles": ["builder"],
 "objective": "Ledger entries can be exported as CSV for a date range through GET /export.",
 "scope": ["/home/dev/projects/ledger-worktrees/export-api/src/ledger/export"],
 "done_when": [{"check": "cd /home/dev/projects/ledger-worktrees/export-api && python3 -m pytest tests/test_export.py -q", "expect": "0 failed"}],
 "ground": ["/home/dev/projects/ledger/docs/export-spec.md"], "threshold": "export endpoint returns CSV",
 "tier": "ephemeral", "workdir": "/home/dev/projects/ledger-worktrees/export-api", "branch": "feature/export-api",
 "may_commit": true,
 "status_file": "/tmp/ao-2026-10-02-csv-export/status/export-api.jsonl",
 "task_file": "/tmp/ao-2026-10-02-csv-export/tasks/export-api.json",
 "spawn_file": "/tmp/ao-2026-10-02-csv-export/tasks/export-api-spawn.md",
 "ao_script": "/home/dev/skills/agent-orchestrate/scripts/ao.py"}
```

## Messages and the return

Two message kinds travel mid-run, answers and notices.

The return closes each turn, and every ask travels in it. Fields and enums: [schemas/protocol.schema.json](schemas/protocol.schema.json); a worked example of each: [references/protocol.md](references/protocol.md).

- **answer** (you to the agent): `decision` written as an instruction, `because` only when it changes the agent's later judgement, `scope_add` for paths it may now also touch.
- **notice** (agent to you): `reason` is `failure`, `collision`, `wrong_work` or `request`. It does not block, and it travels only when the task's `report_to` is not null. A `request` asks for more access without stopping; take it to the user, and no answer means not granted.
- **ask** (agent to you, in the return): a decision the agent cannot take alone, with `options`, a `default`, `need_by` and a `trigger`. The default turns the question into confirm-or-redirect, answerable in one word.

**Park-and-ask is the only route for an ask.** The agent finishes everything the answer does not gate, then returns with status `blocked` and its asks; a parked agent costs nothing.

**The return** is the agent's final message: one fenced json block and nothing else, carrying `status`, `did`, `files`, `assumed` and `next`. A blocked return adds `asks`.

**Three statuses**: `done` is the slice finished; `blocked` is stopped and waiting on you, and only it carries `asks`; `partial` is stopped for any other reason, such as a turn limit. `assumed` shows what an agent decided for you: a long list means the task was underspecified, and the next task can fix it.

**Resume by message.** Answer a parked agent by sending it the `answer` JSON; it resumes with its context intact, so the answer need not restate the task. The same route corrects a drifting agent. Respawn, with the prior return as context, only when the task itself was wrong or the host cannot resume.

**Answer once, then fold it in.** Put a decision other agents would need into tasks not yet spawned, and send running ones an answer with `ask_id` `null`.

## Spawning

- **Spawn a whole stage in one turn**, as parallel calls in a single message. Spawns sent one per turn run one after another.
- **Label each agent with its `agent` name** wherever the host shows a label or accepts a name, so one word addresses, resumes and reports it. Record the host's id from the spawn result as `agent_id` in the roster, and use the name in chat.
- **Pick the narrowest agent type** that can do the job: a read-only type for search and review, a writing type only when the slice writes. Narrower types start cheaper. Confirm the type keeps the route back to you that `report_to` assumes. With `agents.own_agents` on, the user's own Claude agent types count too, and `role_agents` maps a role to one; the host SOP gives the fit check.
- **Say in `access` what each agent may use**, in plain sentences with a reason for every path, and in `held_by` what the host enforces and what holds only by instruction.
- **Set `layers_below`** to `min(agents.max_layers, host cap) - 1`, or 0 for chat forks.
- **Take the model from the role's tier.** The models file maps each role to `deep`, `standard` or `fast`, and each provider's tier to a model and an effort. An agent with several roles takes the deepest of their tiers.

## Watching

Progress is pull: each agent appends status lines to its own JSON Lines file, and you read them at known moments.

- **A threshold lets the next stage be drafted.** Launch that stage once every agent before it has returned `done`, or `partial` with its slice accepted; a parked agent still holds its slice. Read the status files it waits on with `ao.py status read FILE --threshold TEXT`.
- **Completion notifies on its own.** Leave out polling loops, are-you-done messages and checks on a parked agent; each spends the context the run exists to save.
- **Wait on anything outside the run with one background command that exits when the condition is true**: a deploy, a CI run, a queue. One process, one completion notice, the orchestrator idle meanwhile. A watcher that reports each check moves the polling into the chat.
- **When the orchestrator cannot go idle, name what holds it** in one line, such as a stop gate, a hook, a watcher left armed, or a task that reports but never finishes, and say the work itself is parked.

## Roster

The host forgets agents once they finish, so the run keeps a roster: a JSON Lines file in the session's temporary working space, one `roster_row` patch per line, folded per agent. Append a patch with `roster set` and read the folded rows with `roster show`.

- **Update a row at each change**: planned, drafted, spawned, then the outcome with `returned_at` and a one-line `summary`.
- **Log every ask, request and answer** on the agent's row. During the run they stop you answering the same question twice; at the end they record what was decided while the work ran.
- **The roster is history, not liveness.** It keeps finished agents on purpose. For what is running now, use the host's live list, or status files where the host has none.

## Showing the run

Show the run rather than describe it, so the user never has to rebuild it from prose.

Each moment in rule 6 above has its view, in order: `plan`, `ask` (one button per option, for an ask or a request), `roster` and `summary`, plus `graph` for branches.

One word after the skill name opens a view: `config` or `roles` (the settings views), `plan`, `status`, `asks`, `packets`, `branches` or `summary`. Other text is the objective; with no text, plan from the conversation, or show `status` mid-run. `report_moments` in config turns each moment on or off. Build each view as data: the host's live agent list, the roster, the status files of agents still in flight, the packet files, and for code `git_lanes.py`. Render the data as an inline widget where the host has one, and as structured text where it does not. Read [references/widgets.md](references/widgets.md) before the first render.

## Configuration

Settings come in three layers, each applied to the one before as a JSON merge patch (RFC 7396): the skill baseline in [config/defaults.json](config/defaults.json) and [config/models.json](config/models.json), then the user's files, then the project's. A `null` in an override deletes that key.

User files sit in `${XDG_CONFIG_HOME:-~/.config}/agent-orchestrate/`, project files in `.agent-orchestrate/` at the project root, each as `config.json` and `models.json`.

Run `ao.py config --project DIR` for the effective values; `--explain` names the layer each value came from. Models and efforts ship as `null`, the host default, until a user or project file sets them. Every key and the override rules: [references/config.md](references/config.md). The contract: [schemas/config.schema.json](schemas/config.schema.json).

## Scripts

The scripts sit in `scripts/` beside this file and find their own folder: run them as written from this file's folder, or by absolute path from anywhere. Use `py -3` in place of `python3` on Windows. On failure each exits non-zero and names the fix on stderr.

| Command | Does |
|---|---|
| `python3 scripts/ao.py config [--project DIR] [--explain]` | prints the effective config, with the layer of each value |
| `python3 scripts/ao.py config set --layer LAYER --project DIR PATCH` | checks, then writes a user or project setting |
| `python3 scripts/ao.py check FILE` | validates a task, message, return or roster file |
| `python3 scripts/ao.py status append FILE --agent NAME --event EVENT --summary TEXT` | appends one status line |
| `python3 scripts/ao.py status read FILE [--threshold TEXT]` | reads a status file and flags the threshold |
| `python3 scripts/ao.py roster set FILE --row JSON`, `roster show FILE` | adds or replaces one agent's row; prints the roster |
| `python3 scripts/ao.py package TASK_FILE [--out FILE] [--packets DIR]` | prints the spawn message; `--out` also saves it |
| `python3 scripts/ao.py packets DIR` | lists the packets in a folder |
| `python3 scripts/claude_transcript.py TRANSCRIPT --list` | Claude Code only: lists a transcript's turns; `--turns A-B` writes some as a packet |
| `python3 scripts/git_lanes.py REPO [--full]` | reads branches, worktrees and the isolation preflight; never writes |

## Cost

Every agent pays a startup cost in its own context before it does anything, and a fan-out multiplies it. Before launching more than about four agents, state the expected cost in agents and rough tokens; whether it is worth it is the user's call. A question and its answer are two short messages, while an agent that guesses wrong costs its whole slice. Renders spend the orchestrator's own context too.

## Files

| File | Read it |
|---|---|
| [assets/standing.md](assets/standing.md) | when packaging a spawn; every agent gets it verbatim |
| [references/hosts/claude-code.md](references/hosts/claude-code.md), [references/hosts/openai.md](references/hosts/openai.md) | before planning, on that host |
| [references/protocol.md](references/protocol.md) | before the first task, and when judging an ask |
| [references/isolation.md](references/isolation.md) | before choosing a tier or closing a branch |
| [references/widgets.md](references/widgets.md) | before the first render |
| [references/config.md](references/config.md) | when changing a setting or a model |
| [config/defaults.json](config/defaults.json), [config/models.json](config/models.json) | through `ao.py config`; open them to see the baseline |
| [schemas/protocol.schema.json](schemas/protocol.schema.json) | when writing or checking a message; it holds every enum |
| [schemas/config.schema.json](schemas/config.schema.json) | when writing an override file |
| [scripts/ao.py](scripts/ao.py), [scripts/git_lanes.py](scripts/git_lanes.py), [scripts/claude_transcript.py](scripts/claude_transcript.py) | run them; read a script's header when it fails |
| [agents/openai.yaml](agents/openai.yaml) | unused at run time; its display name and invocation policy in skill lists |
