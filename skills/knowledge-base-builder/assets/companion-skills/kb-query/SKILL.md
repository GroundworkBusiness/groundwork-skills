---
name: kb-query
description: Answer questions from a file-based knowledge base governed by kb.config.yaml with citations, uncertainty, and conflict reporting. Use for grounded status, decision, entity, policy, process, or cross-page synthesis questions without modifying the KB unless reviewed writeback is explicitly approved.
---

# Query Knowledge

Find the nearest `kb.config.yaml` by walking upward from the working folder. If none exists, ask the user to select a KB. If several are plausible, show them and ask.

Use one KB by default. Search across KBs only when every selected config permits it and the user confirms the scopes. Never write across KB boundaries.

## Workflow

1. Read `kb.config.yaml`, `AGENTS.md`, `INDEX.md`, and the relevant parts of `SCHEMA.md`.
2. Follow the configured retrieval order and scope rules.
3. Search canonical Markdown knowledge first, then consult evidence when required for freshness, precision, or verification.
4. Answer directly from the files.
5. Cite the specific relative Markdown pages or evidence used.
6. State gaps, stale dates, contradictions, and unsupported inference plainly.
7. If the KB does not answer the question, say what was searched and what is missing.
8. Keep the operation read-only unless the user approves a specific writeback under the config's review policy.
9. Log only approved durable writeback, never routine read-only questions.

## Output

```text
Answer: <direct answer>

Uncertainty: <gaps, conflicts, stale information, or none>

Sources: <relative Markdown links actually used>
```

## Rules

- Never invent facts, citations, platform behavior, or certainty.
- Do not expose secret or PII values found while searching. Warn with paths and categories, exclude the affected material, and continue with safe sources.
- Do not record provider, model, or effort details.
- Keep the result portable across providers and harnesses.
