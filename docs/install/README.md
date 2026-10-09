# Install a Groundwork skill

Choose a skill from the [library](../../README.md#choose-a-skill), then use the route that fits your AI tool. You can install one skill at a time.

## Ask your AI to help

Give it the link to the specific skill folder, or attach that skill's ZIP, and ask:

> Download and install this skill for me. Keep its folder together, and show me how to use it.

If the tool can manage skills, it can help install the package. Otherwise, ask it to walk you through the upload steps for the app you are using.

## Upload the ZIP

The **ZIP** links in the library download individual skill packages from [GitHub Releases](https://github.com/GroundworkBusiness/groundwork-skills/releases). Each ZIP contains one skill folder, including any files it needs.

Upload that ZIP through your tool's Skills area where skill uploads are available. The location and availability depend on the tool and your workspace settings.

| Your tool | Guide |
| --- | --- |
| Claude Chat or Cowork | [Upload a skill to your Claude account](claude.md) |
| Claude Code | [Ask Claude Code to install it, or use a local folder](claude-code.md) |
| ChatGPT Work | [Find the installation route your workspace offers](chatgpt-work.md) |
| Codex | [Use the skill installer, or a local folder](codex.md) |

## Use a local folder

For a tool that reads skills from your computer, unzip the package and install the named skill folder in the location listed in its guide.

If you download the whole repository using GitHub's **Code > Download ZIP**, unzip it first. The individual packages are inside `skills/live/`. The repository ZIP itself is not a single skill to upload.

Keep each package intact, including `references/`, `assets/`, or `agents/` when present. Before replacing an installed copy, save any changes you have made to it.

## Try a single-file skill as a prompt

If the skill folder contains only `SKILL.md` and its license, you can copy the instruction text into a chat before your request. That supplies instructions for the conversation; it does not install a reusable skill.

Use the complete package for skills with supporting files. For example, Knowledge Base Builder includes a contract and companion skills that the main file refers to.

## Confirm it is ready

After installation, find the skill in your tool's skill list or ask the tool to locate it. Try it on a small task you understand, and check the result. The individual guides show how to select a skill explicitly.

## Related

- [Back to the library](../../README.md)
- [Claude](claude.md) · [Claude Code](claude-code.md) · [ChatGPT Work](chatgpt-work.md) · [Codex](codex.md)
