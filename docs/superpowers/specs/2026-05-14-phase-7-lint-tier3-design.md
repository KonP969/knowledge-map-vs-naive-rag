# Phase 7 — Lint Tier 3 (LLM-assisted semantic checks)

**Status:** Design — approved  
**Date:** 2026-05-14  
**Parent spec:** `docs/superpowers/specs/2026-04-27-knowledge-map-rag-design.md` (sekcja "Lint workflow — Tier 3")  
**Predecessor:** Phase 6 — Lint Tier 1+2 (`phase-6-complete`, 303 testy)

## TL;DR

Dodać 4 LLM-assisted semantic checki (Tier 3, severity `info`, opt-in toggle), uzupełnić Tier 2 o LLM-assisted fix dla `empty_questions`, i zamknąć per-action log update. Backend: osobny plik per check w `services/lint/checks/semantic/`. Frontend: toggle "Include semantic checks" w LintPanel. Synchroniczne wykonanie z cap=50 node/check. Testy z mock LLM.

## Motivation

Phase 6 dostarczyła deterministyczny Tier 1+2 (303 testy). Pozostały luki semantyczne których Python nie wykryje bez LLM:
- Dwie encje mogą opisywać tę samą osobę pod różnymi nazwami.
- Sprzeczne claimy mogą leżeć obok siebie bez krawędzi `contradicts`.
- Encja z 7 claimami o jednym temacie powinna mieć Concept node — ale nie ma.
- Summary source.md napisana przy ingeście może nie obejmować claims dodanych później.

Phase 6 odłożyła też LLM-assisted fix dla `empty_questions` (Tier 2) — teraz go domykamy.

## Zakres Phase 7

### Wchodzi

1. **4 nowe checki Tier 3** (`unmarked_contradiction`, `entity_alias_collision`, `missing_concept`, `stale_summary`)
2. **`empty_questions` LLM generator** — fix dla istniejącego Tier 2 issue (dotychczas tylko reject/wontfix)
3. **Per-action log update** — zapis podsumowania do `log.md` gdy wszystkie issues w raporcie są w stanie terminalnym

### Nie wchodzi

- `provenance_missing` span picker UI — ciężkie UI, → Phase 9
- Bulk operations — YAGNI
- Async/polling dla Tier 3 — synchroniczne z cap=50 wystarczy przy docelowej skali wiki (50–200 źródeł)

## Architektura

### Opcja B — osobny plik per check (wybrana)

```
backend/services/lint/checks/semantic/
├── __init__.py
├── unmarked_contradiction.py
├── entity_alias_collision.py
├── missing_concept.py
└── stale_summary.py
```

Każdy plik eksportuje jedną funkcję `check_*(store, llm_client) -> List[LintIssue]`, spójnie z istniejącym wzorcem (`provenance.py`, `navigability.py`).

### Backend — nowe i zmodyfikowane pliki

| Plik | Zmiana |
|---|---|
| `services/lint/checks/semantic/__init__.py` | Nowy |
| `services/lint/checks/semantic/unmarked_contradiction.py` | Nowy |
| `services/lint/checks/semantic/entity_alias_collision.py` | Nowy |
| `services/lint/checks/semantic/missing_concept.py` | Nowy |
| `services/lint/checks/semantic/stale_summary.py` | Nowy |
| `models/lint_models.py` | +4 typy w `IssueType` Literal; +4 Pydantic modele LLM output |
| `services/lint/runner.py` | `run_lint(store, include_semantic=False)` — warunkowe Tier 3 z cap=50 |
| `services/lint/fix_applier.py` | +`empty_questions` generator; +`unmarked_contradiction` fix; +`stale_summary` fix |
| `services/wiki_log.py` | `append_lint_action_summary` — woła się gdy raport terminalny |
| `services/wiki_store.py` | +`update_source_summary`, +`update_node_questions`, +`append_edge` (jeśli brak) |
| `api/lint.py` | `RunLintBody.include_semantic: bool = False` |

### Frontend — modyfikacje

| Plik | Zmiana |
|---|---|
| `types/index.ts` | +4 nowe wartości `IssueType` |
| `components/lint/LintPanel.tsx` | +toggle checkbox "Include semantic checks (LLM, ~30–60s)" przy Run Now |
| `components/lint/LintIssueRow.tsx` | `empty_questions` → aktywny "Generate Questions"; `unmarked_contradiction` + `stale_summary` → "Apply Fix" aktywny; `entity_alias_collision` + `missing_concept` → greyed out |

## Modele danych

### Rozszerzenie `IssueType`

```python
IssueType = Literal[
    # Tier 1 (error)
    "provenance_missing", "dangling_source_ref", "dangling_node_ref", "corrupted_jsonl",
    # Tier 2 (warning)
    "orphan_entity", "orphan_concept", "empty_questions", "empty_description",
    # Tier 3 (info)
    "unmarked_contradiction", "entity_alias_collision", "missing_concept", "stale_summary",
]
```

### Pydantic modele dla LLM output (w `lint_models.py`)

```python
class ContradictionJudgement(BaseModel):
    is_contradiction: bool
    explanation: str

class AliasMergeJudgement(BaseModel):
    should_merge: bool
    explanation: str
    suggested_canonical: str

class MissingConceptJudgement(BaseModel):
    has_missing_concept: bool
    concept_name: str
    explanation: str

class StaleSummaryJudgement(BaseModel):
    is_stale: bool
    proposed_summary: str
    explanation: str
```

## Logika checków Tier 3

### `unmarked_contradiction`

1. Załaduj claims z `claims.jsonl`, zgrupuj po `subject_id`.
2. Dla każdej grupy znajdź pary `(asserts, denies)`.
3. Sprawdź czy istnieje krawędź `contradicts` między `from_=subject_id` dowolnego z claims.
4. Jeśli brak krawędzi → LLM call z tekstami obu claimów (`ContradictionJudgement`).
5. `is_contradiction=True` → `LintIssue(auto_fixable=True, payload={claim_a_id, claim_b_id, subject_id})`.

Fix: append edge `{from: "claim:{claim_a_id}", to: "claim:{claim_b_id}", relation: "contradicts", source_id: claim_a.source_id}` do `edges.jsonl`.  
Cap: max 50 grup subject_id przekazywanych do LLM.

### `entity_alias_collision`

1. Załaduj wszystkie encje, znormalizuj nazwy (lowercase, strip).
2. Dla każdej pary oblicz edit distance (własna implementacja DP, brak nowej zależności).
3. Distance < 3 → LLM call (`AliasMergeJudgement`).
4. `should_merge=True` → `LintIssue(auto_fixable=False, suggested_fix="Merge into {suggested_canonical}", payload={entity_a_id, entity_b_id, suggested_canonical})`.

Cap: max 50 par po przefiltrowaniu distance.

### `missing_concept`

1. Dla każdej encji: pobierz claims gdzie `subject_id == "entity:<id>"`.
2. Jeśli count ≥ 5 → LLM call z listą `claim.text` (`MissingConceptJudgement`).
3. `has_missing_concept=True` → `LintIssue(auto_fixable=False, suggested_fix="Create concept '{concept_name}'", payload={entity_id, concept_name})`.

Cap: max 50 encji z ≥5 claimami.

### `stale_summary`

1. Dla każdego source: pobierz `summary` + claims gdzie `source_id == source.id`.
2. LLM call z `summary` + `[claim.text, ...]` (`StaleSummaryJudgement`).
3. `is_stale=True` → `LintIssue(auto_fixable=True, payload={slug, proposed_summary})`.

Fix: `wiki_store.update_source_summary(slug, payload["proposed_summary"])`.  
Cap: max 50 sources.

## Fix matrix (kompletna Phase 7)

| Issue | auto_fixable | Działanie |
|---|---|---|
| `unmarked_contradiction` | ✅ | Append krawędź `contradicts` do `edges.jsonl` |
| `entity_alias_collision` | ❌ | Tylko reject/wontfix |
| `missing_concept` | ❌ | Tylko reject/wontfix |
| `stale_summary` | ✅ | `update_source_summary(slug, proposed_summary)` |
| `empty_questions` (Tier 2 upgrade) | ✅ | LLM generuje 3–5 pytań → `update_node_questions(node_id, questions)` |

## API

### `POST /api/lint/run` — rozszerzenie

```python
class RunLintBody(BaseModel):
    include_semantic: bool = False
```

Przy `include_semantic=True`: runner wywołuje dodatkowo 4 checki Tier 3 (synchronicznie). Timeout frontendu powinien uwzględniać ~60s.

Pozostałe endpointy (`/fix`, `/reports`, `/report/{id}`) — bez zmian.

## Per-action log update

Po każdym `POST /api/lint/fix` (apply/reject/wontfix): sprawdź czy wszystkie issues w raporcie są w stanie terminalnym (`fixed | rejected | wontfix`). Jeśli tak → `append_lint_action_summary(store, report)`:

```
## [2026-05-14 11:00:00] lint | closed <report_id> | fixed: 8, rejected: 2, wontfix: 3
```

## LLM wywołania

Wzorzec: `client.beta.chat.completions.parse(model=..., messages=[...], response_format=<Model>)` — identyczny jak `intent_parser.py`. Jeden LLM client na moduł, lazy init z `os.getenv("OPENAI_API_KEY")`.

## Testowanie

### Nowe pliki

```
backend/tests/services/lint/semantic/
├── __init__.py
├── test_unmarked_contradiction.py   # ~8 testów
├── test_entity_alias_collision.py   # ~8 testów
├── test_missing_concept.py          # ~6 testów
└── test_stale_summary.py            # ~6 testów
```

Rozszerzenia istniejących:
- `test_runner.py` — +3 testy dla `include_semantic=True/False` i cap
- `test_fix_applier.py` — +5 testów (empty_questions generator, unmarked_contradiction, stale_summary)

**Cel:** ~36 nowych testów → **łącznie ~339 testów** (303 + 36).

### Strategia mock LLM

Fixtures: słownik `{(model, normalized_messages_hash): response_json}`. Testy podają gotowy response — bez API calls. Wzorzec z `retrieval/` pipeline.

### TDD workflow

Per task: red → implementacja → green → commit. Bez wyjątków.

## Kolejność tasków (preview)

1. **Modele** — `lint_models.py` (IssueType +4, 4 Pydantic modele LLM output) + testy modeli.
2. **`unmarked_contradiction`** — check + fix + testy.
3. **`entity_alias_collision`** — check + edit distance + testy.
4. **`missing_concept`** — check + testy.
5. **`stale_summary`** — check + fix + `update_source_summary` w wiki_store + testy.
6. **`empty_questions` generator** — LLM fix + `update_node_questions` w wiki_store + testy.
7. **`runner.py`** — `include_semantic` param + cap + testy.
8. **`wiki_log.py`** — `append_lint_action_summary` + testy.
9. **API** — `RunLintBody.include_semantic` + testy.
10. **Frontend** — toggle, nowe typy, obsługa przycisków; `tsc --noEmit` clean.
11. **Manualny smoke test, full suite, tag `phase-7-complete`.**

## Definicja sukcesu

- ✅ `POST /api/lint/run` z `include_semantic=true` produkuje issues Tier 3 (info).
- ✅ `unmarked_contradiction` i `stale_summary` — Apply Fix działa jednym requestem.
- ✅ `empty_questions` — "Generate Questions" generuje i zapisuje pytania.
- ✅ `entity_alias_collision` i `missing_concept` — Apply Fix greyed out, reject/wontfix działają.
- ✅ Log.md aktualizowany przy zamknięciu raportu.
- ✅ Pełen suite zielony (~339 testów), `tsc --noEmit` clean, tag `phase-7-complete`.
