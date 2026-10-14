# Configuration

Every setting the orchestrator reads, where each one lives, and how a user or a project changes it.
Read this file when you change a setting, choose a model, or write an override file. For the
values in effect right now, run `python3 scripts/ao.py config --explain --project DIR`, with `DIR`
the project root, rather than merging files by hand; to change one, run `ao.py config set`.

## Contents

- Two files, three layers
- How the layers merge
- Seeing the effective config
- Changing a setting with config set
- Keys present in both files
- Run settings
- Model settings
- Overriding a model, an effort or a role's tier
- Overriding a run setting

## Two files, three layers

Configuration is two JSON files. `config.json` holds the run settings: how many agents, how deep
they nest and which agent definitions they may run as, when an agent gets a branch, how each kind
of branch closes and lands, when the run is shown, and the default isolation tier. `models.json`
holds the model settings: the tier each role runs on, the agent type a role may run as, and the
model and effort behind each tier for each provider. Both validate against
[config.schema.json](../schemas/config.schema.json), whose descriptions double as editor hover
text.

Each file comes in three layers, applied in this order:

| Layer | Run settings | Model settings |
|---|---|---|
| skill (baseline) | `config/defaults.json` in the skill folder | `config/models.json` in the skill folder |
| user | `${XDG_CONFIG_HOME:-~/.config}/agent-orchestrate/config.json` | `${XDG_CONFIG_HOME:-~/.config}/agent-orchestrate/models.json` |
| project | `<project root>/.agent-orchestrate/config.json` | `<project root>/.agent-orchestrate/models.json` |

The skill baseline ([defaults.json](../config/defaults.json), [models.json](../config/models.json))
ships with the skill and is replaced when the skill updates, so leave it as shipped and put every
change in a user or project file. A user file applies to every run on the machine; a project file
applies to runs on that project, and travels with the repository when it is committed. The project
root is the directory passed to `ao.py config --project`, else the git root of the working
directory, else the working directory itself. A run across several repositories takes one project
root: the folder the user works from, passed as `--project`. Its overrides govern every agent in the
run. Every layer is optional except the baseline.

Write an override file with only the keys it changes, plus `"schema_version": 1`, which every config
file carries. Add `"$schema"` with the path to `config.schema.json` for editor hover text and
completion. Put run settings in a `config.json` and model settings in a `models.json`, matching the
shipped files.

## How the layers merge

Each layer is applied to the result of the one before as a JSON merge patch (RFC 7396):

- An object merges key by key, at every depth. A key the patch leaves out keeps its value.
- Any other value replaces whole: a string, a number, a boolean, or an array.
- `null` deletes the key.

The nulls in the shipped files are values: `agents.max_active` null means no cap, and a `model` or
`effort` null means the host default. After merging, every key the shipped files carry must still
be set:

- A deleted key whose shipped value is `null` reads as `null` again, its unset value. So
  `"max_active": null` in a project file restores no cap after a user file set one, and
  `"model": null` returns a tier to the host default.
- Deleting any other shipped key is an error that names the file which deleted it. Give the key a
  value instead.
- A key the shipped files leave out can be added by one layer and deleted by a later one. The
  shipped files set every key the schema names, so such a key is one the skill ignores.

The schema describes values, not deletions, so an editor may underline a `null` in an override.
What counts is the merged result: `ao.py config` validates it against the schema and checks it for
completeness.

## Seeing the effective config

```text
python3 scripts/ao.py config --explain --project DIR
```

Run it from the skill folder, with `DIR` the root of the project the run works in. Without
`--project`, the project root is the git root of the working directory, or the working directory
itself outside git. Without `--explain`, it prints the merged config as JSON. With `--explain`, it
prints the project root, every config file it looked for and whether it was found, and one entry
per leaf key with its value, its layer (skill, user or project) and the file it came from. A key
restored to its shipped `null` carries a note saying so. On any error it exits 1 and names the
file and the fix.

Run it at the start of every run, before planning. The tier each role maps to and the models behind
those tiers decide the cost of the plan you are about to show.

## Changing a setting with config set

```text
python3 scripts/ao.py config set --layer user|project [--project DIR] [--reset KEY]... [PATCH]
```

`PATCH` is a JSON object, given as text or as `@FILE` to read it from a file, holding only the keys
that change. `--layer user` writes the user files and `--layer project` the files under
`<project root>/.agent-orchestrate/`, with the project root found as for `config`.

- **Routing.** The top-level keys `reviewed`, `roles`, `role_agents` and `providers` go to
  `models.json`, and every other setting to `config.json`. A key the shipped files do not carry is
  refused at any depth, with its path and the keys allowed beside it, so a misspelled setting is
  never written. `schema_version` and `$schema` are not routed: the command writes
  `"schema_version": 1` itself.
- **Merging.** Each part merges into that layer's file key by key, and a file that does not exist
  yet starts as `{"schema_version": 1}`. A `null` is stored only for a setting whose shipped value
  is `null`: `agents.max_active`, each `role_agents` entry, and each tier's `model` and `effort`.
  Stored in a layer's file, it overrides the layers below with no cap, the built-in type or the
  host default. A `null` for any other key is refused, with the `--reset` that removes it.
- **Resetting.** `--reset KEY`, with `KEY` a dotted key such as `roles.reviewer`, removes that key
  from the layer's file, so the value from the layer below shows through; an object left empty is
  dropped. Repeat it for several keys. With at least one `--reset`, `PATCH` is optional. A key both
  in `PATCH` and in a `--reset` is refused, and a reset of a key the file does not hold changes
  nothing and says so.
- **Checking.** Each value the patch sets is checked against the schema, then the effective config
  is built with the new content in memory and checked exactly as `config` checks it. On any error
  the command exits 1, names the key and the fix, and writes nothing.
- **Writing.** Only then are the files written, as UTF-8, each through a temporary file in the same
  folder and `os.replace`, creating the folder when it is missing. When a replace fails, the files
  already replaced are put back, so on exit 1 nothing is written; after an I/O failure, the error
  names any file it could not restore. The command prints the `--explain` output for the result.

```text
python3 scripts/ao.py config set --layer project --project DIR '{"roles": {"reviewer": "deep"}}'
python3 scripts/ao.py config set --layer project --project DIR --reset roles.reviewer
```

To get no cap or the host default for one project while your user file sets `agents.max_active` or
a tier's `model`, save the `null` to the project layer, such as `{"agents": {"max_active": null}}`.
To take the user file's value again, reset the key in the project layer.

The `config` and `roles` settings views in [widgets.md](widgets.md) save through this command.

## Keys present in both files

In the key tables, a name in braces stands for one key per name listed: `branch_when.{a,b}` means
`branch_when.a` and `branch_when.b`, each with the type, default and meaning on that row.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `$schema` | string | `../schemas/config.schema.json` in the shipped files; optional in an override | Path or URI of the schema, for editor hover text and completion. |
| `schema_version` | integer, always `1` | `1` | Version of the config format. The only required key, so a partial override file validates. |

## Run settings

These live in `config.json` at each layer. Defaults are those in `config/defaults.json`.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `agents` | object | | How many agents run at once, how they share branches and how deep they nest. |
| `agents.max_active` | integer, `1` or more, or null | `null` | Most agents active at once. `null` or absent means no cap. |
| `agents.per_branch` | integer, `1` or more | `1` | Writing agents allowed on one worktree branch at a time; at tier `none`, agents share the checked-out branch. Above `1` is an opt-in and the riskier mode: writers that share a worktree branch follow the tier `none` rules inside its tree, with scopes that share no path, `may_commit` false, and the orchestrator committing; see [isolation.md](isolation.md). An agent and the agents it spawns count as one writer on its branch: it coordinates them, and their scopes lie inside its own. |
| `agents.max_layers` | integer, `1` or more | `1` | The layers of agents in a run. `1` means only the orchestrator spawns; `2` lets each agent it spawns spawn agents of its own, and so on. Each task carries what is left as `layers_below`, set to the smaller of this value and the host's nesting cap, minus 1; see [protocol.md](protocol.md). Agents nest no deeper than the host's nesting cap, which each host SOP names: on Claude, the 3 layers below the main conversation it allows by default; on Codex v2, no cap is enforced, so the setting holds by instruction alone; on Antigravity, the 10 levels below the primary agent its documentation names. A saved value above the cap stays as saved, and each task's `layers_below` stays within the cap. |
| `agents.own_agents` | `off`, `project` or `machine` | `off` | Which of the user's own agent definitions the orchestrator may spawn agents as, beside the host's built-in types. `off` uses the built-in types only; `project` adds the agents defined in the project's `.claude/agents/`; `machine` adds every agent the session has: the project's, the user's `~/.claude/agents/` and those from installed plugins. With it on, the plan may propose a fitting type per agent, and `role_agents` maps a role to one. Claude only: Codex's spawn takes no agent type, and on Antigravity the setting does not reach that host's agent folders, so it has no effect on either; see [hosts/claude-code.md](hosts/claude-code.md) and [hosts/antigravity.md](hosts/antigravity.md). |
| `branch_when` | object | | The situations that give an agent a branch of its own. Set a situation to `false` to keep such agents off a branch of their own. |
| `branch_when.parallel_slice` | boolean | `true` | The slice runs beside other writing agents in the same repository. |
| `branch_when.risky_change` | boolean | `true` | The change could break shared work, so it lands only after review. |
| `branch_when.long_running` | boolean | `true` | The work spans more than one stage or sitting and needs its own line of history. |
| `branch_when.experiment` | boolean | `true` | The outcome is uncertain and the work may be thrown away. |
| `branch_when.hotfix` | boolean | `true` | An urgent fix that lands on its own, apart from work in progress. |
| `branch_kinds` | object | | The three kinds of branch, each with how it closes and how it lands. A parallel slice, a risky change and long-running work get a `feature` branch; an experiment and a hotfix get a branch of their own kind. Branches are named `<kind>/<agent>` unless the repository has a convention. |
| `branch_kinds.{feature,experiment,hotfix}` | object | | How a branch of that kind closes and lands. |
| `branch_kinds.{feature,experiment,hotfix}.integrate` | `merge`, `squash`, `rebase_ff` or `discard` | `merge` | How a branch of that kind closes. `merge` keeps the branch's history with a merge commit; `squash` lands it as one commit; `rebase_ff` rebases it onto the target and fast-forwards; `discard` closes it without integrating. |
| `branch_kinds.{feature,experiment,hotfix}.lands` | `ask` or `auto` | `ask` | Whether a branch of that kind waits for the user's go after review. `ask` waits for it; `auto` lands after review without asking. The plan may still set `auto` for one branch whose work touches no production code; see [isolation.md](isolation.md). |
| `report_moments` | object | | The moments at which the orchestrator shows the run unasked. Set a moment to `false` to show it only on request; see [widgets.md](widgets.md). |
| `report_moments.plan` | boolean | `true` | Show the plan before anything spawns. |
| `report_moments.ask` | boolean | `true` | Show an agent's question when it parks, with one choice per option. A request, or a `permission` ask, reaches the user either way, as one line of chat while this is off; see [widgets.md](widgets.md). |
| `report_moments.roster` | boolean | `true` | Show the roster when the user asks what is happening. |
| `report_moments.summary` | boolean | `true` | Show a summary when the run ends. |
| `report_moments.graph` | boolean | `true` | Show the branch graph whenever branches are the subject. |
| `default_tier` | object | | The isolation tier an agent gets unless its task names another. |
| `default_tier.in_git_repo` | `none`, `ephemeral` or `session` | `ephemeral` | The tier for work in a git repository. |
| `default_tier.outside_git_repo` | `none` | `none` | The tier for work outside a git repository, and the only tier possible there. |

## Model settings

These live in `models.json` at each layer. Defaults are those in `config/models.json`.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `reviewed` | string, `YYYY-MM-DD` | `2026-10-02` | The date the model assignments were last checked against current models. |
| `roles` | object | | The model tier each role runs on. Role names match the role list in [protocol.schema.json](../schemas/protocol.schema.json). |
| `roles.planner` | `deep`, `standard` or `fast` | `deep` | The tier a planner runs on. |
| `roles.builder` | `deep`, `standard` or `fast` | `standard` | The tier a builder runs on. |
| `roles.researcher` | `deep`, `standard` or `fast` | `standard` | The tier a researcher runs on. |
| `roles.reviewer` | `deep`, `standard` or `fast` | `standard` | The tier a reviewer runs on. |
| `roles.adversarial-reviewer` | `deep`, `standard` or `fast` | `deep` | The tier an adversarial-reviewer runs on. |
| `role_agents` | object | | The agent type each role spawns as, from the user's own agent definitions. It applies only while `agents.own_agents` is not `off`. |
| `role_agents.{planner,builder,researcher,reviewer,adversarial-reviewer}` | string or null | `null` | The agent type that role spawns as, by its name as the host lists it, or `null` for the built-in type at the role's tier. A mapped role spawns with no `model` or `effort`, so the definition's own apply. A type missing from the session, outside what `agents.own_agents` allows, or unfit for the agent's slice falls back to `general-purpose` at the role's tier, noted in the plan. |
| `providers` | object | | For each provider, the model and effort behind each tier. A run uses one provider throughout. |
| `providers.{claude,openai,google}` | object | | The tiers for a run on that provider's host: `claude` for Claude Code, `openai` for Codex, `google` for Antigravity. |
| `providers.{claude,openai,google}.{deep,standard,fast}` | object | | One model and the effort to run it at. |
| `providers.{claude,openai,google}.{deep,standard,fast}.model` | string or null | `null` | The model identifier as the host's spawn call takes it; on Antigravity, a tier name (see below). `null` or absent leaves the choice to the host default. |
| `providers.{claude,openai,google}.{deep,standard,fast}.effort` | string or null | `null` | The reasoning effort as the host names it. `null` or absent leaves it at the host default, and a host with no per-agent effort setting ignores it. |

The tiers: `deep` is the most capable model and effort, for planning and adversarial review;
`standard` is the everyday model, for building, research and review; `fast` is a quick, low-cost
model for small mechanical work. An agent with several roles runs on the deepest of their tiers.

**The values each provider takes.** On Claude and OpenAI, a tier's `model` is a model identifier
and its `effort` an effort level, both as that host's spawn call takes them. On Antigravity, leave
all three `providers.google` tiers `null` to keep every child on the session's model, such as
Gemini 4 Argon. A tier set there takes only a value the spawn's `Model` field takes, `inherit`,
`flash_lite`, `flash` or `pro`, never a model slug, and `flash_lite`, `flash` or `pro` hands the
child to a model no evidence identifies. Antigravity sets effort per session only, so
`providers.google.<tier>.effort` is recorded and not applied; leave it `null`. Each host SOP
lists its values ([Claude](hosts/claude-code.md), [OpenAI](hosts/openai.md),
[Antigravity](hosts/antigravity.md)).

Set models and efforts in a user or project `models.json`; the shipped values stay `null`, the host
default.

## Overriding a model, an effort or a role's tier

Each example below is a file you can write by hand, or the `PATCH` for `config set` with the same
keys minus `schema_version`.

**A model.** Run the deep tier on a named model for every run on this machine. User file
`${XDG_CONFIG_HOME:-~/.config}/agent-orchestrate/models.json`:

```json
{
  "schema_version": 1,
  "providers": {
    "claude": {
      "deep": { "model": "DEEP_MODEL_ID" }
    }
  }
}
```

`DEEP_MODEL_ID` is a placeholder: put in its place a model identifier from the host SOP's model
list ([Claude](hosts/claude-code.md), [OpenAI](hosts/openai.md),
[Antigravity](hosts/antigravity.md)). The merge changes only
`providers.claude.deep.model`; the deep tier's `effort` and every other tier keep their values.

**An effort.** Raise the effort behind the standard tier for one project. Project file
`<project root>/.agent-orchestrate/models.json`:

```json
{
  "schema_version": 1,
  "providers": {
    "openai": {
      "standard": { "effort": "high" }
    }
  }
}
```

**A role's tier.** Move reviewers to the deep tier for one project, for example where a review gates
a release. Project file `<project root>/.agent-orchestrate/models.json`:

```json
{
  "schema_version": 1,
  "roles": {
    "reviewer": "deep"
  }
}
```

After any override, run `python3 scripts/ao.py config --explain --project DIR` and confirm the
value shows the layer you expected.

## Overriding a run setting

Close experiment branches without integrating them, and cap a project's runs at four active
agents. Project file `<project root>/.agent-orchestrate/config.json`:

```json
{
  "schema_version": 1,
  "agents": { "max_active": 4 },
  "branch_kinds": {
    "experiment": { "integrate": "discard" }
  }
}
```

An experiment branch still waits for the user's go, since its `lands` keeps its shipped `ask`, and
feature and hotfix branches still close by `merge`.

## Related

- [SKILL.md](../SKILL.md): the run checklist, which resolves config before planning.
- [defaults.json](../config/defaults.json) and [models.json](../config/models.json): the shipped
  baseline.
- [config.schema.json](../schemas/config.schema.json): the rules every config file follows.
- [ao.py](../scripts/ao.py): `config`, which merges the layers and names each value's source, and
  `config set`, which changes a setting in the user or project file.
- [isolation.md](isolation.md): what `branch_when`, `branch_kinds`, `agents.per_branch` and
  `default_tier` decide.
- [standing.md](../assets/standing.md): the rule for an agent whose task's `layers_below` lets it
  spawn agents of its own.
- [widgets.md](widgets.md): the views `report_moments` turns on, and the `config` and `roles`
  settings views.
- [protocol.md](protocol.md): the role list and the `model_tier`, `model` and `effort` fields on a
  roster row.
- [hosts/claude-code.md](hosts/claude-code.md), [hosts/openai.md](hosts/openai.md) and
  [hosts/antigravity.md](hosts/antigravity.md): each host's model and effort values, its nesting
  cap, and on Claude the agent types `own_agents` and `role_agents` use.
