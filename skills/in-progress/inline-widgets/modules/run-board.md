# run-board

**The question:** "What's happening now?" Also: what are my agents doing, what's the status, which
finished, what's waiting on me, where is the build.

**Reach for it when** several things are in motion and the reader needs to know which one needs
them: agents in a run, steps of a pipeline, open items on a checklist, jobs on a queue.

## Rules

- **Header and tallies.** The header carries the name, the run label in mono, and the state chip
  (`1 needs you`, `all finished`, `3 running`), with filter chips after the label inside the 44px
  reserve. One row of mono counts per status follows.
- **The parked question comes first**, when there is one: a card with a 2px `--iw-live-line` frame.
  It carries who is asking, the question, what it blocks, where the asker already looked, the
  default, and when it is needed; then one button per option, the default marked, and a
  `Neither ↗` that opens the discussion.
- **Label sequential versus parallel.** Rows sit in groups whose kicker says which
  (`STAGE 1 · PARALLEL`, `STAGE 2 · SEQUENTIAL`), and a row that waits on another names it
  (`after engine`). Inside a group, anything waiting on the reader sorts first.
- **Each row** shows the name (mono, weight 600) with its scope under it, a status with
  its mark, elapsed time, the last milestone, and what it owns. Anything assumed without
  confirmation hangs under the milestone.
- **Statuses are words with marks.** `running` with a filled red dot, `needs you` as a red chip,
  `done` in green, `partial` in amber (stopped short, look at it), `queued` neutral.
- **The milestone is a label, not a report**: `rebase clean, 41 of 41 tests green`. The account of
  what an agent produced belongs in a summary, after the run.
- **Rows on a fixed grid** (`minmax(0,1fr)` for the milestone column) so nothing reflows as values
  change; paths wrap at any character rather than widening a column.
- **The board is a snapshot.** It shows what was true when it was rendered; `Refresh ↗` renders a
  new one. The action row carries the refresh and the run's next decision.

## Vary the composition

- A pipeline board: one row per step in sequence, a single group, the current step's dot filled.
- A checklist board: rows as items with owners and due dates, the overdue ones first.
- Two parked questions: two ask cards stacked above the rows, oldest first.
- A board with no question: the state chip says `nothing needs you` and the rows come first.
