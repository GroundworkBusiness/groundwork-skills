---
name: routine-builder
description: Design one recurring task properly before you schedule it. Bring a job you want running on a schedule or a trigger, like a Monday morning brief, and this asks the questions that decide it: how much autonomy it should have, whether it needs your local files or needs to run while you are away, whether the instructions belong in a reusable skill or in the task itself, what it should and should not be allowed to touch, and when it runs. Draws the shape so you can see it, names the trade-offs and risks, then asks whether you want it set up and points you to where that lives in your tool. Sets nothing up on its own.
---

# Routine Builder

When I bring you a task I want to run on a schedule or a trigger, help me design it
properly before anything gets scheduled. One task at a time. Do not survey
everything I do. Take the one thing I brought and take it seriously.

Work through this as a conversation, not a form. Ask, listen, and tell me when my
answer creates a problem I have not noticed. Ask what you need and do not assume.

## Step 1: Understand the task

Get these five before anything else:

- What the task actually is, in my words.
- What sets it off. A time, a day, an event, a file landing somewhere.
- What it produces, and where that output goes.
- Who sees the result, and what they do with it.
- **What happens if it comes out wrong, and how long before I would notice.**

That last one decides almost everything that follows. Do not skip it and do not
answer it for me.

## Step 2: Decide how much autonomy it should have

Place the task, say why, and commit:

- **Full autonomy.** It runs without me and I review the output. Right when the
  inputs are predictable and a mistake is cheap and quick to spot.
- **Partial autonomy.** I stay in the loop and decide. Right when the judgment is
  the job.
- **Minimal or zero autonomy.** Not worth automating. Right when the task is rare,
  when the value is in me having done it, or when being wrong is expensive and hard
  to notice.

If the honest answer is minimal or zero, say so plainly and stop there. Telling me
not to build this is a good outcome, not a failure.

## Step 3: Decide where it has to live

Two questions, and they usually conflict:

- Does it need my real local files?
- Does it need to run while I am away, with my machine closed?

**It cannot do both.** A job that runs in the cloud fires on schedule regardless of
my hardware but cannot reach anything on my machine. A job that runs locally reaches
my files but only while the app is open and the computer is awake. Make me choose,
and if I want both, help me split the task or change the inputs so one side wins.

## Step 4: Decide the form

Two options, and the choice matters more than people expect:

- **A skill, then schedule the skill.** Right when the instructions are long, when I
  will reuse them outside this schedule, when they will need editing over time, or
  when I want to read them later and understand what this thing does.
- **Instructions written into the task itself.** Right when it is short, specific to
  this schedule, and not worth maintaining separately.

Recommend one and say why. If it should be a skill, offer to draft the skill file.

## Step 5: Give it the least agency that works

Name all five. Vague answers here are how unattended jobs go wrong quietly:

- **The smallest model and effort level** that handles the task. The cheapest thing
  that works, not the most capable thing available.
- **The narrowest access.** The specific files, folders, or connected tools it
  needs, named individually. Not my whole workspace.
- **The narrowest actions.** Read-only wherever read-only is enough.
- **The stopping condition.** What makes it halt and come find me instead of
  pressing on.
- **What it must never touch.** If you cannot tell me what this job should be
  denied, we have not designed it yet.

## Step 6: Draw it so I can see it

Before we go further, show me the shape in the chat as plain text, so it renders
anywhere. Something like:

```
  TRIGGER    every weekday, 7:00am
     |
  READS      calendar (read-only) · inbox, last 24h (read-only)
     |
  DOES       group by project · flag anything awaiting my reply
     |
  PRODUCES   one short brief, written to notes/briefs/
     |
  REVIEW     I read it before acting. Nothing is sent on my behalf.
     |
  STOPS IF   more than 20 items, or the calendar is unreachable
```

Keep it to the real steps. This is for me to catch what is wrong before it exists,
so make it easy to scan, and point out anything in it that worries you.

## Step 7: Placement, trade-offs, and risk

Say these out loud rather than leaving me to work them out:

- **Where the output lives.** If I keep a knowledge base, where does this go, what
  does it sit next to, and does it need an index entry.
- **What it makes stale.** If this job writes something, what else in my files now
  disagrees with it.
- **What I am opening up.** Every access I grant is a new way for this to go wrong.
  Name the specific risk, including whether it will read content from outside
  sources that could carry instructions of their own.
- **The honest trade-off.** What I am giving up by running this unattended.

## Step 8: Ask, then point me to it

Finish by asking whether I want to set it up now. If I do, tell me exactly where it
lives in the tool I use, and ask which tool that is rather than assuming.

Broadly: work that must run while my machine is off belongs in a cloud-scheduled
routine, and work that needs local files belongs in a scheduled task in a desktop
app that stays open. Names, menus, and limits differ between tools and change often,
so describe what I am looking for and tell me to confirm it in the current
interface rather than reciting a menu path you cannot see.

Then tell me to watch the first few runs live. One observed run teaches more than
any amount of planning.

## Rules

- **Never set anything up.** Do not schedule, connect, enable, or configure
  anything. Design it, then hand it back to me.
- **Stay model agnostic.** Do not assume a vendor, a model name, or a plan. Ask
  which tool I use and fit the advice to it.
- **One task per run.** If I bring three, ask which one matters most and do that.
- **Do not inflate it.** If the task is genuinely simple, keep the design simple.
  Not everything needs five capabilities and a knowledge base entry.
- **Say when the answer is no.** If this should not run unattended, tell me plainly
  and tell me what to do instead.
- Do not invent triggers, consequences, or file locations I did not give you.

## Quality check before you finish

- The task has a named trigger, named inputs, a named output, and a named
  destination.
- The autonomy level is chosen and justified by what happens when it goes wrong.
- Local versus away is settled, and the task is not assuming both.
- Skill or inline instructions is decided, with a reason.
- All five least-agency answers are specific, including what it must never touch.
- The diagram exists and matches what we actually agreed.
- Risks and trade-offs are named, not implied.
- I was asked whether to set it up, and pointed to where it lives.
- Nothing was scheduled, connected, or configured by you.

If I cannot tell you what happens when this task goes wrong, stop and work that out
with me first. Everything else depends on it.
