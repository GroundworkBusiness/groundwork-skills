# Your brand

`brand.md` in this folder sets how the recap PDF looks. Open it in any text editor and change the
text after each colon. A blank value is left off the page.

| Field | What it does |
| --- | --- |
| `configured` | `no` until the brand is set up. While it says `no`, the skill asks you five quick questions before your first recap, then sets it to `yes`. |
| `organization` | Your organization's name, at the top of the first page and in the footer. |
| `tagline` | A short line under the name. Optional. |
| `contact_line` | Contact details for the footer, such as a website or an email address. |
| `document_label` | The label at the top right of the first page. |
| `display_font` | The font for the title and headings. |
| `body_font` | The font for everything else. |
| `accent_color` | A hex color for table headers, headings and rules. The default, `#DBE5F1`, is a pale memo blue. |
| `text_color` | A hex color for the body text. |
| `logo` | The file name of your logo inside this folder, such as `logo.png`. Blank means no logo. |
| `page_size` | `Letter` or `A4`. |
| `footer` | The footer line. `{organization}`, `{tagline}` and `{contact_line}` are filled in from the fields above. |
| `style_notes` | House style for the writing, such as "no em dashes" or "dates as 12 March 2026". |

Fonts must be installed on the computer that makes the PDF. If one is missing, a similar font is
used instead, so check the pages after changing fonts.

A pale accent works: text drawn in it is darkened in the same hue until it is easy to read, and
the pale color itself fills the table headers.

## Adding a logo

1. Save the logo as a PNG or JPG. A wide logo on a transparent background prints best.
2. Put the file in this folder, beside `brand.md`.
3. Set `logo:` to its file name, for example `logo: logo.png`.

It prints 0.6 inches tall, and never wider than 2.5 inches.
