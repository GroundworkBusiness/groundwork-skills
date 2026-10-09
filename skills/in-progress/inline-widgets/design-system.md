# Design system

The rules every inline widget follows, whichever module it uses. Read this once per session before
the first render, then the guide in `modules/` for the shape you are drawing.

The host's own widget guidance (the `read_me` the widget tool asks for before its first call) still
applies. This system sits on top of it: it keeps every technical constraint the host sets and
replaces the host's style defaults in exactly four places, listed under **Allowances**.

## Contents

- Principles
- Tokens: surfaces, text and lines; the status set; the lane set; the token block; the accent and a
  brand color; SVG widgets
- Typography
- The shell
- Layout invariants
- Interaction
- Allowances: tables, kickers and weight 600, up to five color families, one callout line
- The words around a widget
- Anti-patterns, and what to do instead
- Pre-flight

## Principles

1. **The widget holds the picture; the chat holds the words.** Labels, values, legends, chips and
   control names go inside. Anything that explains, qualifies, warns or instructs goes in the chat,
   alternating widget, text, widget. The one exception is the single callout line (see
   **Allowances**).
2. **Readable comes first.** Labels sit in fixed columns and rows, marks sit where their data puts
   them, per-mark detail waits on hover, long labels truncate with the full text on hover, and the
   top-right corner stays clear for the host's menu. Good information in a messy render is a failed
   render.
3. **Correct beats pretty.** Every number in a widget traces to a command, file or source read in
   this turn. A confident wrong fact is worse than no widget.
4. **Color encodes.** A hue appears because it means something, and a legend says what. Color that
   only flags gets one accent.
5. **Every widget is interactive.** At least one ↗ button sends the natural next request; marks and
   rows with more detail drill in; hover carries detail; filters and toggles run locally for free.
6. **Neutral by default.** Host tokens and host type, so a widget reads as part of the chat in both
   themes and can be shared. Brand color arrives only on request.

## Tokens

Widgets name colors by meaning, through the `--iw-*` custom properties below. Their values are the
host's theme variables, so light and dark mode work natively and nothing is re-declared per theme.
Declare them on the widget's outermost element (class `iw`), and declare only the ones the widget
uses.

### Surfaces, text, lines

| Token | Value | Use |
|---|---|---|
| `--iw-ink` | `var(--text-primary)` | values, names, primary labels |
| `--iw-ink-2` | `var(--text-secondary)` | descriptors, kickers, legend text |
| `--iw-ink-3` | `var(--text-muted)` | axis ticks, captions, icons |
| `--iw-card` | `var(--surface-1)` | in-flow tiles, hover wash, quiet chips |
| `--iw-raised` | `var(--surface-2)` | raised cards with a hairline border |
| `--iw-line` | `var(--border)` | hairlines, row dividers, gridlines |
| `--iw-line-2` | `var(--border-strong)` | tree rules, column rules, emphasis |
| `--iw-line-3` | `var(--border-stronger)` | the rare heavy divider |

The outer background stays transparent: the host paints it.

### Status set

One meaning per family, the same in every module. Pair every status color with a word, a shape or
a position, so no judgment rests on hue alone.

| Status | Means | Text / mark | Tint | Line | SVG ramp |
|---|---|---|---|---|---|
| `live` | live attention: running now, or needs you | `--text-danger` | `--bg-danger` | `--border-danger` | `c-red` |
| `done` | done, merged, crossed, passing | `--text-success` | `--bg-success` | `--border-success` | `c-green` |
| `edit` | an edit, the callout, work that stopped short | `--text-warning` | `--bg-warning` | `--border-warning` | `c-amber` |
| `exists` | already there, unchanged, idle, queued | `--text-secondary` | `--surface-1` | `--border` | `c-gray` or `box` |
| `new` | new, proposed, added | `--text-accent` | `--bg-accent` | `--border-accent` | `c-blue` |
| `moved` | moves in, relocated, renamed | `--text-pro` | `--bg-pro` | `--border-pro` | `c-purple` |

`moved` uses the host's `pro` tint where the host has one and falls back to the accent family where
it does not, so the chip always has a color. The word on the chip carries the meaning either way.

**Red carries two states, told apart by form.** Running now is a filled red dot beside its word.
Needs you is a red-tinted chip (`your call`, `needs you`, `blocked`), a red ring where a dot would
sit, or a 2px red frame round the card that is waiting. A finished item is never red: it takes a
muted gray ring or a green `done`. A reader scanning for where to act looks for the chip, the ring
and the frame; a reader scanning for activity looks for filled dots.

### Lane set

Five families for telling lanes, series, stages, vendors or versions apart. They avoid the status
hues first, so a lane never reads as a status. Use them in this order and never cycle past five.

| Lane | HTML text / mark | HTML tint | SVG ramp |
|---|---|---|---|
| 1 | `var(--text-tint-aqua, var(--text-success))` | `var(--bg-tint-aqua, var(--bg-success))` | `c-teal` |
| 2 | `var(--text-tint-violet, var(--text-pro, var(--text-accent)))` | `var(--bg-tint-violet, var(--bg-pro, var(--bg-accent)))` | `c-purple` |
| 3 | `var(--text-tint-orange, var(--text-warning))` | `var(--bg-tint-orange, var(--bg-warning))` | `c-coral` |
| 4 | `var(--text-tint-magenta, var(--text-secondary))` | `var(--bg-tint-magenta, var(--surface-1))` | `c-pink` |
| 5 | `var(--text-tint-blue, var(--text-accent))` | `var(--bg-tint-blue, var(--bg-accent))` | `c-blue` |

The tint tokens are the host's per-hue palette; each carries a role token as its fallback, so the
lane still resolves to a theme color if a host build omits the tints.

### The token block

Copy what the widget uses. No comments inside widget code: the host streams it and comments waste
the stream.

```css
.iw{--iw-ink:var(--text-primary);--iw-ink-2:var(--text-secondary);--iw-ink-3:var(--text-muted);
--iw-card:var(--surface-1);--iw-raised:var(--surface-2);
--iw-line:var(--border);--iw-line-2:var(--border-strong);--iw-line-3:var(--border-stronger);
--iw-live:var(--text-danger);--iw-live-bg:var(--bg-danger);--iw-live-line:var(--border-danger,var(--text-danger));
--iw-done:var(--text-success);--iw-done-bg:var(--bg-success);
--iw-edit:var(--text-warning);--iw-edit-bg:var(--bg-warning);--iw-edit-line:var(--border-warning,var(--text-warning));
--iw-exists:var(--text-secondary);--iw-exists-bg:var(--surface-1);
--iw-new:var(--text-accent);--iw-new-bg:var(--bg-accent);
--iw-moved:var(--text-pro, var(--text-accent));--iw-moved-bg:var(--bg-pro, var(--bg-accent));
--iw-accent:var(--text-accent);--iw-accent-ink:var(--text-accent);--iw-accent-bg:var(--bg-accent);--iw-accent-line:var(--border-accent,var(--text-accent));
--iw-l1:var(--text-tint-aqua,var(--text-success));--iw-l2:var(--text-tint-violet,var(--text-pro, var(--text-accent)));
--iw-l3:var(--text-tint-orange,var(--text-warning));--iw-l4:var(--text-tint-magenta,var(--text-secondary));
--iw-l5:var(--text-tint-blue,var(--text-accent));
color:var(--iw-ink);font-size:13px}
```

### Accent, and a brand color on request

The accent (`--iw-accent`, the host's accent blue) marks the one thing that stands out when color
only flags: the recommended option, the selected row, the item under discussion. One accent per
widget.

A brand color replaces the accent family, the `new` status included, only when the reader asks for it
and names the color. It works as marks, 2px borders and chip tints. Text on a brand tint reads the
host's ink (`--iw-accent-ink`, `--iw-new`), because many brand colors fail contrast as text on a
light surface. Take one value for light mode and one for dark mode. The widget root carries
`data-mode`, so the dark override keys on it, with the operating-system setting as the fallback
when no mode is set. Replace `LIGHT` and `DARK` with the two values.

```css
.iw.brand{--iw-accent:LIGHT;--iw-accent-ink:var(--text-primary);--iw-accent-line:LIGHT;--iw-accent-bg:color-mix(in srgb,LIGHT 18%,transparent);--iw-new:var(--text-primary);--iw-new-bg:var(--iw-accent-bg)}
[data-mode="dark"] .iw.brand{--iw-accent:DARK;--iw-accent-line:DARK;--iw-accent-bg:color-mix(in srgb,DARK 22%,transparent)}
@media (prefers-color-scheme:dark){:root:not([data-mode]) .iw.brand{--iw-accent:DARK;--iw-accent-line:DARK;--iw-accent-bg:color-mix(in srgb,DARK 22%,transparent)}}
```

### SVG widgets

A widget that is one `<svg>` uses the host's ramp classes instead of custom properties, because
the host styles them for both themes and asks for no color `<style>` block in SVG mode.

- Status and lane colors: the ramp column in the tables above. Put `c-*` on the innermost `<g>`
  that holds the shapes, or on the shape itself. A `c-*` on an outer wrapper leaves nested shapes
  black.
- Neutral boxes: `class="box"`. Arrows: `class="arr"` with the host's `#arrow` marker. Leader
  lines: `class="leader"`.
- Lines and rules: `stroke="var(--t)"` (and the host's other short aliases), with opacity for
  weight.
- Text: every `<text>` carries `t`, `ts` or `th`. Inside a `c-*` group the text color follows the
  ramp.

Inline `<svg>` inside an HTML widget can use the `--iw-*` tokens through CSS classes, which is the
better route when a script draws the marks.

## Typography

| Role | HTML | SVG |
|---|---|---|
| header name | 14px, weight 600 | `th` (14px, 500) |
| primary row label, tree name, role | 13px; identifiers in mono | `t` or `th` |
| descriptor, table cell, button, callout | 12px | `ts` (12px) |
| chip, legend, kicker, axis tick, caption | 11px | `ts` |

- **11px is the floor.** Nothing smaller, including axis ticks. SVG measures at 1:1 only when the
  `viewBox` is 680 wide, so an SVG drawn wider shrinks its text below the floor.
- **Sans for words, mono for identifiers.** Paths, file and branch names, roles, commands, hashes,
  counts in a tally: mono. Everything a person would say aloud: the host sans.
- **Tabular numerals** (`font-variant-numeric: tabular-nums`) for any column or row of numbers.
- **Sentence case** everywhere except kickers.
- **Weights 400 and 500**, plus 600 for labels that must stand out (see **Allowances**).
- **Round every displayed number** to the precision the reader needs: integers for counts, one
  decimal for rates, locale formatting for money. Float noise such as `0.30000000000000004`
  never reaches the screen.

## The shell

Every widget with a state uses the same parts, in this order. Modules stack in the body; nothing
else moves.

1. **Header.** A short name (two to four words), the subject label in mono, and a **state chip**
   carrying the one fact that decides whether the reader must act (`2 need you`, `in sync`, `your
   call`, `38 behind`). The header row reserves 44px on its right for the host's menu, and is at
   least 32px tall with 12px beneath it, so the first full-width row below starts clear of the
   corner. Local controls (filters, toggles) sit in the header after the label, or in a row under
   it.
2. **Legend.** Whenever color encodes, before the body: one chip per meaning, in the order the
   body uses them.
3. **Tallies.** Optional single row of mono counts, when counting by eye would be work.
4. **Body.** One to three modules.
5. **Callout.** Optional, one line (see **Allowances**).
6. **Action row.** At the bottom, above nothing. The buttons that send, each ending in ↗. At least
   one on every widget.

An explainer is the exception to the header: it is caption-free, boxes first, with its action row
beneath. A widget that only teaches has no state to chip.

## Layout invariants

Mechanical rules. Follow them and a render cannot collide with itself; describe the outcome instead
and it will.

1. **Marks are positioned by data. Text never is.** A dot, bar, curve or box may sit wherever its
   value puts it. Every label lives in a fixed column or a fixed row, at a coordinate that does not
   depend on a value. Axis ticks sit at fixed scale positions; they are part of the frame.
2. **Per-mark detail goes in a tooltip**: a `title` attribute in HTML, a `<title>` child inside the
   mark in SVG. A commit is a dot; its hash and subject are on hover.
3. **The top-right corner belongs to the host.** Keep about 44px clear at the top right; header
   detail that does not fit goes on a second line under the name.
4. **One subject per widget, three modules at most.** A second subject is a second widget with text
   between them.
5. **A label longer than its column truncates at the column edge** with an ellipsis, and the full
   string goes in its tooltip. It never widens the column or spills into the next.
6. **No prose inside the frame** beyond the one callout line.

And the constraints of the widget environment, which nothing here overrides:

- `widget_code` is a fragment: no `<html>`, `<head>` or `<body>`, no doctype.
- HTML order: the hidden `<h2 class="sr-only">` summary, a short `<style>` block, the content, the
  `<script>` last. SVG order: `role="img"` on the root with `<title>` and `<desc>` as its first
  children, then `<defs>`, then the marks.
- Transparent outer background; the container is about 680px wide; grid columns use
  `minmax(0, 1fr)` so long content cannot push past the edge.
- No fixed positioning, no nested scrolling (horizontal included), no fullscreen calls.
- Nothing hidden with `display: none` while streaming: content in markup is visible as it arrives.
  A script may hide or expand things after streaming, and rows a script renders may be filtered.
- Every color through a CSS variable or a ramp class, so both themes work. No gradients, shadows,
  glows or blur.
- Icons are Tabler outline webfont glyphs (`<i class="ti ti-folder" aria-hidden="true"></i>`), 15
  to 20px. No emoji, no hand-drawn icon paths.
- External scripts only from `cdnjs.cloudflare.com`, `esm.sh`, `cdn.jsdelivr.net` or `unpkg.com`,
  loaded before the inline script that uses them.
- SVG: `viewBox` width 680, height fitted to the content plus about 24px; no named HTML entities
  (use the literal character or a numeric reference such as `&#8599;`), and `&` and `<` escaped
  inside attribute values.

## Interaction

Every widget is interactive, in four ways. Plan them with the content, not after it.

1. **An action row with at least one ↗ button.** It calls `sendPrompt(text)` with the natural next
   request: what the reader would most likely type after looking. Approve as shown, show the
   undeployed commits, draw how the tables relate, pick B.
2. **Drill in where detail exists.** A row, node, mark or card that has more behind it is clickable
   and sends a request about that item. Clickable things show a pointer cursor and a hover wash,
   and say what a click does: a ↗ that appears on hover where the row has room, otherwise a
   tooltip that ends in the action. In SVG, `class="node"` supplies the hover effect.
3. **Detail on hover.** Full names, timestamps, evidence, exact values.
4. **Local controls cost nothing.** Filters, hide toggles, a differences-only switch, a series
   toggle: handled in the script, never sent, and never marked with ↗. Toggle buttons carry
   `aria-pressed`. Rebuild rows in a container, never the control itself, so listeners survive.

**Writing the prompt text.** Write it as the reader would say it, self-contained: name the subject
and the item (`Show me what changed in "fix off-by-one" on feature/cache.`), one request per click,
nothing the reader would not recognise as their own words. A decision button states the decision
(`Answer the contract agent: ship v2 alongside. Then resume it.`). A "neither" button opens the
discussion instead of forcing a choice.

**Live views re-render on request.** A refresh is a ↗ button that asks for a fresh render. No
timers, polling or background fetches that keep the chat busy.

**Mark the default.** Where the agent has a default for a decision, the matching button says so, so
the reader can confirm in one click.

## Allowances

Four places where this system deliberately departs from the host's style defaults. Each has a
limit, and the limit is part of the rule.

### 1. Tables inside a widget

Use a table when the answer is rows the reader will scan across: a roster, the columns of a table,
the files in a folder, the facts per option.

- About **12 visible rows**. Past that, group the rows, filter them locally, or render the first 12
  from a script with a count and a local "show all". The complete list can also go in the chat as
  markdown.
- `table-layout: fixed` with explicit column widths. Long cells truncate with an ellipsis and carry
  the full text in `title`.
- Identifiers in mono, numbers right-aligned in tabular numerals, headers as kickers.
- Rows separated by hairlines, never zebra fills or card-per-row.

### 2. Kickers and weight 600

- **Kickers**: 11px mono, uppercase, letter-spacing about .07em, `--iw-ink-2`. For column heads and
  lane names only. In SVG, `class="ts"` with `style="font-family:var(--font-mono);letter-spacing:.08em"`.
- **Weight 600**: for labels that must stand out (the header name, a role in a roster, a table name
  over its columns). Never for body text or anything that reads as a sentence.

### 3. Up to five color families

- Up to **five color families when each encodes something**, with a legend. Neutral gray is the
  absence of color and never counts toward the five.
- The status set and the lane set can share a widget only when the legend separates them.
- When color only flags (a concern, a recommendation, the current item), use one accent and keep
  everything else neutral.

### 4. One callout line

- One line inside the frame for the fact that changes the decision: `The newest tag sits 22 commits
  before the deploy, so git misreports what is live.`
- It uses the `edit` family: `--iw-edit` text on `--iw-edit-bg` with a hairline `--iw-edit-line`
  border (in SVG, a `c-amber` rect with one `ts` line).
- One line, about 90 characters at most, truncated with its full text in `title` if the container
  narrows. The second sentence, and every qualification, goes in the chat.

## The words around a widget

The chat side is structured too.

- A line or two before the widget saying what it shows, when that is not obvious from the question.
- After it: short bulleted lists with bold headers, a table for sources, sections a reader can skip.
- Never restate what the widget already shows. Add what it cannot: why, what it means, what to do.
- **Pair the visual with the question.** When a decision is pending, the widget carries the proposal
  and the chat (or a question dialog) asks for the decision, beside it.
- Numbers derived from commands name the command, with raw output on request.

## Anti-patterns, and what to do instead

| Instead of | Do this |
|---|---|
| a diagram when the reader asked what something contains | enumerate the literal contents with a contents-list; offer the diagram as a ↗ follow-up |
| sentences packed into the frame, shrinking the picture | labels inside, sentences in the chat, one callout line at most |
| overlapping labels and messy layouts | fixed label columns, data-placed marks, tooltips, the pre-flight check |
| a confident wrong fact | values traced to a command or file read this turn; unknown shown as `unknown` |
| a live view the reader cannot keep in the chat | an inline widget, re-rendered on request |
| low contrast, such as light text on a colored fill | role text on its own tint; host ink on neutral surfaces |
| one composition reused across a set | follow the module's structure and vary the composition every time |
| a view that loses the reader's place on refresh | re-render the same subject in the same shape, with the same filters offered |
| chrome that pushes content around | local controls in the header row, fixed positions |
| bland type or a mere color swap when a new direction was asked for | a different composition within the module |
| visuals only at the end of long work | a widget at each milestone |
| repeated titles and settled items taking the picture's space | settled items in the legend, the summary or the chat |

## Pre-flight

Read the markup, not the render. Every question is answerable from the code.

1. Is any text placed at a data-derived coordinate?
2. Is there a sentence inside the frame other than the one callout line?
3. Is the top-right corner clear by about 44px?
4. Is this one subject, in three modules or fewer?
5. Does every truncation carry a tooltip?
6. Is every color a `--iw-*` token, a host variable or a ramp class?
7. Is anything below 11px, or any SVG `viewBox` other than 680 wide?
8. Is there at least one ↗ button, and does every sending control carry ↗ and every local one not?
9. Is the screen-reader summary present: `h2.sr-only` for HTML, `role="img"` with `<title>` and
   `<desc>` for SVG?
10. Is every displayed number rounded, and does each one trace to something read this turn?
11. Is anything hidden in markup during streaming?
