# Knowledge-base contract

Use this contract as a required shape, then fit paths, page types, fields, approvals, and future branches to the user's work. Do not copy placeholder values blindly.

## Contents

1. [YAML contract](#yaml-contract)
2. [Markdown front doors](#markdown-front-doors)
3. [Page schema](#page-schema)
4. [Synchronization](#synchronization)

## YAML contract

```yaml
version: 1

knowledge_base:
  id: example-kb
  name: Example Knowledge Base
  root: .
  scope: standalone
  purpose: []
  users: []
  recurring_questions: []

front_doors:
  config: kb.config.yaml
  instructions: AGENTS.md
  index: INDEX.md
  schema: SCHEMA.md

storage:
  evidence:
    paths: []
    canonical: true
  knowledge:
    paths: []
    canonical: true
  projects:
    paths: []
  outputs:
    paths: []
    canonical: false
  protected:
    paths: []

source_classes:
  immutable:
    paths: []
    policy: never-edit
  externally_managed:
    paths: []
    policy: read-only-local
    refresh: from-owning-system
  user_managed:
    paths: []
    policy: edit-with-explicit-approval

schema:
  content_format: markdown
  frontmatter_format: yaml
  universal_fields:
    id: {type: string, required: true, unique: true}
    type: {type: string, required: true}
    scope: {type: string, required: true}
    tags: {type: list, required: true}
    source: {type: string-or-list, required: true}
    updated: {type: date, required: true}
    status: {type: string, required: true}
  page_types: {}
  links:
    format: standard-relative-markdown
    wikilinks_allowed: false
    inbound_required: true
    related_section_required: true
    reciprocal_when_useful: true
  taxonomy:
    current_branches: []
    planned_branches: []
    naming_rules: []
    growth_triggers: []

operations:
  ingest:
    update_existing_before_create: true
    require_provenance: true
    surface_conflicts: true
    log_durable_change: true
  query:
    require_citations: true
    report_uncertainty: true
    report_conflicts: true
    writeback: review-required
    log_read_only: false
  lint:
    read_only: true
    checks:
      - broken-links
      - orphan-pages
      - invalid-frontmatter
      - stale-facts
      - contradictions
      - missing-provenance
      - taxonomy-gaps
      - sensitive-information

governance:
  sensitive_information:
    categories:
      - credentials
      - secrets
      - pii
      - financial-information
      - confidential-information
    on_detection: warn-exclude-and-continue
    echo_values: false
    alternatives:
      - redact
      - replace-with-sample-data
      - narrow-scope
  structural_changes:
    may_propose: [create, edit, move, rename, merge, reorganize, remove]
    require_itemized_approval: true
  removals:
    default: move-to-holding-folder
    holding_folder: user-must-confirm
    show_destination_before_move: true
    permanent_delete_requires_separate_confirmation: true

routing:
  default_scope: nearest-config
  one_kb_per_operation: true
  ambiguity: ask
  cross_kb_query: explicit-config-and-user-confirmation
  cross_kb_write: false

platforms:
  selected_harnesses: []
  selected_providers: []
  persist_model: false
  persist_effort: false
  adapters: selected-only

packaging:
  canonical_format: open-agent-skill
  output_directory: outputs/skill-packages
  install_globally: ask
  replace_existing: compare-and-ask
  provide_local_download_link: when-supported
  upload_or_host: explicit-approval

logging:
  durable_events:
    - ingest
    - schema-change
    - taxonomy-change
    - approved-restructure
    - lint-run
    - approved-query-writeback
  routine_queries: false
  runtime_model_and_effort: false

synchronization:
  operational_authority: kb.config.yaml
  contextual_authority: markdown-front-doors
  on_conflict: stop-show-and-ask
```

## Markdown front doors

- `AGENTS.md` explains the purpose, roles, boundaries, source classes, workflows, approvals, and harness adapters.
- `INDEX.md` routes people and agents to canonical knowledge, evidence, projects, outputs, and current work.
- `SCHEMA.md` explains the taxonomy, page types, field meanings, link rules, planned branches, and growth triggers.
- Harness-specific instruction files point to `AGENTS.md`; they do not copy its contents.

## Page schema

Every synthesized page starts with the universal core:

```yaml
---
id: stable-domain-id
type: domain-page-type
scope: kb-scope
tags: []
source: relative/path/to/evidence
updated: YYYY-MM-DD
status: active
---
```

Add fields only when the page type needs them. Define each extension in both `kb.config.yaml` and `SCHEMA.md`.

Use standard relative Markdown links. End substantive knowledge pages with `## Related`. Require at least one inbound link. Add reciprocal links when they improve navigation, maintenance, or query accuracy.

## Synchronization

YAML owns machine-enforced paths, permissions, required metadata, and operation settings. Markdown owns domain meaning, rationale, examples, and human guidance. Validate both after changes. If an operational conflict appears, stop and ask which version to keep.
