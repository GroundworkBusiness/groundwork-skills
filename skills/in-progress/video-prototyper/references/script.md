# Series, outline and script

How to go from the owner's goal to a canonical caption script and a cued script that every voice reads from. Example data: [scenes.example.json](../assets/scenes.example.json).

## Contents

- [Series list](#series-list)
- [Outline](#outline)
- [Narration drafts](#narration-drafts)
- [Writing for speech](#writing-for-speech)
- [The canonical script](#the-canonical-script)
- [scenes.json](#scenesjson)
- [The cue check](#the-cue-check)
- [Saying only what is true](#saying-only-what-is-true)
- [Disclosure card](#disclosure-card)

## Series list

For a series, list every video before outlining any of them. Scenes can then move to the video they fit best, and no video absorbs another's content.

```markdown
| # | Video | Covers | Does not cover |
|---|---|---|---|
| 1 | Three bins | What goes in each bin | Collection days (video 2) |
| 2 | Collection day | When and where to put bins out | Bulky items (video 3) |
```

Record each decision in the decision log at the end of `PLAN.md` as it happens: time, subject, decision, because.

## Outline

Ask before drafting. Check what material already exists, then list what is still missing before a script can be written:

- the goal; any length limit (or "no limit"); the points that must be said; the narrative arc and any comparison it leans on; the examples to show; where each fact comes from; anything on safety or trust; the words and characters banned on screen and in narration (the Banned line of `PLAN.md`); the audience's own terms; what the next video picks up; the disclosure line; names to keep out of the narration.

Then offer an outline table for the owner to react to, with every example marked illustrative:

```markdown
| # | Scene | What the viewer learns | What the screen shows |
|---|---|---|---|
| 1 | First week | The counter fills up; where does it all go? | Four everyday items arrive on a counter |
| 2 | The three bins | Each bin and what it takes | Three bins appear and are named one by one |
```

Talk the scenes through with the owner in this conversation; the owner's corrections at this stage are the cheapest ones.

## Narration drafts

Write per scene, for the ear, with a planned time range, an "On screen" line and a sources line. Number the drafts; fold the owner's points into the next one.

```markdown
### Draft 2, <date>: roughly 60 words, roughly 30 s read calmly
1. **First week, 0:00 to 0:15.** It's your first week in Alder Creek, and the kitchen counter is filling up. ...
   *On screen: four items arrive on a counter, one at a time as named.*
   Sources: the town's sorting guide (illustrative, invented for this example).
```

Time ranges and word counts are planning guesses; real takes vary widely. Trim for time only to meet a limit the owner set.

## Writing for speech

1. A full stop gives the cleanest pause and a comma a brief one. Break up run-on sentences.
2. An ellipsis gives a longer, gentler pause. Keep them few; they also start a new caption unless a lowercase word follows.
3. Long dashes are read inconsistently (a pause, or nothing). Write a comma or a full stop in the script instead. A provider may document `--` as a hesitation cue; that belongs in `scenes.json` only.
4. A question mark raises the pitch at the end. Ask only genuine questions.
5. Get emphasis from word order: the word to stress goes last in a short sentence. CAPS behave differently per provider (a stress cue on one, spelled out on another).
6. Write numbers, money and dates as spoken: "three hundred and forty dollars", "the second of March".
7. Acronyms: spell them out in the text ("U S B") or keep them and add a pronunciation line to the style; the second keeps captions clean. Try both.
8. Point to a web address or file name by where it is ("the address under the video") rather than reading it aloud.
9. Lists: give the order in words ("To start... After that... Last..."); numbered digits are not read reliably.
10. Give a bracketed aside a sentence of its own; brackets make no sound.
11. Close each scene on a whole sentence, and check by ear that every take keeps its final sentence.
12. Request pace in words in the style line, because not every model follows a numeric speed setting.

Write for the real viewer. When viewers do not share one situation, write for the one most of them are in and cover the rest with an "or" clause (illustrative: for a how-to watched mostly on laptops and sometimes on phones, "click, or tap, the green button"). Use plain, unbranded example names.

## The canonical script

`script/script.txt` is the caption text and the alignment target:

- Plain text, one paragraph per scene, one blank line between scenes. The aligner maps paragraph N to scene N.
- No headings, markup, tags or stage directions.
- Sentences end with `.`, `!`, `?` or `...`, optionally followed by a closing quote. Avoid abbreviations with full stops and decimals; write them as spoken.
- No `--` (a hesitation cue belongs in `scenes.json` only).

## scenes.json

The same words plus delivery cues, one entry per scene. The block is [scenes.example.json](../assets/scenes.example.json) shortened to its second scene; a real file lists every scene, numbered from 1:

```json
{
  "schema": 1,
  "title": "Three bins: how curbside sorting works",
  "cue_convention": {"provider": "example-tts", "tags": ["breath", "short pause", "long pause"], "stress": "CAPS", "hesitation": "--"},
  "scenes": [
    {"n": 2, "title": "The three bins", "label": "Three bins",
     "on_screen": "Three empty bins appear, then each one is named with what it takes.",
     "style": "clear and steady",
     "text_cued": "Alder Creek uses THREE bins. <short pause> The blue bin takes clean paper, cans and bottles. ...",
     "variants": {"command": "Alder Creek uses three bins. The blue bin takes clean paper, cans and bottles. ..."}}
  ]
}
```

- `n` is the scene's position: 1 for the first paragraph of `script.txt`, then 2, 3 and so on. Scene files (`s<N>.wav`), plain takes and alignment rely on it, and `cue_check.py` fails on any other numbering.
- `text_cued` is what API voices read. `variants` holds a per-adapter version when a provider needs different delivery cues; every variant keeps the same words.
- `style` is a few words; long direction makes voices drift.
- With no voice, set `text_cued` to the paragraph's words with no delivery cues and `style` to an empty string; `cue_check.py` still compares `text_cued` with the script.
- `label` and `on_screen` feed `cues.json` and the build brief.
- `text_plain_check` (optional) holds the normalised words, written by `cue_check.py --fill` for readers.

[make_voice_pack.py](../scripts/make_voice_pack.py) renders `voice-pack.md` from this file and `script.txt` for hand auditions, so the human and the scripts read the same words.

## The cue check

[cue_check.py](../scripts/cue_check.py) compares every scene's `text_cued` and variants with its paragraph after one normalisation, stated exactly so counts are reproducible:

1. lowercase;
2. remove `<...>` tags;
3. fold curly apostrophes to straight;
4. replace every character outside `a-z`, `0-9` and the apostrophe with a space (this removes `--`);
5. split on whitespace;
6. trim apostrophes at the ends of each word.

It prints `N of N words match`, a word diff on any mismatch, and paragraph against scene counts. It flags in `script.txt` each string the owner bans with `--ban` (from `PLAN.md`); nothing is banned by default, so a long dash is flagged only when the owner bans it. Bans match any capitalisation, and a ban that starts or ends with a letter or digit matches whole words only at that end (a ban of "ai" does not match "said"); required terms match exactly. Separately, the two-hyphen hesitation cue `--` in `script.txt` always fails, because delivery cues belong in `scenes.json`. It exits 1 on any problem.

## Saying only what is true

- State a count or fact only when it is true of the real thing. Check definitions against the source's own wording and quote it on the sources line.
- Keep numbers that will change (versions, counts of parts) out of the narration entirely; a wrong spoken number needs a full re-voice. Put perishable names on title cards and the page.
- Show every part a stated total includes; when the listed parts do not add up, find the missing one in the sources or ask.
- Use only verified names for real people, products, places and organisations. An example name is plain, unbranded and labelled illustrative. When a real name cannot be verified, number or generalise it, and ask.
- Label illustrative examples as illustrative in the brief, the notes and any sources line, and on screen too when a viewer could take one for a real record or when the owner asks.

## Disclosure card

When any voice, music, images or footage is generated, the closing card carries one plain line, also on the hosting page. For a loop or a piece without a closing card, show the line small for the whole loop: directly in `#stage`, outside every `[data-scene]` and outside `[data-bg]`, with no `data-cue` (see [the stage contract](stage-contract.md#hooks-the-timing-audit-reads)), or on the hosting page and beside the screen, as the owner decides. The owner decides the wording, for example:

```text
Made with AI: the narrator's voice, the music and the pictures.
```

In a video that does not loop, the closing card is the last scene. Put the line in its own element in that scene (for example `id="disclosure"`), tag it with the scene's last cue id (`data-cue`), and give it a beat on that cue in the scene's BEATS entry, for example `['disclosure', <index of the last cue in the scene, from 0>, 0]`. It then appears with the last sentence and holds through the tail. Untagged text inside a scene fails R5 (`untagged text in scene N`), and on a video that does not loop, the last scene's R4 clear deadline falls after the video ends, so the audit does not flag the disclosure element for staying up through the tail ([timing-audit.js](../assets/timing-audit.js), R4).
