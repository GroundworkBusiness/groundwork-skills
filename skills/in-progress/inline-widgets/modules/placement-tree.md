# placement-tree

**The question:** "Where does it live?" Also: where does this go, how is it organised, what moves
where, what does the proposed structure look like.

**Reach for it when** the answer is a hierarchy or a placement: folders and files, a proposed
filing, a taxonomy, an org or ownership tree, which project holds which piece, what changes when
something is reorganised. It is the right shape before a reorganisation is approved, because every
node carries its status and the reader can approve the whole tree in one look.

When the reader asks what one of the boxes *contains*, answer with a contents-list for that box.

## Rules

- **Header and legend.** The header carries the name, the root or scope in mono, and a state chip
  for the one fact that needs the reader (`3 calls for you`, `nothing moves yet`). A legend row
  follows, one chip per status the tree uses, in the order the reader will meet them.
- **One root line** in mono at weight 500, then indented rows. Children indent 10px and hang off a
  hairline rule (`--iw-line-2`) on their left.
- **Mono for names, sans for descriptors.** Descriptors are two or three words (`client-facing`,
  `send copy, 9 pp`); the detail goes in the row's `title`.
- **One chip per row**, from the status set: `exists`, `new`, `moves in` (moved), `edit`, and
  `your call` (live) for anything waiting on the reader. A decision reads as a chip (`promote?`,
  `trash?`) in the live family, so the reader sees where they are needed without reading.
- **Going away** (optional): what disappears goes in a muted line or short group after the tree.
- **Long names truncate from the front** when the tail is what identifies them
  (`…Launch-Plan.md`), with the full name in `title`.
- **Depth four at most** inside one widget. A deeper tree splits at a branch: the overview, then a
  second widget for the branch that matters, with text between.
- **About 25 rows** is the practical ceiling. Collapse a folder of unchanged files into one row
  (`12 files, unchanged`).
- **Several roots are fine** when they are one subject (a project folder and the agents it uses);
  a separate subject is a separate widget.
- **Decisions are buttons**, never clickable chips: `Approve as shown ↗`, `Change a placement ↗`,
  and the tree's own decisions (promote, trash). A `changes only` toggle hides unchanged rows.

## Vary the composition

- Folders first or status first: group changed rows at the top when the reader is approving a
  change, keep natural order when they are learning the layout.
- A two-column tree (current and proposed side by side, rows aligned) when the question is what
  moves where.
- Counts on folders (`research/ · 4 files`) when the reader cares about volume.
- Owner or host chips instead of status chips for an ownership map, with a legend.
