# lanes

**The question:** "How did it change?" Also: what's live versus local, how far behind is
production, which branches are in flight, what happened over this run, how did the versions move.

**Reach for it when** the answer is state over time for a few parallel things: pointers on one
history (live, remote, local), branches and their integration, environments, versions, agents over
a run, stages of a release. The shape is horizontal lanes with big dots, sparse labels, time
running left to right, and every gap drawn and counted.

## Rules

- **Three fixed, ruled columns.** A label column on the left (lane names as kickers or mono names,
  with an optional second line), the plot in the middle, and an optional right column for per-lane
  values (drift counts, the agent at work).
- **One lane per pointer, branch or environment, at a fixed y.** A solid spine for history that
  exists, a dashed spine for the gap to where it should be, and big dots (radius 8 to 9 for
  pointers, 4 to 5 for commits) where the data puts them.
- **Header and legend.** The header chip names the drift that matters (`live is 38 behind`,
  `2 agents at work`). A fixed legend row says what each dot color and each dash means.
- **Time runs left to right. Lane position is an index, never a timestamp.**
- **Counts in a column, detail in the tooltip.** Hashes, subjects and exact times go in each mark's
  tooltip; counts go in the right column or the legend row.
- **A gap is drawn and counted**: a dashed segment from where a pointer is to where it should be,
  and the number of commits (or days, or versions) in the right column.
- **Dot color is status, lane identity is the label.** Green at the tip or merged, amber behind,
  red for live attention. When lanes themselves need color (versions, vendors), use the lane set
  and a legend.
- **Integration is typed**: merged, squashed and rebased each get their own glyph and color, and
  each carries the evidence the reader can ask for.
- **Uncommitted or pending work is dotted**: a branch with a dirty tree ends in a dotted tail
  running to now.
- **Agents in their own column**: a filled red dot for an agent at work, a red ring for one waiting
  on the reader, a muted ring for one that finished. One row per agent on the lane, never over the
  plot.
- **Relative age on the axis, exact time on hover.** Axis ticks read `3h ago`, `now`.
- **One repository per widget.** Others that are simply in sync go in the chat line under it.

### The skeleton

Only the marks' x comes from data. Adapt the values, keep the structure.

```js
const W = 680, LABEL_R = 150, PLOT_L = 160, PLOT_R = 500, COL_X = 516;
const LANE_H = 46, TOP = 48;
const y = i => TOP + i * LANE_H;
const x = t => PLOT_L + (1 - t / SPAN) * (PLOT_R - PLOT_L);
```

The label column ends at `LABEL_R`, the plot at `PLOT_R`, and the right column stops about 44px
short of `W` near the top. Rules at `LABEL_R + 4` and `PLOT_R + 8` make any crossing visible.

## Vary the composition

- Pointers only (three lanes on one history) when the question is drift; branches with fork curves
  when the question is work in flight.
- A version lane per release with the lane set, when the question is what shipped when.
- Environments as lanes (dev, staging, production) with promotion arrows between them.
- A right column of agents, of drift counts, or of owners: one per widget.
