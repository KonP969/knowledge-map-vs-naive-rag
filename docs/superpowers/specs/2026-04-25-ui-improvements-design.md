# UI Improvements — Design Spec
**Data:** 2026-04-25  
**Sekcje:** Documents · Chunking Lab · Embeddings · Tutorial

---

## 1. Documents

### 1a. Wyszukiwarka
- Pole `<input>` z ikoną Search umieszczone nad listą dokumentów (poniżej filtra folderów).
- Filtrowanie lokalne (bez backendu): działa na `doc.name.toLowerCase().includes(query)`.
- Stan: `searchQuery: string` w `DocumentManager`.
- Przefiltrowana lista trafia do `DocumentList` jako prop `documents`.

### 1b. Filtr po folderze
- Umieszczony między sekcją upload/crawl a listą dokumentów.
- Renderuje się jako rząd chipów (przycisków): "Wszystkie" | "Bez folderu" | po jednym na każdy folder.
- Stan: `activeFolderId: string | null | "all"` — wartość `"all"` oznacza brak filtra.
- Foldery pobierane w `DocumentManager` przy montowaniu (`api.getFolders()`).
- Obydwa filtry (folder + wyszukiwarka) działają razem — lista przechodzi przez oba filtry przed renderem.

### 1c. Modal przypisania folderu po uploadzie / crawlu
- Nowy komponent: `FolderAssignModal` (plik: `documents/FolderAssignModal.tsx`).
- Props: `docs: DocumentMeta[]`, `folders: Folder[]`, `onAssign(folderId: string | null): void`, `onSkip(): void`, `onCreate(name: string): Promise<Folder>`.
- Treść modala: nagłówek "Przypisz do folderu?", dropdown z istniejącymi folderami + opcja "— Bez folderu —", przycisk "Nowy folder" (inline input do wpisania nazwy), przyciski "Potwierdź" i "Pomiń".
- **Upload:** modal pojawia się po rozwiązaniu obietnicy `api.uploadDocument`. Przy potwierdzeniu wywołuje `api.assignDocumentToFolder(doc.id, folderId)`.
- **Crawl:** modal pojawia się po zdarzeniu `done`. Jeśli dodano > 1 artykuł, modal informuje "Przypisz wszystkie X artykułów do folderu?". Wywołuje `api.assignDocumentToFolder` dla każdego z `addedDocsRef.current`.
- Po pominięciu lub potwierdzeniu dokument(y) trafiają do listy bez zmian widoczności.

### 1d. Kaskadowe usuwanie
- `DeleteConfirmModal` przeniesiony do `components/shared/DeleteConfirmModal.tsx` (jest już w `chunks/`, kopiujemy interfejs).
- `DocumentList` — kliknięcie Trash2 wywołuje `onDeleteRequest(doc)` zamiast `onDelete(id)` (request otwiera modal).
- Handler w `DocumentManager.handleDeleteConfirm`:
  1. `api.deleteChunks(id)` — ignoruje błąd 404 (chunków może nie być)
  2. `api.deleteEmbeddingsByDocument(id)` — ignoruje błąd 404
  3. `api.deleteDocument(id)`
  4. Aktualizacja stanu (`documents`, `selected`).
- Modal pokazuje: nazwę dokumentu + ostrzeżenie "Usuwa też chunki i embeddingi".

---

## 2. Chunking Lab

### Układ
- Lewy panel (`w-72`, bez zmian): `StrategySelector` + ustawienia (`chunk_size`, `overlap`) + żaden dokument nie jest domyślnie wybrany przy montowaniu.
- Prawy panel (`flex-1`): dwa taby — "Kolejka" i "Przeglądaj".

### Tab "Kolejka" (domyślny)
- Lista dokumentów bez chunków (`chunkCounts[doc.id] === undefined || chunkCounts[doc.id] === 0`).
- Każdy wiersz: nazwa dokumentu + przycisk "Chunkuj" (wywołuje `api.generateChunks` z aktualnym `chunkReq` dla tego `doc.id`).
- Po sukcesie dokument znika z kolejki (aktualizacja `chunkCounts`) i pojawia się komunikat inline.
- Przycisk "Chunkuj całą kolejkę" u góry — iteruje przez wszystkie w kolejce sekwencyjnie z progress barem (logika analogiczna do obecnego `generateAll`).
- Jeśli kolejka pusta: komunikat "Wszystkie dokumenty mają chunki."

### Tab "Przeglądaj"
- Picker (dropdown lub lista) z dokumentami posiadającymi chunki (`chunkCounts[doc.id] > 0`).
- Poniżej: `ChunkViewer` dla wybranego dokumentu.
- Przycisk "Usuń chunki" dla wybranego dokumentu (z potwierdzeniem via `DeleteConfirmModal`).
- Jeśli brak: komunikat "Brak chunków. Przejdź do zakładki Kolejka."

### Usunięcie auto-selectu
- `useEffect` do ładowania danych przy montowaniu nie ustawia domyślnie `selectedDocId` — zaczyna się od `""`.

---

## 3. Embeddings

### Układ
- Kontener: `p-6 h-full flex flex-col gap-4` — spójny z innymi panelami.
- Nagłówek z tytułem + dwa taby: "Do wygenerowania" | "Wygenerowane".

### Tab "Do wygenerowania" (domyślny)
- Lista kart (styl `DocumentList`) dla dokumentów BEZ embeddingów.
- Każda karta: nazwa, liczba chunków (z `chunkCounts` — osobny fetch lub reuse `embeddingStatus`), przycisk "Embed".
- Przycisk "Wygeneruj wszystkie" nad listą — zaznacza wszystkie i startuje sekwencyjne generowanie z progress barem.
- Progress i błędy: jak obecna implementacja (inline pod przyciskiem).
- Jeśli wszystkie wygenerowane: komunikat "Brak dokumentów do osadzenia."

### Tab "Wygenerowane"
- Lista kart dla dokumentów Z embeddingami: nazwa + liczba chunków + przycisk "Usuń embeddingi".
- Poniżej: `ScatterPlot` + info o cosine similarity (przeniesione z obecnego layoutu).
- Logika `selectedA` / `selectedB` bez zmian.

### Styl
- Zastąpienie tabeli (`<table>`) kartami (`div.border.rounded-lg`) we wszystkich listach.
- Usunięcie wszelkich hardcoded `bg-gray-*`, `text-gray-*` — zamiana na tokeny projektu (`bg-muted`, `text-muted-foreground`, `border-border`, etc.).
- Dotyczy też `FolderPanel.tsx` jeśli będzie używany gdziekolwiek.

---

## 4. Tutorial

### Część 2: Pełny pipeline RAG — aktualizacje

**PipelineStep Documents:**
- Dodać punkt o wyszukiwarce i filtrze po folderach.
- Dodać punkt o oknie przypisania folderu po uploadzie/crawlu.
- Zaktualizować punkt o usuwaniu: "Kliknięcie kosza usuwa dokument razem z jego chunkami i embeddingami."

**PipelineStep Chunking Lab:**
- Przeformułować opis na nowe dwa taby: zakładka "Kolejka" (dokumenty bez chunków) i "Przeglądaj" (podgląd chunków).
- Usunąć wzmianki o auto-selekcji pierwszego dokumentu.

**PipelineStep Embeddings:**
- Opisać dwa taby: "Do wygenerowania" i "Wygenerowane".
- Usunąć ostrzeżenie o "nie klikaj Generate dwa razy" — UI samo blokuje dokumenty z istniejącymi embeddingami.
- Scatter plot i cosine similarity opisać w zakładce "Wygenerowane".

**Część 3: Troubleshooting:**
- Aktualizacja wiersza "Scatter plot pusty" → kieruje do zakładki "Wygenerowane" w sekcji Embeddings.
- Nowy wiersz: "Chcę usunąć dokument" → "Kliknij ikonę kosza — zostaniesz poproszony o potwierdzenie, po którym usunięte zostaną też chunki i embeddingi."

---

## Pliki do utworzenia / modyfikacji

| Plik | Akcja |
|------|-------|
| `components/shared/DeleteConfirmModal.tsx` | Nowy (wyekstrahowany z `chunks/`) |
| `components/documents/FolderAssignModal.tsx` | Nowy |
| `components/documents/DocumentManager.tsx` | Modyfikacja — search, folder filter, kaskadowy delete, integracja modali |
| `components/documents/DocumentList.tsx` | Modyfikacja — `onDeleteRequest` zamiast `onDelete` |
| `components/documents/UploadZone.tsx` | Modyfikacja — callback z `doc` po uploadzie, trigger modal |
| `components/documents/CrawlPanel.tsx` | Modyfikacja — trigger modal po `done` |
| `components/chunks/ChunkingLab.tsx` | Modyfikacja — nowy layout z tabami, usunięcie auto-select |
| `components/chunks/DeleteConfirmModal.tsx` | Bez zmian (lub import z shared) |
| `components/embeddings/EmbeddingExplorer.tsx` | Modyfikacja — taby, styl kart |
| `components/tutorial/TutorialPanel.tsx` | Modyfikacja — nowe opisy kroków |
