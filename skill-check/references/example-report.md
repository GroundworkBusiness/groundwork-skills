# About the example report

`example-report.html` is an **illustrative specimen** of the report format Step 6 asks for.
It is not a report about anyone's real software.

It was built from a real check and then generalized: the target, the vendor, the plugin,
the file names, the package names, the environment variable and the endpoints are all
invented. What was kept is the shape. The patterns it describes (a hook with no matcher, a
run-time fetch of an unpinned package, a session identifier in telemetry) are real and
common, which is why they make a useful example. But no finding in that file is a claim
about any real product, and it should not be cited as one.

Its verdict is **load it**, which is deliberate. A format example where the answer was
mostly yes is more instructive than a manufactured disaster, because the interesting
question is whether a report stays honest about what it could not see when the news is
basically good.

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
  unread file, the scanned-not-read remainder, and the package the whole review cannot
  reach.

## What it is not

It is not a template to fill in, and you do not need to read it to write a report. Step 6
of `SKILL.md` specifies the document; this is one rendering of it. Different targets need
different sections emphasized, and a target with no run-time fetch has a much simpler
diagram.

## Writing about real targets

A real check names a real thing, and the report will say so plainly. That is the point of
the format and it is fair comment when every claim is quoted from files on disk.

Publishing one is a different decision from writing one. A report that names a vendor,
posted publicly under your own or your company's name, is public commentary on that
vendor, whatever its verdict. Keep the private record honest and specific. Decide
separately, and deliberately, whether a given one gets published, and generalize it first
if the format rather than the finding is the thing worth sharing. That is exactly what
happened to this file.
