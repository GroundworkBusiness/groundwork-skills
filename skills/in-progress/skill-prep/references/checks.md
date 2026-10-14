# The ten checks

## Contents

- [How every check works](#how-every-check-works)
- [1. Private references](#1-private-references)
- [2. Own workflow](#2-own-workflow)
- [3. History](#3-history)
- [4. Future state](#4-future-state)
- [5. Maintainer-only content](#5-maintainer-only-content)
- [6. House style and brand](#6-house-style-and-brand)
- [7. Examples and fixtures](#7-examples-and-fixtures)
- [8. Dependencies](#8-dependencies)
- [9. Fit with the guidance](#9-fit-with-the-guidance)
- [10. Package hygiene](#10-package-hygiene)
- [With an original](#with-an-original)
- [Light fallback basics](#light-fallback-basics)

## How every check works

Each check looks for a class of content. Learn the instances from the workspace at run time (step 2 of the procedure) and from the terms the user supplied, then find where the folder touches them. Record each match that needs a change as a spec item with the workspace item that raised it. List matches judged to need no change under Run, with the reason.

Read for shape as well as for names. A passage can carry someone's setup with no name in it, for example a folder layout, a routine, or a number taken from real work.

## 1. Private references

Look for names of people, organizations, clients, repositories, accounts, addresses, hostnames and local paths that belong to the user or their workspace. Check examples, comments, links and frontmatter as well as prose.

Also look for the shapes these take: absolute home-directory paths, internal URLs, email addresses, account identifiers.

Change: replace with a neutral placeholder or a generic description.

## 2. Own workflow

Look for steps, tools, commands, file layouts and routines that exist because of how the user works rather than because the skill needs them. Take the user's workflows from the instruction files, the memory files and neighboring skills, then connect each one to the passages that echo it.

Change: state the class instead of the instance ("a notes file"), make the step an input the user supplies, or cut it.

## 3. History

Look for dated notes, changelog fragments, lines that record what was decided or settled, provenance statements, wording about what changed over time, version trivia, links to retired items, and comments about why the skill was built.

Change: cut it, or restate it as a present-tense rule.

## 4. Future state

Look for roadmap language: promises of later additions, unfinished-work markers, and mentions of sibling skills or features that are not in the folder.

Change: describe only what the folder does now.

## 5. Maintainer-only content

Look for notes addressed to the author, test scaffolding, release procedures, internal review checklists, decision logs, and files the skill never reads.

Change: move the content out of the folder, or cut it. Moving it is the user's decision, so present it as a recommendation.

## 6. House style and brand

Look for voice rules, naming schemes, color, font and logo values, signature blocks, boilerplate, and templates that carry the user's identity. Find the user's style and brand sources in the workspace (style guides, brand files, voice rules in the instruction files) and connect each to the folder.

Change: turn the instance into an input ("the user's brand") or a neutral default.

## 7. Examples and fixtures

Read every example, sample output and fixture. Look for real names, real numbers and real structure, including examples that look invented but follow a real project's shape.

Change: replace with invented content that keeps the teaching point.

## 8. Dependencies

List the tools, services, accounts, packages, connectors, models, harness features and environment variables the skill assumes. For each one, record whether the skill states it and what happens when a stranger lacks it.

Change: state the requirement, add a fallback, or remove the dependency.

## 9. Fit with the guidance

Compare the folder with the guidance gathered in step 3: naming, the description (what and when, third person, length), entry-file size, reference depth and linking, contents lists on long files, consistent terms, time-sensitive text, frontmatter validity, path style. Cite the source on every item.

Apply the stance recorded in step 1. A skill meant to stay agnostic should carry no model- or harness-specific assumptions without a fallback. A skill fitted to a model or harness is checked against that target's guidance.

When the guidance asks for work that lives outside the folder, such as evaluations or testing across models, look for evidence in the files around the skill's creation and in paths the user supplied. With none found, or with evidence that covers only part of the ask, record one recommendation under Items that names what is missing. Reserve Could not check for a check you were unable to run.

When no guidance is in hand, apply the [light fallback basics](#light-fallback-basics) and list the remaining guidance under Could not check.

## 10. Package hygiene

Look for:

- stray and junk files: system files, caches, editor files, build output;
- secret-shaped strings and credential files;
- symlinks, large files and binary files;
- absolute local paths;
- links that do not resolve inside the folder;
- executable bits that serve no purpose.

When the folder sits in a git repository with a remote (look for a `.git` folder in it or in a parent folder), note under Run that history does not travel and that the public copy should go in as plain files, because history can carry what the files no longer say. Keep this note out of Items.

When a destination was given, read its README, contributing and release documents, and its existing skills. Record the layout and naming conventions, the shape of a catalog entry, and link style under Run. Record as items only the places where the folder departs from them and any name collision. Leave the writing of any catalog entry to the user.

## With an original

When an original was given, apply each proposed change to the text and compare it with the original. Record as an item any step, input or safeguard that a change would remove and the skill still needs.

## Light fallback basics

Use these when no guidance is in hand:

- The frontmatter parses and carries a name and a description.
- The name uses lowercase letters, numbers and hyphens, runs 64 characters or fewer, carries no XML tags, does not use a platform vendor's name, and matches the folder name.
- The description says what the skill does and when to use it, in the third person, in 1,024 characters or fewer, with no XML tags.
- The entry file stays concise, a few hundred lines at most.
- Other files are linked from the entry file and sit one level below it.
- Long files open with a contents list.
- Paths use forward slashes.
