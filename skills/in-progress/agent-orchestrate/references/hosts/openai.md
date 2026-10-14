# OpenAI host SOP

How an orchestrator running in Codex maps each host-neutral step of the skill to this host's tools.
It covers the Codex CLI and the Codex bundled inside the ChatGPT desktop app. Checked against
`codex-cli` 0.157.1 and the Codex 0.159.2 that the desktop app bundles; recheck a fact before
relying on it after an upgrade, and treat everything under "Not yet verified" as open.

## Contents

- How to tell you are on this host
- Operations
- Delivering the standing text and the task
- Models and effort
- Isolation
- Watching and completion
- Resuming and correcting an agent
- Showing the run
- Running the skill's scripts and where a standalone skill is discovered
- Traps
- Not yet verified
- Related

## How to tell you are on this host

- **The provider.** Your tools include `spawn_agent`, either as a direct tool in the `collaboration`
  namespace or, on some models, only inside `functions.exec` as `tools.multi_agent_v1__spawn_agent`.
  That is Codex.
- **The surface.** The ChatGPT desktop app (bundle id `com.openai.codex`) bundles its own Codex binary
  at `Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`, separate from the `codex` CLI
  on PATH, and the two versions can differ. Their multi-agent tool definitions were identical in the
  versions checked, so the operations below hold on both unless an entry says otherwise.
- **The multi-agent tool surface, v1 or v2.** Codex ships two sets of multi-agent tools. Detect which
  one this session has before writing any task; the first entry under "Operations" says how.

## Operations

Each entry below is one row of the capability table in [SKILL.md](../../SKILL.md). Every entry
depends on the tool surface, so detect it first.

**Detect the tool surface from the tool names present.**

| Surface | Tools present |
|---|---|
| v2 | `spawn_agent` (input `task_name`, `message`, `fork_turns`), `send_message`, `followup_task`, `wait_agent`, `list_agents`, `interrupt_agent`, as direct tools in the `collaboration` namespace |
| v1 | `spawn_agent` (input `message` or `items`, `fork_context`), `send_input`, `resume_agent`, `wait_agent`, `close_agent`; on models whose `tool_mode` is `code_mode_only`, these exist only inside `functions.exec`, as `tools.multi_agent_v1__<name>(...)` |

- `send_message`, `followup_task` or `list_agents` present: v2.
- `send_input`, `resume_agent` or `close_agent` present, directly or as `tools.multi_agent_v1__*`
  inside `functions.exec`: v1.

The session model decides the surface: its catalog entry's `multi_agent_version` (`codex debug models`
prints it, with `tool_mode`, for each model). A model whose catalog entry has no
`multi_agent_version` is expected to follow the `features.multi_agent_v2` flag (inferred, not
observed); the flag is stable and off by default. The catalog
wins over the flag: `--disable multi_agent_v2` leaves a v2 model on v2.

### Spawn with standing text, task, model and effort

- **v2:** `spawn_agent` with `{task_name, message, fork_turns, model?, reasoning_effort?}`.
  - `task_name`: lowercase letters, digits and underscores only; anything else fails with
    `agent_name must use only lowercase letters, digits, and underscores`. Derive it from the task's
    `agent`: lowercase it, replace every character outside a-z, 0-9 and _ with an underscore, and
    rename an agent whose result would be `root`, which is reserved (`export-api` becomes
    `export_api`).
  - `message`: the whole text `ao.py package` prints (see the next section).
  - `fork_turns`: `"none"` when the task's `fork` is false, and `"all"` when it is true, which
    spawns a chat fork: a copy of the whole parent conversation, then the message. After a
    compaction, plan for a fork that sees the summary and the turns since; exactly what a fork
    inherits then is unverified on this host, so put any earlier detail the agent needs in its task
    or a packet. It takes `"none"`, `"all"` or a positive integer string, and defaults to `"all"`.
    Pass no number: which end of the conversation a number counts from is unverified.
  - The call returns `{"task_name": "/root/<name>"}`; record that value as `agent_id` in the roster.
  - The call works as a direct tool only; it cannot be made from inside `functions.exec`.
- **v1:** `spawn_agent` with `{message, fork_context, model?, reasoning_effort?}`, where
  `fork_context` matches the task's `fork`: false for a fresh agent, true for a chat fork. Pass
  `message` and leave `items` out, since the call takes one or the other. The call returns
  `{agent_id, nickname}`; record `agent_id`. On a `code_mode_only` model, make the call inside
  `functions.exec` as `tools.multi_agent_v1__spawn_agent({...})`.
- **Agent types:** neither schema exposed `agent_type` in testing, and the spawn descriptions listed
  no roles, so spawn every agent as the default type. The task's `scope` is what keeps a reviewer
  read-only. Codex's spawn takes no agent type, so `agents.own_agents` and `role_agents` have no
  effect on this host, and the settings views hide them.
- **Access:** every child inherits the parent's sandbox (see "Isolation (a worktree per agent)"),
  and the spawn takes no agent type, so nothing narrows one agent's tools. A task's `access` holds
  by instruction on this host, and its `held_by` says so, such as "Every agent shares this
  session's sandbox, so its tools, read paths and network use hold by instruction."
- **Permission to spawn:** the host forbids spawning unless the user, or applicable AGENTS.md or
  skill instructions, explicitly ask for sub-agents, delegation or parallel agent work. This skill's
  own instructions are such a request. On v1 the spawn description adds that a request for depth,
  research or analysis does not count. Word the plan's go question as "Spawn these N sub-agents?",
  so the user's yes names sub-agents too.
- **Limits:** on v2 the cap is `features.multi_agent_v2.max_concurrent_threads_per_session`, and the
  host's hint counts the root among the active agents. The documented
  `[agents] max_concurrent_threads_per_session` (alias `agents.max_threads`) excludes the primary
  thread, and Codex chooses a value when it is unset. Spawn in waves under the cap. Nesting has a
  cap on v1 only (see "Traps"); on v2, `agents.max_layers` holds by instruction alone.
- **Fallback:** standing text and task both in the spawn message, which is how this host carries
  them anyway. Where `spawn_agent` is absent altogether, run one process per agent:
  `codex exec -C <dir> -m <model> -c model_reasoning_effort=<effort> -s workspace-write --json -o <file> "<message>"`.

### Parent to child message

- **v2:** `send_message` with `{target, message}`. It starts no turn; the child sees the message at
  its next model step (observed). `target` takes the
  relative name (`<name>`) or the canonical one the spawn returned (`/root/<name>`) interchangeably.
- **v2, at once:** `interrupt_agent` with `{target}` stops the child's current turn and returns
  `{"previous_status": "running"}`; `list_agents` then shows it `interrupted`. Follow with
  `followup_task` to give it the new direction.
- **v1:** `send_input` with `{target, message, interrupt?}`, where `target` is the `agent_id`. It
  returns `{"submission_id": "..."}`. `interrupt: true` interrupts the current task and handles the
  message immediately.
- **Fallback:** answer at resume, or respawn with the prior return as context.

### Child to parent message mid-run

- **v2:** the child calls `send_message` with `target` `/root` (or the parent's canonical name). The
  root receives it as its own block, `Message Type: MESSAGE` with `Task name`, `Sender` and
  `Payload`, ahead of the child's final answer. Every v2 child holds the full collaboration tool set.
- **v1:** no tool that addresses the parent appeared in a v1 child's tool list, so treat the child's
  final answer as its only channel.
- **`report_to`:** `"/root"` on v2, when you are the root session; `null` on v1.
- **Fallback:** notices fold into the return.

### Resume a finished or parked agent by message

- **v2:** `followup_task` with `{target, message}`, the message carrying the answer. It starts a new
  turn with the agent's history, for a completed agent and for an interrupted one alike. It takes
  non-root targets only. v2 has no close or resume tool.
- **v1:** three calls in order, the sequence verified: `close_agent` with `{target}` (returns
  `{"previous_status": {"completed": "..."}}`), then `resume_agent` with `{id}` (returns
  `{"status": "pending_init"}`), then `send_input` with the answer. The agent continues with its
  history.
- **Fallback:** respawn with the prior return as context.

### Completion notice

- **v2:** a child's final message arrives as its own block: `Message Type: FINAL_ANSWER`, with
  `Task name`, `Sender` (`/root/<name>`) and `Payload` (the return). `wait_agent` with
  `{timeout_ms?}` blocks until a child finishes, any message arrives, new input arrives or the
  timeout passes. It returns no content: only a short summary such as `Wait completed.`,
  `Wait interrupted by new input.` or `Wait timed out.` (possibly with a timeout-adjustment note),
  plus `timed_out`, as in `{"message": "Wait completed.", "timed_out": false}`. Read the return
  from the `FINAL_ANSWER` block. The timeout's default and bounds come from
  `features.multi_agent_v2.{default,min,max}_wait_timeout_ms`.
- **v1:** `wait_agent` with `{targets, timeout_ms?}` (default 30000, minimum 10000, maximum
  3600000) returns each target's status, such as
  `{"status": {"<agent_id>": {"completed": "<final message>"}}, "timed_out": false}`, followed by an
  automatic `subagent_notification`. The statuses are `pending_init`, `running`, `interrupted`,
  `shutdown`, `not_found`, `{"completed": string or null}` and `{"errored": string}`.
- **Fallback:** read status files at known moments.

### List live agents

- **v2:** `list_agents` with `{path_prefix?}` returns
  `{"agents": [{"agent_name": "/root", "agent_status": "running"}, {"agent_name": "/root/<name>", "agent_status": {"completed": "..."}}]}`.
  It lists the root too and keeps completed agents, so read `agent_status` for liveness.
- **v1:** no list tool.
- **For the user:** `/agent` or `/subagents` in the CLI switches between agent threads, and
  `codex agents` browses all agent sessions on the shared local app-server daemon. The desktop docs
  show a Subagents panel in an illustration only. The read-only Active and Done lists are
  documented for ChatGPT Work on the web.
- **Fallback:** roster plus status files.

### Isolation (a worktree per agent)

- **Both surfaces:** no per-agent isolation. All agents share the parent's directory, and edits one
  makes are visible to the others at once. Children inherit the parent's sandbox.
- **Fallback:** tier none: path-disjoint slices, the orchestrator commits.

### Inline widget

- **Both surfaces:** no widget tool appeared in any tool list checked.
- **Fallback:** structured text.

## Delivering the standing text and the task

`python3 scripts/ao.py package TASK_FILE` checks the task and its packets and prints the spawn
message as plain text, in up to four parts:

1. **The standing text**: [assets/standing.md](../../assets/standing.md) without its `## Related`
   section.
2. **The context packets** the task lists, each in a `<packet>` element, when it lists any.
3. **The roles block**: `## Your role` (or `## Your roles`), then one list line per role on the task,
   each with that role's description from the protocol schema.
4. **The task**: a `<task>` element holding the task object as one fenced json block.

The same task sits at the absolute path in `task_file`; `package` refuses a task whose `task_file`
names a different file.

**On this host, put the whole printed text, unchanged, in `spawn_agent`'s `message`,** on v2 and v1
alike. A spawned subagent has no standing-text slot that a standalone skill can fill: a custom
agent's `developer_instructions` needs a file written in `~/.codex/agents/` or `.codex/agents/`, and
`-c developer_instructions=...` is a launch-time override of a whole `codex` or `codex exec`
process. A running session cannot set it per spawn, which leaves it no channel for in-session
subagents. The spawn message therefore carries every part.

**Packets.** A packet travels in `message` with the rest of the spawn text, so the same packet
serves a run on either provider. Packets built from a range of the saved transcript are a Claude
Code feature: on this host, write each packet from your own context.

Every child also receives the AGENTS.md chain for its working directory, as a user-role message
headed `# AGENTS.md instructions for <cwd>`, even with `fork_turns: "none"` or
`fork_context: false`. That is why the standing text travels in the message and never in a file
named `AGENTS.md`.

## Models and effort

The models file, [config/models.json](../../config/models.json), maps each role to a tier and each
tier to `providers.openai.<tier>.model` and `.effort`. Both ship as `null`.

- **Mapping.** Pass the tier's `model` as `spawn_agent`'s `model` and its `effort` as
  `reasoning_effort`, on v2 and v1 alike. Use a slug from the "Available model overrides" list in
  the `spawn_agent` description, with an effort that line lists.
- **Bad values fail at the spawn**, with `Unknown model ... for spawn_agent. Available models: ...` or
  `Reasoning effort ... is not supported for model ...`.
- **With `null`, leave the parameter out.** The agent then takes `[agents] default_subagent_model`
  and `default_subagent_reasoning_effort`, then the parent's. A custom agent file's own `model` and
  `model_reasoning_effort` would win over both and could not be changed, but this skill writes none.
- **Set an effort whenever you set a model.** The docs say a model chosen without an effort runs
  that model's default effort, the spawn schema says an omitted effort inherits the parent's, and
  which one applies is unverified.
- **On v2, overrides need `fork_turns` `"none"` or a number.** A full fork inherits the parent's model
  and effort; the host's own hint says it takes no overrides, yet a full fork given overrides returned
  no error. So spawn a chat fork without `model` and `reasoning_effort`, and record the parent's
  model and effort in its roster row.
- **Record what you requested** as the roster's `model` and `effort`, and `agent_type` as `null`.
- **Session level:** in the desktop app, `/model` and `/reasoning` set the session's model and
  effort; in the CLI, `/model` sets both.

## Isolation

- **Subagents get tier none.** Codex has no per-agent worktree, so plan each subagent at tier `none`,
  with path-disjoint slices and the orchestrator committing (`may_commit` false).
- **A worktree per session.** `codex --worktree` and `codex exec --worktree` run a whole session in a
  new managed git worktree. They need the `worktrees` feature (stable, on), local execution, and a
  source that is not explicitly untrusted. In the desktop app, each chat runs Local or in a Worktree:
  worktrees live under `$CODEX_HOME/worktrees` with a detached HEAD, a worktree can be made
  permanent, `/worktree` and `/local` switch modes, and the 15 most recent worktrees are kept. The
  host's v2 hint says all agents share one directory, so a session worktree separates the run from
  your checkout, not the agents from each other (for a desktop Worktree chat, see "Not yet
  verified").
- **Ephemeral and session tiers per agent** have no verified route on this host; see "Not yet
  verified". Keep subagents at tier `none`.
- **The base of a new worktree.** How `codex --worktree` and the desktop app pick the base is
  unverified; see "Not yet verified". The preflight of
  [git_lanes.py](../../scripts/git_lanes.py) reads git alone: its `commits_not_on_remote_default`
  counts the commits on HEAD that the remote's default branch lacks, which is what a worktree based
  on that branch would miss. When you create a worktree yourself, name its base, as
  [isolation.md](../isolation.md) says.
- **`.worktreeinclude`.** The desktop app's managed worktrees read a `.worktreeinclude` file
  (documented, not observed). The desktop app also copies an ignored `AGENTS.override.md` into its
  managed worktrees.

## Watching and completion

- **Wait once per expected event.** On v2, `wait_agent` ends when a child finishes, when any message
  or new input arrives, or at the timeout; read the block that ended it, then wait again only for
  what is still outstanding. A loop of short waits is polling.
- **On v1,** pass the stage's `agent_id` values as `targets`.
- **Read thresholds from status files** with `ao.py status read FILE --threshold TEXT`.
- **Close each v1 agent** with `close_agent` once its return is accepted and no resume is expected:
  a completed v1 agent stays open and holds a concurrency slot until closed. v2 has no close tool and
  `list_agents` keeps completed agents.
- **A scripted orchestrator.** `codex exec --json` shows v2 collaboration calls only for `wait`;
  spawns, messages, follow-ups, lists and interrupts leave no item. v1 runs emit `spawn_agent`,
  `wait`, `close_agent` and `send_input` items with `agents_states`.
- **Approvals a child needs** (documented, not observed). In the interactive CLI, an approval request
  can surface from an inactive agent thread; the overlay names the source thread and `o` opens it.
  Under `codex exec`, an action that needs new approval fails, and the error comes back to the
  parent. Children reapply the parent turn's live overrides (`/permissions`, `--yolo`). In the
  desktop app, subagents inherit the permission mode chosen beneath the composer. Slice the work so
  children need no new approval, and run approval-gated steps yourself.

## Resuming and correcting an agent

- **Answer a parked agent:** on v2, `followup_task` to its name; on v1, `close_agent`, `resume_agent`,
  then `send_input`. Write the first line as `Answer to <ask id>: <decision>`, then any packet the
  answer carries, then the `answer` as one fenced json block, last. The agent keeps its history, so
  the answer need not restate the task.
- **Correct a running agent:** on v2, `send_message`, which it reads at its next model step, or
  `interrupt_agent` then `followup_task` to redirect it at once; on v1, `send_input`, with
  `interrupt: true` to redirect it at once.
- **Answer a request** while the agent keeps working: on v2, `send_message`; on v1, `send_input`
  without `interrupt`. Write the first line as `Answer to request <request id>: <decision>`, then
  the `answer` with `request_id` set, and append the message to the agent's `spawn_file`. Once the
  agent has parked on the request, answer it as a parked agent, with `followup_task` on v2,
  since `send_message` to an idle agent starts no turn. On v1 a child has no tool that reaches you,
  so its need for more access arrives as an ask in a parked return instead.
- **Steer, stop or close by asking.** On both surfaces you can ask Codex directly to steer a running
  subagent, stop it, or close finished subagent threads.
- **Process level:** `codex exec resume [SESSION_ID or --last] [PROMPT]`, `codex resume`,
  `codex fork` and `codex queue --thread <uuid or name> --message <text>` exist in the CLI's help;
  their behaviour is unverified.

## Showing the run

- **Both surfaces:** render every view as structured text, as [widgets.md](../widgets.md) describes.
- **CLI:** the terminal UI renders Markdown and shows an inline visualization as a link that opens in
  the browser (read from the binary, not observed). `codex exec` prints text or JSONL only.
- **Desktop app:** how it renders Mermaid or an inline visualization is not verified.

## Running the skill's scripts and where a standalone skill is discovered

**Discovery.** At session start Codex scans these skill roots:

- `.agents/skills` in the working directory and in each parent up to the repository root;
- `.codex/skills` in the project;
- `~/.codex/skills`, `~/.agents/skills` and `~/.codex/skills/.system`;
- plugin caches under `~/.codex/plugins/cache/`;
- `/etc/codex/skills`, which the docs add.

Install this skill by placing its folder at `~/.agents/skills/agent-orchestrate` or at
`.agents/skills/agent-orchestrate` in the repository. The desktop app lists skills in its Skills
sidebar and at `codex://skills`; the CLI has `/skills` and `$name`.

**The skill's folder.** The model-visible skill list shows each skill as
`- <name>: <description> (file: rN/<dir>/SKILL.md)`, with a "Skill roots" table that maps each `rN`
to an absolute path. Join the two to get the skill folder's absolute path.

**`agents/openai.yaml`** sits beside SKILL.md. Its `interface` keys are `display_name`,
`short_description`, `icon_small`, `icon_large`, `brand_color` and `default_prompt`, and
`policy.allow_implicit_invocation` decides whether the skill appears in the model-visible list. This
skill ships `true`. With `false`, the skill drops out of that list and only an explicit
`$agent-orchestrate` loads it. To turn a skill off, add a `[[skills.config]]` entry with `path` or
`name` (one of the two) and `enabled = false`.

**Running scripts.** Codex sets no skill-folder environment variable, and the working directory is
the model's choice. Run every script by absolute path, such as
`python3 <skill folder>/scripts/ao.py config`, pass output paths as absolute arguments, and set each
task's `ao_script` to `<skill folder>/scripts/ao.py`. The scripts find their own folder through
`__file__` and run inside the session's sandbox. The collaboration tools are out of reach from a
script, so every spawn, message and wait is a tool call you make.

**The run's files.** Codex names no scratch directory for a session. Make one folder for the run in
the system temporary directory, such as with `mktemp -d`. Under `workspace-write`, `/tmp` and
`$TMPDIR` are writable roots unless `exclude_slash_tmp` or `exclude_tmpdir_env_var` removes them
(documented), and children inherit the parent's sandbox.

## Traps

Each fails silently or looks like success.

1. **Hard-coded tool names fail on one surface.** v1 names fail on a v2 session and the reverse, and
   `--disable multi_agent_v2` does not bring v1 back on a v2 model. Detect the surface first.
2. **`--ephemeral` breaks the default spawn and every chat fork.** `fork_turns: "all"` needs the
   parent's persisted history; in an ephemeral `codex exec` the spawn fails with
   `collab spawn failed: no thread with id: <the parent's id>`. `fork_turns: "none"` spawns fine, so
   there a chat fork is planned fresh: put the context in its task, or in a packet when the packet
   conditions apply.
3. **A full fork is the v2 default.** A spawn without `fork_turns` copies your whole conversation,
   private context included, into the child, along with your model and effort.
4. **AGENTS.md reaches every child,** even one spawned without context. A per-run file named
   `AGENTS.md` or `AGENTS.override.md` in the working tree leaks into every agent and every later
   session there.
5. **AGENTS.md arrives as a user-role message,** so it ranks below developer instructions.
6. **`agents.max_depth` binds v1 only.** v2 ignores it, and every v2 child holds `spawn_agent`, so a
   child can spawn its own children. On v2 the skill's `agents.max_layers` holds by instruction
   alone: each task's `layers_below` and the standing text keep an agent from spawning past it.
   With no host cap there, set `layers_below` for a task you spawn directly to
   `agents.max_layers` minus 1. On v1, the depth `agents.max_depth` allows is the host's nesting
   cap: set `layers_below` to the smaller of `agents.max_layers` and that cap, minus 1. On both, a
   chat fork gets 0, and an agent's child gets one less than its parent.
7. **Two keys name the concurrency cap.** v2 reads
   `features.multi_agent_v2.max_concurrent_threads_per_session` and counts the root; the documented
   `[agents]` key excludes the primary thread.
8. **Finished agents linger.** v1 completed agents hold a slot until `close_agent`; v2 keeps them in
   `list_agents`.
9. **`codex exec --json` hides v2 collaboration calls** other than `wait`.
10. **v2 `wait_agent` returns no content.** A loop that parses the wait result for the answer gets
    nothing; the answer is in the `FINAL_ANSWER` or `MESSAGE` block.
11. **`send_message` to an idle agent does nothing until a turn starts.** Use `followup_task` for an
    agent that has finished or been interrupted; it cannot target the root.
12. **Spawning needs an explicit request.** The host spawns only when the user, or applicable
    AGENTS.md or skill instructions, explicitly ask for sub-agents, delegation or parallel agent
    work; on v1 a request for depth, research or analysis does not count. Word the go question so
    that the user's yes names sub-agents.
13. **`task_name` rejects hyphens and capitals, and `root` is reserved.** Map `export-api` to
    `export_api`.
14. **The collaboration tools are out of reach from scripts.** v2 tools cannot be called from inside
    `functions.exec`, and v1 tools on `code_mode_only` models exist only there; neither is reachable
    from a skill's shell scripts.
15. **A skill with implicit invocation off is invisible** in the model-visible list, so a subagent
    cannot find it by its description. It needs an explicit `$name`.
16. **`codex debug prompt-input` leaves `$skill` mentions unexpanded,** while `codex exec` expands
    them. Test explicit invocation with `codex exec`.
17. **The script working directory is the model's choice.** Pass absolute paths.
18. **The docs recommend a model an account may lack.** A spawn naming a slug missing from the
    catalog fails with `Unknown model`. Fill the models file from the "Available model overrides"
    list in the `spawn_agent` description.
19. **Untrusted folders start read-only,** and a project's `.codex/` layers (config, custom agents)
    load only for trusted projects. Pass `-s workspace-write` to `codex exec` explicitly.

## Not yet verified

Each item below is open. Treat it as unverified until a check runs.

**Desktop app:**

- Which tool surface, v1 or v2, the desktop app exposes for a given model, and whether its sessions
  apply `~/.codex/config.toml`. The bundled binary reads that file when run on its own with the
  default `CODEX_HOME`.
- Whether the desktop app has a Subagents panel, whether it shows each child's model and effort,
  and whether you can type into a child's thread directly.
- Where a child's approval request appears: the main chat, the child's thread, or nowhere.
- Whether Mermaid or an inline visualization renders in the chat.
- Whether a per-subagent stop or interrupt control exists.
- Whether `$agent-orchestrate` typed in the Codex composer invokes the skill, and how a skill with
  implicit invocation off shows in the Skills sidebar.
- Whether subagents in a Worktree chat all write inside that chat's worktree, and whether any extra
  worktree appears per subagent.
- A signal inside a session that tells the desktop app from the CLI.

**Both surfaces:**

- Whether a child's final answer reaches a root that is not inside `wait_agent`, starting a turn on
  its own. Every run checked used `wait_agent`.
- Which turns a numeric `fork_turns` copies: the first N of the parent's conversation or the last
  N. Until it is checked, a chat fork takes `"all"` and never a number.
- Whether a chat fork (`fork_turns: "all"`, or `fork_context: true` on v1) spawned after the
  session compacted gets the compacted history or the full one. The skill plans as if it gets the
  summary and the turns since.
- Whether a completed v2 agent still holds a concurrency slot, and whether setting only the
  documented `[agents]` key changes the v2 cap.
- Whether `model` and `reasoning_effort` took effect on a spawned child; `codex exec` output does
  not show which model a child ran on.
- That a model whose catalog entry has no `multi_agent_version` follows the
  `features.multi_agent_v2` flag.
- Whether `spawn_agent` accepts a catalog slug (`codex debug models`) that its "Available model
  overrides" list leaves out.
- Which effort a child runs when a model is set and no effort is: that model's default (the docs)
  or the parent's (the spawn schema).
- Whether the children of a session launched with `-c developer_instructions=...` inherit it.
- That v1 offers no child-to-parent tool. None was in the v1 child's tool list.
- Process-level resume with `codex exec resume`, `codex resume` and `codex queue` (help text only).
- One `codex exec --worktree` process per agent as a per-agent worktree tier.
- How `codex --worktree` and the desktop app pick a new worktree's base, and whether
  `codex --worktree` reads `.worktreeinclude`.
- Whether a child may write to a worktree outside the session's workspace under `workspace-write`.
  Every child checked wrote inside the parent's repository.
- `features.multi_agent_v2.subagent_developer_instructions` as a standing-text channel.
- The directive that produces an inline visualization.
- Whether the script working directory is always the skill folder. Both runs used it.
- A whole run on the `codex exec` fallback, one process per agent.
- That a child under `workspace-write` appends to a status file in the system temporary directory;
  the documented default allows it.

## Related

- [SKILL.md](../../SKILL.md): the run checklist and the capability table these operations fill.
- [standing.md](../../assets/standing.md): the standing text every agent receives in `message`.
- [protocol.md](../protocol.md): the spawn, the mid-run messages and the return this host carries.
- [isolation.md](../isolation.md): the tiers, how a branch closes, and making a worktree yourself.
- [widgets.md](../widgets.md): the views, rendered as structured text on this host.
- [config.md](../config.md): the settings and the models file's layering.
- [models.json](../../config/models.json): the tier for each role and the model for each tier.
- [ao.py](../../scripts/ao.py): `package`, `packets`, `status`, `roster`, `check` and `config`.
- [git_lanes.py](../../scripts/git_lanes.py): the preflight, whose `commits_not_on_remote_default`
  counts what a worktree based on the remote's default branch would miss.
- [claude-code.md](claude-code.md): the same headings for the Claude host.
