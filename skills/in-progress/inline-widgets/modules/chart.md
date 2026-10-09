# chart

**The question:** "How much, how fast?" Also: what's the trend, when will it cross the line, how
big is each part, what are the high and low estimates.

**Reach for it when** the answer is numbers the reader has to judge: a trend, a projection with a
range, a comparison of magnitudes, a part of a whole, a value against a budget. A single number is
a stat tile, a handful are a row of tiles, and more than about seven classes that all matter are a
table.

## Follow the reader's mental model

The encoding is the reader's, not the chart library's. Readers carry a picture of the answer: a fan
or cone for high and low estimates, line width for volume, no assumed linear fit.

1. **Mock it fast.** Draw the first version from the most likely picture, with a small, honest
   dataset, rather than asking questions first.
2. **Offer the correction.** Every chart carries `Draw it differently ↗`, which asks the reader how
   they picture it and redraws.
3. **Keep what they chose.** Once the reader names an encoding, reuse it for that subject for the
   rest of the session.

## Rules

- **Header and legend.** The header carries the name, the subject in mono, and the state chip for
  the number that matters (`crosses budget in week 9`, `12% over plan`). The legend sits in a fixed
  row above the plot: a swatch or line sample per series, with its name.
- **Plot.** Recessive gridlines, axis ticks at fixed positions in muted ink, marks in the series
  color. An optional callout names the one number that changes the decision. The action row
  carries `Draw it differently ↗`, `Show the numbers ↗` and a drill-down.
- **Pick the form before the color**: bars for magnitude, a line for a trend, a fan (a band between
  low and high around a central line) for an estimate with a range, a stacked bar for part to
  whole, a dumbbell for before and after, one highlighted series over gray ones when one series is
  the point.
- **One y-axis.** Two scales are two charts.
- **Series color follows the entity, never its rank**, and filtering never repaints. A single
  series takes the accent; several take the lane set in order; a budget or threshold line takes the
  `edit` family.
- **Text wears text tokens.** Values, ticks and legend words stay in ink; a swatch beside the word
  carries the color.
- **Marks**: lines 2px with round joins; bars 24px or thinner with a 4px rounded data end; point
  markers 8px or larger; a band at about 14% opacity of its series color.
- **No direct labels at data positions.** Series names live in the legend row and values on hover,
  so nothing collides as the data moves. Mark "now" in the axis row, not on the plot.
- **State units** in the legend or the axis (`$ per week`).
- **Inline SVG inside HTML** is the default: marks take the `--iw-*` tokens directly and both
  themes work. For thousands of points use a chart library on a canvas, which cannot read CSS
  variables: read the tokens once with `getComputedStyle(document.documentElement)` and pass the
  values in.
- **Local controls**: toggle series, the band or the threshold; switch weekly and cumulative; a
  slider for an assumption, recomputed in the script. A click on a point or bar asks for its
  breakdown.

## Vary the composition

- A row of stat tiles over the chart when two or three headline numbers frame it.
- Small multiples, one mini chart per entity on a shared scale, instead of many lines on one plot.
- A meter against a limit for a single ratio.
- Line width as a second encoding (volume along a trend) when the reader thinks in both at once.
