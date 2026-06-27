# Semantic retrieval over the knowledge graph — Implementation Plan

**Goal:** Restore natural-language semantic recall by embedding claims and retrieving them by
cosine, expanding via the graph, and answering from claim text — fixing partial-name queries,
wrong description-based "definitions", and missing fragments.

**Spec:** `docs/superpowers/specs/2026-06-15-semantic-retrieval-over-graph-design.md`

**Backend tests:** `cd backend && python -m pytest ...`. TDD throughout. Commit per task.
Co-Author trailer on commits: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## Phase 1 — embeddings + vector store (pure, no live network in tests)

### Task 1.1: `vector_store.py`
- Create `backend/services/vector_store.py`, test `backend/tests/services/test_vector_store.py`.
- `class VectorStore`: `add(ids: list[str], vectors: list[list[float]])`, `search(query: list[float], top_k:int) -> list[tuple[str,float]]` (cosine, desc), `save(path)`, classmethod `load(path)`, `__len__`, `ids` property. Backed by a NumPy float32 matrix; cosine = normalized dot. Persist as `.npz` (matrix) + ids json, or a single `.npz` with an object array of ids.
- Tests (no network): add 3 vectors, search returns nearest first; identical vector scores ~1.0; save+load round-trips ids and search; empty store search returns [].

### Task 1.2: `embeddings_service.py`
- Create `backend/services/embeddings_service.py`, test `test_embeddings_service.py`.
- `embed_texts(texts: list[str], *, embed_fn: Optional[Callable[[list[str]], list[list[float]]]] = None, batch_size: int = 256) -> list[list[float]]`. Default `embed_fn` calls OpenAI `text-embedding-3-small`; tests inject a fake embed_fn. Batches inputs; preserves order; empty input -> [].
- `embed_query(text) -> list[float]` convenience (single).
- Tests: injected fn receives batched calls covering all inputs; order preserved; len(out)==len(texts).

---

## Phase 2 — claim index + semantic retrieval + context

### Task 2.1: claim index builder
- Create `backend/services/semantic_index.py`, test `test_semantic_index.py`.
- `CLAIM_INDEX_PATH(store) -> Path` = `store.root/"wiki"/"embeddings"/"claims.npz"`.
- `build_claim_index(store, *, embed_fn=None) -> VectorStore`: read all claims, embed each `claim.text`, build+save a VectorStore keyed by claim id. Returns it.
- `load_claim_index(store) -> Optional[VectorStore]` (None if absent).
- Tests (injected embed_fn returning deterministic vectors, e.g. hash-based): builds index with one vector per claim; persisted file loads; ids == claim ids.

### Task 2.2: semantic retrieval + graph expansion
- Create `backend/services/retrieval/semantic_retrieval.py`, test `test_semantic_retrieval.py`.
- `semantic_candidates(question, store, *, vector_store, embed_fn, top_k_claims=20) -> list[Candidate]`:
  1. embed question, `vector_store.search(qvec, top_k_claims)` -> claim ids.
  2. load those claims; group by subject entity/concept and by source.
  3. emit `Candidate` objects for the subject entities/concepts (and the sources) of the hit
     claims, scored by summed claim similarity; attach the hit claim ids on the candidate
     (new optional field `claim_ids: list[str]` on `Candidate`) so context assembly can lead
     with exactly the semantically-relevant claims.
  4. graph expansion: include entities/concepts reachable by one edge from a hit subject.
- Tests with a tmp store + a handful of claims/entities and a stub embed_fn that makes the
  question vector closest to the "Vector Premium" claims: returns that entity as top candidate
  with its claim_ids attached; an unrelated claim is not surfaced.

### Task 2.3: wire Stage 2 (hybrid) + context assembly
- Modify `candidate_filter`/`retrieval_pipeline`: Stage 2 = semantic_candidates (if a claim
  index exists) merged with the existing lexical `filter_candidates` (union by artifact_id,
  scores added). If no index, fall back to lexical only (backward compatible).
- Modify `context_assembly`: when a candidate carries `claim_ids`, lead the section with those
  claim texts (verbatim, with `[claim:id]` anchors); demote `description_preview` to a trailing
  "(node summary: …)" line.
- Tests: pipeline-level test with a stub embed_fn proving the answer context contains the hit
  claim text and the claim anchors; lexical-only path still works when no index present.

---

## Phase 3 — embed existing data + live verification

### Task 3.1: rebuild script + ingest hook
- Add `backend/scripts/rebuild_embeddings.py` (build_claim_index over the active store).
- Hook `ingest_pipeline` Stage 5 to update the claim index for the new source's claims (append),
  or simplest: mark index stale and rebuild lazily. Keep minimal; full rebuild script is the
  primary path for now.

### Task 3.2: live verification (manual, real graph)
- Run `rebuild_embeddings` over the current 837 claims.
- Query "Vector" and "czym jest kolekcja Porta Vector Premium" through the API; confirm sensible
  answers citing real Vector-Premium claims (not "linia wzornicza", not "PORTA HIDE").

---

## Phase 4 — gold-set eval (separate, after 1–3 land)

Thin runner -> `/api/retrieval/query` + hand-written gold questions (PORTA CPL, acoustic
package, frames) judged by reused `tests/rag_evaluation/evaluator.py`. Quantify before/after.

---

## Notes
- `Candidate` gains an optional `claim_ids: list[str] = []` field (used by semantic path +
  context assembly). Backward compatible.
- Embedding the question is one extra LLM/embedding call per query; record its ms via
  `record_query(embedding_ms=…)` (the field already exists in `llm_service.record_query`).
