---
name: knowledge-base-builder
description: Plan, preview, build, or retrofit a right-sized file-based knowledge base from an existing folder or document collection. Use when the user wants an interlinked Markdown wiki, a full YAML operating contract, future-aware taxonomy, preserved source evidence, or portable Ingest, Query, and Lint skills packaged for their selected AI harnesses.
---

# Knowledge Base Builder

Build a right-sized knowledge base for the user's current work and confirmed future plans. Keep the system knowledge-base agnostic, Markdown-first, and governed by a full YAML contract. Preserve valuable narrative context instead of reducing the system to configuration fields.

Read [references/kb-contract.md](references/kb-contract.md) before designing or building.

## 1. Ground the setup

Identify the current harness, provider, model, and effort level when possible. Use model and effort only to guide this setup conversation. Do not persist them. Record only the user-selected harnesses and providers because they affect packaging and adapters.

Ask which harnesses should receive packages. Generate adapters only for those targets. Never assume that Claude Code, Cowork, ChatGPT Work, Codex, Antigravity, or another product shares an installation format with the others.

## 2. Protect the starting point

Ask the user to work from a copy when the folder contains originals or live working files. Inventory protected paths before changing anything.

Classify sources as:

- **immutable:** never edit;
- **externally managed:** read locally, refresh from the owning system;
- **user managed:** edit only with explicit approval.

Scan for likely secrets, credentials, PII, financial information, and confidential material. If found:

1. warn calmly with affected paths and risk categories;
2. never print the sensitive values;
3. exclude affected files from further inspection by default;
4. continue with safe material;
5. offer redaction, sample data, or a narrower scope.

Do not tell the user that sensitive data is safe to use. Do not frame the warning as a reason to abandon the knowledge-base build.

## 3. Inspect deeply before asking

Read existing front doors, instructions, indexes, schemas, and the folder tree. Inventory every file. Deeply read all supported documents when the collection is reasonably sized.

For large or unsupported collections:

- report file counts and formats;
- propose representative batches;
- state exactly what was and was not read;
- never describe a sampled review as comprehensive.

Note authoritative sources, recurring entities and workflows, naming patterns, duplicates, contradictions, stale dates, gaps, and questions the files appear designed to answer. Separate observations from assumptions.

## 4. Interview for the present and future

Ask two or three high-value questions per round. Explain briefly why the round matters. Use an available interview, brainstorming, or planning skill when helpful, without making it a dependency.

Resolve:

- users and recurring questions;
- authoritative, sensitive, volatile, and protected sources;
- human versus agent ownership;
- expected outputs and approval boundaries;
- selected harnesses and providers;
- current and planned integrations;
- expected source growth, future users, projects, reporting needs, and workflows;
- how the user expects the KB to grow over the next six to eighteen months.

Design for that growth without creating empty folders or placeholder pages. Record planned branches, page types, naming rules, and growth triggers in the YAML contract and Markdown schema. Create them only when real content arrives.

## 5. Design the contract and context

Create these universal front doors:

```text
kb.config.yaml   Machine-readable contract
AGENTS.md        Canonical operating instructions and context
INDEX.md         Human and agent navigation
SCHEMA.md        Taxonomy, page types, YAML fields, links, and growth rules
```

Keep harness-specific instruction files as thin pointers to `AGENTS.md`. Do not duplicate operating guidance.

Use standard relative Markdown links, never wikilinks. Give every substantive knowledge page at least one inbound link and a `## Related` section. Add reciprocal links only when they improve navigation, maintenance, or query accuracy.

Require this universal YAML frontmatter core on synthesized pages, then add page-type fields fitted to the domain:

```yaml
id:
type:
scope:
tags: []
source:
updated:
status:
```

Treat YAML as authoritative for paths, permissions, required metadata, and operation settings. Treat Markdown as authoritative for meaning, rationale, examples, and human guidance. If they conflict operationally, stop, show the conflict, and ask which version to keep.

## 6. Preview before building

Present:

- the goal, users, and recurring questions;
- inspection coverage and unresolved gaps;
- the proposed taxonomy and future growth rules;
- a compact folder tree;
- a Mermaid relationship diagram when supported;
- exact files to create or edit;
- proposed moves, renames, merges, reorganizations, and removals;
- protected paths and approval boundaries;
- one representative source for the first test.

Ask whether the architecture makes sense. Do not build before explicit approval.

The user may approve structural changes individually. For proposed removal, default to moving the item into a user-approved holding folder outside the active KB. Show the exact destination before approval and in the completion summary. Permanent deletion requires separate explicit confirmation.

## 7. Build the approved system

Create as much structure as the evidence and confirmed future plans justify. Do not impose page-count or taxonomy limits. Avoid empty scaffolding and duplicated knowledge.

- Write `kb.config.yaml`, `AGENTS.md`, `INDEX.md`, and `SCHEMA.md`.
- Preserve Markdown context and provenance.
- Update existing knowledge before creating a competing page.
- Apply the confirmed YAML frontmatter and page-type extensions.
- Add standard relative Markdown links and `## Related` sections.
- Record unknowns instead of guessing.
- Log durable changes only: Ingest, taxonomy changes, approved restructuring, Lint results, and approved Query writeback.

Do not log routine read-only queries or transient model and effort details.

## 8. Prepare global companion skills

After the architecture is approved, check whether compatible global Ingest, Query, and Lint skills already exist. If they do, compare and reuse them. Do not overwrite them.

If they are missing, use the canonical sources in `assets/companion-skills/` to create one global portable skill set. Each skill must locate the nearest `kb.config.yaml`, operate on one KB by default, and remain provider agnostic.

For selected harnesses only:

1. generate thin, verified adapters when their format is known;
2. provide an integration note when it is not verified;
3. stage packages in a user-confirmed output folder, defaulting to `outputs/skill-packages/`;
4. validate the portable skills and ZIP files;
5. provide clickable local download links when supported;
6. ask before global installation or replacement.

Do not upload or host packages without approval.

## 9. Seed and verify

Ingest one representative source. Verify that the original is unchanged, relevant existing pages were updated, provenance resolves, and useful links were added.

Run one real test for each operation:

1. **Ingest:** integrate one source under its source-class policy.
2. **Query:** answer one recurring question with citations and uncertainty.
3. **Lint:** detect one real or seeded defect without fixing it.

Confirm that front doors agree, YAML and Markdown are synchronized, links resolve, protected paths remain untouched, and the built structure matches the approved preview.

## Rules

- Ask before structural changes.
- Keep consequential decisions with the user.
- Never invent facts, citations, platform behavior, or safety assurances.
- Prefer readable files and deterministic search before databases, embeddings, or RAG.
- Keep responses short unless depth is needed or requested.
- Never send, install, publish, deploy, upload, or share without explicit approval.

## Related

- [KB contract](references/kb-contract.md)
