# Showing the run

The orchestrator shows the run rather than describing it, so the user never rebuilds it from prose.
There are six views of the run, `plan`, `ask`, `roster`, `summary`, `graph` and `packets`, each
built as data from the roster, the status files, the agents' returns, the packet files and the git
reader, and two settings views, `config` and `roles`, built from the effective config. Render that data as an inline widget where
the host has a widget tool, and as structured text where it does not; the host SOP
([Claude](hosts/claude-code.md), [OpenAI](hosts/openai.md), [Antigravity](hosts/antigravity.md))
says which. Both forms carry the same fields. Read this file before the first render of a run, and before the first settings view.

## Contents

- When each view renders
- Where the data comes from
- The view and the chat
- plan
- ask
- roster
- summary
- graph
- packets
- config and roles: the settings views
- Rendering as a widget
- Rendering as structured text

## When each view renders

Four moments show the run without being asked, plus the graph whenever branches are the subject.
Each one is on by default and turned off in config with `report_moments` (see
[config.md](config.md)); a view that is off still renders whenever the user asks for it.

- `plan`: a plan is ready, before anything spawns, and again when the plan changes
  (`report_moments.plan`).
- `ask`: an agent parks with status `blocked` (`report_moments.ask`). A request, or a `permission`
  ask, goes before the user when it arrives either way, with the orchestrator's review beside it,
  since access is theirs to give: in this view while `report_moments.ask` is on, and as one line of
  chat while it is off.
- `roster`: the user asks what is happening, who is done or who is waiting
  (`report_moments.roster`).
- `summary`: the run ends (`report_moments.summary`).
- `graph`: branches are the subject, because the user asks about them or branches close
  (`report_moments.graph`).

**Call words.** One word after the skill name, such as `/agent-orchestrate status`, opens a view:

- `config`: the `config` settings view, the run settings;
- `roles`: the `roles` settings view, who runs each role;
- `plan`: the `plan` view of the current run;
- `status`: the `roster` view;
- `asks`: everything waiting on the user, in two groups: parked asks, and open requests from
  agents still working;
- `packets`: the `packets` view, the run's context packets and the project's kept ones;
- `branches`: the `graph` view;
- `summary`: the `summary` view.

Any other text after the skill name is the run's objective. With no text, the skill plans from the
conversation, or renders `status` while a run is live. A run view called with no run in this
session says so in one line of chat; `branches` still draws the graph of the repository in front of
you.

The settings views are not report moments, and `report_moments` has no switch for them. Each
renders when the skill is called with its word, when the user asks to see or change the settings,
and again after each save. The `packets` view is not a report moment either: it renders on its
word, when the user asks about the run's context, and again after each save, update or keep.

## Where the data comes from

- **The roster**: one `roster_row` per agent, read with the `roster` subcommand of
  [ao.py](../scripts/ao.py). It is history, not liveness.
- **Status files**: the last line of each agent still in flight, and whether its threshold line is
  there (`threshold_crossed`).
- **Returns**: `status`, `did`, `files`, `assumed`, `next`, `asks`, `verdict`, `findings` and
  `report`, as defined in [protocol.md](protocol.md).
- **The host's live agent list**: which agents are running right now. The host SOP names the tool,
  or says the host has none.
- **The git reader**: `python3 scripts/git_lanes.py REPO` for `preflight`, `worktrees` and `lanes`
  (see [isolation.md](isolation.md)). Add `--full` when branches close or a squash needs
  confirming, since only it detects squashed branches.
- **Config**: `report_moments`, and the method and landing for each kind of branch. The settings
  views read every setting from `python3 scripts/ao.py config --explain --project DIR`.
- **Packets**: `python3 scripts/ao.py packets DIR` for the run's `packets/` folder and for the
  project's `.agent-orchestrate/packets/` (see [protocol.md](protocol.md)).

Field names below are the names in those sources, so a view is a selection, never a rewording.

## The view and the chat

The view holds the visual, the lane and axis labels, the legend, the control labels and the values.
The chat holds the commentary: anything that explains, qualifies, warns or instructs. A label
belongs in the view; a commentary sentence belongs in the chat. Protocol values stay inside as the
readable sentences they are: access summaries, `held_by`, path reasons, questions and request
needs, and the orchestrator's review beside a request. When a render needs commentary, alternate:
the view, then the text about it, then the next view.

Hold to this as a budget. Commentary inside a view arrives one reasonable sentence at a time and
compounds until the picture is a caption. A preflight warning, a note about a branch outside the
run, a strip of commit ids: each goes in the chat beneath the view.

## plan

Before anything spawns. One row per proposed agent.

- From each `roster_row` in state `planned` or `drafted`: `agent`, `roles`, `stage`, `objective`,
  `scope`, `waits_on`, `threshold`, `tier`, `branch`, `branch_reason`, `branch_kind`, `integrate`,
  `lands`, `model_tier`, `agent_type`, `model`, `effort`, `fork`, `packets`, `access`.
- **Access**, beside the scope and the context, always as sentences: the `summary`, then `held_by`,
  then each `read` path followed by its reason and the network line with its reason. A row with no
  `access` shows `set by the agent type`. Every agent's `held_by` is shown, so the reader sees what
  the host enforces and what holds only by instruction.
- **Context**, beside the tier, in words:
  - `fresh` for an agent with no fork and no packets;
  - `fork of this chat as it stands` for a chat fork, adding `(compacted N times; plan on the
    summary and the turns since)` once the chat has compacted, and its model as `this chat's
    model`. After a compaction, plan for a fork that sees the summary and the turns since; exactly
    what a fork inherits then is unverified on this host, so put any earlier detail the agent needs
    in its task or a packet;
  - `packets: grounding r2, api-contract r1`, each name with the revision from the row's `packets`;
    a packet still to be saved from an earlier agent's return shows where it will come from, such
    as `api-contract (from export-api's return)`.
  - A fork where the host SOP's check says this host cannot fork shows `fork not available here`,
    and the agent is planned fresh: its context goes in its task, or in a packet when the packet
    conditions apply.
- **Agent type.** Each drafted row shows its `agent_type` beside its `model` and `effort`. With
  `agents.own_agents` on, an agent on one of the user's own types shows that type's own model and
  effort, and a mapped type that fell back shows `general-purpose` at the role's tier with the
  reason, such as `fallback: TYPE not in this session`.
- For each branch, its kind, its method, and how it lands: `on your go` for `lands` `ask`,
  `after review` for `auto`.
- **Shared branches.** A branch that carries more than one writing agent (`agents.per_branch` above
  1) shows `shared` after its name on each of its agents' rows.
- A row for a later stage shows its plan line only (`agent`, `roles`, `objective`, `scope`,
  `waits_on`, `threshold`) and its context, because its task is not drafted yet and the view shows
  nothing it does not have.
- **The collision verdict, computed per stage.** Two agents in the same stage collide when a path in
  one's `scope` equals or contains a path in the other's. Check it two ways. Compare the absolute
  paths as written, which catches overlap anywhere, including a repository nested inside another.
  Inside a repository, also compare paths relative to the tree each agent writes (its `workdir` in a
  worktree, the repository root at tier `none`), since one file has a different absolute path in
  each worktree of the same repository. The same relative path in two separate repositories is no
  collision. Name the pair and the shared path. Agents in different stages may share paths safely,
  so a check across the whole plan invents collisions.
- **Tiers** from each repository's preflight: `tiers_available`, and each entry of `tiers_blocked`
  shown as unavailable with its reason, so the reader learns what is impossible where and why. A run
  across several repositories shows one line per repository.
- **Tallies**: agents per stage and per model tier, the numbers behind the cost of the plan.

Widget controls. Local: take an agent out, which recomputes the verdict. Sends: launch the stage,
re-cut the slices, show one agent's full task.

```text
PLAN  2026-10-02-csv-export  2 stages, 3 agents  slices are clean

STAGE 1
  export-api      builder    ephemeral  feature/export-api  standard
    objective     Ledger entries can be exported as CSV for a date range through GET /export.
    context       packets: grounding r1
    owns          src/ledger/export/
                  tests/test_export.py
    access        Reads the ledger code and edits the export package; runs the tests; no web.
    held by       Write tools and Bash come from the agent type general-purpose; no web and the
                  read paths hold by instruction.
    reads         src/ledger/currency.py, for how amounts are rounded
    network       no: everything it needs is in the repository
    waits on      nothing
    threshold     export endpoint returns CSV
    branch        feature  merge  lands on your go

STAGE 2  plan lines only
  export-docs     builder
    objective     The export endpoint is documented for API users.
    context       fork of this chat as it stands, on this chat's model
                  packets: grounding r1, api-contract (from export-api's return)
    owns          docs/export.md
    waits on      export-api
    threshold     none
  export-review   reviewer
    objective     The export-api branch is checked against its task before it merges.
    context       fresh
    owns          nothing, read-only
    waits on      export-api
    threshold     none

TIERS
  available       none, ephemeral, session
  unavailable     none

REPLY  launch stage 1  /  re-cut  /  show a task
```

## ask

An agent has parked, or has sent a request and kept working. One view per parked agent, with one
block per ask in its return, and one block per open request.

- From the `ask`: `id`, `agent`, `question`, `blocks`, `tried`, `options` (each `id`, `label` and
  `detail`), `default`, `need_by`, `milestone`, `trigger`.
- From the agent's `roster_row`: `roles`, `stage`, `branch`.

The `default` is the field that matters most: it turns the open question into a confirm or redirect
answerable in one word, so mark it on its option.

Widget controls. Sends: one button per option, each sending that choice back; one more for
"neither", which opens the discussion instead of forcing a choice. The orchestrator writes the
`answer` from the choice. This view is the strongest reason to render at all: it turns the answer
step from a paragraph the user composes into one choice.

**Two groups.** The `asks` word, and any render with more than one item, puts everything waiting on
the user in two groups, each under its own heading:

- **Stopped, waiting on you**: parked asks. An ask whose `request_id` names a request shows that
  request inside its block, since the agent has stopped on it. A parked ask whose `trigger` is
  `permission` carries the orchestrator's `review` and `recommend` lines whether or not it names a
  request, under its request when `request_id` names one and under its options when none does. For
  a request, recommend `grant`, `refuse` or `grant with changes`, and its buttons are those of a
  request. For a `permission` ask with no request behind it, recommend an option by its `id`, or
  `neither` when none is suitable, and say when that differs from the agent's `default`; its
  buttons stay one per option plus "neither".
- **Still working, asked you**: open requests, from each roster row's `requests` that no answer
  names yet, for agents in state `spawned`. A request moves to "Stopped, waiting on you" once its
  agent parks, and then shows only inside the parked ask whose `request_id` names it.

A request renders as sentences, never as bare paths: `need`, `why`, `meanwhile`, each path in
`paths_needed` followed by its reason, and the `tools` asked for. A path to change that another
agent in the stage holds shows `held by AGENT; grant once it returns done, or partial with its
slice accepted` beside its reason. It always says that no answer means not granted. Beside it sits
the orchestrator's review, computed per request, and per `permission` ask with no request behind
it, as [protocol.md](protocol.md) "Answering a request" describes: `review`, one line per check
that found something, or `no problems found`, then `recommend`: `grant`, `refuse` or
`grant with changes` for a request, and an option's `id` or `neither` for a `permission` ask with
no request behind it. The user decides. A request's buttons are `grant`, `refuse` and
`grant with changes`, which opens the discussion; the orchestrator writes the `answer`, with
`request_id` set, from the choice.

```text
ASK  export-api-1  from export-api (builder, stage 1)  needed now

question      May I add an index on ledger_entries.created_at? Its migration lives in
              migrations/, outside my scope.
blocks        The large-range check in done_when; the endpoint and its other tests are finished.
trigger       outside_slice
tried         src/ledger/models.py
              migrations/ listed, read-only
              pytest tests/test_export.py: 14 passed, 1 failed (timed out at 30 s)
options       A  Add the index migration
                 One new file, migrations/0042_entries_created_at.sql; the large-range test passes.
              B  Page by id instead  (default)
                 No migration; a large date range becomes several requests.

REPLY  A  /  B  /  neither, to discuss
```

The same view in stage 2, with a parked ask from one agent and an open request from another, as
`asks` shows it:

```text
ASKS  2026-10-02-csv-export  1 stopped, 1 still working

STOPPED, WAITING ON YOU
  export-review-1  from export-review (reviewer, stage 2)  needed now
    question    The spec asks for the large-range check on a copy of the production data, which I
                cannot reach. Check it against the test fixtures instead?
    options     A  Check it against the fixtures  (default)
                B  Leave the large-range check unreviewed

STILL WORKING, ASKED YOU
  export-docs-1  request from export-docs (builder, stage 2)
    need        Read the module that defines the error codes GET /export returns.
    why         The limits section lists each error the endpoint returns, and the spec does not
                name them.
    paths       export-api/src/ledger/export/errors.py, because it defines every error code the
                endpoint returns
    meanwhile   Writing the request and response sections, which do not need the codes.
    until then  not granted
    review      no problems found
    recommend   grant

REPLY  export-review-1 A  /  export-review-1 B  /  export-review-1 neither  /
       grant export-docs-1  /  refuse export-docs-1  /  grant export-docs-1 with changes
```

## roster

Mid-run. One row per agent.

- From each `roster_row`: `agent`, `roles`, `stage`, `state`, `scope`, `tier`, `branch` or
  `workdir`, `threshold`, `threshold_crossed`, `waits_on`, the number of open `asks`, and the
  number of open `requests`, which do not change its `state`.
- From the status file: the last line's `at`, `event` and `summary`.
- From the host's live agent list: whether the agent is running now.

Outside git the roster is the status view, since the graph needs branches: a row with no branch
shows its `workdir`, and its `owns` lines show where it writes.

`state` takes the roster's values exactly: `planned`, `drafted`, `spawned`, `done`, `blocked`,
`partial`. `blocked` means waiting on the orchestrator and nothing else. Rows in state `blocked` sort
to the top, because they are the only rows where the run waits on the reader; then `spawned`; then
the rest by stage.

Widget controls. Local: filter by state, expand a row. Sends: an instruction to one agent, a
refresh.

```text
ROSTER  2026-10-02-csv-export  1 waiting on you

BLOCKED
  export-api      builder    stage 1  feature/export-api
    last          14:21  blocked  parked on export-api-1
    owns          src/ledger/export/
                  tests/test_export.py
    threshold     export endpoint returns CSV, crossed
    asks open     1

DRAFTED
  export-docs     builder    stage 2  feature/export-docs
    owns          docs/export.md
    waits on      export-api
    threshold     none

PLANNED
  export-review   reviewer   stage 2  none
    waits on      export-api

REPLY  an instruction to one agent  /  refresh
```

## summary

The run is over. One block per agent, then the open assumptions.

- From each return: `agent`, `status`, `did`, `files`, `assumed`, `next`, and for review roles
  `verdict` and `findings`; `report` when there is one.
- From the roster row: `roles`, `branch`, `branch_kind`, `integrate`, `lands`.
- From the lanes, run with `--full`: each branch's `fate` and its `proof`.
- **Assumptions awaiting the user**: every `assumed` item across all returns, numbered, in one
  block of its own. A long list means a task was underspecified, which the next run can fix.

Widget controls. Local: accept or undo an assumption, which is triage the user does silently. Sends:
one integrate action carrying only what is still unresolved, a diff request, a write-up of the run's
current state.

```text
SUMMARY  2026-10-02-csv-export  3 agents finished  1 assumption to review

export-api      builder    done    feature/export-api  open
  did           Built GET /export and the CSV writer in src/ledger/export/
                Wrote 15 tests in tests/test_export.py; all pass
  files         src/ledger/export/__init__.py
                src/ledger/export/writer.py
                tests/test_export.py
                migrations/0042_entries_created_at.sql
  next          none

export-docs     builder    done    feature/export-docs  merged
  did           Wrote docs/export.md: request, response and limits
  files         docs/export.md
  next          none

export-review   reviewer   done    verdict revise
  findings      1  The CSV writer leaves a field containing a comma unquoted. (revise)
                2  Both done_when checks run and pass. (accept)
  next          Fix the first finding, then merge feature/export-api.

ASSUMPTIONS AWAITING YOU
  1  export-api   Dates are written as YYYY-MM-DD, matching the existing JSON API

REPLY  accept all  /  undo 1  /  integrate what is open  /  show a diff
```

## graph

Branches over time, from the git reader. One lane per branch.

- From each lane: `branch`, `tip`, `base`, `ahead`, `behind`, `commits` (each `sha`, `subject`,
  `when`, `author`, `rebased`), `dirty`, `trunk`, `fate`, `proof`.
- From `worktrees`: the `path` of the tree each branch is checked out in, and `locked`.
- From the roster and the host's live agent list: the agents on each branch, each with its role and
  whether it is running. An agent with a branch of its own sits on that lane. An agent at tier
  `none` sits on the lane of the branch checked out where it works, so agents that share a branch
  appear together; read-only agents count too. An agent outside any repository sits on no lane, and
  an agent whose work spans two repositories appears on each repository's board.

Per lane: the branch name and its path, a fork from its parent where it branched, a mark per
commit, and a spine that runs to now for an active branch. A branch with uncommitted work (`dirty`)
ends in a dotted tail rather than at its last commit, so an agent mid-edit never looks finished. A
`dirty` of null means unknown, never clean: say so in the chat beside the view.

**Fates are typed.** `merged`, `squashed`, `rebased`, `open` and `trunk` each get their own mark, and
each carries its `proof` for the user to see on request. A fate without its proof is a guess wearing
a label. Run the reader with `--full` before showing `squashed`, since only the full run detects it.

**Red means running, and only running.** It is the one fact a reader cannot derive from the picture,
so an agent that has finished never renders the way a live one does.

- **Live**: a filled red dot, with the role and what the agent is doing now.
- **Finished**: a hollow or muted dot, never red, with the role and a few words on what it did. The
  full account belongs to the summary.

Order live agents first. Past three finished agents on one board, collapse them to a count that
expands on request.

**Liveness comes from the host, not the roster.** An agent is live when the host lists it as
running and the roster has its row, which supplies its branch or, at tier `none`, its working
folder; render nothing that is not in both.
A host may list finished agents too, so read the status the host gives each one. Where the host has
no live list (its SOP says), an agent counts as presumed live when its row is `spawned` and its
status file has no `done`, `blocked` or `partial` line whose `at` is later than the row's
`spawned_at`, which records the latest spawn or resume; earlier such lines are history, and one
stamped in the same second leaves liveness unknown. Mark liveness you cannot settle as unknown. On hosts that lock an agent's
worktree while it runs, a `locked` worktree corroborates it. The roster keeps
finished agents on purpose, so a view built from the roster alone shows finished agents as working.

Widget controls. Local: hide integrated branches, hide agents. Sends: what a commit changed, the
uncommitted diff, the evidence behind a fate, an instruction to an agent.

```text
GRAPH  ledger  trunk main  2 branches  1 agent running

main                 trunk
  tip                5d0c7e2

feature/export-api   open     3 ahead, 0 behind main
  tree               /home/dev/projects/ledger-worktrees/export-api  dirty
  commits            c41d2e9  Add the index migration
                     9b07f13  Add the CSV writer
                     e52a8c4  Add GET /export
  agents             export-api   builder   running: quoting fields that contain a comma

feature/export-docs  merged   ancestry: git for-each-ref --merged=main refs/heads
  agents             export-docs  builder   finished: wrote docs/export.md
```

## packets

The run's context packets, and the packets the project has kept, with which agent holds which
revision. One row per packet.

- From `python3 scripts/ao.py packets RUN/packets`: `name`, `revision`, `about`, `source`, `kept`,
  `bytes`.
- From `python3 scripts/ao.py packets ROOT/.agent-orchestrate/packets`: the kept packets, each
  marked `kept, not in this run` until it is copied into the run's folder.
- From each `roster_row`'s `packets`: the agents given each packet and the revision each holds. An
  agent on an older revision than the file shows how far behind it is, such as `r1, one behind`.
- `kept` reads `kept` or `temporary`, never yes or no.
- A packet in this run that also has a kept copy shows the run's revision and, when the kept copy's
  differs, that one too, such as `r3   temporary   kept copy r2`: an update sets `Kept: no` until
  that revision is copied to the project again.

The header chip says the one fact that may need the reader: the count of agents on an older
revision, else the count of packets in this run.

Widget controls. Local: expand a row, filter to this run or kept packets. Sends: `save` (a new
packet, from what was just settled in the chat or from an agent's return), `update` (rewrite a
packet and add 1 to its revision, then choose which running agents get it as an answer), `show` (the
packet's text, in the chat) and `keep` (copy it to the project and report what git does with the
copy: tracked, ignored or untracked). Attaching a packet to an agent is a change to the plan, made
in the `plan` view.

```text
PACKETS  2026-10-02-csv-export  1 agent on an older revision

grounding       r2   temporary   410 bytes
  about         What the user settled about the export format, so every export agent starts from
                the same decisions.
  source        the chat, as settled with the user on 2026-10-02
  given to      export-api    r1, one behind
                export-docs   r2
api-contract    r1   temporary   380 bytes
  about         The GET /export contract from the return of export-api, for the agents that build
                on it.
  source        agent export-api's return
  given to      export-docs   r1
house-style     r3   kept, not in this run   1210 bytes
  about         How this project writes documentation for API users.
  source        the chat, as settled with the user on 2026-09-28
  given to      no agent in this run

REPLY  save NAME from ...  /  update NAME  /  show NAME  /  keep NAME
```

## config and roles: the settings views

Two views show the settings and change them: `config` for the run settings in `config.json`, and
`roles` for who runs each role, from `models.json`. Each opens on request, as "When each view
renders" says, never at a report moment.

- **Data.** `python3 scripts/ao.py config --explain --project DIR` gives each setting's `key`,
  `value`, `layer` and `file`, and the `files` it looked for. The `roles` view also reads, at render
  time, the session's agent types and the models the host offers, as below.
- **Rows.** Each row shows the setting's label, a control, the layer its value came from (`skill`,
  `user` or `project`) and a reset. The label's tooltip carries the setting's description from
  [config.schema.json](../schemas/config.schema.json); a sentence about a setting goes in the chat.
- **Reset.** A reset marks that key to be removed from the chosen layer's file, so the value from
  the layer below shows through. Choosing `host default`, `built-in` or no cap is a value, not a
  reset: it stores `null` in that file, which overrides the layers below.
- **Header.** The title, `Config` or `Roles`, and a chip: the count of unsaved changes while any are
  pending, otherwise `all shipped defaults` when every value comes from the skill layer, else the
  number of values the user's files set, such as `3 set in your files`. Keep the host's corner
  clear.
- **Save to.** A choice on its own line under the title, `Your machine` (the user layer) or `This
  project` (the project layer), starting on `Your machine`, with the path of the file the save
  writes beneath it: `config.json` for `config`, `models.json` for `roles`.
- **Action row.** `Discard changes` is local: it returns every control to its saved value. `Save`
  is a send, marked with a trailing arrow: it sends the view, the layer, only the changed keys as
  one JSON patch, nested as in the file, and each reset as `reset KEY`, such as
  `save roles --layer project {"providers": {"claude": {"deep": {"model": null}}}} reset roles.reviewer`.
  The orchestrator runs `python3 scripts/ao.py config set --layer LAYER --project DIR PATCH`, with
  `--reset KEY` for each reset and `PATCH` left out when only resets are pending, and renders the
  view again from the `--explain` output it prints. On exit 1 nothing is written; after an I/O
  failure, the error names any file it could not restore. The error line goes in the chat beneath
  the view.

**Colors are on buttons only.** In an On/Off switch or a segmented control, the chosen option is
green, from the host's success tokens, and a chosen Off is red, from its danger tokens. Unchosen
options keep the host's plain button style, and so do dropdowns and text fields. Set the colors as
inline styles marked `!important`, each token with a fallback, because the host's button styles
override class-based colors:

```text
chosen       background: var(--bg-success, #EAF3DE) !important;
             color: var(--text-success, #3B6D11) !important;
             border-color: var(--border-success, #97C459) !important
chosen Off   background: var(--bg-danger, #FCEBEB) !important;
             color: var(--text-danger, #A32D2D) !important;
             border-color: var(--border-danger, #F09595) !important
```

The colors follow the values, so a view reopened from the saved files shows the same colors. Green
and red mark choices here; in the graph, red still means running and nothing else.

### config

The run settings, in five groups:

- **Agents.**
  - `agents.max_active`: a number field, 1 or more, empty for no cap, which stores `null`.
  - `agents.per_branch`: a number field, marked `riskier` above 1.
  - `agents.max_layers`: a number field, 1 or more, with a maximum only where the host SOP names a
    nesting cap (3 on Claude by default, 10 on Antigravity, as its documentation names). A saved
    value above the host's cap shows as saved, with a note that the host allows fewer; the view
    never lowers it on its own.
  - `agents.own_agents`: an On/Off switch tagged `Claude only`. On reveals an indented sub-choice,
    `Choose agents from: This project / Your machine`, for `project` or `machine`, which starts on
    `Your machine` when the switch is first turned on. The sub-choice exists only in this view; the
    file holds one value, `off`, `project` or `machine`. On any host other than Claude, where the
    setting has no effect, the row is hidden.
- **When an agent gets its own branch.** The five `branch_when` switches, each tagged with the kind
  of branch it gives: `feature` for `parallel_slice`, `risky_change` and `long_running`, then
  `experiment` and `hotfix`.
- **Branch kinds.** One row each for `feature`, `experiment` and `hotfix`: the name pattern
  `<kind>/<agent>`, a method dropdown (`branch_kinds.<kind>.integrate`) and a landing control,
  `ask me` or `auto` (`branch_kinds.<kind>.lands`).
- **Show unasked.** The five `report_moments` switches.
- **Default tier.** `default_tier.in_git_repo` as a segmented control, `none`, `ephemeral` or
  `session`. `default_tier.outside_git_repo` shows locked at `none`, the only tier outside git.

### roles

Who runs each role, and the models behind each tier:

- **Who runs each role.** One row per role. An agent picker, hidden while `agents.own_agents` is
  `off` or on any host other than Claude. Then either the role's tier as a segmented
  control, `deep`, `standard` or `fast`, or, once an agent is picked, `its own: MODEL, EFFORT`,
  read from that agent's definition.
  - **The agent list** fills at render time from the session's agent types (the host SOP says where
    they come from), keeping only the types `own_agents` admits and that pass the fit check for the
    role: a builder needs write tools, and every role needs Bash, a type that can be resumed, one
    that does the work itself, and instructions that leave room for the standing text. Each entry
    shows where it is defined: this project, `~/.claude/agents`, a plugin's name, or the session.
    A first entry, `built-in`, stores `null`.
  - **The filter.** With `own_agents` `machine` only, a filter labeled as one, with a funnel icon
    and `not saved`, narrows every agent list by source: all, this project, `~/.claude/agents`, or
    one plugin. It is local and never saved.
- **Model and effort per tier.** A `Claude` tab, an `OpenAI` tab and a `Google` tab, each with one
  row per tier holding a model dropdown and an effort dropdown.
  - **Claude models:** `host default`, which stores `null`, and the family names `opus`, `sonnet`,
    `haiku` and `fable`. Beside each family, show the version it runs today, filled at render time
    and never stored in the skill: the session's own model for its family, the host's current-model
    list where the host's context gives one, else the family name alone. A save stores the family
    name.
  - **Claude efforts:** `host default`, then `low`, `medium`, `high`, `xhigh` and `max`.
  - **OpenAI:** the model slugs and efforts the `spawn_agent` description lists, where the session
    has them; elsewhere a text field for each.
  - **Google:** `host default`, which stores `null` and keeps the child on the session's model,
    then the tiers Antigravity's spawn takes:
    `inherit`, `flash_lite`, `flash` and `pro`. The effort dropdown holds `host default` alone,
    tagged `session only`, since Antigravity sets effort per session and never per spawn.
- **Preview.** The file the save would write: its path, `models.json` in the chosen layer, and its
  content, which is the file as it reads now with the pending changes merged in. It updates as each
  control changes and as the Save to choice moves.

### The settings views as structured text

Where the host has no widget tool, render each settings view in a `text` fence: a heading line with
the view's name and its chip, a `save to` line with the layer and the file's path, then one block
per group, one line per key with its value and its layer. A row the host hides is left out. The
user replies with one `key = value` line per change, `key = default` for the `null` of a setting
that ships as `null` (no cap, the built-in type or the host default), `key = reset` for a reset,
and `save to project` to write the project file instead; the orchestrator builds the patch and the
resets from the reply, runs `config set`, and shows the view again from its output.

```text
CONFIG  all shipped defaults
save to       your machine  /home/dev/.config/agent-orchestrate/config.json

AGENTS
  agents.max_active                       none        skill
  agents.per_branch                       1           skill
  agents.max_layers                       1           skill
  agents.own_agents                       off         skill   Claude only

WHEN AN AGENT GETS ITS OWN BRANCH
  branch_when.parallel_slice              on          skill   feature
  branch_when.risky_change                on          skill   feature
  branch_when.long_running                on          skill   feature
  branch_when.experiment                  on          skill   experiment
  branch_when.hotfix                      on          skill   hotfix

BRANCH KINDS
  branch_kinds.feature.integrate          merge       skill   feature/<agent>
  branch_kinds.feature.lands              ask         skill
  branch_kinds.experiment.integrate       merge       skill   experiment/<agent>
  branch_kinds.experiment.lands           ask         skill
  branch_kinds.hotfix.integrate           merge       skill   hotfix/<agent>
  branch_kinds.hotfix.lands               ask         skill

SHOW UNASKED
  report_moments.plan                     on          skill
  report_moments.ask                      on          skill
  report_moments.roster                   on          skill
  report_moments.summary                  on          skill
  report_moments.graph                    on          skill

DEFAULT TIER
  default_tier.in_git_repo                ephemeral   skill
  default_tier.outside_git_repo           none        skill   locked

REPLY  key = value  /  key = default  /  key = reset  /  save to project
```

The `roles` example has `agents.own_agents` on and a builder agent set in the project file.
`OPUS_VERSION` stands for the version filled at render time, never a stored value.

```text
ROLES  3 set in your files
save to       your machine  /home/dev/.config/agent-orchestrate/models.json

WHO RUNS EACH ROLE
  roles.planner                           deep                         skill
  role_agents.builder                     ledger-builder               project
                                          its own: sonnet, high
  roles.researcher                        standard                     skill
  roles.reviewer                          deep                         user
  roles.adversarial-reviewer              deep                         skill

MODEL AND EFFORT PER TIER  claude
  providers.claude.deep.model             opus (OPUS_VERSION)          user
  providers.claude.deep.effort            host default                 skill
  providers.claude.standard.model         host default                 skill
  providers.claude.standard.effort        host default                 skill
  providers.claude.fast.model             host default                 skill
  providers.claude.fast.effort            host default                 skill

MODEL AND EFFORT PER TIER  openai
  providers.openai.deep.model             host default                 skill
  providers.openai.deep.effort            host default                 skill
  providers.openai.standard.model         host default                 skill
  providers.openai.standard.effort        host default                 skill
  providers.openai.fast.model             host default                 skill
  providers.openai.fast.effort            host default                 skill

MODEL AND EFFORT PER TIER  google
  providers.google.deep.model             host default                 skill
  providers.google.deep.effort            host default (session only)  skill
  providers.google.standard.model         host default                 skill
  providers.google.standard.effort        host default (session only)  skill
  providers.google.fast.model             host default                 skill
  providers.google.fast.effort            host default (session only)  skill

REPLY  key = value  /  key = default  /  key = reset  /  save to project
```

## Rendering as a widget

**The shell.** Every widget has the same four parts, in this order; only the body changes.

1. **Header**: what the view is, the run label, and a state chip with the one fact that decides
   whether the reader must act, such as "1 waiting on you", "slices are clean" or "all agents
   finished". When something outside the run keeps the orchestrator from going idle (a stop gate, a
   hook, a watcher left running), the chip says that instead, because it outranks the run's own
   state.
2. **Tallies**: one optional row of counts, for when there are enough agents that counting them by
   eye is work.
3. **Body**: one or more views. Three in one widget is the practical ceiling; past that, use a
   second widget with text between them.
4. **Action row**: the buttons. Mark every button that sends something back to the orchestrator
   with a trailing arrow, so the reader can tell which controls are local and which cost a turn.

Local interactions (filtering, expanding, ticking off, recomputing a count) stay inside the widget.
Only a decision goes back.

**Layout invariants.** These are mechanical: follow them and a render cannot collide with itself.

1. **Marks are placed by data; text never is.** A dot, a bar or a curve sits wherever its value puts
   it. Every label sits in a fixed column or a fixed row, at a coordinate that depends on no value.
2. **Per-mark detail goes on hover**, as a tooltip on the mark, never as visible text beside it. A
   commit is a dot; its id and subject appear on hover.
3. **The top-right corner belongs to the host**, which may draw its own controls there. Keep the
   space they take clear; in the Claude desktop app that is about 44 px. Put header detail that
   does not fit on a line of its own under the title.
4. **One board per widget.** A second repository, a second run or a second subject is a second
   widget, with text between them.
5. **A label longer than its column is cut at the column edge** with an ellipsis, and the full text
   goes in its tooltip. It never widens the column or spills into the next one.
6. **No commentary inside the frame.** A sentence that explains a lane belongs in the chat beside
   the widget. Protocol values stay inside as the readable sentences they are: access summaries,
   `held_by`, path reasons, questions and request needs, and the orchestrator's review beside a
   request.

Before emitting, read the markup for five things: any text placed at a data-derived coordinate, any
commentary sentence inside the frame, a crowded top-right corner, more than one board, and any
truncation without a tooltip.

**Graph geometry.** Three columns at fixed x with a rule between them: branch labels on the left,
the plot in the middle, agents on the right, stopping well short of the host's corner. Time runs
left to right inside the plot. Each lane sits at a fixed y set by its index, never by a time. Only
the x of a mark comes from data.

```text
0          label edge                          plot edge   agent column       width minus the host's reserve
|  branch   |               plot                   |   agents   |      (host's corner)
```

## Rendering as structured text

Where the host has no widget tool, render each view as structured text in a `text` fence, so the
alignment survives: headed blocks and aligned lines, never a Markdown table. The worked forms above
show each view.

- **A heading line** opens the view: its name in capitals, the run label, and the state chip in
  words.
- **One block per stage, state or agent**, opened by a capitalized heading or by the agent's name
  in the first column.
- **Aligned lines**: a short label in a fixed-width first column, then the value. A list continues
  on following lines under the first value, one item per line.
- **Put the row the reader acts on first**: a parked agent, an open assumption.
- **A long value takes its own line or lines**, wrapped at a word boundary under its column. Show
  paths relative to the project root where that is unambiguous.
- **Close with a REPLY line** naming the replies that act, separated by slashes, so a choice costs
  the reader one word.

The split holds here too: the block holds values, and anything that explains, qualifies or warns
goes in the prose around it.

## Related

- [SKILL.md](../SKILL.md): the run checklist and the moments that call for each view.
- [protocol.md](protocol.md): the `ask`, `return` and `roster_row` fields the views draw on, and the
  packet files behind the `packets` view.
- [isolation.md](isolation.md): the preflight, worktree and lane fields behind the plan's tiers and
  the graph.
- [config.md](config.md): `report_moments`, the method and landing for each kind of branch, and
  `config set`, which the settings views save through.
- [defaults.json](../config/defaults.json): the shipped `report_moments`.
- [ao.py](../scripts/ao.py): `roster` and `status`, the sources of the roster and plan views,
  `packets`, the source of the packets view, and `config`, the source of the settings views.
- [git_lanes.py](../scripts/git_lanes.py): the reader behind the graph.
- [hosts/claude-code.md](hosts/claude-code.md), [hosts/openai.md](hosts/openai.md) and
  [hosts/antigravity.md](hosts/antigravity.md): whether the host has a widget tool and a live agent
  list, and on Claude the agent types the `roles` view lists.
