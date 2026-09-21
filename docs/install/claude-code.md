# Claude Code

## Ask Claude Code to install it

Give Claude Code the link to the skill folder or the location of its downloaded ZIP. For example:

> Install the Ask First skill from https://github.com/GroundworkBusiness/groundwork-skills/tree/main/skills/ask-first for my personal use. Keep the complete folder, and check before replacing an existing copy.

## Install the folder yourself

Unzip the skill package and copy its folder to one of these locations:

| Scope | Location of the instruction file |
| --- | --- |
| Your local projects | `~/.claude/skills/ask-first/SKILL.md` |
| One project | `<your-project>/.claude/skills/ask-first/SKILL.md` |

Replace `ask-first` with the selected skill's folder name. Keep its supporting files alongside `SKILL.md`.

Claude Code can also sync enabled account skills when you sign in with a Claude account. Follow the [Claude account guide](claude.md) for that route. Local installation and account syncing are distinct options.

## Use it

Type `/ask-first`, replacing the name with your installed skill. Claude can also choose a skill when your task matches its description. If a newly installed skill does not appear, start a fresh session and check the folder location.

Source: [Anthropic's skill documentation](https://code.claude.com/docs/en/skills). Documentation checked: September 21, 2026.

## Related

- [Installation overview](README.md)
- [Claude Chat and Cowork](claude.md)
- [Back to the library](../../README.md)
