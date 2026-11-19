# Knowledge-Map RAG vs Naive RAG

*[English](README.md) · Polski*

[![CI](https://github.com/KonP969/knowledge-map-vs-naive-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/KonP969/knowledge-map-vs-naive-rag/actions/workflows/ci.yml)

Lokalna, edukacyjna aplikacja webowa realizująca **Knowledge-Map RAG** — eksperyment
zainspirowany krytyką naiwnego RAG autorstwa Andreja Karpathy'ego. Zamiast przeszukiwać
surowe fragmenty tekstu, system przy każdym wgraniu wyciąga ze źródła strukturalny
graf wiedzy — encje, koncepty i pojedyncze twierdzenia — i odpowiada na pytania,
przeszukując ten graf i rozumując nad nim, pokazując każdy krok.

To projekt badawczo-poznawczy: chodzi o to, żeby pipeline retrievalu był *czytelny*,
a nie żeby był produkcyjnym stackiem RAG.

![Wiki Chat — pytanie, jego 5-etapowy ślad retrievalu i cytowana odpowiedź](docs/screenshots/wiki-chat.png)

Zadajesz pytanie, a pipeline przebiega u góry, etap po etapie; odpowiedź poniżej
cytuje dokładnie te twierdzenia (claims), których użył.

| | |
|---|---|
| [![Knowledge Map](docs/screenshots/knowledge-map.png)](docs/screenshots/knowledge-map.png) | [![Pipeline ingestu](docs/screenshots/ingest.png)](docs/screenshots/ingest.png) |
| Graf, z którego budowane są odpowiedzi | 5-etapowy pipeline ingestu, dla każdego źródła |
| [![Sources](docs/screenshots/sources.png)](docs/screenshots/sources.png) | [![Tutorial](docs/screenshots/tutorial.png)](docs/screenshots/tutorial.png) |
| Każde wgrane źródło i co z niego wyciągnięto | Wbudowany przewodnik po całym podejściu |

Przy pierwszej wizycie krótki tour przeprowadza przez panele — można go powtórzyć
w dowolnej chwili przyciskiem **Tour** w nagłówku.

## Dlaczego nie naiwny RAG?

Klasyczny RAG (podziel → embeduj → szukaj po wektorach → wstaw do promptu → LLM)
ma problem z:

- **Sprzecznymi faktami** — dwa źródła się nie zgadzają; model dostaje oba i je miesza
- **Pytaniami wieloprzeskokowymi** — odpowiedź wymaga połączenia faktów z kilku dokumentów
- **Aktualizacjami w czasie** — nowsze źródło zaprzecza starszemu, ale stary fragment wygrywa na podobieństwie

Knowledge-Map RAG wyciąga strukturę przy ingeście — encje, koncepty, twierdzenia
(każde z proweniencją) i krawędzie — a potem odpowiada przez 5-etapowy pipeline
rozumowania. Każde zdanie w odpowiedzi da się dociągnąć do konkretnego twierdzenia.

![Naiwny RAG vs Knowledge-Map RAG — co jest zapisywane przy wgrywaniu i co czyta model odpowiadający](docs/naive-vs-knowledge-map.svg)

To są hipotezy. Następna sekcja pokazuje, jak wypadają w pomiarach.

## Czy to jest lepsze od naiwnego RAG? Wyniki pomiarów

Krótko: **nie we wszystkim.** Wyraźnie wygrywa przy zbieraniu faktów rozsianych po
wielu dokumentach i rzadziej powtarza podrzucone fałszywe twierdzenie; przy prostych
pytaniach o fakt jest na równi albo nieco gorzej; i jest 7–9× wolniejsze.

**Warunki.** 15 polskich artykułów wnętrzarskich (blog producenta drzwi; nie ma ich
w tym repo). Punktem odniesienia jest uczciwy naiwny RAG na tym samym tekście i tych
samych modelach: fragmenty po 800 znaków z zakładką 150, `text-embedding-3-small`,
top-5 po cosinusie, `gpt-4o-mini` z temperaturą 0 i poleceniem przyznania się, gdy
kontekst nie zawiera odpowiedzi. Odpowiedzi ocenia sędzia LLM (`gpt-4o-mini`) w skali
0–10. Pomiar z 2026-11-12.

| | Naiwny RAG | Knowledge-Map RAG |
|---|---|---|
| Proste pytania o fakt (15) — poprawność / użyteczność / wierność | **9,4** / **7,1** / **10,0** | 8,6 / 7,0 / 9,5 |
| Pytania wieloprzeskokowe (10) — te same trzy oceny | 8,2 / 5,9 / **9,6** | **8,3** / **6,9** / 9,3 |
| Pytania „wymień wszystkie…” (6) — ile oczekiwanych elementów padło | 4 / 29 | **12 / 29** |
| 4 podrzucone sprzeczności — odpowiedź podaje *tylko* fałszywą wersję | 3 / 4 | **1 / 4** |
| 4 podrzucone sprzeczności — odpowiedź mówi, że źródła się nie zgadzają | 0 / 4 | 0 / 4 |
| Czas odpowiedzi | **~1,8 s** | ~13–17 s |
| Wywołania LLM na pytanie | **1** | 3 (+ ekstrakcja przy wgrywaniu) |

Co te liczby pokazują, a czego nie:

- **Prawdziwa przewaga to zbieranie faktów.** Przy pytaniu „gdzie katalog poleca X?”
  naiwny RAG widzi 5 fragmentów, a mapa wiedzy zbiera wszystkie twierdzenia o X ze
  wszystkich artykułów, każde z podpisem źródła.
- **Sprzeczności są wykrywane, ale jeszcze nie tłumaczone.** Ingest znajduje podrzucone
  sprzeczności (5 zapisanych, 0 fałszywych alarmów na czystym korpusie) i zapisuje je
  jako krawędzie `contradicts`, a Knowledge-Map RAG zwykle nie powtarza fałszywej wersji — ale
  odpowiedź rzadko mówi wprost *„źródła się nie zgadzają”* (2 / 4 w jednej
  przebudowie grafu, 0 / 4 w tej).
- **Proste pytania tracą szczegóły.** Odpowiedź powstaje z wyekstrahowanych twierdzeń,
  nie z oryginalnego tekstu, więc szczegół pominięty przy ekstrakcji przepada.
- **Przebudowy się różnią.** Ponowna ekstrakcja tego samego korpusu przesuwała wynik
  prostych pytań między 8,6 a 9,6. Różnice poniżej ~1 punktu traktuj jako szum.
- **Małe próby, sędzia LLM.** 10–15 pytań na zestaw, oceniane przez model z tej samej
  rodziny, która odpowiada. Sędzia raz dał 10/10 odpowiedzi powtarzającej tylko
  fałszywą stronę sprzeczności, dlatego wiersze o pokryciu i sprzecznościach są
  policzone ręcznie.

Odtworzenie (wymaga klucza OpenAI; pełny przebieg to kilka centów):

```bash
cd backend
python scripts/run_gold_eval.py      --questions porta_multihop   # Knowledge-Map RAG
python scripts/run_naive_baseline.py --questions porta_multihop   # naiwny baseline
python scripts/build_conflict_vault.py                            # korpus + podrzucone sprzeczności
python scripts/run_gold_eval.py --vault wiki_data/bench_conflict --questions porta_conflict
```

Zestawy pytań są w `backend/tests/rag_evaluation/gold_questions.py`. Dotyczą korpusu
PORTA, więc przy własnych źródłach potrzebne są własne pytania.

## Architektura

```
  INGEST                            RETRIEVAL
  ──────                            ─────────
  Plik źródłowy                     Pytanie użytkownika
     │                                  │
  1. Parse       (deterministyczny) 1. Intent Parser     (LLM)
  2. Classify    (LLM)              2. Candidate Filter   (leksykalny + semantyczny)
  3. Resolve     (deterministyczny) 3. Selection          (LLM)
  4. Conflict Detect (LLM)          4. Context Assembly
  5. Save + Reindex                 5. Answer Generator   (LLM)
     │                                  │
  wiki_data/ (Markdown + JSONL)     QueryTrace (pełny ślad audytu)
```

Gdy retrieval nie jest pewny, przejmuje **agent fallback** z 10 narzędziami.

**Przechowywanie:** płaskie pliki — strony Markdown plus logi JSONL twierdzeń i
krawędzi. Bez bazy danych, bez usługi vector store. Przenośne, czytelne, diffowalne.

## Panele

| Panel | Co robi |
|---|---|
| **Ingest** | Podgląd, jak plik przechodzi przez 5-etapowy pipeline ingestu. Widok edukacyjny — pliki dodaje się w **Sources**. |
| **Sources** | Każde wgrane źródło z jego tagami, streszczeniem, kluczowymi wnioskami i wygenerowanymi pytaniami. Wgrywanie plików lub import z URL. |
| **Wiki Chat** | Zadajesz pytanie i widzisz pełny ślad retrievalu: intent, ocenionych kandydatów, selekcję LLM, złożony kontekst, cytowaną odpowiedź. |
| **Knowledge Map** | Graf encji i konceptów. Kliknij węzeł, żeby zobaczyć jego twierdzenia, krawędzie i źródła. |
| **Lint** | Kontrola integralności wiki — węzły-sieroty, brak proweniencji, sprzeczności, kolizje aliasów, nieaktualne opisy. Część z auto-poprawką. |
| **Metrics** | Zużycie tokenów w sesji i szacowany koszt. |
| **Tutorial** | Wbudowany przewodnik po architekturze plus interaktywne walkthroughs. |

## Stack

| Warstwa | Technologia |
|---|---|
| Backend | FastAPI · Python 3.10+ |
| Frontend | React 19 · TypeScript · Vite · Tailwind |
| LLM | OpenAI API (domyślnie `gpt-4o-mini` i `text-embedding-3-small`) |
| Przechowywanie | Płaskie pliki — Markdown + JSONL |

## Instalacja

### Wymagania

- Python 3.10+
- Node.js 18+
- Klucz API OpenAI

### 1. Środowisko backendu

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # potem wpisz OPENAI_API_KEY do .env
```

### 2. Zależności frontendu

```bash
cd frontend
npm install
```

### 3. Uruchom oba

```bash
./dev.sh        # macOS / Linux
.\dev.ps1       # Windows (PowerShell)
```

Uruchamia API na `http://localhost:8000` (Swagger pod `/docs`) i aplikację na
`http://localhost:5173`. Vite proxuje `/api` do backendu, więc nie ma nic więcej
do konfiguracji. Ctrl+C zatrzymuje oba.

Żeby uruchomić osobno:

```bash
cd backend  && uvicorn main:app --port 8000
cd frontend && npm run dev
```

> Na części konfiguracji Windows `uvicorn --reload` umiera po pierwszym przeładowaniu
> i serwuje stary kod. Jeśli to trafisz — odpalaj bez `--reload` i restartuj ręcznie.

## Wypróbuj bez wgrywania czegokolwiek

`wiki_data/default` startuje pusty. Żeby zobaczyć aplikację z gotowym grafem, wskaż
dołączony demo-korpus (3 artykuły z Wikipedii o RAG, bazach wektorowych i
word embeddings) — odkomentuj tę linię w `backend/.env`:

```
WIKI_DATA_DIR=wiki_data/.example
```

**Sources**, **Knowledge Map** i **Lint** działają bez klucza API. **Wiki Chat** i
**Ingest** wołają OpenAI, więc dalej potrzebują klucza. Zobacz
`backend/wiki_data/.example/README.md`.

Przykładowe pytania:

- *What problem with large language models does retrieval-augmented generation address?*
- *How do vector databases find similar records?*
- *How are word embeddings related to vector search?*

## Własne źródła

1. W **Sources** wrzuć pliki `.pdf`, `.docx`, `.txt` lub `.md`, albo zaimportuj z URL
2. Poczekaj, aż pipeline ingestu skończy
3. Zadawaj pytania w **Wiki Chat** i czytaj ślad
4. Eksploruj powiązania w **Knowledge Map**
5. Uruchamiaj **Lint** co kilka ingestów, żeby wyłapać sprzeczności i luki

Retrieval działa najlepiej przy konkretnych pytaniach faktograficznych („Kto założył
X?", „Czym A różni się od B?") nad kilkoma źródłami, które się wzajemnie uzupełniają.
Bardzo szerokie prompty („opowiedz mi wszystko") z założenia wypadają słabo.

## Układ projektu

```
backend/
├── api/                    routery FastAPI
├── models/                 modele Pydantic
├── services/
│   ├── ingest_pipeline.py  5-etapowy ingest
│   ├── retrieval/          5-etapowy retrieval + agent fallback
│   ├── lint/               kontrole integralności
│   ├── wiki_store.py       odczyt/zapis wiki_data/
│   └── wiki_index.py       regeneracja 00-Index
├── scripts/                skrypty eval + utrzymaniowe
├── tests/                  ~470 testów jednostkowych + integracyjnych
└── wiki_data/
    ├── default/            twoja baza wiedzy (git-ignored, startuje pusta)
    └── .example/           dołączony demo-korpus

frontend/src/
├── api/client.ts           typowany klient API
└── components/             jeden folder na panel
```

## Struktura danych wiki

```
wiki_data/<nazwa>/
├── raw/                    sparsowane kopie każdego źródła
└── wiki/
    ├── 00-Index/           auto-generowany główny indeks
    ├── 10-Concepts/        jeden plik Markdown na koncept
    ├── 20-Entities/        jeden plik Markdown na encję
    ├── 30-Sources/         strony metadanych źródeł
    ├── claims.jsonl        każde wyciągnięte twierdzenie
    ├── edges.jsonl         każda wyciągnięta relacja
    └── embeddings/         wektory twierdzeń do recallu semantycznego
```

## Testy

```bash
cd backend && python -m pytest -q     # ~500 testów jednostkowych + integracyjnych

cd frontend && npm run test:e2e       # smoke suite Playwright — uruchamia (lub reużywa)
                                      # serwery dev, backend na demo-korpusie, bez klucza API
```

## Licencja

MIT — zobacz [LICENSE](LICENSE). Demo-korpus w `backend/wiki_data/.example/` to
tekst z Wikipedii (CC BY-SA 4.0); zobacz jego `ATTRIBUTION.md`.
