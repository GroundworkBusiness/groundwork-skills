# Codex

## Ask the skill installer

Give Codex the link to the individual skill folder and ask it to install that skill. For example:

> Use $skill-installer to install https://github.com/GroundworkBusiness/groundwork-skills/tree/main/skills/ask-first for my personal use. Keep the complete folder, and check before replacing an existing copy.

You can also give Codex the location of a ZIP you downloaded from the [library](../../README.md#choose-a-skill).

## Install the folder yourself

Unzip the package and copy the skill folder into the appropriate location:

| Scope | Location of the instruction file |
| --- | --- |
| Your user account | `~/.agents/skills/ask-first/SKILL.md` |
| One repository | `<your-repository>/.agents/skills/ask-first/SKILL.md` |

Keep the rest of the package alongside `SKILL.md`.

## Use it

Select the installed skill in your tool's skill picker. In Codex CLI or the IDE extension, use `/skills` or mention `$ask-first` in your request. Codex can also select relevant skills automatically. If the skill does not appear after installation, restart the session.

Source: [OpenAI's skill documentation](https://learn.chatgpt.com/docs/build-skills). Documentation checked: September 21, 2026.

## Related

- [Installation overview](README.md)
- [ChatGPT Work](chatgpt-work.md)
- [Back to the library](../../README.md)
