# Spec — Semantic retrieval over the knowledge graph

**Date:** 2026-06-15
**Status:** Approved design, decomposed into the plan alongside this file.

## Why (reconciliation with the 2.0 premise)

The 2.0 redesign (`2026-04-27-knowledge-map-rag-design.md`) deliberately **removed similarity
search** in favour of structural navigation, to fix cross-document synthesis failures. But the
same spec wrote the escape hatch verbatim: *"deterministic structural retrieval first; **add
embeddings only if structural fails**. We start without; door remains open via `llm_service`
abstraction."*

Structural retrieval has now demonstrably failed for the real use case (factual lookup over a
product catalog): exact-name-only matching means "Vector" returns garbage and never reaches
the "Porta Vector Premium" entity; answers are built from generic node `description`
("linia wzornicza drzwi") instead of the catalog facts; whole-source questions/tags pollute
every node ("god nodes") and wreck the lexical ranking. Adding semantic retrieval is therefore
not a regression — it is the exact contingency 2.0 anticipated.

## Architecture (hybrid — evolution of 2.0, not a revert)

Semantic recall as the engine + the graph as the connection layer + answers from claim text.

```
question
  -> embed question
  -> SEMANTIC recall: top-K CLAIMS by cosine over claim embeddings   (fixes partial names / NL / "Vector")
  -> GRAPH expansion: the claims' subject entities/concepts, related claims, edges
  -> context built from the VERBATIM claim text (node description demoted)
  -> LLM answers and cites [claim:id]  -> real fragments              (fixes "no fragments")
```

The **claim** is the unit of truth, so we embed claims (not chunks, not whole sources). The
graph is retained and does real work (expansion, relations, aggregation like "which models have
the acoustic package"). The existing lexical score is kept as a **secondary signal** (hybrid),
not the sole recall path. Stages 1/3/5 (intent, selection, answer) are unchanged — only fed
better candidates.

## Components

- `services/embeddings_service.py` — batch OpenAI `text-embedding-3-small` calls; the network
  call is injectable for tests.
- `services/vector_store.py` — flat cosine over a NumPy matrix (a few thousand claims = instant),
  persisted to disk; maps `claim_id -> vector`. Pure, no network.
- claim-embedding index — built after ingest and by a one-off `rebuild_embeddings` script over the
  existing 837 claims; persisted under `wiki_data/<profile>/wiki/embeddings/`.
- `services/retrieval/semantic_retrieval.py` — question -> top-K claims -> graph expansion ->
  `Candidate` list (same shape downstream stages already consume).
- retrieval pipeline Stage 2 — semantic recall first, merged with the existing lexical score.
- `context_assembly` — lead with claim text; node description demoted to a trailing line.

## What stays from 2.0

The graph, claims, entities/concepts, edges, structural navigation (now as the expansion layer
and for cross-doc synthesis), and the Learning-Lab visibility of every stage. The only thing
removed is **lexical matching as the *sole* recall path.**

## Phases (each shippable, TDD)

1. `embeddings_service` + `vector_store` (pure/injectable; no live network in tests).
2. claim index builder + semantic Stage 2 + graph expansion + `context_assembly` rewrite.
3. embed the existing 837 claims (rebuild script) + **live verification** on the two failing
   queries ("Vector", "czym jest kolekcja Porta Vector Premium") — both must return a sensible
   answer with real cited fragments.
4. gold-set eval to measure the improvement with numbers.

## Out of scope (later)

Entity de-duplication across types (Org vs Product), and re-extraction prompt tuning for node
descriptions. Semantic recall makes these much less damaging, so they drop in priority.

## Testing

Pure units (embeddings batching with injected fn, vector cosine/search/persist) are unit-tested
without network. Pipeline wiring tested with a stub embed_fn + a tmp graph. Phase 3 is a live
manual check against the real graph. Phase 4 quantifies via the gold-set runner.
