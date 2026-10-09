# explainer

**The question:** "How does it work?" Also: what happens when I run this, walk me through the flow,
what talks to what, how does X fit with Y.

**Reach for it when** the answer is a mechanism: a command that starts a skill that forks an agent
that returns a table; a request moving through a pipeline; how two tools hand work to each other.
It is also the shape to show before a spec is written, so the reader can see the flow and correct
it while correcting is cheap.

## Rules

- **The shape.** A row of three or four boxes with arrows, left to right, over two detail cards that
  each open one of the boxes above. Each box is a name (`th`) and a two-word subtitle (`ts`):
  `/audit · you type this`, `skill · the procedure`, `agent · the sandbox`,
  `drift table · claim vs live`. Each card holds four or five short label lines
  (`tools: Read, Grep, Glob, Bash`, `no Agent, so it cannot fan out`).
- **Caption-free frame.** No title line and no state chip: the boxes are the title. The action row
  sits beneath: run it, walk through a real run, show the next level down.
- **Three or four boxes.** Five or more shrink each box below its label; split into an overview
  and a second widget for the part that matters, with text between.
- **Two ramps plus gray.** Gray for the ends (what the reader types, what comes back), one ramp per
  kind of thing in the middle. A detail card takes the ramp of the box it opens.
- **Subtitles are two words**, detail lines are labels. A line that needs a verb and an object
  (`checks each claim against live`) is the longest a line gets.
- **Arrows stop at box edges** and never cross another box or label.
- **Box width from the longest label**: about 8px per character at 14px and 7px at 12px, plus 24px
  of padding. Four boxes and three gaps fit in 600px.
- **Every box is a `class="node"` group** that sends a question about itself, with a `<title>`
  carrying the one-line detail that would not fit.
- **Built in SVG when static;** in HTML with inline SVG when a stepper or a toggle earns its place
  (step through one box at a time, or switch between the happy path and the failure path).
- **A cycle is a stepper with a return**, never a ring of boxes.

## Vary the composition

- Top to bottom instead of left to right when the flow is a stack (layers, a call chain).
- One detail card spanning the width when only one box needs opening.
- Boxes grouped in a dashed container when some of them run in one place (inside the fork, on the
  server).
- An HTML stepper, one panel per stage, when each stage has its own inputs and outputs.
