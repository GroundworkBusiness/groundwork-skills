---
name: inline-widgets
description: Draws answers as interactive visuals inside the chat with the show_widget tool, in seven shapes. A placement tree shows where something lives, a contents list shows what is in it, an explainer shows how it works, lanes show how it changed over time, a run board shows what is happening now, a comparison shows which option to pick, and a chart shows how much and how fast. Use when asked to show, visualize, draw, map, chart or render something, or asked "where does X live", "what's in X", "how does X work", "what changed", "what's the status" or "which should I pick", at each milestone of multi-step work, and before any decision the reader has to make. Includes a design system, a guide for each shape and working examples.
argument-hint: "[subject]"
---

# Inline widgets

Subject named with the command, if any: $ARGUMENTS

## What this covers

Inline chat widgets: the fragments Claude renders inside the conversation with the show_widget
tool, where the reader can see them, click them and keep reading.

Run `/inline-widgets [subject]` to make a widget now for the subject named after the command, or
for the current context when nothing is named: the answer just given, the work in progress, the
decision on the table. Claude also loads this skill on its own when an answer has a shape, and
renders without asking permission first. Either way, pick the module, render the widget, and put
the words in the chat beside it. Ask first only when two subjects are equally likely.

It needs a chat that provides the show_widget tool. Where there is none, give the same answer as a
markdown list or table.

It carries three things:

- **A design system**: tokens on the host's theme, a status set and a lane set, type, the widget
  shell, layout invariants, interaction rules, four allowances with their limits, and the
  anti-patterns. [design-system.md](design-system.md)
- **Seven modules**, each keyed to the question the reader is asking. [modules/](modules/)
- **Working examples**, one per module, named after it. [examples/](examples/README.md)

## Pick the module from the question

The reader's question picks the module. Read the module's guide before drawing it.

| The reader is asking | Module guide | Example |
|---|---|---|
| "Where does it live?" | [placement-tree](modules/placement-tree.md) | [placement-tree.html](examples/placement-tree.html) |
| "What's in it?" | [contents-list](modules/contents-list.md) | [contents-list.html](examples/contents-list.html) |
| "How does it work?" | [explainer](modules/explainer.md) | [explainer.svg](examples/explainer.svg) |
| "How did it change?" | [lanes](modules/lanes.md) | [lanes.html](examples/lanes.html) |
| "What's happening now?" | [run-board](modules/run-board.md) | [run-board.html](examples/run-board.html) |
| "Which should I pick?" | [compare](modules/compare.md) | [compare.html](examples/compare.html) |
| "How much, how fast?" | [chart](modules/chart.md) | [chart.html](examples/chart.html) |

**Contents versus shape.** "What's in X" gets a contents-list: the literal contents, enumerated,
every table with its columns, every file, every field. "Where does X live" or "how does X fit" gets
a placement-tree or an explainer. When a request could be either, enumerate first and offer the
shape as a ↗ follow-up. A diagram drawn when the reader wanted the list is the wrong answer.

**One subject per widget, three modules at most.** A second subject is a second widget, with text
between the two.

**Format.** Use HTML for trees, tables, cards and anything with a control. Use inline SVG inside
the HTML when data places the marks (lanes, chart). Use a standalone SVG only for a static picture
of fixed boxes and arrows (the explainer) that needs click-throughs and nothing else.

## Workflow

1. **Name the question**, then the module from the table above.
2. **Read** [design-system.md](design-system.md) once per session, and the module's guide each time
   you use a module.
3. **Open the module's example** for its structure. Follow the structure and vary the composition:
   your subject, your data, your layout within the module's rules. Never clone an example
   wholesale, and never reuse one composition across a set of widgets.
4. **Gather real values first.** Correct beats pretty: every number, name and status traces to a
   command, file or source read in this turn. Say `unknown` in the widget rather than guess.
5. **Build the fragment.** HTML: the hidden `<h2 class="sr-only">` summary, a short style block
   with only the `--iw-*` tokens the widget uses, the content, the script last. SVG: `role="img"`
   with `<title>` and `<desc>` first, ramp classes for color, `viewBox` 680 wide.
6. **Make it interactive**: an action row with at least one ↗ button that sends the natural next
   request, drill-in on rows and marks that have more behind them, and detail on hover. HTML
   widgets also get at least one local filter or toggle.
7. **Run the pre-flight** at the end of the design system. It reads the markup, not the render.
8. **Render** with show_widget. Call the host's `read_me` once per session before the first
   render, as the tool asks.
9. **Put the words in the chat**, structured: a line before the widget when its subject is not
   obvious; after it, short bulleted lists with bold headers and a table for sources. Add what the
   widget cannot show (why, what it means, what to do) and never restate what it shows.
10. **Pair it with the question.** When a decision is pending, the widget carries the proposal and
    the chat, or a question dialog, asks for the decision beside it.

## House rules

- **The widget holds the picture; the chat holds the words.** Inside: labels, values, legends,
  chips, control names, and at most one callout line for the fact that changes the decision.
- **Readable first.** Labels in fixed columns, marks placed by data, per-mark detail in tooltips,
  truncation with the full text on hover, about 44px clear at the top right.
- **Visualize often.** At each milestone of multi-step work, not only at the end. Show the visual
  before the plan or the decision, not after it.
- **Color encodes.** Up to five color families when each means something, with a legend. Color that
  only flags gets one accent. Red is live attention: running now, or needs you.
- **Every widget is interactive**, and ↗ marks every control that sends a message. Local controls
  cost nothing and carry no arrow.
- **Re-render on request.** A live view refreshes when the reader clicks `Refresh ↗` or asks; no
  timers and no background process keeping the chat busy.
- **Neutral by default.** Host tokens and host type. A brand color only when the reader asks for it.
- **Name things so they can be followed.** Real branch, file and role names in mono, full names on
  hover.
