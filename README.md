# Groundwork Skills

Groundwork's library of AI skills, reusable workflows, and supporting resources, built by [Groundwork Business Consulting](https://groundworkbusiness.com).

A skill is a saved set of instructions for a task you do more than once. Give your AI a way to ask better questions, carry work between sessions, organize knowledge, or check the tools you use. Pick the skills that fit your work, read them, and make them your own.

The library grows as Groundwork develops and shares skills. Each skill has its own folder, with the files it needs. `skills/live/` holds the released skills, and `skills/in-progress/` holds skills that are still being finished. The downloads and the plugin come from `skills/live/`. Installation guides and examples live in `docs/`.

## Choose a skill

| Skill | What it does | Download |
| --- | --- | --- |
| [Ask First](skills/live/ask-first/SKILL.md) | Asks useful questions and lays out a plan before acting. | [ZIP](https://github.com/GroundworkBusiness/groundwork-skills/releases/latest/download/ask-first.zip) |
| [Handoff](skills/live/handoff/SKILL.md) | Writes a summary another chat, tool, or person can pick up. | [ZIP](https://github.com/GroundworkBusiness/groundwork-skills/releases/latest/download/handoff.zip) |
| [Close-Out](skills/live/close-out/SKILL.md) | Checks the work and brings files and status up to date before you finish. | [ZIP](https://github.com/GroundworkBusiness/groundwork-skills/releases/latest/download/close-out.zip) |
| [Brain Dump](skills/live/brain-dump/SKILL.md) | Turns a recorded walkthrough and your working files into structured knowledge. | [ZIP](https://github.com/GroundworkBusiness/groundwork-skills/releases/latest/download/brain-dump.zip) |
| [Knowledge Base Builder](skills/live/knowledge-base-builder/SKILL.md) | Plans and builds a file-based knowledge base, with companion skills for adding, finding, and checking knowledge. | [ZIP](https://github.com/GroundworkBusiness/groundwork-skills/releases/latest/download/knowledge-base-builder.zip) |
| [Connector Check](skills/live/connector-check/SKILL.md) | Reviews what an AI connection can access and do, and whether it earns its place. | [ZIP](https://github.com/GroundworkBusiness/groundwork-skills/releases/latest/download/connector-check.zip) |
| [Routine Builder](skills/live/routine-builder/SKILL.md) | Designs a recurring task, including its schedule, autonomy, and boundaries. | [ZIP](https://github.com/GroundworkBusiness/groundwork-skills/releases/latest/download/routine-builder.zip) |
| [Skill Check](skills/live/skill-check/SKILL.md) | Reads a skill or plugin's files and reports what it does, what deserves attention, and what could not be checked. | [ZIP](https://github.com/GroundworkBusiness/groundwork-skills/releases/latest/download/skill-check.zip) |

Each ZIP contains one complete skill folder and its license. Downloads live in [GitHub Releases](https://github.com/GroundworkBusiness/groundwork-skills/releases). The editable originals live in [skills/live/](skills/live/).

## In progress

These skills work but are still being finished, so their instructions may change. They have no ZIP download, and the plugins do not load them. To try one, give your AI the link to its folder, or copy the whole folder as described in [How to add one](#how-to-add-one).

| Skill | What it does |
| --- | --- |
| [Inline Widgets](skills/in-progress/inline-widgets/SKILL.md) | Draws answers as interactive visuals inside the chat: trees, lists, explainers, timelines, boards, comparisons, and charts. Needs a chat with the show_widget tool. |
| [Meeting Recap](skills/in-progress/meeting-recap/SKILL.md) | Turns meeting notes, a transcript, or a recording into a recap of what was decided, who owes what by when, and what is still open, as Markdown and a PDF in your own brand. |

## How to add one

**Want the simplest path?** Give your AI the link to the skill you want, or attach its ZIP, and ask:

> Download and install this skill for me. Keep its folder together, and show me how to use it.

If your tool can manage skills, it can help put the files where they belong. If it cannot, use its Skills upload area or follow the guide for your tool:

- [Claude Chat and Cowork](docs/install/claude.md)
- [Claude Code](docs/install/claude-code.md)
- [ChatGPT Work](docs/install/chatgpt-work.md)
- [Codex](docs/install/codex.md)

There are several ways to add a skill. The [installation overview](docs/install/README.md) explains ZIP uploads, local folders, and using a single-file skill as a prompt.

**Keep the whole folder.** Some skills need references or companion files beside `SKILL.md`. Copying only the instruction text leaves those files behind.

**Want the whole library at once?** Claude Code and Codex can install it as one plugin and update it from this repository:

```sh
claude plugin marketplace add GroundworkBusiness/groundwork-skills
claude plugin install groundwork-skills@groundwork-skills
```

```sh
codex plugin marketplace add GroundworkBusiness/groundwork-skills
codex plugin add groundwork-skills@groundwork-skills
```

The plugin brings every skill in the library. To skip one, turn it off in your tool, or add skills one at a time as described above.

## Read it before you run it

Skills give an AI instructions on your behalf. Read the files before adding one, including skills from this library. [Skill Check](skills/live/skill-check/SKILL.md) can help you do that reading.

The [example Skill Check report](docs/examples/skill-check/README.md) shows the report format using an invented target. It is an illustration, not a finding about a real product.

## Environment

No local Python setup is needed to use these skills. The following environment is for maintainers who validate the library and build download packages: Python 3.11 or later, managed with [uv](https://docs.astral.sh/uv/).

```sh
uv sync --locked
uv run python scripts/build_packages.py --check
uv run python scripts/build_packages.py
```

The build discovers the skill folders in `skills/live/` automatically and writes one ZIP per skill and a checksum file into `dist/`. See [adding skills and releasing the library](docs/releasing.md).

## License

[MIT](LICENSE). You can use, change, and redistribute the skills. Keep the copyright and license notice with copies or substantial portions of the work.

Built by [Groundwork Business Consulting](https://groundworkbusiness.com). AI built on solid ground.

## Related

- [Installation overview](docs/install/README.md)
- [Skill source folders](skills/)
- [Example report](docs/examples/skill-check/README.md)
- [Releasing the library](docs/releasing.md)
