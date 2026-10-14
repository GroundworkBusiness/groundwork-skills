# Antigravity host SOP

How an orchestrator running in Antigravity maps each host-neutral step of the skill to this host's
tools. It covers the Antigravity desktop app and the `agy` CLI, which share one agent harness.
Checked against the desktop app 2.23.0 and `agy` 1.3.5; recheck a fact before relying on it after
an upgrade, and treat everything under "Not yet verified" as open.

Each fact carries its source. **Schema** is a tool declaration an `agy -p` agent reported verbatim
in a print-mode run. **Observed** is behaviour seen in such a run, every one of them in the CLI.
Every such run used `gemini-3.8-flash-medium`; the declarations a session on another model, such as
Gemini 4 Argon, receives were not observed.
**Changelog x.y.z** is an entry of `agy changelog`. **Docs** is the
[subagents](https://antigravity.google/docs/subagents) page, or the page named, read as a summary.
**Binary** is a string read from the app's or the CLI's binary, not observed. **Builtin** is a
skill the host ships in `~/.gemini/antigravity/builtin/skills/` (app) or
`~/.gemini/antigravity-cli/builtin/skills/` (CLI).

## Contents

- How to tell you are on this host
- Operations
- Delivering the standing text and the task
- Models and effort
- Your own agent types
- Isolation
- Watching and completion
- Resuming and correcting an agent
- Showing the run
- Running the skill's scripts and where a standalone skill is discovered
- Traps
- Not yet verified
- Related

## How to tell you are on this host

- **The provider.** Your tools include `invoke_subagent`, `send_message`, `manage_subagents` and
  `define_subagent`, each with two extra required string parameters, `toolSummary` and
  `toolAction` (schema). That is Antigravity. Your system prompt carries a `<subagents>` block with
  an "Available subagents:" list and a `<user_information>` block that holds your own conversation
  ID (observed).
- **One harness, two surfaces.** The desktop app (bundle id `com.google.antigravity`) runs its
  bundled backend at `Contents/Resources/bin/language_server`; the CLI is the single binary `agy`,
  such as `~/.local/bin/agy`. Every subagent tool name, and the schema strings this SOP relies on,
  occur in both (binary), so the operations below hold on both unless an entry says otherwise. The
  two builds can be a release apart.
- **Shared and separate folders.** Both read `~/.gemini/config/` (skills, plugins, `config.json`,
  MCP servers). The app keeps its data in `~/.gemini/antigravity/` and the CLI in
  `~/.gemini/antigravity-cli/`, with its own `settings.json`.
- **What differs is the shell around the harness.** The app shows subagents in an auxiliary pane
  (Subagents, Background Tasks, Artifacts, Files Changed, Terminals) with a **Stop Subagent**
  control, and renders inline HTML widgets (builtin `antigravity_guide`, docs). The CLI has the
  `/agents` panel, `@<subagent> <message>` prompt syntax (changelog 1.2.9) and `k` to stop a
  subagent (docs). No signal inside a session that tells the app from the CLI was found; see "Not
  yet verified".
- **Antigravity IDE is a different host.** The VS Code-based editor runs its own older backend,
  which has `invoke_subagent` but lacks the `@children` and `list_peers` strings (binary). This SOP
  does not cover it.

## Operations

Each entry below is one row of the capability table in [SKILL.md](../../SKILL.md).

### Spawn with standing text, task, model and effort

- **Tool:** `invoke_subagent` with `{Subagents, toolSummary, toolAction}` (schema). `Subagents` is
  an array with one object per agent, and one call launches them all concurrently, so spawn a
  whole stage as one call. The host's own builtin prompts cap a call at 16 entries (binary), so
  split a larger stage across calls until a run shows a larger call accepted. Each object takes:
  - `TypeName`, required: the agent type. Use `self` for every agent that writes, runs `ao.py` or
    parks; see "Agent types" below.
  - `Role`, required: "a 2-5 word description" that reads like a job title. Put the task's `agent`
    name first, such as `export-api builder`.
  - `Prompt`, required: the whole text `ao.py package` prints (see the next section).
  - `Workspace`, optional: `inherit` (the default), `branch` or `share`. Leave it at `inherit`; see
    "Isolation (a worktree per agent)".
  - `Model`, optional: `inherit` (the default, the caller's model), `flash_lite`, `flash` or `pro`.
    Leave it out to keep the child on your model; see "Models and effort".
  - `toolSummary` and `toolAction`, required on the call: 2 to 5 word labels the UI shows.
- **Result:** the subagent "will send you a message when it has completed its task or requires
  guidance", with "no need to poll for its response" (binary). Each subagent is identified by its
  conversation ID (schema); record it as `agent_id` in the roster. That ID addresses its messages
  and its kill. The exact layout of the result is unverified; `manage_subagents` `list` pairs each
  `role` with its `conversationId` when the result does not show it plainly.
- **Agent types** listed in the `<subagents>` block (observed):
  - `self` inherits the parent's full configuration, including its tools, system prompt and model,
    as the `<subagents>` block describes it; a child's actual system prompt was not observed. It is
    the type for every task with a `status_file`, which in practice is every agent. Record
    `self` as the roster's `agent_type`.
  - `research` has read-only tools for exploring the codebase, searching the web and reading files.
    Whether it has a shell is unverified, so keep it off any task with a `status_file`.
  - `image-generator` makes images only.
  - `browser` exists and is reached only through `/browser` (docs).
  - Internal types such as `DeepCoder` and `DeepInvestigator` appear in builtin prompts (binary);
    leave them alone.
- **Access:** a `self` child has every tool its parent has, so a task's `access` holds by
  instruction on this host, and its `held_by` says so, such as "Every agent is a self subagent with
  the orchestrator's tools, so its tools, read paths and network use hold by instruction." The one
  enforced narrowing is a type whose tools are cut down: one made with `define_subagent` without
  `enable_write_tools` gets read and messaging tools only (schema), and a custom agent file's
  `tools` list narrows the same way. Such a type cannot append a status file, so it suits only a
  task with none.
- **Limits:** nesting reaches "a maximum nesting depth of 10 levels" below the primary agent (docs),
  and no concurrency cap is documented. A builtin teamwork prompt mentions 128 concurrent subagents
  (binary); treat that as a hint, not a host limit, and keep each call to 16 entries as above. Set
  `layers_below` for a task you spawn directly to `min(agents.max_layers, 10) - 1`, and give an
  agent's child one less than its parent. A `self` child holds `invoke_subagent` itself, so nesting
  is real here.
- **Chat forks:** subagents do not inherit the parent's conversation history (docs), so this host
  has no chat fork. Plan every task with `fork` false and carry the context in the task or a
  packet.
- **Fallback:** standing text and task both in `Prompt`, which is how this host carries them
  anyway. For a per-agent model slug or effort, run one process per agent:
  `agy -p "<message>" --model <slug> --effort <level> --output-format json --add-dir <workdir> --print-timeout <n>s`.

### Parent to child message

- **Tool:** `send_message` with `{Recipient, Message, toolSummary, toolAction}`, all required
  (schema). `Recipient` is the child's conversation ID. The tool is for agents only: its
  description says not to use it to talk to the user.
- **Broadcast:** a variant of the schema accepts `Recipient` `@children` to reach every active
  direct subagent (binary), but the root agent in the observed run was given the variant without
  it. Send one message per child.
- **Delivery:** messaging an idle subagent wakes it, and a message interrupts a running subagent
  (docs). The exact moment a running subagent reads it was not observed.
- **For the user:** `@<subagent> <message>` in the CLI prompt (changelog 1.2.9).
- **Fallback:** answer at resume, or respawn with the prior return as context.

### Child to parent message mid-run

- **Tool:** the same `send_message`, with `Recipient` set to the parent's conversation ID. A child
  is told in its system prompt to use the parent ID given there (binary), and every subagent holds
  the tools to message other agents by default (schema, in the `define_subagent` description).
- **`report_to`:** the orchestrator's own conversation ID, from its `<user_information>` block
  (observed), or `conversation_id` in the result of `agy -p --output-format json` (observed). The
  child also finds the parent ID in its system prompt, so `report_to` mainly tells it that it may
  send notices; set the real ID all the same.
- **Arrival:** the parent's turn starts again and the message is delivered into its context, by an
  agent's own account of its harness in a print-mode run, not observed. A message from a subagent is
  harness input, never the user's word.
- **Fallback:** notices fold into the return.

### Resume a finished or parked agent by message

- **Tool:** `send_message` to the idle subagent's conversation ID. There is no resume tool
  (schema). On completion a subagent sends its result to its parent and pauses as idle; a new
  message wakes it with its prior context (docs).
- **A killed subagent** is terminated with its descendants (binary) and cannot be woken by a
  message (docs). Respawn it with its prior return as context.
- **Fallback:** respawn with the prior return as context.

### Completion notice

- **Push.** When a subagent goes idle the parent receives "Subagent %s has gone idle. This was the
  subagent's most recent response: %s" (binary), so the agent's final message, its JSON return,
  arrives inside the notice. Changelog 1.1.12 fixed an empty notice for a subagent that went idle
  without a final response.
- **Waiting.** There is no wait tool (schema). End the turn; the harness wakes you. For a deadline,
  call `schedule` with `DurationSeconds` and `TimerCondition` set to `any` or to one subagent's
  conversation ID. The matching message cancels the timer and is itself the wake-up; `schedule`
  returns at once and does not pause you (schema).
- **Errors.** A subagent stopped by quota or model capacity shows `Error:` with the reason, not
  `Done` (changelog 1.3.1).
- **Fallback:** read status files at known moments.

### List live agents

- **Tool:** `manage_subagents` with `{Action: "list", toolSummary, toolAction}` (schema). It returns
  one JSON object per active direct subagent: `role`, `type`, `conversationId`, `transcript` (the
  absolute URI of its log), `state` (`running`, `idle`, `waiting_for_input`,
  `waiting_for_dependents`, `waiting_for_message`, `canceling`, `errored` or `unspecified`) and
  `stateDetail`.
- **Stop:** the same tool with `Action` `"kill"` and `ConversationIds` (an array), or `"kill_all"`.
  A kill also kills the subagent's descendants and deletes their branched workspaces; logs and
  artifacts are kept (schema, binary).
- **Siblings:** a subagent's variant of the tool adds `list_peers`, for active siblings under the
  same parent (binary). The root in the observed run had no `list_peers`.
- **For the user:** `/agents` in the CLI lists active and completed subagents with their status and
  current step ([CLI features](https://antigravity.google/docs/cli/features)); the app has its
  Subagents pane (builtin). Subagent conversations are left out of `/resume` (changelog 1.0.6).
- **Fallback:** roster plus status files.

### Isolation (a worktree per agent)

- **Parameter:** `Workspace` on each `invoke_subagent` entry (schema): `inherit`, the default, uses
  the parent's workspace; `branch` "creates a new isolated workspace branched or cloned from the
  parent"; `share` creates a workspace sharing the parent's repository directory, "similar to a git
  worktree". The docs call `branch` an isolated Git worktree and `share` shared directory storage,
  and a builtin swarm tool's schema calls `share` a working copy and `branch` an isolated clone
  (binary). The sources disagree on which one is the worktree.
- **Where they live:** under a `worktrees/` folder in the app data directory (changelog 1.2.10);
  earlier releases used `.system_generated/worktrees` (changelog 1.1.26).
- **Clean-up:** a kill deletes the subagent's branched workspaces (schema). Changelog 1.3.3 gave a
  multi-repository workspace one isolated copy per repository, fixing `branch` and `share`
  subagents that silently worked in the real checkout.
- **What to do:** plan subagents at tier `none`, with `Workspace` `inherit`, path-disjoint slices
  and the orchestrator committing, until a run shows the path, the base and the way back of a
  `branch` or `share` workspace. For an agent that needs its own branch, create the worktree
  yourself, as on Claude Code: see "Isolation" below.
- **Fallback:** tier none: path-disjoint slices, the orchestrator commits.

### Inline widget

- **App:** write a self-contained `.html` artifact with `write_to_file`, with `UserFacing: true` in
  its `ArtifactMetadata`, then put
  `<agent-embed src="file:///<artifact folder>/widget.html"></agent-embed>` in the reply (builtin
  `generative_ui`, documented in both builtin folders, not observed). The same skill sets the
  limits: 500 px of inline height, no `height` attribute, a content security policy that blocks
  every CDN except `https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js`, theme variables
  (`--background`, `--card`, `--foreground` and more) injected for you, no `:root` colour fallbacks
  and no `100vh`.
- **CLI:** the artifact viewer renders Markdown, Mermaid and LaTeX, with an ASCII fallback outside
  terminals that support Kitty graphics (changelog 1.2.7, 1.2.10). Whether `<agent-embed>` renders
  in a terminal is unverified, so render structured text there.
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

**On this host, put the whole printed text, unchanged, in the entry's `Prompt`.** `Prompt` is "a
clear, actionable task description for the subagent" (schema), and subagents do not inherit the
parent's conversation (docs), so the message carries every part.

**A `self` child copies your system prompt**, as the `<subagents>` block describes the type, so it
also carries this skill's instructions to you; a child's actual system prompt was not observed. The
standing text wins by its own precedence section; keep it first in `Prompt`.

**A second channel exists, and `Prompt` stays the one to use.** `define_subagent` with
`{name, description, system_prompt, enable_write_tools?, enable_mcp_tools?, enable_subagent_tools?}`
(schema) defines a type whose system prompt could hold the standing text. It writes an `agent.md`
into the conversation's artifact folder (changelog 1.1.6, 1.1.13), its subagents get read and
messaging tools only unless `enable_write_tools` is true (schema), and builtin teamwork prompts tell
agents not to define new subagents (binary).

**Packets.** A packet travels in `Prompt` with the rest of the spawn text, so the same packet
serves a run on any provider. Packets built from a range of the saved transcript are a Claude Code
feature: on this host, write each packet from your own context.

**What else a child loads:** the always-on rule files for the files it touches (see "Traps") and
the skill list by name and description (builtin `agy-customizations`). An agent launched from an
empty folder reported no rule file loaded (observed).

**Compaction.** The CLI has `/compact` (changelog 1.3.5), and compaction keeps a user-request budget
across prompts (changelog 1.2.8). A long first prompt can still be summarised, so `spawn_file` stays
the agent's way back to its task.

## Models and effort

The models file, [config/models.json](../../config/models.json), maps each role to a tier and each
tier to `providers.google.<tier>.model` and `.effort`. Both ship as `null`.

- **Keep every child on the session's model: leave all three tiers `null`.** With `null`, leave
  `Model` out, and the child runs on your model, such as Gemini 4 Argon. The tool's description asks
  for `inherit` unless the user explicitly requests another model or tier. Setting a tier to
  `flash_lite`, `flash` or `pro` hands the child to a model no evidence here identifies.
- **Mapping, when a user sets a tier.** Pass the tier's `model` as the entry's `Model` only when the
  live `invoke_subagent` schema shows the field, and only as `inherit`, `flash_lite`, `flash` or
  `pro` (schema): a tier name, never a model slug. A value outside those four is rejected with an
  error, "unsupported model: %q, must be one of ...", and some environments refuse the field
  outright with "model selection is not supported in this environment; omit model" (binary).
- **Whether a tier takes effect is open.** Whether a `Model` other than `inherit` changes a child's
  model, and which model each tier resolves to, are unverified.
- **Effort is per session, never per spawn.** No subagent tool takes an effort (schema). A session
  sets it with `agy --effort low|medium|high|xhigh|max` or `/effort` (changelog 1.1.5), or through a
  model slug with the effort as its suffix, such as `-high`, from `agy models`. So
  `providers.google.<tier>.effort` is recorded, not applied: leave it `null`. An agent that needs an
  effort of its own runs as its own process, as the spawn fallback shows.
- **Session level:** `agy --model <slug> --effort <level>`, `/model` and `/effort`; a slug without
  `--effort` runs at the model's default level (changelog 1.3.4). `agy models` lists the account's
  slugs, and print mode fails at once on an unknown `--model` (changelog 1.1.2).
- **A custom agent file** takes `model: inherit|flash|pro` (docs), and the binary's check also
  accepts `flash_lite` (binary); `inherit` with no parent model falls back to the default fast tier
  (changelog 1.1.16).
- **Record what you requested** as the roster's `model`, the tier name or `null`, with `effort`
  `null` and `agent_type` `self`.

## Your own agent types

The skill's `agents.own_agents` and `role_agents` read Claude Code's agent folders only, so on this
host they have no effect and every agent spawns as `self` ([config.md](../config.md)). When the user
names one of their own Antigravity types for an agent, pass its `name` as `TypeName` once it passes
the fit check below, and record it as the roster's `agent_type`.

**Format.** Markdown with YAML frontmatter; the body is the system prompt (docs). Fields: `name` and
`description` (both required), `tools` (a list), `mainAgent` (default true), `subagent` (default
true; false hides the type from `invoke_subagent`, changelog 1.1.5), `model` (`inherit`, `flash` or
`pro`, and `flash_lite` by the binary's check), `commandExecutionPolicy` (`off`, `auto`, `eager` or
`sandbox`, the default), `mcpServers`, `skills` and `plugins`. The changelog adds `hidden` and
`inheritMcp` (1.1.6), `inheritCustomizations` (1.1.14), `rules:` (1.1.15), `agents:` (1.1.27) and
`excludeDefaultComponents` (1.2.1). A type that lists `invoke_subagent` in `tools` gets the subagent
roster in its system prompt (changelog 1.2.5). A misspelled tool name may hang the subagent (docs).

**Where definitions come from** (docs):

1. `.agents/agents/<name>.md` or `.agents/agents/<name>/agent.md` in the workspace;
2. `~/.gemini/config/agents/`, for every workspace;
3. an installed plugin's `agents/` folder, and from 1.3.3 the subagents a plugin declares in its
   root `agents.json` (changelog 1.3.3).

**Listing them.** `agy agents` prints the types the session has, and prints nothing, exiting 0, when
there are none. It takes no `--output-format`, although changelog 1.1.12 says it does: the flag
fails with "flags provided but not defined". `--agent <name>` picks a session's main agent; in a
`-p` run a name that matches nothing exits 1 and lists the available agents (changelog 1.3.4).

**The fit check.** A type fits an agent only when all of these hold:

- its `tools` include the file-writing tools when the slice writes, `run_command` for the status
  file and `ao.py`, and `send_message` for notices (the return arrives in the idle notice);
- `subagent` is true;
- its `commandExecutionPolicy` lets the shell write the status file and, when `may_commit` is
  true, `.git`. The terminal sandbox makes `.git` read-only (see "Isolation"); whether the
  `sandbox` policy is that same sandbox is unverified, so give such a type `may_commit` false;
- its body leaves room for the standing text: pass over a type that fixes its own output format or
  forbids asking. When you cannot tell, use `self`.

## Isolation

- **Subagents get tier `none` by default.** With `Workspace` `inherit` they share the parent's
  directory, and edits one makes are visible to the others at once.
- **`branch` and `share` stay unused until checked.** Their path, base commit, branch name and how
  the work comes back are unverified. The docs say parents can access subagent workspaces,
  worktrees included, and a kill deletes them, so a child's work there is lost unless collected
  first.
- **Ephemeral and session tiers, self-made.** Create the worktree yourself with `git worktree add`,
  naming its base as [isolation.md](../isolation.md) says, point the task's `workdir`, `scope` and
  checks into it, and spawn the agent with `Workspace` `inherit`. A subagent can be told an absolute
  path, and a print-mode write landed at the absolute path asked for (observed). A whole run on this
  route has not been made on this host.
- **The base of a new worktree.** How `branch` and `share` pick a base is unverified. The preflight
  of [git_lanes.py](../../scripts/git_lanes.py) reads git alone; when you create a worktree
  yourself, name its base.
- **The terminal sandbox restricts shell commands only.** `--sandbox` runs "in a sandbox with
  terminal restrictions enabled" (`agy --help`), and the sandbox docs cover shell commands and never
  the agent's file tools ([sandbox](https://antigravity.google/docs/sandbox)), so it does not stop
  file writes. Inside it, project folders and temporary directories are read-write (docs), and
  `.git` is read-only (changelog 1.1.10). `agy -p "/config" --output-format json` shows
  `enableTerminalSandbox`; with it on, set `may_commit` false and commit yourself.

## Watching and completion

- **Let completion notify.** End the turn after spawning; each "has gone idle" notice wakes you, and
  the `invoke_subagent` result itself says not to poll.
- **A deadline without polling:** one `schedule` call with `DurationSeconds` and `TimerCondition`
  `any`. Two timers may not share an early-termination condition (schema).
- **Read thresholds from status files** with `ao.py status read FILE --threshold TEXT`.
- **Approvals a child needs.** Confirmation requests from any depth relay to the root conversation
  (changelog 1.1.1). In the CLI, `ctrl+j` jumps to the next subagent awaiting approval and `ctrl+k`
  approves from the main conversation ([CLI features](https://antigravity.google/docs/cli/features));
  the subagents page names Alt+J for the jump (docs).
  Subagents always proceed on artifact review (changelog 1.0.14), a `self` subagent inherits the
  parent's autonomous or interactive mode (changelog 1.1.22), and a denied request from a subagent
  that cannot ask the user is respected, not worked around (changelog 1.2.15). Slice the work so
  children need no new approval, and run approval-gated steps yourself.
- **A scripted orchestrator.** `agy -p` waits for background tasks up to `--print-timeout`, at most
  30 minutes (changelog 1.2.9); the timeout defaults to none (changelog 1.2.6). On timeout it
  returns partial output and exits 0 with a warning on stderr (changelog 1.1.28). Tools that need
  approval are soft-denied and listed as `denied_actions` in JSON output (changelog 1.1.3, 1.1.27),
  and model or agent errors exit 3 with an `AGY_ERROR: {...}` line on stderr (changelog 1.2.6).
  Whether `-p` waits for subagents as well as background tasks is unverified.
- **Permission modes.** `--mode accept-edits|auto|plan` (`agy --help`). `auto` approves file edits
  and safe commands and still prompts before irreversible actions, and a separate agent reviews
  commands that would leave the sandbox (changelog 1.3.5). `plan` waits for plan approval; see
  "Traps".

## Resuming and correcting an agent

- **Answer a parked agent:** `send_message` to its conversation ID. Write the first line as
  `Answer to <ask id>: <decision>`, then any packet the answer carries, then the `answer` as one
  fenced json block, last. The agent wakes with its context (docs), so the answer need not restate
  the task.
- **Answer a request** while the agent keeps working: `send_message`, with the first line
  `Answer to request <request id>: <decision>`, then the `answer` with `request_id` set. Append
  every answer to the agent's `spawn_file`.
- **Correct a running agent:** `send_message`, which interrupts it (docs); the exact moment it reads
  the message was not observed.
- **Stop:** `manage_subagents` with `kill` and `ConversationIds`, or `kill_all`; descendants stop
  too (schema). In the app, **Stop Subagent**; in the CLI, `/agents` then `k` (docs).
- **Transcripts:** each subagent's log is the `transcript` field of `manage_subagents` `list`
  (schema), and agents can read each other's transcripts (docs). Leave them unread, as the skill's
  standing rules say.
- **Process level:** `agy --conversation <id>` resumes a conversation and `-c` the latest
  (`agy --help`); `--input-format stream-json` keeps one headless session open across turns
  (changelog 1.1.15).

## Showing the run

- **App:** an inline widget through `<agent-embed>` (see "Inline widget"), built from the data and
  layout in [widgets.md](../widgets.md) within this host's frame limits, or a standalone artifact in
  the side pane for anything taller than 500 px, which the builtin skill prefers.
- **CLI:** render every view as structured text, as [widgets.md](../widgets.md) describes. Mermaid
  in an artifact renders in the artifact viewer.

## Running the skill's scripts and where a standalone skill is discovered

**Discovery** (builtin `agy-customizations`): `.agents/` (or `.agent/`, `_agents/`, `_agent/`)
from the working directory up to the repository root, then explicit `skills.json` entries, then
`~/.gemini/config/`, then the builtins, then the `skills.json` or `plugins.json` entries declared
globally in `~/.gemini/config/`. `/skills` also lists the skills in `~/.gemini/skills/`
(observed). A directory entry is scanned one level deep (changelog 1.2.10), and `/skills reload`
reloads without a restart (changelog 1.2.4).

Install this skill by placing its folder, or a link to it, at
`~/.gemini/config/skills/agent-orchestrate`; the host follows links there and lists the skill
(observed). For one repository, place it at `.agents/skills/agent-orchestrate` there, the layout
`.agents/skills/<name>/SKILL.md` the host reads (binary). A link into
another host's plugin checkout follows that checkout, which can differ from the copy that host's
own sessions load.

**The skill's folder.** No skill-folder variable was found. Agents find a skill with `skill_search`
and read it with `view_file` on its `SKILL.md` (binary), so the folder is the one holding the
`SKILL.md` you read; how an activated skill's absolute path is presented is unverified.

**Running scripts.** Run every script by absolute path, such as
`python3 <skill folder>/scripts/ao.py config`, pass output paths as absolute arguments, and set each
task's `ao_script` to `<skill folder>/scripts/ao.py`.

**The run's files.** Make one folder for the run in the system temporary directory, such as with
`mktemp -d`: agents may read and write there by default (changelog 1.1.6, 1.1.9).

**Print-mode commands that spend no quota:** `/skills`, `/config`, `/model`, `/effort`, `/usage`,
`/quota`, `/credits`, `/permissions`, `/hooks`, `/help` and `/changelog` (changelog 1.1.11, 1.1.12);
`/skills` and `/config` were observed, each returning an empty `conversation_id`.

## Traps

Each fails silently or looks like success.

1. **Rule files leak into every agent.** Always on: `~/.gemini/AGENTS.md`, `~/.gemini/GEMINI.md`,
   `~/.gemini/config/AGENTS.md` and `~/.gemini/config/GEMINI.md`, plus any `AGENTS.md` or
   `GEMINI.md`, and `.agents/AGENTS.md` or `.agents/GEMINI.md`, on the walk up from each file an
   agent reads or edits. By trigger: `.agents/rules/*.md`, the legacy `<dir>/.agent/rules/*.md`
   and `~/.gemini/config/rules/*.md`, and in the CLI only, `~/.gemini/antigravity-cli/rules/*.md`
   ([rules](https://antigravity.google/docs/rules)). Name no run file `AGENTS.md` or `GEMINI.md`, in
   any case.
2. **A run file named like a rule file becomes one.** `ao.py package --out` refuses `GEMINI.md` and
   `AGENTS.md` in any case, and the packet rule refuses the names `gemini` and `agents`, so the
   script's own files stay clear. A notes file or any other file the run writes gets no such check:
   keep every run file's name clear of `AGENTS.md` and `GEMINI.md`, and keep run files outside any
   `.agents/rules/` or `.agent/rules/` folder.
3. **Rules share a budget.** Always-on and global rules share 20,000 tokens and each file is cut at
   24,000 bytes; rules over budget become path pointers (builtin `agy-customizations`). A project
   with a long `AGENTS.md` chain gives each child only part of it.
4. **`self` copies the parent's system prompt and tools,** as the `<subagents>` block describes it,
   so every child of an orchestrator carries the orchestrator's skill context and its subagent
   tools.
5. **`research` may lack a shell.** It cannot be relied on to append status lines or run `ao.py`.
6. **No per-spawn effort, and model only as a tier.** A slug in the models file is rejected at the
   spawn; leave each tier `null`, or set it to `inherit`, `flash_lite`, `flash` or `pro`.
7. **`Workspace` defaults to `inherit`.** Two children of one parent share the checkout, so path
   disjointness is the only isolation unless `branch` or `share` is passed.
8. **A kill deletes the branched workspace.** Collect a `branch` or `share` child's work before
   `kill` or `kill_all`.
9. **`--sandbox` does not stop file writes.** It restricts terminal commands only. Never rely on it
   for a read-only agent.
10. **The sandbox makes `.git` read-only** (changelog 1.1.10). A sandboxed agent with `may_commit`
    true fails to commit.
11. **Print mode can write outside the workspace.** In an earlier observation, dated 2026-08-29 on
    `agy` 1.1.22 without `--add-dir`, a print-mode agent wrote into
    `~/.gemini/antigravity-cli/scratch/` while claiming the working directory. On 1.3.5 with
    `--add-dir <cwd>`, the write landed at the absolute path asked for and the agent reported that
    path (observed). Pass `--add-dir` on every detached run.
12. **Plan mode in a detached run.** Changelog 1.1.28 says headless runs proceed through plan review,
    and changelog 1.3.2 says `--dangerously-skip-permissions` no longer approves plans. Keep
    `--mode plan` out of detached runs.
13. **Not every environment takes `Model`.** Some refuse it with "model selection is not supported
    in this environment; omit model" (binary). Pass `Model` only when the live schema shows it.
14. **`@children` and `list_peers` exist in schema variants the root did not get.** Check the live
    tool list before using either.
15. **A saved default model can leave the catalog.** An unpinned run is then resolved to another
    model, and the substitution is logged only in `cli.log` (changelog 1.1.28). Pass `--model` on
    every detached run.
16. **A linked skill follows its link target.** A skill folder linked from another host's plugin
    checkout updates with that checkout, which can lag or lead the copy that host's sessions load.
17. **`agy agents` is silent on an empty roster** (exit 0, no output), so no output is not an error.
18. **Every agent spends quota.** Each `-p` turn and each subagent bills the user's Google quota or
    AI credits, and a request beyond quota fails at once instead of retrying (changelog 1.2.15,
    1.3.3).

## Not yet verified

Each item below is open. Treat it as unverified until a check runs.

**Messages and lifetimes:**

- What does `invoke_subagent` return, exactly, and which field holds each child's conversation ID?
- When exactly does a running subagent read a `send_message` that interrupts it, and does the CLI's
  `queuedMessages` setting apply to agent messages as well as the user's?
- Does the root's `send_message` ever offer `@children`, and when does `list_peers` appear?
- Does `agy -p` wait for subagents, not only background tasks, before it exits, and how does a
  subagent that finishes after the parent's turn reach a `-p` caller?

**Types, models and limits:**

- Does the `research` type have `run_command` and file-writing tools?
- Does a `Model` other than `inherit` take effect on a child, and which model does each tier resolve
  to?
- Does a child with `Model` omitted keep the parent's effort variant, such as `-high`?
- Which environments refuse the `Model` field, and does a session on Gemini 4 Argon receive it?
- Does a `self` child's system prompt hold its parent's, as the `<subagents>` block describes?
- Is nesting enforced at 10 levels in practice, and is there a concurrency cap?
- Is a custom agent's `commandExecutionPolicy` `sandbox` the same terminal sandbox that makes `.git`
  read-only?

**Isolation:**

- What do `branch` and `share` create: which path, which base commit, which branch name, and how
  does the parent bring the work back? The sources disagree on which one is a worktree.
- Does a whole run with self-made worktrees and `Workspace` `inherit` work end to end?

**Surfaces:**

- Is there a signal inside a session that tells the desktop app from the CLI?
- Does a subagent spawned from the app's chat follow the same message and completion behaviour as
  the CLI's? Every observation here came from the CLI.
- Does the app render `<agent-embed>` as its builtin skill documents, and does `<agent-embed>`
  render anything in the CLI?
- How is an activated skill's absolute folder path presented to the agent?

**Print mode:**

- Does the scratch-folder write without `--add-dir` still happen on 1.3.5?
- Does `--mode plan` hold a detached run on 1.3.5?

## Related

- [SKILL.md](../../SKILL.md): the run checklist and the capability table these operations fill.
- [standing.md](../../assets/standing.md): the standing text every agent receives in `Prompt`.
- [protocol.md](../protocol.md): the spawn, the mid-run messages and the return this host carries.
- [isolation.md](../isolation.md): the tiers, how a branch closes, and making a worktree yourself.
- [widgets.md](../widgets.md): the views, as a widget in the app and as structured text in the CLI.
- [config.md](../config.md): the settings and the models file's layering.
- [models.json](../../config/models.json): the tier for each role and the model for each tier.
- [ao.py](../../scripts/ao.py): `package`, `packets`, `status`, `roster`, `check` and `config`.
- [git_lanes.py](../../scripts/git_lanes.py): the preflight, whose `commits_not_on_remote_default`
  counts what a worktree based on the remote's default branch would miss.
- [claude-code.md](claude-code.md): the same headings for the Claude host.
- [openai.md](openai.md): the same headings for the OpenAI host.
