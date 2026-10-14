# The protocol

How an orchestrator and its agents talk. There are three protocols and they stay apart: the
spawn, which hands an agent its standing text and its task; the messages that travel between spawn
and return (an agent's notice, and the orchestrator's answer); and the return, which ends every
agent turn and carries every ask. Two records sit beside them: the status line an agent appends as
it goes, and the roster row the orchestrator keeps for each agent.

Every structured message is a JSON object with `"schema_version": 1` and a `kind` that names its
definition in [protocol.schema.json](../schemas/protocol.schema.json). Objects stay open: a reader
ignores fields it does not know. Validate a message with the `check` subcommand of
[ao.py](../scripts/ao.py) before you send or act on it. Read this file when you write a task, when
an agent asks, and when you judge whether an agent was right to stop.

## Contents

- One message, one shape
- The spawn
- Context: packets and chat forks
- Access: what an agent may use
- Status lines
- When an agent hits something it does not know
- Parking and notices
- The return
- Answering
- The roster row
- Worked examples, one per kind

## One message, one shape

| Kind | From, to | When | Carried as |
|---|---|---|---|
| `task` | orchestrator to agent | at spawn | a `<task>` element in the spawn message, a file at `task_file`, and the saved message at `spawn_file` |
| `ask` | agent to orchestrator | the agent needs a decision | inside the return, when the agent parks |
| `answer` | orchestrator to agent | a decision is made | the message that resumes a parked agent, or a message to a running one |
| `notice` | agent to orchestrator | something the orchestrator must know now | a mid-run message, only when the task's `report_to` is set |
| `return` | agent to orchestrator | the end of every turn | the agent's final message, one fenced json block |
| `status_line` | agent to its status file | the moment something becomes true | one JSON Lines line |
| `roster_row` | orchestrator to the roster | each change in an agent's state | one patch line in a JSON Lines file, folded into one row per agent |

Field names are snake_case and enum values are lowercase. Paths are absolute and use forward
slashes. Times are RFC 3339 UTC at seconds precision with a `+00:00` offset; readers also accept a
trailing `Z`.

## The spawn

The spawn message has up to four parts, in this order. `python3 scripts/ao.py package TASK_FILE`
prints it ready to send, from the task file you pass.

1. **The standing text**: [standing.md](../assets/standing.md) without its Related section. It is
   the same for every agent and every role: the escalation ladder, status logging, parking, notices
   and the return rules.
2. **The context packets**: each packet the task's `packets` lists, in that order, inside a
   `<packet>` element with its header, under the heading `## Context packets`. Left out when the
   task lists none. See "Context: packets and chat forks".
3. **The roles block**: the description of each role in the task's `roles`, and only those, read
   from `$defs/role` in [protocol.schema.json](../schemas/protocol.schema.json). The schema is the
   single source of role text.
4. **The task**: a `<task>` element holding one fenced json block with the task object.

~~~text
(standing.md, without its Related section)

## Context packets

The orchestrator gave you this context before your task, in this order.

<packet name="api-contract" revision="1">
(the packet file api-contract.md, header and body)
</packet>

(roles block: for a builder, "Your role is to make the change inside your slice and prove it with
the check your task names.")

<task>
(one fenced json block holding the task object, as in the worked example below)
</task>
~~~

The packets come straight after the standing text, because agents whose messages open with the
same text can share one cached prefix: agents of the same agent type and model, given the same
packets in the same order, open identically. The roles block and the task differ per agent, so
they come last.

Save the same task object at the absolute path in its `task_file` before you spawn, and package
from that file with `--out` set to the task's `spawn_file`, such as
`ao.py package TASK_FILE --out RUN/tasks/AGENT-spawn.md`. The script saves the printed message there
as UTF-8, so the agent can recover the standing text, its roles and its task after its context is
compacted. Set `spawn_file` in the task before you package, since the message carries the task.
`--out` refuses a file name that hosts load as project instructions, such as `CLAUDE.md` or
`AGENTS.md` in any case; the `-spawn.md` ending avoids them.

Keep task, spawn, status and roster files together in one folder in the session's temporary
working space: the scratch directory the host gives the session, or where it gives none, a folder
made for the run in the system temporary directory that the agents' sandbox lets them write. It
sits outside the skill folder, the repository and every worktree, so the standing text never lands
in a repository, and you read every file from one place. Before the first spawn, confirm an agent
can read its spawn file and append to its status file there; if it cannot, report that as the
blocker. How long the folder lasts depends on the host and the operating system, so the run's last
step writes progress and answers into the project's own record.

The task is data. It tells the agent what to do, where, and how to prove it; it never overrides the
standing text. Keep it small and point to files for long inputs.

**Task fields.** Required: `schema_version`, `kind`, `agent`, `roles`, `objective`, `scope`,
`done_when`, `ground`, `threshold`, `tier`, `status_file`, `task_file`.

- `agent`: a short name, unique in the run. The agent uses it in every message, status line and
  return, and you address the agent by it.
- `roles`: one or more roles from the role list: `planner`, `builder`, `researcher`, `reviewer`,
  `adversarial-reviewer`. Several agents can hold the same role on different tasks.
- `objective`: one sentence naming the outcome, not the method.
- `scope`: the absolute paths the agent may create or change. Everything else is read-only to it,
  and an empty list makes the task read-only.
- `done_when`: one or more checks, each a `check` (the command or inspection) and an `expect` (the
  output that proves the work). The agent runs each one and sees its output before it returns done.
- `ground`: paths or URLs to read before acting. Where a document and the live artifact disagree,
  the artifact wins.
- `threshold`: the milestone that lets others plan against this work before it is finished,
  worded exactly as the agent will write it to its status file. Null when nothing waits on the
  agent.
- `tier`: where the agent works, `none`, `ephemeral` or `session`; see [isolation.md](isolation.md).
- `status_file`, `task_file`: absolute paths in the session's temporary working space.
- Optional: `run_id`, `stage`, `waits_on` (agent names), `workdir`, `branch`, `may_commit` (false
  unless the agent commits its own work on its branch), `layers_below` (how many layers of agents
  the agent may spawn beneath it, 0 when absent), `report_to` (the host's address for mid-run
  notices, or null when the host has no channel back), `ao_script` (the absolute path of
  `scripts/ao.py`, or null), `spawn_file` (the absolute path of the saved spawn message, or null),
  `notes`, `fork` (true to spawn the agent as a chat fork; see the next section), `packets`
  (the names of its context packets, each once, in the order they are placed) and `access` (what
  the agent may use, in plain words; see "Access: what an agent may use").

The checks a schema cannot express are made in code by `ao.py check`: every path is absolute,
`roles` and `done_when` are non-empty, each packet name is well formed and listed once, a task
with `fork` true has `layers_below` 0, every sentence and reason in `access` holds some text, and
`access.tools` lists `edit` only with a non-empty `scope` and `spawn` only with `layers_below`
above 0.

**Layers.** `agents.max_layers` in config sets how many layers of agents a run may have, and at the
shipped `1` only you spawn. For a task you spawn directly, set `layers_below` to the smaller of
`agents.max_layers` and the host's nesting cap, minus 1; with no host cap, use
`agents.max_layers` minus 1. A chat fork gets 0, and an agent's child gets one less than its
parent. Each host SOP names its cap. An agent with `layers_below` above 0 may spawn agents for
parts of its own slice under the same standing text, each with a scope inside its own and a
`layers_below` one less; it answers their asks or raises them as its own, and its return answers
for their work. Your roster holds the agents you spawned; theirs reach you through that return.

## Context: packets and chat forks

An agent starts fresh by default: the spawn message, plus what its host loads on its own, such as
project instruction files. The plan chooses two additions per agent, and the plan view shows the
choice beside each agent's tier: context packets, and a chat fork. Local files and tools stay where
they are: `ground` lists what to read first, and the agent type gives the tools.

**When to use a packet.** Context is worked out in the chat; a packet is what you write from it.
Put context in the task, as `notes` or a `ground` file, when one agent needs it once. Propose a
packet when the same context goes to two or more agents, when it must outlast your own compaction,
or when the user asks for one, as in "save what we just settled as grounding".

**A packet file** is `packets/NAME.md` in the run's folder, beside the `tasks/` and `status/`
folders, so it is temporary like every run file. It is Markdown written for a person to read, and
it opens with a header:

~~~text
# Packet: grounding
Revision: 2
About: What the user settled about the export format, so every export agent starts from the same decisions.
Source: the chat, as settled with the user on 2026-10-02
Kept: no

- A row per ledger entry, with a header row: date, account, amount, currency.
- Dates are written as YYYY-MM-DD; a field that contains a comma is quoted.
~~~

- `NAME`: lowercase letters, digits and hyphens, starting with a letter or a digit, the same in the
  title line and the file name. `claude` and `agents` are refused, since `claude.md` and
  `agents.md` load as project instructions.
- `Revision`: 1 for a new packet. Each update adds 1.
- `About`: one plain sentence saying what this context is and why agents get it.
- `Source`: where it came from, in words, such as "the chat, as settled with the user on
  2026-10-02", "agent export-api's return" or "turns 12-20 of transcript SESSION_ID".
- `Kept`: `no` for a packet of this run only, `yes` once the user keeps it.
- The header ends at the first blank line. The body follows, and it is never empty.

`ao.py package` reads each packet the task lists from `packets/` beside the task file, or, when that
folder is absent, from `packets/` in the folder above it, which is the run's folder when task files
sit in `tasks/`; `--packets DIR` names the folder outright. A missing or empty packet, or one whose
header does not parse, ends the command with exit 1 and a `Fix:` line, and nothing is written to
`--out`. `ao.py packets DIR` prints each packet in a folder with its name, revision, about, source,
kept and size in bytes, for the packets view.

**Updating a packet.** Rewrite the file, add 1 to `Revision` and set `Kept: no` until you copy that
revision to the project again. An agent already running keeps the revision it was given. It gets
the new one only when you or the user decide it needs it, as an answer whose `packets` names the
packet and its new revision. The message carries the packet's text before the answer's json block,
in a `<packet>` element as the spawn message carries it, so the answer stays the last json block.
Append that message to the agent's `spawn_file` like every answer, and set the new revision in the
agent's roster row.

**A return as a packet.** An agent's return, or the report it names, can be saved as a packet for
agents in later stages, such as `api-contract` from the return of `export-api`, with `Source`
naming the agent. It replaces re-describing upstream work in each next-stage task.

**Keeping a packet.** When the user says to keep a packet, copy it to
`.agent-orchestrate/packets/NAME.md` at the project root, and set `Kept: yes` in that copy and in
the run's. Then tell the user what git does with the file, because a packet may hold private chat.
Outside a git repository, where `git -C ROOT rev-parse --show-toplevel` fails, nothing tracks it.
Inside one, with PATH the copy's path, `.agent-orchestrate/packets/NAME.md`, `git -C ROOT ls-files
--error-unmatch PATH` exiting 0 means git tracks it; otherwise `git -C ROOT check-ignore -q PATH`
exiting 0 means git ignores it, and exiting 1 means it is untracked and a commit includes it only
once someone stages it. Report any other failure as unknown. A later run lists the kept packets in
its packets view, with `ao.py packets ROOT/.agent-orchestrate/packets`. When one is attached to an
agent, copy it into the run's `packets/` folder first, so `package` reads the run's folder alone.

**Packets from earlier turns.** On Claude Code, [claude_transcript.py](../scripts/claude_transcript.py)
reads the session's saved transcript, which keeps the turns from before an in-session compaction,
and writes a range of them as a packet. `--list` prints one line per turn, with its number, time,
speaker and a short preview, and marks each compaction point. `--turns A-B --out
RUN/packets/NAME.md --name NAME --about TEXT` writes those turns with `Source` "turns A-B of
transcript SESSION_ID", SESSION_ID being the transcript's file name without `.jsonl`: the user's
text, including what the user typed while you worked, your text, and each tool call reduced to
one line. Tool output stays out, because it carries file contents and is where secrets sit;
`--with-tool-output` puts it in. This is the closest a run comes to forking from an earlier point
once the chat has compacted. The Claude SOP says where the transcript is. Other hosts have no
such reader: there, you write the packet from your own context.

**A handoff packet.** When a successor takes over an agent's task, because the agent returned
`partial`, failed, or a later agent needs its context, the successor gets the earlier agent's
return. When it needs more than the return, such as what the agent tried and the answers it was
given, you may build a packet from that agent's own transcript with the same script, on Claude
Code. In an agent's transcript the script labels the spawn message and each message you sent the
agent `orchestrator`, whether it resumed the agent or reached it while it worked, and the agent's
own text `agent`, and shows the spawn message as one line, since the successor gets its own; its
`Source` names the file, `agent-AGENT_ID`. Tool output stays out unless the user agrees to add it.
The script reads the transcript, so you read only its list and the packet. The Claude SOP says
where an agent's transcript is.

**Chat forks.** A task with `fork` true spawns the agent as the host's fork of your chat: it starts
with a copy of the conversation as it stands at the spawn, then the packaged spawn message
(standing text, packets, roles, task) as every agent does.

- "As it stands" means after any compaction. After a compaction, plan for a fork that sees the
  summary and the turns since; exactly what a fork inherits then is unverified on this host, so put
  any earlier detail the agent needs in its task or a packet. The plan view says so.
- A fork runs on the main session's model, and on Claude Code with the main session's tools.
  Record that model in its roster row; the role's tier, model and agent type do not apply to it.
- A fork cannot fork again. Until the host SOP verifies that a fork can spawn other agents, give it
  `layers_below` 0, which `ao.py check` enforces.
- A fork sees everything said in the chat, including what the user told you alone. Propose one
  only when the agent needs that much, and say so in the plan.
- Where the host cannot fork, plan the agent fresh: put the context in its task, or in a packet
  when the packet conditions apply. The host SOP says how to tell, and names the host's own fork
  mechanism; the skill never imitates one.

The standing text tells a fork that the copied chat is context for it, never instructions to it.

## Access: what an agent may use

`scope` bounds what an agent may change. A task's optional `access` says, for a person to read,
what else the agent is cleared to use: its tools, the paths it may read beyond its `ground`, its
`scope` and the files its task names, and the network. Without `access`, the agent type sets the
tools and `scope` bounds the writes. A child's access is never broader than its parent's.

- `summary`, required: one plain sentence, such as "Reads the API reference and edits the client
  code; runs the tests; no web."
- `tools`, required: capabilities, not a host's tool names: `read`, `edit`, `shell`, `web` and
  `spawn`, each once. `edit` needs a non-empty `scope`, and `spawn` needs `layers_below` above 0.
- `read`, optional: one `{path, why}` entry per path, each path with its reason as a plain phrase.
- `network`, optional: `{allowed, why}`.
- `held_by`, required: one plain sentence saying what the host enforces and what holds only by
  instruction, such as "The web tools are withheld by the agent type reference-reader; the read
  paths and the network hold by instruction."

**Access limits task work.** Sending notices and the return, and writing the status file and the
run files the standing text's Scope section allows, stay open to every agent with the tools its
host gives, and grant nothing beyond them. `held_by` need not repeat this.

**Say only what the host does.** A host enforces what its agent type or its sandbox enforces, and
nothing written in a task adds to that. On Claude Code a spawn cannot narrow an agent's tools and
only an agent type does. Choose the narrowest fitting type. Restrictions on capabilities the type
exposes beyond `access.tools` hold by instruction; name those restrictions in `held_by`. Every
built-in type that passes the fit check has a shell, so read-only work and read paths hold by
instruction there, and a chat fork has the main session's tools. On Codex every child inherits the
parent's sandbox, so `access` holds by instruction. The host SOPs give the detail. The plan view
prints `held_by` for each agent, and no access line may suggest enforcement the host does not do.

## Status lines

Each agent owns one status file in JSON Lines: UTF-8, one JSON object per line, each line ending in
a newline, appended and never rewritten. The agent is its only writer.

- `started` when the agent has read its task and begun.
- `milestone` each time something becomes true on the way to done.
- `threshold` the moment the task's threshold becomes true, with `summary` set to the threshold
  wording exactly. That exact match is what lets the orchestrator draft the next stage.
- `blocked`, `done` or `partial` as the agent returns, matching the return's `status`.

With `ao_script` set, the agent appends through the `status` subcommand of `ao.py` at that path,
which works from any working directory. With `ao_script` null, the agent appends the line by hand.

## When an agent hits something it does not know

Three moves, in this order. Asking is the last of them.

1. **Resolve it.** When the answer is reachable inside the scope and the ground (a file the agent
   may read, the live artifact, the output of a command it may run), the agent goes and gets it.
   This covers nearly every case.
2. **Assume it.** When the answer is out of reach but the choice is reversible, cheap to undo and
   leaves the slice the same slice, the agent decides, records the decision in the return's
   `assumed`, and keeps going. Naming, ordering, formatting and the shape of an intermediate are
   decided this way. An orchestrator who wanted otherwise says so after the return, which costs one
   message instead of a stalled run.
3. **Ask.** Only when one of the six triggers holds. The ask names it in `trigger`.

| `trigger` | Holds when |
|---|---|
| `outside_slice` | The answer lives outside the slice: getting it means touching something the task did not grant. |
| `costly_if_wrong` | Guessing wrong is expensive: irreversible, outward-facing, spends money, changes shared state, or throws away real work. |
| `ambiguous_task` | The task is ambiguous where it is load-bearing: two honest readings give materially different deliverables. |
| `contradicts_ground` | The live artifact contradicts the task, and the difference changes the job. |
| `missing_precondition` | Something the task assumed would exist does not, and the slice cannot proceed without it. |
| `permission` | Something was denied or blocked, or the slice needs more access than the task gives. The ask goes to the orchestrator, which takes it to the user. |

An ask carries a decision and nothing else. Handle each of these inside the slice instead:

- progress worth reporting: append a `milestone` status line;
- whether to continue: continue;
- whether the task was understood: start, and record any reading taken in `assumed`;
- a question already answered once: follow the answer;
- anything readable inside the slice: read it.

Several unknowns travel together: one return carries every open ask in `asks`, each with its own
`id`.

The `default` is the field that keeps the run moving. It turns an open question into a confirm or
redirect the orchestrator can settle in one word. It is a recommendation, not permission: silence
leaves the agent parked until the orchestrator answers and resumes it. An agent that cannot name a
default is usually looking at something irreversible, and says so in the question.

## Parking and notices

An agent raises something in one of two ways, and each has its own job.

**Park and ask.** Every ask travels this way, in the return. The agent finishes everything the
answer does not gate, appends a `blocked` status line, and ends its turn with a return whose
`status` is `blocked` and whose `asks` holds every open question. A parked agent costs nothing while
it waits, and the host's completion notice reaches the orchestrator. The answer resumes the agent
with its own context intact. Each ask's `need_by` says how soon the answer matters: `now` when the
gated work cannot move without it, or `before_milestone` with the milestone named in `milestone`.

**Send a notice.** The exception, sent mid-run and only when the task's `report_to` is set. It
carries what the orchestrator must know now and cannot usefully learn later, and its `reason` is
one of four:

- `failure`: a hard failure, such as a broken base, a tool that will not run, or a check that
  cannot pass for reasons outside the slice;
- `collision`: the slice collides with another agent's work;
- `wrong_work`: the work has turned out to be the wrong work;
- `request`: the slice needs more access than the task gives (below).

A notice does not block. `continuing` says whether the agent keeps working (true) or is stopping,
in which case a return follows (false). A notice carries only what the orchestrator needs to know;
a question that gates the agent's own work is an ask, and the agent parks with it.

**Send a request** when the slice needs a path, a tool or the network that its task does not give.
A request is a notice that asks without stopping:

- `id`: the agent name plus a counter, unique in the run, as for an ask; `need`: one plain sentence
  saying what more access is needed; `why`; and `meanwhile`: what the agent keeps doing. Optional:
  `paths_needed`, one `{path, why}` entry per path, and `tools`, from the same list as
  `access.tools`. `continuing` is always true.
- The agent keeps working on the rest of its slice. It parks only when nothing is left that it can
  do without the answer: it then returns `blocked` with an ask whose `trigger` is `permission` and
  whose `request_id` names the request.
- It batches related needs into one request, and never requests what its scope, its access or its
  ground already allows. That keeps requests rare.
- No answer means not granted. Like an ask's default, a request authorizes nothing by itself.

When `report_to` is null the host has no channel back: the agent sends no notices and reports
everything in its return. A need for more access then waits until the agent has done all it can
without it, and travels as an ask with the trigger `permission`. A failure it can work around goes on a `milestone` status line and into
the return; a collision, wrong work, or a failure it cannot get past ends the turn, as `blocked`
with an ask or as `partial`.

**Message framing.** A notice is plain text: a readable first line, then the notice object as one
fenced json block, which every notice carries. An answer sent to an agent takes the same shape,
with the answer object in the block; an answer that carries packets places each one, in a
`<packet>` element, between the first line and the block, so the block stays last. A plain
correction to a drifting agent may go as text alone, without a block. Write the first line for a
reader who sees nothing else, because some hosts preview only that line.

## The return

Every agent turn ends with a return: exactly one fenced json block holding one `return` object, and
nothing else in the final message. Readers take the last json fence in the message, so a header
line a host adds does no harm.

- `status`: `done` when the slice is finished; `blocked` when the agent stopped and waits on the
  orchestrator; `partial` when it stopped for any other reason, such as a turn limit or a failure
  it could not get past.
- `did`: up to three items, one line each.
- `files`: the absolute paths created or changed, empty when none.
- `assumed`: the decisions taken without confirmation, empty when none.
- `next`: one line, or null.
- `asks`: present and non-empty exactly when `status` is `blocked`.
- `verdict` and `findings`: from a reviewer or an adversarial-reviewer. Findings are ranked, most
  important first, and each names its evidence: a path read, a command and its output, or a URL.
- `report`: the absolute path of a longer report the task asked for, or null.

The orchestrator checks every return with `ao.py check` the moment it arrives. A return that fails
the check goes back to its agent with the error, by message.

## Answering

The orchestrator holds the plan, the other slices and the conversation the agent never saw, so it
answers most asks itself.

- **Answer in the turn the ask arrives.** A parked agent is holding up the run, and every agent
  waiting on its threshold waits with it.
- **Decide it.** Take to the user only what is theirs: money, anything outward-facing or public,
  anything irreversible, a real change of scope, and a denied permission. A `scope_add` that
  answers an `outside_slice` ask is yours to decide when it stays inside the objective; a need for
  more access is the user's.
- **Write the decision as an instruction.** Set `ask_id` and, when the answer picks an option,
  `option_id`. Give `because` only when it changes the agent's later judgement. Widen the scope only
  through `scope_add`, with absolute paths, inside the agent's `workdir` when it works in a
  worktree, and only with a path no other agent in its stage holds: compare each with their scopes
  as the plan's collision verdict does. When another agent holds it, refuse, or grant it once that
  agent has returned `done`, or `partial` with its slice accepted; a blocked agent keeps its paths.
  Add each granted path to the agent's roster row's `scope`. Empty or absent leaves the scope
  unchanged.
- **Answer once, then fold it in.** When the question would occur to any agent nearby, write the
  answer into the tasks not yet spawned and send it to the running agents it affects as an answer
  with `ask_id` null. The same question arriving three times means the task was a line short.
- **Fix the cause.** A repeated question means the task was wrong, not the agent. Correct the agent
  when the slice is right and the execution is off; respawn only when the slice itself was mis-cut.
- **An answer settles a decision, never a permission.** It is never approval for something the
  agent's own permission settings blocked, and blocked work never moves to a sibling agent to get
  around the block. Take the permission to the user.
- **Log it.** Add the ask and the answer to the agent's roster row, in `asks` and `answers`.

Deliver the answer as a message: a readable first line, then the answer in a fenced json block.
Resume a parked agent with it, and append the same message to the agent's `spawn_file` as UTF-8,
so an agent compacted later still has every answer it was given. Append with a file tool rather
than the shell's `>>`, which Windows PowerShell 5.1 writes as UTF-16LE. On a host that cannot
resume an agent, respawn it with the standing text, its task, its prior return and the answer. A folded-in answer reaches a running agent by
message where the host can message a running agent, and otherwise at its next resume. The host SOPs
([Claude](hosts/claude-code.md), [OpenAI](hosts/openai.md)) name the tool for each.

### Answering a request

Access is the user's to give, so every request, and every ask whose `trigger` is `permission`, goes
before the user. Review it first.

- **Review each request before it reaches the user.** Check four things:
  - **Collision.** Run the plan's collision verdict again for each path the agent would change,
    against the scopes of the other agents in its stage. A path another agent holds waits until
    that agent returns `done`, or `partial` with its slice accepted; a blocked agent keeps its paths.
  - **The host.** Whether the host can give it, as "Grant only what the host can give" below says.
  - **The slice.** Whether it still fits the slice. A need that changes what the agent delivers is
    a change of scope, and the user decides it as one.
  - **Anything else wrong with it**, such as a path it would change outside its `workdir` when it
    works in a worktree, a need its scope, access or ground already covers, or a reason that does
    not explain the path. A read outside its `workdir` is judged by its reason and what the host
    can give.
- **A `permission` ask with no request behind it gets the same review.** Answer it by `ask_id`
  alone.
- **Show your finding and a recommendation beside the request or the ask.** The asks view carries
  one line per check that found something, or one saying none did, and a recommendation. For a
  request, recommend `grant`, `refuse` or `grant with changes`. For a `permission` ask with no
  request behind it, recommend an option by its `id`, or `neither` when none is suitable, and say
  when that differs from the agent's `default`. The user decides.
- **Send the user's decision to the running agent** as an answer with `ask_id` null and
  `request_id` naming the request, so it reads it while it works: the host SOP names the tool for
  messaging a running agent. Log the request in the row's `requests` and the answer in `answers`.
- **An open request does not change the agent's state; a blocked return does.** Once the agent
  returns `blocked` on a request, show the request only inside its parked ask, answer with both
  `ask_id` and `request_id`, and resume the agent by the parked-agent route. Read any return that
  arrived since before you route the answer.
- **Grant only what the host can give.** A grant widens what the task allows: a path to change
  through `scope_add`, a path to read or the network in `decision`. A path to change follows the
  `scope_add` rule above. A tool the agent's type lacks cannot be added to a running agent; do that
  step yourself, or respawn the agent on a wider type with its prior return as context. A grant
  changes no host permission.

## The roster row

The orchestrator keeps one row per agent with the `roster` subcommand of `ao.py`. The roster is
history, not liveness: a row stays after its agent returns, so a reader learns who is running now
from the host, and learns from the roster what each agent was given, what it asked and what was
decided.

A row moves through `state` in this order: `planned` (a plan line only), `drafted` (the full task is
written and waits for its stage), `spawned` (running, or resumed after an answer), then `done`,
`blocked` or `partial` as it returns. A `blocked` row goes back to `spawned`, with `spawned_at` set
to the time of the resume, when the answer resumes the agent. `threshold_crossed` turns true once the threshold line appears in the status file.

A row for an agent with a branch of its own carries `branch_reason`, the situation that gave it the
branch; `branch_kind`, the kind that situation sets (`feature`, `experiment` or `hotfix`); and
`integrate` and `lands`, the kind's configured method and landing unless the plan changed them for
this agent. [isolation.md](isolation.md) says how a branch closes.

`agent_type` records the host agent type the agent was spawned as: a built-in type such as
`general-purpose`, or one of the user's own agent definitions when `agents.own_agents` allows it
(see [config.md](config.md)). It is `null` on a host whose spawn takes no type. `model` and
`effort` record what the agent runs on, which for one of the user's own types is its definition's.

`access` repeats the task's, and `requests` keeps every request the agent sent; a request is open
until an answer in `answers` names it in `request_id`. `fork` and `packets` record the agent's
context. `packets` lists each packet the agent holds, with
the revision it got at spawn; set the newer revision when an answer carries one. A chat fork's
`model` is the main session's model, whatever its role's tier says.

## Worked examples, one per kind

One run, `2026-10-02-csv-export`, adds a CSV export to a repository at `/home/dev/projects/ledger`.
The builder `export-api` works in its own worktree on branch `feature/export-api`; in stage 2 a
builder, `export-docs`, documents the endpoint as a chat fork, and a reviewer, `export-review`,
checks the work. Task, spawn and status files live in `/tmp/ao-2026-10-02-csv-export/`, and the
run's packets in its `packets/` folder: `grounding`, saved from the chat, and `api-contract`, saved
from the return of `export-api`. Each example below validates against its definition in the
protocol schema.

### task

The spawn message's `<task>` element holds this block, and the same object sits at `task_file`.
It gets the packet `grounding`, and its `access` names the one file it reads beyond its ground.
`ORCHESTRATOR_ADDRESS` is a placeholder: the real `report_to` value is the mid-run address the
host SOP ([Claude](hosts/claude-code.md), [OpenAI](hosts/openai.md)) names, or null where the host
has none.

```json
{
  "schema_version": 1,
  "kind": "task",
  "run_id": "2026-10-02-csv-export",
  "agent": "export-api",
  "roles": ["builder"],
  "objective": "Ledger entries can be exported as CSV for a date range through GET /export.",
  "scope": [
    "/home/dev/projects/ledger-worktrees/export-api/src/ledger/export",
    "/home/dev/projects/ledger-worktrees/export-api/tests/test_export.py"
  ],
  "done_when": [
    {
      "check": "cd /home/dev/projects/ledger-worktrees/export-api && python3 -m pytest tests/test_export.py -q",
      "expect": "every test passes, 0 failed"
    },
    {
      "check": "cd /home/dev/projects/ledger-worktrees/export-api && python3 -m ledger.export --sample | head -1",
      "expect": "date,account,amount,currency"
    }
  ],
  "ground": [
    "/home/dev/projects/ledger/docs/export-spec.md",
    "/home/dev/projects/ledger/src/ledger/models.py"
  ],
  "threshold": "export endpoint returns CSV",
  "stage": 1,
  "waits_on": [],
  "tier": "ephemeral",
  "workdir": "/home/dev/projects/ledger-worktrees/export-api",
  "branch": "feature/export-api",
  "may_commit": true,
  "layers_below": 0,
  "packets": ["grounding"],
  "access": {
    "summary": "Reads the ledger code and edits the export package; runs the tests; no web.",
    "tools": ["read", "edit", "shell"],
    "read": [
      {
        "path": "/home/dev/projects/ledger/src/ledger/currency.py",
        "why": "how amounts are rounded, which the CSV writes as they are"
      }
    ],
    "network": { "allowed": false, "why": "everything it needs is in the repository" },
    "held_by": "Write tools and Bash come from the agent type general-purpose; no web and the read paths hold by instruction."
  },
  "report_to": "ORCHESTRATOR_ADDRESS",
  "ao_script": "/home/dev/skills/agent-orchestrate/scripts/ao.py",
  "status_file": "/tmp/ao-2026-10-02-csv-export/status/export-api.jsonl",
  "task_file": "/tmp/ao-2026-10-02-csv-export/tasks/export-api.json",
  "spawn_file": "/tmp/ao-2026-10-02-csv-export/tasks/export-api-spawn.md",
  "notes": "Run the full test suite once before changing anything, so a failure already on the base is known."
}
```

The task for `export-docs` in stage 2. It starts as a chat fork, so it has the chat's discussion of
who reads the documentation, and it gets two packets: `grounding`, saved before the chat compacted,
and `api-contract`, saved from the return of `export-api`. Its `access` says what it may use: it
reads the endpoint and the CSV writer, and asks for the error codes later, in the request below. As
a chat fork on Claude Code it has the main session's tools, so `held_by` says all of it holds by
instruction.

```json
{
  "schema_version": 1,
  "kind": "task",
  "run_id": "2026-10-02-csv-export",
  "agent": "export-docs",
  "roles": ["builder"],
  "objective": "The export endpoint is documented for API users.",
  "scope": ["/home/dev/projects/ledger-worktrees/export-docs/docs/export.md"],
  "done_when": [
    {
      "check": "grep -c '^## ' /home/dev/projects/ledger-worktrees/export-docs/docs/export.md",
      "expect": "3 or more: request, response and limits"
    }
  ],
  "ground": ["/home/dev/projects/ledger/docs/export-spec.md"],
  "threshold": null,
  "stage": 2,
  "waits_on": ["export-api"],
  "tier": "ephemeral",
  "workdir": "/home/dev/projects/ledger-worktrees/export-docs",
  "branch": "feature/export-docs",
  "may_commit": true,
  "layers_below": 0,
  "fork": true,
  "packets": ["grounding", "api-contract"],
  "access": {
    "summary": "Reads the export code and the spec, writes docs/export.md, and runs commands only to check its work; no web.",
    "tools": ["read", "edit", "shell"],
    "read": [
      {
        "path": "/home/dev/projects/ledger-worktrees/export-api/src/ledger/export/__init__.py",
        "why": "the GET /export endpoint the page describes, as export-api built it"
      },
      {
        "path": "/home/dev/projects/ledger-worktrees/export-api/src/ledger/export/writer.py",
        "why": "the columns and quoting the response section describes"
      }
    ],
    "network": { "allowed": false, "why": "everything it needs is in the repository" },
    "held_by": "This agent is a chat fork with this chat's tools, so its tools, read paths and no web all hold by instruction."
  },
  "report_to": "ORCHESTRATOR_ADDRESS",
  "ao_script": "/home/dev/skills/agent-orchestrate/scripts/ao.py",
  "status_file": "/tmp/ao-2026-10-02-csv-export/status/export-docs.jsonl",
  "task_file": "/tmp/ao-2026-10-02-csv-export/tasks/export-docs.json",
  "spawn_file": "/tmp/ao-2026-10-02-csv-export/tasks/export-docs-spawn.md"
}
```

### status_line

The line `export-api` appends when its threshold becomes true. The `summary` repeats the task's
threshold exactly.

```json
{
  "schema_version": 1,
  "kind": "status_line",
  "agent": "export-api",
  "at": "2026-10-02T14:05:12+00:00",
  "event": "threshold",
  "summary": "export endpoint returns CSV"
}
```

### notice

Sent mid-run. The message's first line reads "Notice from export-api (failure, continuing): the
base branch fails 3 tests before any change", and this block follows it.

```json
{
  "schema_version": 1,
  "kind": "notice",
  "agent": "export-api",
  "reason": "failure",
  "summary": "The base branch fails 3 tests in tests/test_ledger.py before any change in this slice.",
  "detail": "The failures are in currency rounding, outside the slice. The export tests run on their own and pass.",
  "paths": ["/home/dev/projects/ledger-worktrees/export-api/tests/test_ledger.py"],
  "continuing": true
}
```

### notice: a request

`export-docs` needs to read a file outside its `access` and keeps writing meanwhile. The message's
first line reads "Request from export-docs (still working): read the module that defines the
export's error codes", and this block follows it.

```json
{
  "schema_version": 1,
  "kind": "notice",
  "agent": "export-docs",
  "reason": "request",
  "id": "export-docs-1",
  "summary": "export-docs asks to read the export's error codes and keeps writing the other sections.",
  "need": "Read the module that defines the error codes GET /export returns.",
  "why": "The limits section lists each error the endpoint returns, and the spec does not name them.",
  "meanwhile": "Writing the request and response sections, which do not need the codes.",
  "paths_needed": [
    {
      "path": "/home/dev/projects/ledger-worktrees/export-api/src/ledger/export/errors.py",
      "why": "it defines every error code the endpoint returns"
    }
  ],
  "continuing": true
}
```

The user grants it, and the orchestrator sends this answer to the running agent. Its first line
reads "Answer to request export-docs-1: granted, read errors.py".

```json
{
  "schema_version": 1,
  "kind": "answer",
  "agent": "export-docs",
  "ask_id": null,
  "request_id": "export-docs-1",
  "subject": "Reading the export's error codes",
  "decision": "You may read /home/dev/projects/ledger-worktrees/export-api/src/ledger/export/errors.py. Change nothing there."
}
```

### ask

The question `export-api` parks on. Adding a migration is outside its scope, so the trigger is
`outside_slice`, and the default stays inside the slice.

```json
{
  "schema_version": 1,
  "kind": "ask",
  "id": "export-api-1",
  "agent": "export-api",
  "question": "May I add an index on ledger_entries.created_at? Its migration lives in migrations/, outside my scope.",
  "blocks": "The large-range check in done_when; the endpoint and its other tests are finished.",
  "tried": [
    "/home/dev/projects/ledger/src/ledger/models.py",
    "migrations/ listed, read-only",
    "python3 -m pytest tests/test_export.py -q: 14 passed, 1 failed (test_export_large_range timed out at 30 s)"
  ],
  "options": [
    {
      "id": "A",
      "label": "Add the index migration",
      "detail": "One new file, migrations/0042_entries_created_at.sql; the large-range test then passes."
    },
    {
      "id": "B",
      "label": "Page by id instead",
      "detail": "No migration; a large date range becomes several requests."
    }
  ],
  "default": "B",
  "need_by": "now",
  "trigger": "outside_slice"
}
```

### return

`export-api` ends its turn parked. `asks` carries the ask above, so `status` is `blocked`.

```json
{
  "schema_version": 1,
  "kind": "return",
  "agent": "export-api",
  "status": "blocked",
  "did": [
    "Built GET /export and the CSV writer in src/ledger/export/",
    "Wrote 15 tests in tests/test_export.py: 14 pass, 1 times out on a large range"
  ],
  "files": [
    "/home/dev/projects/ledger-worktrees/export-api/src/ledger/export/__init__.py",
    "/home/dev/projects/ledger-worktrees/export-api/src/ledger/export/writer.py",
    "/home/dev/projects/ledger-worktrees/export-api/tests/test_export.py"
  ],
  "assumed": ["Dates are written as YYYY-MM-DD, matching the existing JSON API"],
  "next": "Answer export-api-1; the large-range test then passes or is replaced by paging.",
  "asks": [
    {
      "schema_version": 1,
      "kind": "ask",
      "id": "export-api-1",
      "agent": "export-api",
      "question": "May I add an index on ledger_entries.created_at? Its migration lives in migrations/, outside my scope.",
      "blocks": "The large-range check in done_when; the endpoint and its other tests are finished.",
      "tried": [
        "/home/dev/projects/ledger/src/ledger/models.py",
        "migrations/ listed, read-only",
        "python3 -m pytest tests/test_export.py -q: 14 passed, 1 failed (test_export_large_range timed out at 30 s)"
      ],
      "options": [
        { "id": "A", "label": "Add the index migration" },
        { "id": "B", "label": "Page by id instead" }
      ],
      "default": "B",
      "need_by": "now",
      "trigger": "outside_slice"
    }
  ],
  "report": null
}
```

A reviewer's return carries a verdict and ranked findings, each with its evidence. This one is
from `export-review` in stage 2, which had a read-only task.

```json
{
  "schema_version": 1,
  "kind": "return",
  "agent": "export-review",
  "status": "done",
  "did": [
    "Checked feature/export-api against the export-api task and its done_when checks",
    "Ran both checks and one extra case for quoted fields"
  ],
  "files": [],
  "assumed": [],
  "next": "Fix the first finding, then merge feature/export-api.",
  "verdict": "revise",
  "findings": [
    {
      "summary": "The CSV writer leaves a field containing a comma unquoted.",
      "verdict": "revise",
      "evidence": "python3 -m ledger.export --sample with an account named 'Smith, J' prints 5 columns on that row instead of 4.",
      "paths": ["/home/dev/projects/ledger-worktrees/export-api/src/ledger/export/writer.py"]
    },
    {
      "summary": "Both done_when checks run and pass.",
      "verdict": "accept",
      "evidence": "python3 -m pytest tests/test_export.py -q: 15 passed."
    }
  ],
  "report": null
}
```

### answer

The orchestrator picks option A. The message's first line reads "Answer to export-api-1: add the
index migration (option A)", and this block follows it.

```json
{
  "schema_version": 1,
  "kind": "answer",
  "agent": "export-api",
  "ask_id": "export-api-1",
  "subject": "Index on ledger_entries.created_at",
  "option_id": "A",
  "decision": "Add the index as migrations/0042_entries_created_at.sql, change nothing else under migrations/, then rerun the large-range check.",
  "because": "A stage-2 report also filters entries by date, so the index serves both.",
  "scope_add": ["/home/dev/projects/ledger-worktrees/export-api/migrations/0042_entries_created_at.sql"]
}
```

### roster_row

The row for `export-api` after the answer resumed it.

```json
{
  "schema_version": 1,
  "kind": "roster_row",
  "agent": "export-api",
  "roles": ["builder"],
  "stage": 1,
  "state": "spawned",
  "objective": "Ledger entries can be exported as CSV for a date range through GET /export.",
  "scope": [
    "/home/dev/projects/ledger-worktrees/export-api/src/ledger/export",
    "/home/dev/projects/ledger-worktrees/export-api/tests/test_export.py",
    "/home/dev/projects/ledger-worktrees/export-api/migrations/0042_entries_created_at.sql"
  ],
  "waits_on": [],
  "threshold": "export endpoint returns CSV",
  "threshold_crossed": true,
  "tier": "ephemeral",
  "workdir": "/home/dev/projects/ledger-worktrees/export-api",
  "branch": "feature/export-api",
  "branch_reason": "parallel_slice",
  "branch_kind": "feature",
  "integrate": "merge",
  "lands": "ask",
  "status_file": "/tmp/ao-2026-10-02-csv-export/status/export-api.jsonl",
  "task_file": "/tmp/ao-2026-10-02-csv-export/tasks/export-api.json",
  "agent_id": "a3f9c1e7b2d40581",
  "agent_type": "general-purpose",
  "model_tier": "standard",
  "model": null,
  "effort": null,
  "packets": [{ "name": "grounding", "revision": 1 }],
  "access": {
    "summary": "Reads the ledger code and edits the export package; runs the tests; no web.",
    "tools": ["read", "edit", "shell"],
    "read": [
      {
        "path": "/home/dev/projects/ledger/src/ledger/currency.py",
        "why": "how amounts are rounded, which the CSV writes as they are"
      }
    ],
    "network": { "allowed": false, "why": "everything it needs is in the repository" },
    "held_by": "Write tools and Bash come from the agent type general-purpose; no web and the read paths hold by instruction."
  },
  "spawned_at": "2026-10-02T14:23:05+00:00",
  "returned_at": "2026-10-02T14:21:47+00:00",
  "summary": "Parked on export-api-1, answered with option A, resumed.",
  "asks": [
    {
      "schema_version": 1,
      "kind": "ask",
      "id": "export-api-1",
      "agent": "export-api",
      "question": "May I add an index on ledger_entries.created_at? Its migration lives in migrations/, outside my scope.",
      "blocks": "The large-range check in done_when; the endpoint and its other tests are finished.",
      "tried": ["/home/dev/projects/ledger/src/ledger/models.py"],
      "options": [
        { "id": "A", "label": "Add the index migration" },
        { "id": "B", "label": "Page by id instead" }
      ],
      "default": "B",
      "need_by": "now",
      "trigger": "outside_slice"
    }
  ],
  "answers": [
    {
      "schema_version": 1,
      "kind": "answer",
      "agent": "export-api",
      "ask_id": "export-api-1",
      "subject": "Index on ledger_entries.created_at",
      "option_id": "A",
      "decision": "Add the index as migrations/0042_entries_created_at.sql, change nothing else under migrations/, then rerun the large-range check."
    }
  ]
}
```

The row for `export-docs` once it is drafted. As a chat fork it records the main session's model,
`packets` records the revision of each packet it was given, and `access` repeats its task's.

```json
{
  "schema_version": 1,
  "kind": "roster_row",
  "agent": "export-docs",
  "roles": ["builder"],
  "stage": 2,
  "state": "drafted",
  "objective": "The export endpoint is documented for API users.",
  "scope": ["/home/dev/projects/ledger-worktrees/export-docs/docs/export.md"],
  "waits_on": ["export-api"],
  "threshold": null,
  "tier": "ephemeral",
  "workdir": "/home/dev/projects/ledger-worktrees/export-docs",
  "branch": "feature/export-docs",
  "branch_reason": "parallel_slice",
  "branch_kind": "feature",
  "integrate": "merge",
  "lands": "ask",
  "status_file": "/tmp/ao-2026-10-02-csv-export/status/export-docs.jsonl",
  "task_file": "/tmp/ao-2026-10-02-csv-export/tasks/export-docs.json",
  "agent_type": "fork",
  "model": "opus",
  "effort": null,
  "fork": true,
  "packets": [
    { "name": "grounding", "revision": 2 },
    { "name": "api-contract", "revision": 1 }
  ],
  "access": {
    "summary": "Reads the export code and the spec, writes docs/export.md, and runs commands only to check its work; no web.",
    "tools": ["read", "edit", "shell"],
    "read": [
      {
        "path": "/home/dev/projects/ledger-worktrees/export-api/src/ledger/export/__init__.py",
        "why": "the GET /export endpoint the page describes, as export-api built it"
      },
      {
        "path": "/home/dev/projects/ledger-worktrees/export-api/src/ledger/export/writer.py",
        "why": "the columns and quoting the response section describes"
      }
    ],
    "network": { "allowed": false, "why": "everything it needs is in the repository" },
    "held_by": "This agent is a chat fork with this chat's tools, so its tools, read paths and no web all hold by instruction."
  }
}
```

## Related

- [SKILL.md](../SKILL.md): the run checklist this protocol serves.
- [standing.md](../assets/standing.md): the standing text every agent receives at spawn.
- [protocol.schema.json](../schemas/protocol.schema.json): the definition of every message kind.
- [ao.py](../scripts/ao.py): `check`, `status`, `roster`, `package` and `packets`.
- [claude_transcript.py](../scripts/claude_transcript.py): packets built from earlier turns, on
  Claude Code.
- [isolation.md](isolation.md): the tier, workdir and branch fields on a task.
- [widgets.md](widgets.md): the views built from asks, returns and roster rows.
- [config.md](config.md): the model tier behind each role.
- [hosts/claude-code.md](hosts/claude-code.md) and [hosts/openai.md](hosts/openai.md): how each host carries
  spawn, messages, resume and the completion notice.
