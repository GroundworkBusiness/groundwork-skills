---
name: handoff
description: Write a clean handoff when you need to pause, hand this off, or pick this up next time. Produces a self-contained summary a new chat, a different tool, or a colleague can pick up cold.
---

# Handoff

When I ask for a handoff, write a short, self-contained summary that lets a brand new chat (or another person) continue this work without any of our history. This is a state-transfer task, not another implementation pass. Assume the reader was not here for any of it.

## One file, always overwritten

A handoff is a rolling resume point, not a historical log. Each run overwrites the last. Never keep `HANDOFF-v2.md`, dated copies, or an append-only log.

## Where to save it

- **If you can write files**, save the handoff as `HANDOFF.md` in the workspace or project root. If no clear root, ask me where to put it, or print it inline so I can save it where it belongs.
- **If you cannot write files** (chat-only environment), print the handoff inline. I will copy it.

## Content shape

Use a `## Section Header` for each of the following, in order. Keep each section to a short paragraph or a few bullets, no walls of text. Omit any section that genuinely does not apply.

1. **Goal.** One or two sentences on what we are trying to accomplish.
2. **Context.** The facts, materials, and constraints someone would need to step in. Include anything I pasted or pointed to that still matters.
3. **Decisions so far.** What we settled on, and why, so it does not get re-argued.
4. **Where we are.** What is done (with verification, if any was performed), and what is in progress right now. Distinguish what you actually checked from what is assumed.
5. **Files and artifacts.** Any files, links, or artifacts the next session will need. Name them precisely.
6. **Next steps.** The specific next actions, in the order they should happen.
7. **Open questions.** Anything unresolved, or waiting on me.

## Rules

- Keep it tight and concrete. Plain language, short sentences, no filler.
- Aim for under one screen of reading. If it runs past 400 words, you have too much narrative.
- Write for a cold reader. No "as we discussed" or "we agreed." Name the thing directly.
- Distinguish facts from assumptions. If something is unknown or unverified, say so plainly instead of guessing.
- Pull the real specifics: names, numbers, file names, exact wording that matters. A handoff that is too vague to act on has failed.
- Do not commit, push, or send the handoff anywhere outside the user's machine. The user moves it from here.
- Finish with one line I can paste into a new chat to start it cold, in this shape: "Pick up this work. The handoff above has the full context. The immediate next step is: ..."

## Quality check before you finish

- The next session could start cold from this one file.
- The first item in Next steps is concrete and immediately actionable.
- Anything you did not actually verify is labeled as an assumption.
- The file does not contain unrelated changes or commentary.

If I have not given you enough to write a useful handoff, ask me what is missing before you write it.
