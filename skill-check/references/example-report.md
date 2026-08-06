# About the example report

`example-report.html` is a real skill-check report, kept unedited as a worked example of
the format Step 6 asks for.

It reviews `azure:microsoft-foundry`, a skill inside Microsoft's `azure` plugin
(v1.1.75, `claude-plugins-official`), checked on 2026-08-06. Nothing in it is invented or
tidied up for presentation: the findings, the quoted lines, and the coverage counts are
what the check actually produced. Its verdict is **load it**, which is worth noting,
because a useful example of this format is one where the answer was mostly yes and the
report still has to be honest about what it could not see.

## What to look at

- **The masthead.** The verdict sits beside the coverage counts. This is the rule the
  format exists to enforce: a verdict never travels without what it is worth. Here that
  matters, because one of the counts is "1 package unknowable."
- **The diagram.** It shows what fires when, with a boundary line across it separating
  what was auditable on disk from what gets fetched at run time. That line is the report's
  main finding, drawn instead of argued.
- **The accent color.** It appears on exactly two things: the concern numbers and that
  boundary. Disclosures stay neutral, because disclosures are not accusations.
- **The last section.** "What could not be checked" is not a disclaimer. It names an
  unread file, the scanned-not-read remainder, and the npm package the whole review
  cannot reach.

## What it is not

It is not a template to fill in, and you do not need to read it to write a report. Step 6
of `SKILL.md` specifies the document; this is one instance of it. Different targets will
need different sections emphasized, and a target with no run-time fetch has a much simpler
diagram.

It is also not a security advisory about the Azure plugin. It is a snapshot of one
version on one day, and it says so in its own footer.

## Note on paths

The report quotes three `~`-relative paths from the machine it was run on, including an
npx cache directory name. They are local artifact paths, not credentials or identifiers,
and they are left in because the format calls for quoting evidence rather than describing
it.
