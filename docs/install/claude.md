# Claude Chat and Cowork

Start with the ZIP for the skill you want from the [library](../../README.md#choose-a-skill).

## Add it to your account

1. Open **Customize > Skills**.
2. Use the add button, choose **Create skill**, then **Upload a skill**.
3. Upload the ZIP and enable the skill in your list.
4. Start a new conversation or Cowork task and ask Claude to use the skill by name.

Use the upload steps even when Claude offers a **Save skill** button for a ZIP attached to a conversation. That button saves only `SKILL.md` and leaves out the skill's other files, so a skill with `references/`, `assets/` or scripts will not work properly.

Skills require **Code execution and file creation**. Your organization's settings may also control whether you can upload them. Anthropic's [Skills guide](https://support.claude.com/en/articles/12512180-use-skills-in-claude) covers the current menus and prerequisites.

## Cowork and local files

Cowork loads enabled skills from your Claude account. Putting a folder in `~/.claude/skills/` alone does not install it for Cowork. See Anthropic's [Cowork and cloud-session guidance](https://code.claude.com/docs/en/skills#use-skills-in-cowork-and-cloud-sessions).

Use the [Claude Code guide](claude-code.md) for local folder installation.

Documentation checked: September 21, 2026. Attached-ZIP install tested: October 21, 2026.

## Related

- [Installation overview](README.md)
- [Back to the library](../../README.md)
