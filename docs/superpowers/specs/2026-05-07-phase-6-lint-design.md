# Phase 6 — Lint Tier 1+2 Design

**Status:** Design — approved
**Date:** 2026-05-07
**Parent spec:** `docs/superpowers/specs/2026-04-27-knowledge-map-rag-design.md` (sekcja "Lint workflow")
**Predecessor:** Phase 5 — Graph View (`phase-5-complete`, 237 testów)

## TL;DR

Dodać deterministyczny system kontroli jakości wiki: 8 typów wykrywanych issues w dwóch tierach (provenance/integrity + navigability), zapis raportu jako JSON, panel UI z tabelą issues i per-issue fix workflow. Bez LLM. Skupia się na strukturalnych gwarancjach (provenance invariant, "islands with bridges" topology) — Tier 3 (semantic, LLM-assisted) odłożony do Phase 7.

## Motivation

Spec rodzicielski określa Lint jako "Karpathy operation 3" — wiki health check chroniący provenance invariant i navigability. Bez Lint:
- Można dodać claim bez `source_id` (utrata audytu).
- Krawędź może wskazywać na nieistniejący node (zepsuty graph).
- Encja bez incoming edges/claims jest niewidoczna w retrievalu — leży w wiki, ale Stage 2 jej nie wybierze.
- Pusta `questions[]` blokuje Stage 2 candidate scoring (DW: "pytania to złoto retrievalu").

Phase 6 dostarcza wykrycie + minimum fixów deterministycznych. Reszta (LLM-assisted span picker dla `provenance_missing`, generator pytań dla `empty_questions`) idzie do Phase 7.

## Architektura

### Backend — nowe moduły

```
backend/
├── models/
│   └── lint_models.py
├── services/
│   └── lint/
│       ├── __init__.py
│       ├── checks/
│       │   ├── __init__.py
│       │   ├── provenance.py        # Tier 1
│       │   └── navigability.py      # Tier 2
│       ├── runner.py                # orkiestrator
│       └── fix_applier.py           # deterministyczne fixy
└── api/
    └── lint.py                      # POST /api/lint/run, GET /api/lint/reports, ...
```

### Backend — zmodyfikowane

- `backend/services/wiki_store.py` — dodać minimalny zestaw operacji delete/update wymaganych przez fix_applier:
  - `delete_claim(claim_id)` — usuwa linię w `claims.jsonl`
  - `delete_edge(edge_id)` — usuwa linię w `edges.jsonl`
  - `delete_jsonl_line(path, line_no)` — usuwa konkretną wadliwą linię (z backupem `.bak`)
  - `delete_entity(slug, entity_type)` — usuwa plik `wiki/20-Entities/<type>/<slug>.md`
  - `delete_concept(slug)` — usuwa plik `wiki/10-Concepts/<slug>.md`
  - `update_entity_description(slug, entity_type, new_description)` — pisze pole `description` we frontmatter
  - `update_concept_description(slug, new_description)` — pisze pole `definition` we frontmatter
- `backend/services/wiki_log.py` — dodać `append_lint_summary(report_id, found, fixed, rejected, wontfix)` — pisze linię do `log.md`
- `backend/main.py` — register `lint_router`

### Frontend — nowe pliki

```
frontend/src/components/
└── lint/
    ├── LintPanel.tsx                # główny panel
    └── LintIssueRow.tsx             # render jednego issue + akcje
```

### Frontend — zmodyfikowane

- `frontend/src/types/index.ts` — dodać `LintIssue`, `LintReport`, `IssueType`, `IssueSeverity`
- `frontend/src/api/client.ts` — dodać `runLint`, `listLintReports`, `getLintReport`, `applyLintFix`, `rejectLintIssue`, `markWontFix`
- `frontend/src/components/Sidebar.tsx` — dorzucić wpis "Lint" (ikona `ShieldCheck` z lucide-react)
- `frontend/src/App.tsx` — routing dla nowego panela

## Modele danych

### `LintIssue` (Pydantic)

```python
IssueSeverity = Literal["error", "warning", "info"]

IssueType = Literal[
    # Tier 1 (error)
    "provenance_missing",
    "dangling_source_ref",
    "dangling_node_ref",
    "corrupted_jsonl",
    # Tier 2 (warning)
    "orphan_entity",
    "orphan_concept",
    "empty_questions",
    "empty_description",
]

IssueStatus = Literal["open", "fixed", "rejected", "wontfix"]

class LintIssue(BaseModel):
    id: str                          # stabilny: "{type}:{location_hash}"
    type: IssueType
    severity: IssueSeverity
    location: str                    # np. "claims.jsonl:42", "entity:e_007", "wiki/20-Entities/Person/jan.md"
    description: str                 # human-readable, np. "Claim cl_017 has no source_id"
    suggested_fix: Optional[str]     # human-readable opis tego, co zrobi auto-fix; None jeśli brak
    auto_fixable: bool               # czy fix_applier umie to naprawić bez interwencji
    payload: Dict[str, Any] = {}     # type-specific dane (np. claim_id, edge_id, slug, entity_type)
    status: IssueStatus = "open"
```

### `LintReport`

```python
class LintReport(BaseModel):
    id: str                          # ISO-like timestamp: "2026-05-07T14-30-00"
    created_at: datetime
    issues: List[LintIssue]
    counts_by_severity: Dict[str, int]   # {"error": 3, "warning": 12, "info": 0}
    counts_by_type: Dict[str, int]
```

Plik raportu: `wiki_data/wiki/lint_reports/<id>.json`. Po `apply_fix` / `reject` / `wontfix` aktualizujemy `status` issue w pliku raportu (rewrite całego JSON-a — raport to ~kilkadziesiąt issues max, atomic write).

### Stabilne ID issue

Aby `Apply Fix` działał na konkretne issue z raportu, ID musi być deterministyczne. Format:
- `provenance_missing:claim:<claim_id>` lub `provenance_missing:edge:<edge_id>`
- `dangling_source_ref:claim:<claim_id>` / `dangling_source_ref:edge:<edge_id>`
- `dangling_node_ref:edge:<edge_id>:<from|to>`
- `corrupted_jsonl:<path>:<line_no>`
- `orphan_entity:<entity_id>`
- `orphan_concept:<concept_id>`
- `empty_questions:<node_prefix>:<node_id>` (entity/concept/source)
- `empty_description:<node_prefix>:<node_id>`

## Checki

### Tier 1 — provenance & integrity (`provenance.py`)

#### `provenance_missing`
Iteruj po claims i edges. Issue jeśli:
- Claim: brak `source_id` lub `span` (tutaj: zwykle przejdzie walidacja Pydantic, ale fallback dla ręcznie edytowanych plików — odczytaj `claims.jsonl` linia po linii, próbuj sparsować, jeśli brak pól w surowym dict → issue).
- Edge: jak wyżej dla `edges.jsonl`.

W praktyce Pydantic odrzuci niepoprawne — więc check faktycznie wykrywa **uszkodzone ręcznie pliki** zanim Pydantic je odbije. Dlatego implementacja czyta JSONL surowo (`json.loads` na linii) i sprawdza klucze w dict, nie poprzez model.

#### `dangling_source_ref`
Buduj zbiór wszystkich `source.id` z `index.json`. Dla każdego claim/edge sprawdź `source_id` ∈ zbiór. Jeśli nie → issue.

#### `dangling_node_ref`
Buduj zbiór wszystkich `entity.id` i `concept.id`. Dla każdej krawędzi sprawdź `from` i `to` (po stripowaniu prefixu) — czy odpowiedni id istnieje. Jeśli nie → issue.

#### `corrupted_jsonl`
Czytaj `claims.jsonl` i `edges.jsonl` linia po linii. Każda linia, która rzuca `json.JSONDecodeError` → issue z `location=<path>:<line_no>`.

### Tier 2 — navigability (`navigability.py`)

#### `orphan_entity`
Encja nie ma:
- Żadnej krawędzi (incoming ani outgoing).
- Żadnego claimu (`subject_id == "entity:<id>"`).

#### `orphan_concept`
Concept nie ma żadnej **incoming** krawędzi (ma być "thin bridge", więc bez incoming nic nie łączy).

#### `empty_questions`
Entity / Concept / Source z `questions == []`.

#### `empty_description`
- Entity: `len(description.strip()) < 30`
- Concept: `len(definition.strip()) < 30`
- Source: `len(summary.strip()) < 30`

## Fix matrix

| Issue | Auto-fix | Działanie |
|---|---|---|
| `provenance_missing` | ❌ | Tylko Reject / Won't-fix. Span picker → Phase 7. |
| `dangling_source_ref` | ✅ | Usuń claim/edge (`delete_claim` / `delete_edge`). |
| `dangling_node_ref` | ✅ | Usuń edge. |
| `corrupted_jsonl` | ✅ | Usuń wadliwą linię (z backupem `.bak`). |
| `orphan_entity` | ✅ | Usuń plik encji (`delete_entity(slug, type)`). |
| `orphan_concept` | ✅ | Usuń plik conceptu. |
| `empty_questions` | ❌ | Tylko Reject / Won't-fix. Generator pytań → Phase 7 (LLM). |
| `empty_description` | ✅ (edit) | Inline edit description (textarea w UI → `update_entity/concept_description`). |

Frontend rozróżnia trzy tryby UI per-issue:
- **Apply Fix** — jeden klik (delete) lub edit-and-save (description).
- **Reject** — issue znika z aktywnej listy, status `rejected`.
- **Won't-fix** — jak Reject, ale semantycznie "świadomie zostawiam".

Nieaktywny **Apply Fix** dla typów bez auto-fixa (UI greys out button).

## API

### `POST /api/lint/run`

Body: `{}` (puste; przyszłość: `{"include_semantic": true}` dla Tier 3).

Response: `LintReport` (właśnie utworzony, status open dla wszystkich issues).

Side-effect: zapis `wiki_data/wiki/lint_reports/<id>.json`, append do `log.md`:
```
## [2026-05-07 14:30:00] lint | run <id> | found: 15 (3 errors, 12 warnings)
```

### `GET /api/lint/reports`

Response: `List[{id, created_at, counts_by_severity, total}]` — lista historycznych raportów.

### `GET /api/lint/report/{report_id}`

Response: pełny `LintReport`.

### `POST /api/lint/fix`

Body:
```json
{
  "report_id": "2026-05-07T14-30-00",
  "issue_id": "dangling_source_ref:claim:cl_017",
  "action": "apply" | "reject" | "wontfix",
  "edit_payload": null | {"description": "..."}
}
```

Logika:
- `apply` z `auto_fixable=true` → `fix_applier.apply(issue, edit_payload)`, status → `fixed`.
- `apply` z `auto_fixable=false` → 400.
- `reject` → status → `rejected`.
- `wontfix` → status → `wontfix`.

Po każdym `apply/reject/wontfix` aktualizujemy raport (rewrite JSON-a, atomic write).

**Logowanie:** w Phase 6 dopisujemy do `log.md` tylko przy `POST /api/lint/run`. Per-action update logu (podsumowanie po zamknięciu raportu) → Phase 7+.

## UI — `LintPanel.tsx`

```
┌──────────────────────────────────────────────────────────────────┐
│ Lint                                              [Run Now]      │
├──────────────────────────────────────────────────────────────────┤
│ Last report: 2026-05-07 14:30  •  3 errors  •  12 warnings       │
│ [All] [Errors] [Warnings] [Open] [Fixed]                         │
├──────────────────────────────────────────────────────────────────┤
│ ⛔ dangling_source_ref                                            │
│   claim cl_017 references missing source src_999                 │
│   suggestion: delete claim                                        │
│   [Apply Fix] [Reject] [Won't-fix]                                │
├──────────────────────────────────────────────────────────────────┤
│ ⚠ orphan_entity                                                   │
│   entity:e_004 has no edges and no claims                         │
│   suggestion: delete entity                                        │
│   [Apply Fix] [Reject] [Won't-fix]                                │
├──────────────────────────────────────────────────────────────────┤
│ ⚠ empty_description                                               │
│   concept:c_009 description < 30 chars                            │
│   [textarea inline] [Save] [Reject]                               │
└──────────────────────────────────────────────────────────────────┘
```

- `Run Now` → POST /api/lint/run, refresh listy.
- Filtry: severity (All/Error/Warning), status (Open/Fixed/Rejected/Won't-fix).
- Issue row: badge ikoną, krótki opis lokacji, opis błędu, suggested_fix, akcje.
- `empty_description` ma inline textarea zamiast samego "Apply Fix".
- Po fixie row dostaje status badge `fixed` i ukrywa się przy default filter (Open).
- Empty state: "No lint reports yet. Click Run Now."

## Testowanie

### Backend

Nowe testy w:
- `backend/tests/services/lint/test_provenance_checks.py` — ~10 testów (4 typy × happy/sad path)
- `backend/tests/services/lint/test_navigability_checks.py` — ~10 testów
- `backend/tests/services/lint/test_runner.py` — orkiestrator, integracja z wiki_store
- `backend/tests/services/lint/test_fix_applier.py` — ~6 testów (po jednym per typ auto-fixable)
- `backend/tests/api/test_lint_api.py` — endpointy

Cel: ~30 nowych testów. Po Phase 6: ~267 testów (237 + 30).

### Workflow testowy (TDD)

Per task: red → implementacja → green → commit. Bez wyjątków.

## Kolejność tasków (preview)

1. **`lint_models.py`** + testy modeli.
2. **Tier 1 checks** (`provenance.py`) + testy.
3. **Tier 2 checks** (`navigability.py`) + testy.
4. **`runner.py`** + zapis raportu + testy.
5. **`wiki_store` deletes/updates** + testy.
6. **`fix_applier.py`** + testy.
7. **API endpoints** (`api/lint.py`) + testy.
8. **Frontend types + api client.**
9. **`LintPanel.tsx`** + sidebar + routing.
10. **Manualny smoke test, full suite, tag `phase-6-complete`.**

Plan implementacji rozpisze to do checkboxów per-step.

## Pominięte z głównego specu (świadomie)

- `missing_backlinks` — pole `mentioned_in` nie istnieje w modelach `Entity`/`Concept`. Fix wymagałby refaktoru modelu. Odłożone do Phase 7+ wraz z decyzją czy to pole ma sens.
- Bulk operations — YAGNI; dodać przy realnej skali raportu.
- Tier 3 (semantic, LLM) — Phase 7.
- LLM-assisted fix dla `provenance_missing` (span picker UI) — Phase 7.
- LLM-assisted fix dla `empty_questions` (generator pytań) — Phase 7.

## Definicja sukcesu

- ✅ `POST /api/lint/run` produkuje `LintReport` z 8 typami issues.
- ✅ Każdy typ auto-fixable da się naprawić jednym requestem `POST /api/lint/fix` (lub edit-form dla `empty_description`).
- ✅ Raport persystowany jako JSON, statusy aktualizowane przy fixach.
- ✅ Panel `Lint` w UI: Run Now działa, lista issues z filtrami, akcje per-issue, refresh stanu.
- ✅ Pełen suite zielony (~267 testów), tag `phase-6-complete`.
