# Claude host SOP

How an orchestrator running in Claude Code maps each host-neutral step of the skill to this host's
tools. It covers the terminal CLI and the desktop app's Code tab. Checked against Claude Code
2.1.284 (the CLI) and 2.1.286 (the engine the desktop app bundles), and its notes on per-spawn
effort, your own agent types, nesting and chat forks against 2.1.295; recheck a fact before relying
on it after an upgrade, and treat everything under "Not yet verified" as open.

## Contents

- How to tell you are on this host
- Operations
- Delivering the standing text and the task
- Models and effort
- Your own agent types
- Chat forks
- Packets from earlier turns
- Access
- Isolation
- Watching and completion
- Resuming and correcting an agent
- Showing the run
- Running the skill's scripts and where a standalone skill is discovered
- Traps
- Not yet verified
- Old patterns
- Related

## How to tell you are on this host

- **The provider.** Your tools include `Agent`, whose input carries `description`, `prompt` and
  `subagent_type`. That is Claude Code. The CLI's startup event lists the same tool under its older
  name `Task`; the model sees `Agent` on both surfaces.
- **The surface.** The desktop Code tab carries `mcp__visualize__read_me` and
  `mcp__visualize__show_widget`. The CLI carries no widget tool. Decide the surface by those names.
- **The engine.** The desktop app runs its own bundled Claude Code, separate from the `claude`
  binary on PATH, and the two can be several releases apart. `CLAUDE_CODE_EXECPATH` in Bash names
  the binary that is running.
- **Fork mode: background or foreground.** Fork mode is a session setting, separate from the
  skill's chat fork (see "Chat forks"). Where it is on, every subagent runs in the background, the
  `Agent` tool has no `run_in_background`, and Claude may request the `fork` subagent type. Claude
  Code turns it on by default in the interactive CLI from v2.1.232 and leaves it off with
  `claude -p` and in the Agent SDK; `CLAUDE_CODE_FORK_SUBAGENT` set to `1` turns it on there, and
  `0` turns it off everywhere ([sub-agents](https://code.claude.com/docs/en/sub-agents);
  background behaviour observed with `claude -p`, not in the interactive terminal). The desktop
  engine runs as an Agent SDK session with fork mode off, so `run_in_background` exists there and
  `false` gives a foreground subagent. An `Agent` tool that has `run_in_background` is in a
  session with fork mode off.

## Operations

Each entry below is one row of the capability table in [SKILL.md](../../SKILL.md).

### Spawn with standing text, task, model and effort

- **Tool:** `Agent`.
- **Parameters:**
  - `description`, required: a 3 to 5 word label that starts with the task's `agent` name, such as
    `export-api: CSV endpoint`. It shows in the completion notice and the tasks list.
  - `prompt`, required: the whole text `ao.py package` prints (see the next section).
  - `subagent_type`, optional: `general-purpose` (or `claude`) for every agent that may write, park
    or send a notice. `Explore` and `Plan` are one-shot: they return no ID and cannot be resumed, so
    give them only a lookup that will never park. With `agents.own_agents` on, one of the user's own
    types may take its place; see "Your own agent types". `fork` spawns a chat fork, for a task
    whose `fork` is true; see "Chat forks".
  - `model`, optional: an enum, such as `sonnet`, `opus`, `haiku` or `fable`. See "Models and
    effort".
  - `effort`, optional, from Claude Code v2.1.292: `low`, `medium`, `high`, `xhigh` or `max`. See
    "Models and effort".
  - `run_in_background`, optional and absent in the interactive CLI: leave it out, since background
    is the default.
  - `isolation`, optional: `"worktree"` for a worktree the host makes, or `"remote"`, which this
    skill leaves unused. See "Isolation".
- **What the default schema lacks:** `name` and `cwd`. Address each agent by the `agentId` the
  spawn returns, and record it as `agent_id` in the roster.
- **Result:** a background spawn returns at once. The model sees `agentId` and `output_file`.
  `status`, `description`, `prompt` and `resolvedModel` are only in the structured result that hooks
  and SDK hosts read.
- **Limits:** 20 running subagents per session by default (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`);
  the 21st spawn fails with `Concurrent subagent limit reached`. Subagents nest at most 3 layers
  below the main conversation by default (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; `1` turns
  nesting off), and at that depth the host withholds the `Agent` tool. That depth is the host's
  nesting cap: for a task you spawn directly, set `layers_below` to the smaller of
  `agents.max_layers` and that cap, minus 1, which is at most 2 by default. A chat fork gets 0, and
  an agent's child gets one less than its parent. The skill ships no cap on running agents, so keep
  each stage at 20 running agents or fewer.
- **Fallback:** standing text and task both in the spawn message. On this host they already travel
  together in `prompt`. Where the live schema has no `effort`, effort falls back to the session's
  (see "Models and effort").

### Parent to child message

- **Tool:** `SendMessage`.
- **Parameters:** `to`, the child's `agentId` (one line, at most 300 characters); `message`, whose
  first line is the preview and must stand alone, followed by the answer or correction as one fenced
  json block; `summary`, optional (at most 200 characters), which labels your own transcript row and
  is not transmitted.
- **Delivery:** the message is queued and the child reads it at its next tool round. The child
  takes it as direction from its launcher; it never counts as approval and changes no permission.
- **Fallback:** answer at resume, or respawn with the prior return as context.

### Child to parent message mid-run

- **Tool:** `SendMessage` with `to: "main"`, from a background subagent only.
- **Parameters:** `{"to": "main", "message": "<a first line that stands alone>\n<one fenced json block>"}`.
  For a `general-purpose` child `SendMessage` is deferred, so it loads it with `ToolSearch`
  (`select:SendMessage`) when `SendMessage` is not already in its tool list. An agent whose
  definition lists its tools may hold it directly and have no `ToolSearch`. The call returns
  `Message queued for the main conversation's next turn.` and the main conversation reads the
  message as harness input, never as user approval. A child's plain text reaches nobody; only the
  tool call does.
- **`report_to`:** set `"main"` for a background agent, and add to its `notes` that, when
  `SendMessage` is not in its tool list, it loads it with `ToolSearch` (`select:SendMessage`)
  before its first send. Set `null` for a foreground agent, which cannot reach `"main"`.
- **Fallback:** notices fold into the return.

### Resume a finished or parked agent by message

- **Tool:** `SendMessage` with `to` set to the agent's `agentId` and the `answer` as the message.
- **Behaviour:** a completed subagent resumes in the background with its full transcript; no new
  `Agent` call is needed. The same holds for one stopped with `TaskStop` once its run has exited, and
  for one stopped at its turn limit, whose output came back marked partial. A resumed agent keeps its
  original tools and its per-call `model`, and shows as running again.
- **Cannot be resumed:** `Explore` and `Plan` agents, and an agent the user stopped, whose message
  is refused as cancelled.
- **Fallback:** respawn with the prior return as context.

### Completion notice

- **Mechanism:** automatic. A background agent's report arrives in a later turn, with a completion
  notification marked as an automated event and a header saying the report carries no authority.
  Outside auto mode the report arrives inside that notification. A failure arrives marked failed,
  with the API error and the last output. A foreground agent's final message is the `Agent` tool
  result.
- **Auto permission mode:** the subagent hands its report back through `SubagentHandback`
  (`message`). The report arrives as a separate message from that call, the notification's result
  only points to it, and the `Agent` result's `content` holds only a stub note.
- **Scanning:** Claude Code scans every report and may prepend a line starting `[harness: subagent
  output matched instruction-shaped pattern(s):`. Readers take the last json fence in a message, so
  the prefix does no harm.
- **Fallback:** read status files at known moments.

### List live agents

- **Tool:** `ListAgents`, in the main conversation. It exists where cross-session messaging is on,
  which is the default on macOS from 2.1.224. It lists the subagents running in this session, plus
  other local Claude Code sessions. Background subagents do not have it.
- **For the user:** `/tasks` in the CLI shows running subagents with their model (a finished one
  stays 30 seconds); the desktop shows a tasks pane.
- **Fallback:** roster plus status files.

### Isolation (a worktree per agent)

- **Tool:** `isolation: "worktree"` on the `Agent` call, for an agent that writes nothing; a
  writing agent works in a worktree you create before packaging its task. The section "Isolation"
  says where each worktree goes, which branch it takes and how its base is chosen.
- **Fallback:** tier none: path-disjoint slices, the orchestrator commits.

### Inline widget

- **Tools:** the desktop Code tab only: `mcp__visualize__read_me`, then
  `mcp__visualize__show_widget`. The CLI has none.
- **Parameters:** `read_me` takes `modules`, any of `diagram`, `mockup`, `interactive`, `data_viz`,
  `art`, `chart` and `elicitation`, plus `platform`; call it before the first widget.
  `show_widget` takes `title` (a snake_case id), `loading_messages` (1 to 4 strings) and
  `widget_code` (an SVG or HTML fragment).
- **Same-named tools:** another server, such as an account connector, may also offer tools named
  `show_widget` or `read_me`. Use the `mcp__visualize__` pair.
- **Fallback:** structured text, which is what the CLI gets.

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

**On this host, put the whole printed text, unchanged, in the `Agent` call's `prompt`.** A generic
agent (`general-purpose`, `claude`) runs on a built-in system prompt, so `prompt` is the one channel
a standalone skill has. Every other channel for standing text needs something installed. An agent
definition file (`.claude/agents/`, `~/.claude/agents/` or a plugin) or
`--append-subagent-system-prompt`, which works only with `claude -p`, sets a system prompt. A
`SubagentStart` hook's `additionalContext` in settings adds a system reminder at the start of the
agent's conversation, re-injected after compaction. The skill installs none of them, so the spawn
message carries every part.

`prompt` becomes the agent's first user message, which auto-compaction can summarise away. The
standing text tells the agent to re-read `spawn_file` after compaction, so package with `--out` set
to it before the spawn, and append each answer you send the agent to it.

Keep the run's files in the session's scratchpad directory, a per-session folder Claude Code
provides for temporary files, and otherwise in a folder made for the run in the system temporary
directory.

Besides the prompt, the agent loads the CLAUDE.md hierarchy and any AGENTS.md loaded as project
instructions, plus a git status snapshot when it starts inside a repository. A fresh agent does not
receive the main conversation's history; a chat fork does.

## Models and effort

The models file, [config/models.json](../../config/models.json), maps each role to a tier and each
tier to `providers.claude.<tier>.model` and `.effort`. Both ship as `null`.

- **Model.** Pass the tier's `model` as the `Agent` call's `model`. The parameter is an enum (such
  as `sonnet`, `opus`, `haiku`, `fable`), so the models file holds one of the values the live schema
  lists; check the schema before filling it in. With `null`, leave `model` out:
  the agent then takes its definition's model, then `CLAUDE_CODE_SUBAGENT_MODEL`, then the main
  conversation's model.
- **A family alias is not a version.** An alias in the main model's family resolves to the main
  model's exact ID.
- **Record the model.** Write the model you requested into the roster's `model`, or the session's
  model when you left `model` out. `/tasks` in the CLI, or the desktop tasks pane, shows the model
  actually running. Once the agent's first turn is in, read the model that ran from the first
  assistant line of its `output_file`, its `message.model`, and correct the row when it differs;
  read no further into that file:

  ```text
  python3 -I -c "import json,sys
  for l in open(sys.argv[1]):
    d=json.loads(l)
    if d.get('type')=='assistant': print(d['message']['model']); break" OUTPUT_FILE
  ```
- **Effort.** Pass the tier's `effort` as the `Agent` call's `effort` (`low`, `medium`, `high`,
  `xhigh` or `max`); with `null`, leave it out and the agent takes its definition's effort, then the
  session's. `CLAUDE_CODE_EFFORT_LEVEL` overrides both. Record the effort you requested in the
  roster's `effort`. The parameter needs Claude Code v2.1.292 or later, and a resumed agent keeps
  it ([sub-agents](https://code.claude.com/docs/en/sub-agents)).
- **Which wins.** A tier's model and effort, passed per spawn, win over the agent type's own; with
  `null`, the type's own apply. Two settings win over the spawn: `CLAUDE_CODE_EFFORT_LEVEL` for
  effort, and `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, which ignores a per-spawn model.
- **Where the live schema has no `effort`,** every agent runs at the session's effort, set by
  `CLAUDE_CODE_EFFORT_LEVEL`, `--effort`, `/effort`, or settings (the per-model level under
  `modelSettings`, or `effortLevel`, which in user settings does not apply to Opus 5.5 and later);
  in the desktop app, by its effort control. An installed agent definition's frontmatter `effort`
  still sets effort per agent there. `printenv CLAUDE_EFFORT` in Bash shows the level in effect;
  write it into the roster's `effort`. The word `ultrathink` in a prompt nudges one turn and leaves
  the API effort unchanged.

## Your own agent types

With `agents.own_agents` `off`, the default, every agent spawns as a built-in type. With it on, an
agent may spawn as one of the user's own agent definitions, and `role_agents` maps a role to one
([config.md](../config.md)).

**Where definitions come from**, highest priority first; when two share a name, the higher wins
([sub-agents](https://code.claude.com/docs/en/sub-agents)):

1. managed settings, organization-wide;
2. the `--agents` flag, for the current session;
3. the project's `.claude/agents/`, found by walking up from the working directory, the closest
   winning;
4. `~/.claude/agents/`, for all of the user's projects;
5. an installed plugin's `agents/` folder.

`project` admits only the types defined in the project's `.claude/agents/`; `machine` admits every
type the session has.

**The session's list.** Claude Code lists the session's agent types for the orchestrator, in the
`Agent` tool's description or in a system reminder, one line each as
`- NAME: DESCRIPTION (Tools: ...)`, with later reminders for types added or removed (read from the
2.1.295 desktop engine). Pass a name as `subagent_type` exactly as listed. The list gives no source,
model or effort: find each type's definition file in the locations above and read its frontmatter
`model`, `effort`, `tools` and `disallowedTools`. A listed type with no file found, such as one from
managed settings or the `--agents` flag, shows its source as the session and its model and effort
as its own.

**Changes without a restart.** Claude Code watches `~/.claude/agents/` and `.claude/agents/`, and
the next spawn uses a new or edited definition within a few seconds. A restart is still needed for
the first definition in a newly created `agents` folder and for definitions in a folder added with
`--add-dir`; a session started with `--disable-slash-commands` watches neither folder.

**The fit check.** A type fits an agent only when all of these hold:

- it has write tools (`Edit`, `Write`) when the slice writes, and its definition sets no
  `isolation: worktree`, since the host route cannot reach a writing slice;
- it has `Bash`, for the status file;
- it can be resumed when the agent may park; `Explore` and `Plan` are one-shot;
- it does the work itself rather than handing it to another tool, such as a type that forwards the
  task to another provider's CLI, which would break one provider per run;
- its instructions leave room for the standing text: read the whole definition, and pass over a
  type whose body fixes its own output format, forbids parking or asking, or tells it to work
  beyond a given scope. When you cannot tell, fall back to `general-purpose`.

`(Tools: All tools)` passes the tool checks; a list, or `All tools except ...`, passes only with
the tools named. A type whose tools leave out `SendMessage` takes `report_to` `null`.

**Proposing a type.** With `own_agents` on, propose a fitting type per agent in the plan, where it
shows beside the agent's model and effort; the user's go covers it.

**A role mapped in `role_agents`** spawns with that `subagent_type` and with no `model` or `effort`,
so the definition's own apply, then the session's. Record the type as the roster's `agent_type`,
and the definition's model and effort, or the session's where it names none or `inherit`, as
`model` and `effort`; the plan shows all three. An agent whose roles map to different types spawns
as `general-purpose` at the deepest of their tiers.

**The fallback.** A mapped type that is missing from the session, outside what `own_agents` admits,
or unfit for the agent's slice spawns as `general-purpose` at the role's tier, and the plan notes
it on the agent's row.

## Chat forks

A chat fork is one agent that starts with a copy of this chat: the `Agent` tool's `fork` subagent
type, used for a task whose `fork` is true. It is not fork mode, the session setting under "How to
tell you are on this host", although fork mode on is what lets Claude request it. Facts below are
from the [sub-agents](https://code.claude.com/docs/en/sub-agents) page unless marked.

- **When you can request one.** Only where fork mode is on: the `Agent` tool has no
  `run_in_background`. The desktop engine runs with fork mode off and refuses one: on 2.1.295,
  `subagent_type: "fork"` returned `Agent type 'fork' not found. Available agents: ...`. A deny
  rule `Agent(fork)` blocks forks even where fork mode is on. Where you cannot fork, or the spawn
  returns that error, plan the agent fresh: put the context in its task, or in a packet when the
  packet conditions apply, and the plan says `fork not available here`.
- **The call.** `subagent_type: "fork"`, a `description` as for any agent, and as `prompt` the whole
  text `ao.py package` prints: a fork still receives the standing text, its packets, its roles and
  its task. Leave out `model`: this host's `Agent` schema describes it as "Ignored for
  subagent_type: "fork" -- forks always inherit the parent model", and the page says a fork runs on
  the main session's model. Leave out `effort`, which the page documents for non-fork subagents
  only. `isolation: "worktree"` is accepted for a fork, as for any agent.
- **What it inherits.** The main session's system prompt, its exact tool pool and its whole
  message history, so its first request reads the main chat's prompt cache. A fresh agent starts a
  cache of its own.
- **As it stands.** The copy is the conversation at the moment of the spawn. After a compaction,
  plan for a fork that sees the summary and the turns since; exactly what a fork inherits then is
  unverified on this host, so put any earlier detail the agent needs in its task or a packet, which
  can be built from the transcript (next section).
- **No fork from a fork.** A fork cannot fork again. At the nesting limit it keeps the `Agent` tool,
  which then returns an error. Give every fork `layers_below` 0 until a check shows it can spawn
  other agents.
- **Record it.** In the roster row: `agent_type` `fork`, `fork` true, `model` the main session's
  model, and `effort` the session's level (`printenv CLAUDE_EFFORT` in Bash). The role's tier, the
  models file and `role_agents` do not apply to a fork.
- **The user's own commands are separate.** `/subtask` forks from the prompt line, and `/fork`,
  `/branch` and `/rewind` copy or roll back a whole session. The skill forks only through the
  `Agent` tool.

## Packets from earlier turns

- **The transcript.** Claude Code saves each session's main conversation as JSON Lines at
  `~/.claude/projects/<project folder>/<session id>.jsonl`. The project folder is the session's
  start directory with every `/` replaced by `-`, such as `-home-dev-projects-ledger` for
  `/home/dev/projects/ledger`, and the session id is the UUID in the session's scratchpad path.
  Both were checked on 2026-10-13 against one desktop session's file, by structure alone.
- **Compaction keeps the file.** An in-session compaction adds a `compact_boundary` line and a
  summary line, and the turns before it stay in the file, so a packet can still be built from turns
  the live chat has lost. A session continued after the context limit starts a new file. The
  script reads any session file, so take a range from the file that holds it.
- **Messages typed while you work.** A message the user sends while you are mid-turn is saved as a
  `queued_command` attachment with `origin.kind` `human`, not as a user line; the script reads it
  as a turn of the user's (seen on the desktop engine and the CLI, 2.1.217 to 2.1.295).
- **An agent's transcript.** Each subagent's own transcript is
  `~/.claude/projects/<project folder>/<session id>/subagents/agent-<agentId>.jsonl`, the file its
  spawn result's `output_file` links to (seen on 2026-10-13, desktop 2.1.295). Its first user
  message is the spawn message. A message you send with `SendMessage` appears in it as a user line
  marked `isMeta` with `origin.kind` `coordinator` when it resumes the agent, and as a
  `queued_command` attachment with that origin when the agent is running (seen on the desktop
  engine, 2.1.215 to 2.1.295). The script labels the spawn message and each such message
  `orchestrator` and the agent's own text `agent`, and shows the spawn message as one line. Build
  a handoff packet from it ([protocol.md](../protocol.md)) only when the successor needs more than
  the earlier agent's return.
- **List, then write.** `python3 <base directory>/scripts/claude_transcript.py TRANSCRIPT --list`
  prints each turn with its number, time, speaker and a short preview, and marks each compaction
  point. Agree the range with the user, then write the packet with `--turns A-B --out
  RUN/packets/NAME.md --name NAME --about TEXT`. Its `Source` names the transcript by its file
  name without `.jsonl`: the session id, or `agent-<agentId>`. Tool output stays out unless you add
  `--with-tool-output`; ask the user first, since it carries file contents and secrets.
- **One format.** The script reads these transcripts and no other format. It tells a session's
  file from a subagent's by structure, and its header says how and which lines open a turn.

## Access

A task's `access` names capabilities; on this host they map to these tools: `read` to `Read`,
`Grep` and `Glob`; `edit` to `Edit`, `Write` and `NotebookEdit`; `shell` to `Bash` (or
`PowerShell`); `web` to `WebFetch` and `WebSearch`; `spawn` to `Agent`.

- **Only an agent type narrows tools.** The `Agent` call has no parameter that narrows an agent's
  tools; a definition's `tools`, `disallowedTools` and `permissionMode` do. Choose the narrowest
  fitting type, by the fit check under "Your own agent types". Restrictions on capabilities the type
  exposes beyond `access.tools` hold by instruction; name those restrictions in `held_by`.
- **What a built-in type enforces.** Every built-in type that passes the fit check has `Bash`, and
  `general-purpose` has every tool, so on it read-only work, the read paths, no web and no network
  all hold by instruction.
- **What one of the user's own types can enforce.** With `agents.own_agents` on, a type whose
  definition lists `disallowedTools: WebFetch, WebSearch`, or a `tools` list without them, withholds
  the web tools, so `web` left out of `access.tools` is enforced. The shell can still reach the
  network, so `network` with `allowed` false holds by instruction, and so do read paths.
- **A chat fork** has the main session's exact tool pool, so its `access` holds by instruction
  alone.
- **Write `held_by` from this,** naming the type, such as "The web tools are withheld by the agent
  type reference-reader; the read paths and the network hold by instruction."

## Isolation

The tiers map to this host as follows.

- **none**: leave `isolation` out. The agent starts in the main conversation's current directory and
  works in place, and the orchestrator commits (`may_commit` false). It is the only tier outside a
  git repository.
- **ephemeral, self-made route**: the route for every writing agent on a worktree tier. Create the
  worktree before you package the task, with `git -C REPO worktree add -b BRANCH PATH BASE`, where
  REPO is the repository the agent's slice is in, as
  [isolation.md](../isolation.md) describes, set the task's `workdir` and `branch`, point its `scope` and `done_when` checks at
  absolute paths inside the worktree, and leave `isolation` out. There is no `cwd` parameter, so the
  agent starts in the main conversation's directory and enters `workdir` itself, using absolute
  paths as the standing text requires. As at tier none, the scope is the boundary on this route.
- **ephemeral, host route, for an agent that writes nothing**: `isolation: "worktree"`. Claude Code
  creates `<repo>/.claude/worktrees/agent-<agentId>` on branch `worktree-agent-<agentId>`. `<repo>`
  is the git root of the main conversation's current directory, not the slice's folder, so make sure
  that directory is inside the target repository before the spawn. Outside a git repository, with no
  `WorktreeCreate` hook, the spawn fails with `Cannot create agent worktree: not in a git repository
  and no WorktreeCreate hooks are configured.` The agent's edits and commands aimed at the main
  checkout are refused, and the worktree's path exists only once the spawn returns, so a task
  written before the spawn cannot name it. A writing agent on this route could not reach its
  `scope`; use the route only for a task with an empty `scope`. Leave the task's `branch` and
  `workdir` null, then write `worktree-agent-<agentId>` and the worktree path into the roster row.
- **session**: use the self-made route, so you choose the path and the branch name, and keep the
  worktree when the agent finishes.
- `isolation: "remote"` is out of scope for this skill; pass `"worktree"` only.

**Clean-up on the host route.** When the agent finishes having changed nothing, the host removes the
worktree and its branch. A worktree with changes stays, locked while the agent runs, until a periodic
sweep after `cleanupPeriodDays`, and that sweep never removes work. The finished result carries
`worktreePath` and `worktreeBranch` only when the worktree was kept. Close each kept worktree
yourself, in the order [isolation.md](../isolation.md) gives.

**How the host picks a new worktree's base.** This applies to the host route only; on the self-made
route, BASE is whatever you name. Before each spawn with `isolation: "worktree"`, work the base out
yourself:

1. **Read the setting.** Take `worktree.baseRef` from the first of these files that sets it:
   `<repo>/.claude/settings.local.json`, `<repo>/.claude/settings.json`, then the user settings file
   (`~/.claude/settings.json`, or `settings.json` in `$CLAUDE_CONFIG_DIR` when that is set). With
   none set, the value is `"fresh"`. The accepted values are `"fresh"` and `"head"`; a branch name
   is not one. The desktop engine loads the same user, project and local sources.
2. **`"head"`** resolves to the current local `HEAD` of the main conversation's directory; inside a
   worktree, to that worktree's `HEAD`.
3. **`"fresh"`** resolves to the default branch of the remote named `origin`; Claude Code reads no
   other remote. It takes the branch `origin/HEAD` points to, else `main` when `origin/main` exists
   locally, else `master` when `origin/master` does, else the name `main`. When that branch's
   remote-tracking ref exists locally, the worktree starts from it, fetched first when the
   repository's last fetch is more than 24 hours old (that fetch gives up after 5 seconds). When it
   does not, Claude Code fetches the branch at the spawn and falls back to local `HEAD` only when
   that fetch fails: no remote named `origin`, no such branch there, or no network.
4. **Count what the agent would miss** with `git rev-list --count <base>..HEAD` in the main
   conversation's directory, using the base from step 2 or 3. When the preflight of
   [git_lanes.py](../../scripts/git_lanes.py) reports `remote_name` `origin` and a `remote_head`
   equal to that base, its `commits_not_on_remote_default` is the same count. When the base is not
   recorded locally, the count cannot run, so treat the miss as unknown. Above zero or unknown, take
   the self-made route with the current branch as BASE, or ask the user whether to set
   `worktree.baseRef` to `"head"` (`/config` offers it as "Worktree base ref" and writes it to the
   user settings file); a durable setting is theirs to choose.

So in a repository with an `origin`, a fresh worktree starts from the default branch rather than the
branch in front of you, and lacks unmerged and unpushed work.

**Files a worktree lacks.** A `.worktreeinclude` file at the project root, in gitignore syntax, makes
Claude Code copy the files that match it and are gitignored into each worktree it creates for a
subagent. A `WorktreeCreate` hook bypasses it. On the self-made route, give the agent a setup step
for the files it needs. On the host route, repository filter drivers are skipped, so Git LFS files
arrive as pointers.

## Watching and completion

- **Let completion notify.** Background is the default, and each report arrives in a later turn on
  its own. Between notices the orchestrator stays idle.
- **Read thresholds from status files** with `ao.py status read FILE --threshold TEXT`.
- **Leave `output_file` unread**, apart from the one model line "Models and effort" reads. It is a
  symlink to the agent's full JSONL transcript under `~/.claude/projects/`, and it grows with
  everything the agent reads. For a handoff packet, `claude_transcript.py` reads it, and you read
  only its list and the packet.
- **Nested agents.** In the interactive CLI a subagent waits for its own background children. In
  `claude -p` and Agent SDK sessions it does not, and a child that finishes after its launcher
  reports to the main conversation. So an agent whose task's `layers_below` lets it spawn gives its
  children `run_in_background: false` where its schema has that parameter, and their reports come
  back to it as tool results.
- **A scripted orchestrator.** `claude -p` stays open while background agents run, for at most 10
  minutes of idle waiting (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`), then stops them and drops their
  partial results. It emits one `result` per turn, so each report arrives in a later `result`.
- **Hand-back ends the run.** From 2.1.285, a subagent in auto mode ends its run as soon as it hands
  its report back; see "Old patterns".

## Resuming and correcting an agent

- **Answer a parked agent** with `SendMessage` to its `agentId`. Write the first line as
  `Answer to <ask id>: <decision>`, then any packet the answer carries, then the `answer` as one
  fenced json block, last. The agent resumes in the background with its transcript, so the answer
  need not restate the task.
- **Correct a running agent** the same way; it reads the message at its next tool round.
- **Answer a request** while the agent works, the same way: `SendMessage` to its `agentId`, the
  first line `Answer to request <request id>: <decision>`, then the `answer` with `request_id` set.
  The agent reads it at its next tool round, and nothing parks. Append the message to its
  `spawn_file`. The sub-agents page says a running agent is reached by the agent ID its spawn
  returned.
- **Stop a running agent** with `TaskStop` and its ID. An unknown ID returns an error that lists the
  running background agents by ID and description.
- **Answer in batches under the cap.** A resume takes a running slot without checking the limit of
  20, so answering many parked agents at once can exceed it.
- **Respawn** an `Explore` or `Plan` agent, or one the user stopped, with the prior return as
  context.
- **After a restart,** resume the same session; its subagent transcripts last `cleanupPeriodDays`
  (default 30).

## Showing the run

- **Desktop Code tab:** call `mcp__visualize__read_me` once with the modules the view needs and the
  `platform`, then render each view with `mcp__visualize__show_widget`. The desktop-only tool
  `mcp__ccd_session__read_widget_context` reads a rendered widget's state.
- **CLI:** structured text, as [widgets.md](../widgets.md) describes.

## Running the skill's scripts and where a standalone skill is discovered

**Discovery.** Claude Code finds a skill at:

- `~/.claude/skills/<name>/SKILL.md`, for every project on this machine, in the CLI and in desktop
  local sessions;
- `.claude/skills/<name>/SKILL.md` in the start directory and in each parent up to the repository
  root;
- `<subdir>/.claude/skills/` nested in the project, once Claude touches a file there or after
  `/add-dir`;
- `.claude/skills/` inside a directory added with `--add-dir`;
- enterprise managed skills.

A symlinked skill folder is followed. A skill folder anywhere else is found only when a plugin serves
it, so place or symlink this folder into one of the locations above.

**Running scripts.** When the skill is invoked, Claude Code prepends
`Base directory for this skill: <absolute path>` to it. Run every script by absolute path from that
directory, such as `python3 <base directory>/scripts/ao.py config`, and set each task's `ao_script` to
`<base directory>/scripts/ao.py`. The scripts find their own folder through `__file__`.
`${CLAUDE_SKILL_DIR}` is substituted only inside SKILL.md and `allowed-tools`, is unset in Bash and is
never expanded in reference files, so this skill uses the base directory instead.

## Traps

Each fails silently or looks like success.

1. **No `name` without agent teams.** The default `Agent` schema has no `name`, although a docs page
   describes one. Address agents by `agentId`.
2. **Agent teams change what spawns.** With `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` on, a named spawn
   from the main conversation of an interactive CLI session becomes a full teammate session unless
   the call itself passes `isolation`. Agent teams are a CLI feature, absent from the desktop app.
   Run the skill with the variable unset or `0`.
3. **`run_in_background` vanishes** where fork mode is on (the interactive CLI default) or background
   tasks are disabled. Plan on background agents on both surfaces.
4. **`model` vanishes** when `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is set, and every agent runs the
   forced model.
5. **Per-spawn effort needs v2.1.292 or later.** On an older engine the `Agent` schema has no
   `effort`, and a tier's effort in the models file is recorded, not applied.
6. **Worktree isolation follows the main conversation's directory,** which moves when the main
   conversation runs `cd`.
7. **A fresh worktree starts from `origin`'s default branch,** not the branch in front of you,
   unless `worktree.baseRef` is `"head"`. It starts from local `HEAD` only when the fetch of that
   branch fails, as in a repository with no remote named `origin`.
8. **Worktrees with changes stay** until the retention sweep. Close each one yourself.
9. **Claude Code tells every subagent not to write report or summary .md files** in a note it appends
   to the system prompt. Name every file you want written in the task: the `status_file` always, and
   a `report` path when you want a longer report.
10. **Standing text in `prompt` can be compacted away.** The `spawn_file` is the agent's way back.
11. **`output_file` is the full transcript.** Reading it floods your context.
12. **Background subagents cannot list agents.** Without names, a child knows only `main`.
13. **`"main"` works only from a background subagent.** Sent from the main conversation it fails with
    a note that "main" addresses you; address a child by its `agentId`.
14. **Resumes bypass the concurrency cap.**
15. **An agent the user stopped refuses a resume.** One stopped with `TaskStop` accepts it.
16. **In auto mode the `Agent` result is a stub.** A hook or script that reads its `content` finds no
    report; the report is the `SubagentHandback` message.
17. **A background agent's permission grant is session-wide.** Answering its prompt with "don't ask
    again" applies to the main conversation too.
18. **Nested reports can land in the main conversation** in `claude -p` and Agent SDK sessions.
19. **`claude -p` drops slow background agents** after 10 minutes of idle waiting.
20. **Two engines on one machine.** A fix in the changelog may exist in the CLI and not in the
    desktop's bundled engine, or the reverse.
21. **The environment block can disagree with the working directory.** An agent's "Is a git
    repository" line has been observed wrong; run `git rev-parse` to decide.
22. **`SendMessage` costs a `general-purpose` child one extra call,** since it is deferred there and
    loads through `ToolSearch`.
23. **A `claude -p` run emits one `result` per turn.** A script that stops at the first one loses
    every report.
24. **Startup is not free.** Startup context varies with the agent type and the tools and MCP
    servers loaded. Count that overhead before choosing the fan-out.
25. **A file named `claude.md` loads as project instructions.** On a case-insensitive disk (the
    macOS default) Claude Code reads it as a nested `CLAUDE.md` once a session touches its folder.
    Name every file the run writes, task files and notes included, so that it matches neither
    `CLAUDE.md` nor `AGENTS.md` in any case.
26. **Fork mode is not a chat fork.** Fork mode is a session setting that runs every subagent in
    the background; a chat fork is one agent spawned with the `fork` type. Fork mode on is what
    makes the `fork` type available, so a desktop session, with fork mode off, has none (refused on
    2.1.295).
27. **A chat fork carries the whole chat.** Everything said in this conversation reaches it,
    private context included, and only its final report comes back.

## Not yet verified

Each item below is open. Treat it as unverified until a check runs.

- A child's mid-run message to `"main"` inside the desktop Code tab. It was run live with
  `claude -p` only; parent-to-child messages and resumes were seen in the desktop.
- That nested children in the desktop report to the main conversation, as in Agent SDK sessions. The
  desktop engine classifies itself as non-interactive, so this is expected, not tested.
- What `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` does inside the desktop engine.
- The layout inside a completion notification (a `<task-notification>` element with `<task-id>`,
  `<status>`, `<summary>`, `<result>` and `<usage>`, statuses `completed`, `failed`, `killed` or
  `blocked`). It was read from the binary, not observed in full.
- Resuming an agent from a session run with `--no-session-persistence`. No transcript is written
  there, so the resume is expected to fail.
- The `Agent` call's `effort` parameter. It was seen in a desktop session's live schema on
  2026-10-13 and in the sub-agents docs, not yet in the CLI's live schema; check it there before
  relying on it.
- That a nested agent's foreground children report back to it in the desktop app.
- The format and placement of the session's agent type list. They were read from strings in the
  2.1.295 desktop engine, not observed in the CLI.
- Whether a per-spawn `effort` applies to a chat fork. The sub-agents page documents `effort` for
  non-fork subagents only, so the skill leaves it out.
- Whether a chat fork can spawn agents that are not forks. Until a check shows it can, a fork gets
  `layers_below` 0.
- Whether `CLAUDE_CODE_FORK_SUBAGENT=1` makes the desktop engine accept `subagent_type: "fork"`.
  Without it, 2.1.295 refuses one.
- That a chat fork spawned after a compaction gets the summary and the later turns, not the
  earlier ones. It follows from the page's "the entire conversation so far"; it was not observed.
- The transcript's folder name for a project path holding characters other than letters, digits,
  `-` and `/`.
- How a `SendMessage` message appears in an agent's transcript in the CLI. Every coordinator line
  and `queued_command` attachment checked came from the desktop engine.

## Old patterns

Behaviour of earlier releases, for a machine that has not upgraded.

- Before 2.1.285, a subagent in auto mode did not end its run when it handed its report back.
- `TaskOutput` was removed in 2.1.277. Read a background agent's report from its completion
  notice, and its progress from its status file.

## Related

- [SKILL.md](../../SKILL.md): the run checklist and the capability table these operations fill.
- [standing.md](../../assets/standing.md): the standing text every agent receives in `prompt`.
- [protocol.md](../protocol.md): the spawn, the mid-run messages and the return this host carries.
- [isolation.md](../isolation.md): the tiers, how a branch closes, and the self-made worktree route.
- [widgets.md](../widgets.md): the views, as a widget in the desktop and as structured text in the CLI.
- [config.md](../config.md): the settings and the models file's layering, including
  `agents.own_agents` and `role_agents`.
- [models.json](../../config/models.json): the tier for each role and the model for each tier.
- [ao.py](../../scripts/ao.py): `package`, `packets`, `status`, `roster`, `check` and `config`.
- [git_lanes.py](../../scripts/git_lanes.py): the preflight, whose `commits_not_on_remote_default`
  counts what a worktree based on the remote's default branch would miss.
- [claude_transcript.py](../../scripts/claude_transcript.py): packets built from earlier turns of this
  host's saved transcripts, a session's or an agent's.
- [openai.md](openai.md): the same headings for the OpenAI host.
- [antigravity.md](antigravity.md): the same headings for the Antigravity host.
