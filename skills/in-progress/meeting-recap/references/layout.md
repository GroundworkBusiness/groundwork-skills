# Recap page layout

This is the page `scripts/build_recap.py` builds from the markdown recap. If you cannot run the
script, build the same page with your own document tools from this description, export it to
PDF, and look at every page before sending it.

Values in `{braces}` come from `brand/brand.md`. A blank value is left out, along with any label,
line or separator that only existed to hold it. Where this page says **accent text**, **accent
mark** or **pale fill**, see Color below: they are derived from `{accent_color}`.

## Page

- Paper: `{page_size}`, portrait. Letter is 8.5 x 11 in; A4 is 210 x 297 mm.
- Margins: 0.75 in top, 1 in left and right, 0.8 in bottom.
- Body text: `{body_font}` 10.5 pt in `{text_color}`, line spacing 1.15, 6 pt after each paragraph.

## Letterhead, top of page one only

A borderless band across the full text width, split 60 / 40.

- Left, stacked: the logo when `{logo}` is set, 0.6 in tall and never wider than 2.5 in; then
  `{organization}` in `{display_font}` 13 pt bold; then `{tagline}` in 9.5 pt italic, accent text.
- Right, aligned right and to the bottom of the band: `{document_label}` in `{display_font}` 15 pt
  bold, accent text, letter-spaced.
- Under the band: a 1.5 pt rule in the accent mark across the text width, then 12 pt of space.

## Title and facts

- Title, the `#` line: `{display_font}` 18 pt bold, accent text, 10 pt after.
- Facts, the `**Key:** value` lines: a two-column table split 22 / 78. Labels in 8.5 pt bold
  capitals, gray #666666, on the pale fill. Values in 10 pt. Hairline borders in #C8C8C8. 14 pt of
  space after the table.

## Sections

- Each `##` heading: `{display_font}` 12.5 pt bold, accent text, 14 pt before and 5 pt after,
  kept on the same page as what follows it.
- Paragraphs are body text. A bold lead-in such as `**Budget.**` stays bold.
- Bullets: a `•` in the accent mark, hanging indent 0.25 in, 3 pt after.
- Numbered items: the number in bold accent text, hanging indent 0.3 in, 3 pt after.
- Web links show their text, underlined, in accent text. A link to a local file shows its text
  only, because a file path means nothing on paper.
- The last section, `A Note On This Summary`, is the AI statement. Its heading is like any other;
  its text is 9.5 pt in a block on the pale fill, with a 3 pt bar in the accent mark at the left.

## Tables

- Full text width. Header row filled with `{accent_color}`, its labels in 8.5 pt bold capitals:
  white on a dark accent, or the accent darkened until it reads on a light one. Body cells in
  9.5 pt, hairline borders in #C8C8C8, about 0.08 in of padding at each side.
- Action Items and Completed Since the Call start from fixed columns: # 6%, Item 35%, Owner 12%,
  Target or Completed 19%, Notes 28%. The Owner column is bold.
- Any other table sizes its columns to their content, none narrower than 10% or wider than 50%.
- No column is narrower than its longest word, so a name never breaks in the middle. A column that
  needs more room takes it from the column with the most to spare.
- A row never splits across a page break. The header row repeats at the top of every page the
  table reaches.
- 6 pt of space after each table.

## Footer, every page

A hairline rule in the accent mark, then one line in 8 pt gray: `{footer}` at the left and
`Page N of M` at the right. Empty fields in `{footer}`, and the separators beside them, are dropped.

## Color

`{accent_color}` fills the table header row. Everything else is derived from it, so a pale brand
color still gives a readable page. The default, #DBE5F1, is a pale memo blue.

- **Accent text** (title, document label, headings, links, list numbers, tagline): the accent,
  darkened in its own hue until it has 4.5:1 contrast on white. A dark accent is used as it is.
- **Accent mark** (rules, bullets, the AI statement's bar): the same, at 3:1.
- **Pale fill** (fact labels, the AI statement block): the accent mixed toward white until it is
  pale.
- Body text is `{text_color}`, darkened the same way if it would not reach 4.5:1.

For the default blue this gives accent text #4576B1, accent mark #6D95C6 and header labels #3C679B.

## Before sending

- The last section is `A Note On This Summary`.
- Nothing is cut off, clipped or overlapping, and no heading sits alone at the bottom of a page.
- The fonts are the ones named in the brand card. A font missing where the PDF was made is
  replaced by a similar one; install it, or name another in `brand/brand.md`.
- The file sent is the PDF, rebuilt from the final markdown.
