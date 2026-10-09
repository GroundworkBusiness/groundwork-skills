# contents-list

**The question:** "What's in it?" Also: what does this contain, what are the columns, which files
are in there, what fields does it have, list everything in X.

**Reach for it when** the reader wants the literal contents of one thing: every table and its
columns, every file in a folder, every field in a form, every step decision in a stage, every
setting in a config.

**Contents versus shape.** "What's in X" gets this module. "Where does X live" gets a
placement-tree, and "how does X fit" or "how does X work" gets an explainer. When a request could be
either, enumerate first, and offer the shape as a ↗ follow-up (`Draw how the tables relate ↗`).

## Rules

- **Enumerate, do not summarise.** The value is the literal list. Every item the reader asked about
  is present, by its real name, in mono.
- **One table for a flat list** (files in a folder): name, then two to four attribute columns.
  **A grid of small tables, one per container,** for a two-level list (tables and their columns,
  sections and their fields): two columns of cards at 680px, each card holding its own table.
- **Header and controls.** The header chip carries the count or the one finding that matters
  (`4 tables · 20 columns`, `1 table without a key`). Local controls: a filter box and a toggle
  such as `keys only` or `changed only`.
- **Attributes, not prose.** Type, size, key, owner, modified: short values in their own columns.
  A note on an item goes in `title`.
- **Keys and flags as chips**: `PK`, `FK`, `unique`, `nullable`, `new`, in the status or neutral
  family, never color-only.
- **Counts in the header, not a paragraph**: `20 columns`, `1,284 rows`, rounded and tabular.
- **Offer the next step** in the action row: sample the data, draw the shape, export the list.

## Vary the composition

- One table with a group row per container, when there are many small containers.
- A file list with a size bar (a thin data-placed mark in its own column) when volume matters.
- A form or config as label and value pairs in two columns, with changed values in the `edit`
  family.
- Before and after columns when the contents changed, with `new` and `edit` chips.
