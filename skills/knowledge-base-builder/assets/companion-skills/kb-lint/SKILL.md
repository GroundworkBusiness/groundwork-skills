---
name: kb-lint
description: Run a read-only health audit of a file-based knowledge base governed by kb.config.yaml. Use to find broken Markdown links, orphans, invalid YAML frontmatter, stale facts, contradictions, missing provenance, taxonomy drift, sensitive-information risks, and config-to-Markdown conflicts.
---

# Lint Knowledge

Find the nearest `kb.config.yaml` by walking upward from the working folder. If none exists, ask the user to select a KB. If several are plausible, show them and ask. Audit one KB at a time and report cross-KB scopes separately.

## Checks

- Required front doors exist and agree: `kb.config.yaml`, `AGENTS.md`, `INDEX.md`, and `SCHEMA.md`.
- YAML frontmatter matches the universal core and page-type extensions.
- Standard relative Markdown links resolve.
- Wikilinks are absent unless the contract explicitly permits them.
- Every substantive knowledge page has inbound coverage and a `## Related` section.
- Canonical ownership is clear; duplicate or competing pages are flagged.
- Provenance resolves to evidence.
- Immutable and externally managed sources are unchanged locally.
- Stale facts, contradictions, unsupported synthesis, and taxonomy gaps are surfaced.
- Planned branches and growth triggers remain aligned with actual growth.
- Likely secrets, credentials, PII, financial information, and confidential material are reported by path and category without printing values.
- Durable operations are logged and routine read-only queries are not.
- Generated packages and outputs remain outside the canonical knowledge graph.

## Output

Report coverage and counts first. Then provide a concise findings table with:

```text
Priority | File | Finding | Evidence | Suggested next step
```

Distinguish verified defects from possible risks. State what was not inspected.

## Rules

- Remain read-only. Propose fixes but do not apply them without a separate request and the config's approvals.
- Never combine findings from multiple KBs into one unscoped result.
- Never print sensitive values.
- Do not record provider, model, or effort details.
- Keep the result portable across providers and harnesses.
