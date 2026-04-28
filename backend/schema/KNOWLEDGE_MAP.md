# Knowledge Map — Conventions

This document is the constitution for the wiki layer. The LLM and the codebase follow these rules verbatim.

## Layers

1. **Sources** (`wiki/30-Sources/<slug>.md`) — leaves; one per ingested raw source.
2. **Entities** (`wiki/20-Entities/<Type>/<slug>.md`) — typed: Person, Org, Product, Place, Event.
3. **Concepts** (`wiki/10-Concepts/<slug>.md`) — cross-cutting bridges between entities.
4. **Claims** (`wiki/claims.jsonl`) — atomic statements with provenance.
5. **Edges** (`wiki/edges.jsonl`) — typed relations between nodes.

Plus:
- `wiki/00-Index/index.md` (human catalog) and `wiki/00-Index/index.json` (machine-readable). Regenerated after every mutation.
- `wiki/log.md` — chronological append-only operation log.

## Slug rules

- Lowercase, hyphenated, ASCII-folded. Example: "Łazienka — sypialnia" → `lazienka-sypialnia`.
- Stripped of punctuation; whitespace and hyphens collapsed.
- Unique per layer; on collision append `-2`, `-3`, ... (deterministic).

## Frontmatter (YAML at top of every .md)

Every page has YAML frontmatter; `description`/`summary`/`definition` is the post body.

### Source

```yaml
id: "src_<n>"
title: "..."
type: "article|pdf|docx|txt|url"
raw_path: "raw/<slug>/parsed.md"
ingested_at: "2026-04-28T10:00:00"
source_url: "https://..."   # optional
key_takeaways: ["..."]
questions: ["..."]
tags: ["..."]
```

### Entity

```yaml
id: "e_<n>"
type: "Person|Org|Product|Place|Event"
aliases: ["..."]
mentions_count: 0
questions: ["..."]
tags: ["..."]
```

### Concept

```yaml
id: "c_<n>"
parent_concept: "..."   # optional
examples: ["..."]
related: ["..."]
questions: ["..."]
tags: ["..."]
```

## Claims (one JSON object per line in claims.jsonl)

```json
{"id": "cl_<n>", "text": "...", "subject_id": "entity:e_001|concept:c_001",
 "source_id": "src_<n>", "span": {"start": 0, "end": 0, "text": "..."},
 "confidence": 0.0, "polarity": "asserts|denies", "related_claim_ids": []}
```

Dedup key: `sha256(id|subject_id|normalized_text|polarity)`. Phase 2 adds semantic dedup across different IDs.

## Edges (one JSON object per line in edges.jsonl)

```json
{"id": "ed_<n>", "from": "entity:e_001", "to": "concept:c_001",
 "relation": "<closed list>", "source_id": "src_<n>",
 "span": {"start": 0, "end": 0, "text": "..."}, "confidence": 0.0}
```

Closed list of relations (10): `mentions`, `defines`, `contradicts`, `supports`, `derives_from`, `instance_of`, `part_of`, `associated_with`, `causes`, `precedes`. Free-form relations are rejected.

Dedup key: `(from, to, relation, source_id)`.

## Provenance invariant

**Every claim, every edge, and every assertion in entity/concept descriptions has `source_id + span`. No exceptions.** The Lint workflow (Phase 6) enforces this.

## Topology

- Sources have **one** structural link — to their primary hub (Concept or Entity).
- Cross-entity routing only via Concepts (the "thin bridges").
- Result: graph reads as 5–20 islands with thin bridges, not a single tangle.

## Operations

- **Ingest**: parse → classify (LLM Pydantic) → resolve+template-generate → optional conflict detection → save. See Phase 2 spec.
- **Query**: parse intent → filter candidates → select → assemble context → answer. See Phase 3 spec.
- **Lint**: check provenance, integrity, navigability (Tier 1+2 deterministic), semantic (Tier 3 LLM). See Phase 6/7 spec.

## Atomic writes

All file writes go via tmp file + rename. Never write directly to a final path.
