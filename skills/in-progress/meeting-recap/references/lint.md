# Disclosure scan

A recap records what is true. It never records how that was checked, what it was checked against,
or what state your own work is in. The reader was in the room: your verification tells them
nothing they need, and it shows them how your work is run.

## What stays out

| Keep out | Invented example |
| --- | --- |
| Verification workings | "Checked the Sent folder: the price sheet has not gone out yet." |
| Hashes, byte counts, integrity claims | "The workbook is 48,210 bytes and matches its SHA-256 hash." |
| Build state and test vocabulary | "The scheduling template passes its acceptance check on four fixtures." |
| Delivery state narrated at the reader | "Nothing has been sent to Anika yet", in a recap going to Anika |
| Notes about keeping the record | "The transcript does not say who raised this, so it is listed as agreed rather than decided." |
| Internal work timings | "Drafting this recap ran from 4:10 to 4:45 PM." |
| Tools, paths, repositories, commands, release names | "The fix is on a branch in the repo and will deploy Friday." |

State the fact and drop the method. An item that a check showed is still undone simply stays in
Action Items. An integrity check becomes nothing at all, because the reader never doubted it.

The evidence still matters. Keep it in your own notes or in the Internal Working Notes, which are
exempt from this scan: the recap carries the finding, your notes carry the proof.

Two things look similar and stay: the **Source:** line naming what the recap was built from, and a
plain statement that someone's own data was deliberately left out. Both tell the reader about
their own material, not about your process.

## The scan

Run it on the text of the finished PDF, because that is what the reader gets:

```sh
pdftotext -layout recap.pdf - | grep -niE 'gmail|sent folder|\binbox\b|[0-9],[0-9]{3} bytes|\bsha-?256\b|\bhash(es)?\b|verified by|byte-identical|read ?back|\bfixtures?\b|acceptance check|test suite|regression|\bcommits?\b|\brepo(sitory)?\b|\bbranch(es)?\b|\bdeploy(ed|ment)?\b|on disk|local file|\bgit\b'
```

Without `pdftotext`, run the same `grep -niE '...'` on the markdown recap.

Read every hit, then cut it or keep it for a reason. Ordinary business uses are fine: a bank
branch, a regression analysis, "send it to my inbox". The test is whether the sentence describes
the subject of the meeting or describes your method.

The scan cannot see every class above. Read the recap once more for delivery status, notes about
keeping the record, and work timings, which have no fixed words to match.

## Word boundaries are deliberate

Do not loosen them. An unanchored `CLI` matches inside "client", an unanchored `release` matches
"release money", and `commit(ted)` matches "committed to testing". Terms like those made an
earlier version of this scan fire on ordinary sentences, and a scan that fires on everything gets
ignored.

If you change the pattern, run it on both samples below first. Every line of the first should hit;
no line of the second should.

Should hit, all seven lines:

```text
Gmail shows the price sheet has not gone out.
Checked the Sent folder this morning.
The workbook is 48,210 bytes.
Its SHA-256 hash matches the copy on disk.
The template passes its acceptance check on four fixtures.
The fix is on a branch in the repo and will deploy Friday.
Read back from the local file after the last commit.
```

Should not hit:

```text
The client asked the board to release money for the pilot.
Anika committed to testing the new booking flow in May.
Client feedback goes to the June meeting.
```
