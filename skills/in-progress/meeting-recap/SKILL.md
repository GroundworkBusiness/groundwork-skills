---
name: meeting-recap
description: Turn meeting notes, a transcript, or a recording into a recap people can act on, with what was decided, who owes what by when, what is already done, and what is still open. Writes a markdown recap and a matching PDF in your own brand, plus internal notes or a longer narrative on request. Use when someone shares meeting notes, a transcript or a recording, or asks for a meeting recap, summary, minutes, follow-up, action items, or "what did we decide".
---

# Meeting Recap

A recap the people who were there can check and act on.

## What you get

- **Always:** the recap as markdown, and the same recap as a PDF in the user's brand.
- **On request:** Internal Working Notes (terse, for the user's own team: what changed, risks, next steps) and an In-Depth Summary (the full narrative, with context and reasoning). Both are markdown only.

## Steps

1. If the source is a `.vtt` caption file, convert it with `scripts/vtt_to_text.py` and check the copy as [references/transcripts.md](references/transcripts.md) describes. Read the converted copy, and only once the check passes. Never read just the lines that carry a `<v Speaker>` tag: Teams puts the rest of most cues on the lines below.
2. Read the whole source. List attendees, decisions, action items with owner and date, and open questions.
3. Confirm the date and attendee list against the calendar invite if you can read it; otherwise ask. Never infer either from the transcript. If `brand/brand.md` says `configured: no`, ask the brand questions (Your brand) in the same message.
4. Draft the recap in the shape below, ending with the AI note.
5. **Ask before you build.** List the open action items for the user and ask which are already done, and when, and whether anything promised goes out with the recap. Move those into Completed Since the Call.
6. Build the PDF (Rendering).
7. Run the disclosure scan on the PDF text. Fix every real hit in the markdown and rebuild.
8. Look at every page.
9. Deliver both files: where the user keeps meeting records, or beside the source. In a chat app, offer both as downloads.

## The recap shape

These headings, in this order:

- `# <Meeting title>`, then three facts lines: `**Date:**` and `**Attendees:**` as confirmed, and `**Source:**`, what it was built from ("Transcript of the video call")
- `## Executive Summary`
- `## Discussion Summary`: a paragraph per topic, each opening with a **bold lead-in.**
- `## Decisions`: numbered
- `## Action Items`: a table, `# | Item | Owner | Target | Notes`
- `## Completed Since the Call`: only when something already moved, `# | Item | Owner | Completed | Notes`
- `## Open Questions`: bullets
- `## A Note On This Summary`: always last

The PDF script reads exactly this: one `#` title, `**Key:** value` facts, `##` sections, paragraphs, `- ` bullets, `1. ` items and pipe tables. Name the files `<date>_<Organization>_<Slug>_Recap.md` and the same name `.pdf`.

## Completed Since the Call

Action Items holds only open work. Anything already done moves here, with the actual date in Completed and, in Notes, what shows it happened, in the reader's terms ("Sent to the board chair"). Never delete a done item: a shorter list reads as dropped work. Leave its Decision as it is; the two together trace an agreement to its outcome.

- **Something moved between the call and the recap.** Confirm it with the user (step 5) or the file itself; never take it on trust.
- **The recap's own email fulfils an item** ("I'll send you the price sheet"). Completed reads `This email`; Notes names the attachment.

## Keep your working out of it

The recap and PDF record what is true, never how you checked it or what state your own work is in: no verification steps, file sizes or hashes, test results, or the tools and file paths behind your work, and no delivery status told to the reader. State the fact; drop the method. Internal Working Notes are exempt.

Read [references/lint.md](references/lint.md) before the disclosure scan, because the grep's word boundaries were tuned and loosening them makes it useless.

## Say it was AI-produced

End every recap with this section, word for word, except "transcript": say "recording" or "notes" when that was the source.

```markdown
## A Note On This Summary

This recap was produced from the meeting transcript using AI, then reviewed. It should be
accurate, but it is a machine reading of a conversation. If anything here looks wrong or does
not match what you remember, tell me and I will correct it.
```

The PDF sets it apart as a shaded block at the bottom. Hedge nowhere else: the recap asserts what happened.

## Your brand

`brand/brand.md` holds the name, tagline, contact line, fonts, colors, logo, page size, footer and style notes; [brand/README.md](brand/README.md) explains each. It ships with a pale memo blue and `configured: no`.

While it says `no`, ask five questions before building: the organization name; a tagline, if any; the contact line for the footer; keep the default fonts and colors, or name theirs; and whether there is a logo (PNG or JPG) to copy into `brand/`. Write the answers into `brand.md`, copy the logo, and set `configured: yes`. If they skip, keep the defaults and still set `yes`. Ask again only when they say the brand changed.

If the skill folder is read-only, write the card and logo to a `brand/` folder beside the recap, pass `--brand <that folder>` to the script, and give the user the filled `brand.md` for their copy of the skill.

## Rendering

```sh
uv run <skill>/scripts/build_recap.py <recap.md>
```

It needs Python 3.11+ and LibreOffice (`python3` works once python-docx is installed), writes `<name>.pdf` beside the recap, and stops with a one-line reason if something is missing. Without code execution or LibreOffice, follow [references/layout.md](references/layout.md) with your own document tools.

Then turn every page into an image in a scratch folder (`pdftoppm -png -r 80 <name>.pdf <scratch>/page`) and look at each one. Never assume the PDF opened. Rebuild after every content change, so the PDF is never the render of an older draft. A `.docx` is only an intermediate; never send one.

## Voice

- Plain words.
- Short sentences.
- Name people, dates and amounts precisely.
- No buzzwords or filler.
- Assert what happened; hedge only in the AI note.

Apply any style notes in `brand/brand.md`.
