---
name: kb-ingest
description: Add or refresh source material in a file-based knowledge base governed by kb.config.yaml. Use when the user wants to ingest documents, integrate new evidence into existing Markdown knowledge, update links and provenance, or record conflicts without changing protected sources.
---

# Ingest Knowledge

Find the nearest `kb.config.yaml` by walking upward from the working folder. If none exists, ask the user to select a KB. If several are plausible, show them and ask. Operate on one KB only.

## Workflow

1. Read `kb.config.yaml`, `AGENTS.md`, `INDEX.md`, and `SCHEMA.md`.
2. Confirm the source paths and their source classes.
3. Scan for likely secrets, credentials, PII, financial information, and confidential material. Name affected paths and categories, never values. Exclude affected files by default and continue safely.
4. Inspect the new source and the existing knowledge it may affect.
5. Present a short plan naming files to create or edit. Ask for approval before writing.
6. Preserve immutable and externally managed sources. Follow explicit approval rules for user-managed sources.
7. Update existing canonical pages before creating new pages.
8. Add YAML frontmatter, provenance, standard relative Markdown links, inbound coverage, and `## Related` sections required by the schema.
9. Surface contradictions and uncertainty. Do not silently choose a winner.
10. Update `INDEX.md` and the durable operation log when the contract requires it.
11. Verify links, metadata, source integrity, and changed-file scope.

## Rules

- Never invent facts or citations.
- Never write across KB boundaries.
- Never move, rename, merge, reorganize, or remove existing files without itemized approval.
- For approved removal, show the exact user-confirmed holding-folder destination. Permanent deletion requires separate confirmation.
- Do not record provider, model, or effort details.
- Keep the result portable across providers and harnesses.
