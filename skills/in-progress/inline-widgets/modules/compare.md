# compare

**The question:** "Which should I pick?" Also: compare these, what are the options, A or B, what
are the trade-offs, which one do you recommend.

**Reach for it when** the reader has a decision between two to four options. Show it before
asking, and ask beside it.

## Rules

- **The decision itself is asked in the chat**, beside the widget, or in a question dialog: the
  widget carries the proposal, the chat carries the question.
- **Option cards side by side**, two to four across (`repeat(n, minmax(0,1fr))`). Each card holds a
  Tabler icon, the option's name, a one-line tag of three to six words, then the same fact rows in
  the same order on every card (cost, effort, risk, what it needs, whether it can be undone), then
  the card's own pick button (`Pick A ↗`).
- **Header and callout.** The header carries the name, the decision in a few words, and the state
  chip (`your call`). An optional callout names the one fact that separates the options
  (`Only B and C keep running while this machine sleeps.`). The action row carries
  `Neither, talk it through ↗` and any local toggle.
- **The recommended card** carries a 2px `--iw-accent-line` border and a small `recommended` badge.
  Every other card keeps the hairline border. One recommendation at most, stated plainly on its
  card and argued in the chat.
- **Same facts, same order, every card**, so the eye can run across a row. Values are short (`about
  $4 a month`, `30 min`), with the basis on hover (`30 runs a month at 2 minutes each`).
- **Differences carry the color**: a value that is worse than the others' takes the `edit` family,
  one that is uniquely good takes `done`; identical values stay neutral.
- **Two to four options.** More than four is a table in the chat, or a shortlist first.
- **A comparison table stays a card grid** here; a long feature matrix goes in the chat as markdown.
- **Local controls.** `differences only` hides the fact rows where every option agrees; a weighting
  toggle (cost first, effort first) reorders the cards.

## Vary the composition

- Now versus proposed: two cards, the proposed one accented, with the changed facts in `edit`.
- A mockup comparison: each card holds a small mockup of the option instead of fact rows.
- A ranked list when one option clearly wins: the winner as a full card, the others as compact rows
  beneath.
- A slider that sets a volume (runs a month, seats) and recomputes each card's cost locally.
