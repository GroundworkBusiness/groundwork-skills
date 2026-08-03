# Groundwork Skills

Eight small, portable skills for working with AI. They work on their own, and they
work better together.

Each skill is a short markdown file that tells the AI how
to behave before it starts working. That is the whole idea.

## What a skill is

A skill is a saved instruction set the AI reads before it does a task. Instead of
explaining the same expectations at the start of every chat, you write them once
and load them. The AI picks the skill up when the work matches.

A skill is plain markdown with a name and a description at the top. You can read
every one of these in about two minutes, and you should, because a skill you have
not read is just an instruction you did not write.

## The eight

| Skill | What it does |
|---|---|
| `ask-first` | Makes the AI ask before it assumes. Questions first, honesty about what it does not know, a plan you approve before it acts. |
| `handoff` | Writes a self contained summary of a session so you can move chats, move tools, or hand off to a person without losing the thread. |
| `close-out` | The sibling of handoff. Ends a session by making sure your files, notes, and index are actually true before you walk away. |
| `brain-dump` | Turns a recorded walkthrough plus your real files into structured entries. Works on copies, folds into what exists, asks before it files. |
| `knowledge-base-builder` | Inspects, interviews, plans, and shows you the structure before building a file based knowledge base. Ships with companion ingest, query, and lint skills. |
| `connector-check` | Reviews a connector before you trust it: what it can access, what it can do, what it costs you in context, and whether it earns its place. |
| `routine-builder` | Designs one recurring task before you schedule it: how much autonomy, local or cloud, skill or inline, what it may and may not touch, and when it runs. |
| `skill-check` | Inspects a skill before you load it, and audits the ones you already have. Reads the actual files rather than the description, separates what it quietly does from what should worry you, and gives you a plain verdict. Installs nothing. |

## Using them

Each skill is a folder containing a `SKILL.md`. Copy the folder into wherever your
tool looks for skills.

**Claude Code.** Drop the folder into `~/.claude/skills/` for personal use, or
`.claude/skills/` inside a project to scope it to that project. It becomes
available in new sessions.

**Codex and other CLI harnesses.** Same shape. Place the folder in the skills
directory your install reads, or point your `AGENTS.md` at it. Check your tool's
own documentation for the exact path, since these differ between versions.

**ChatGPT on the web.** Open **Plugins** in the sidebar, then the **Skills** tab,
then **Create** and **Upload from your computer**. Two things worth knowing before
you try. Skills are generally available on Business, Enterprise, Healthcare, and
Edu plans rather than Free or Plus. And on Enterprise and Edu workspaces the
feature is off by default and an administrator has to switch it on. If you do not
see a Plugins entry in your sidebar, that is usually why. Personal skills also do
not sync between the desktop app and web, so you add them in each place
separately. Verified against OpenAI's documentation in August 2026; check it
yourself if the interface has moved.

## Read them before you run them

These files instruct an AI on your behalf, and that is exactly why you should read
one before loading it. That applies to skills from anyone, including these. ChatGPT
scans uploads and will sometimes flag one for review, which is the same instinct
pointed at the same problem.

`skill-check` does that reading with you. Point it at a skill before you install it,
or at the ones already sitting in your skills directory. It reads every file the
install would leave on your machine, including the hooks and manifests that never
appear in a `SKILL.md`, and it reports rather than acts. It changes nothing and
installs nothing, including itself.

## License

MIT. Use them, change them, ship them in your own work. Attribution is welcome and
not required.

---

Built by [Groundwork Business Consulting](https://groundworkbusiness.com).
AI built on solid ground.
