# Crawler quality + scrape UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make blog scraping pull real article bodies (not nav/hub/teaser pages), let the user file scraped sources into a new or existing folder, and raise the article-count cap to 100.

**Architecture:** Replace the DOM-link-order article discovery in `web_crawler.py` with a layered, standards-based discovery (sitemap → RSS feed → link-scrape) where every layer is passed through one path-prefix/same-domain filter. Thread an optional `folder` through the existing SSE crawl-ingest endpoint, assigning it to each ingested source via the existing `WikiStore.set_source_folder`. Frontend gets a folder `datalist` input and a 1–100 slider in the crawl form.

**Tech Stack:** Python 3.9, FastAPI, Pydantic v2, trafilatura (sitemaps/feeds/extract), lxml, pytest; React + TypeScript frontend.

**Spec:** `docs/superpowers/specs/2026-06-09-crawler-quality-scrape-ux-design.md`

**Backend test workflow:** always `cd backend && python -m pytest ...` (conftest/import paths are rooted at `backend/`).

---

## File Structure

- `backend/services/web_crawler.py` — **modify**: remove `_is_article_url` + `_collect_urls`; add `_filter_article_urls` (pure), `_scrape_listing_links`, `_fetch_sitemap_urls`, `_fetch_feed_urls`, `_discover_article_urls` (layered); point `crawl_url` at `_discover_article_urls`.
- `backend/api/crawl.py` — **modify**: `CrawlRequest.folder` + `max_articles` bound `le=100`; assign folder after each successful ingest.
- `backend/tests/services/test_web_crawler.py` — **create**: filter + layering tests (network mocked).
- `backend/tests/api/test_crawl_api.py` — **create**: folder threading + bound tests.
- `frontend/src/api/client.ts` — **modify**: `crawlAndIngestStream` gains a `folder` argument.
- `frontend/src/components/wiki/SourcesPanel.tsx` — **modify**: folder `datalist` input + 1–100 slider in the crawl form.

---

## Task 1: Pure article-URL filter

**Files:**
- Modify: `backend/services/web_crawler.py`
- Test: `backend/tests/services/test_web_crawler.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/services/test_web_crawler.py`:

```python
from services.web_crawler import _filter_article_urls


def test_filter_keeps_only_urls_under_listing_prefix():
    listing = "https://www.porta.com.pl/otworzsiena/wnetrza"
    candidates = [
        "https://www.porta.com.pl/otworzsiena/wnetrza/10-sposobow-na-nowoczesne-wnetrza",
        "https://www.porta.com.pl/otworzsiena/wnetrza/5-popularnych-stylow",
        "https://www.porta.com.pl/otworzsiena/wnetrza",          # the listing itself
        "https://www.porta.com.pl/otworzsiena/kontakt",          # sibling nav, not under prefix
        "https://www.porta.com.pl/otworzsiena",                  # hub, not under prefix
        "https://other.com/otworzsiena/wnetrza/x",               # different domain
    ]
    kept = _filter_article_urls(candidates, listing)
    assert kept == [
        "https://www.porta.com.pl/otworzsiena/wnetrza/10-sposobow-na-nowoczesne-wnetrza",
        "https://www.porta.com.pl/otworzsiena/wnetrza/5-popularnych-stylow",
    ]


def test_filter_excludes_blocked_segments_and_extensions():
    listing = "https://measureschool.com/blog"
    candidates = [
        "https://measureschool.com/blog/server-side-gtm-guide",
        "https://measureschool.com/blog/page/2",                 # blocked segment 'page'
        "https://measureschool.com/blog/diagram.png",            # blocked extension
        "https://measureschool.com/services",                    # not under /blog
    ]
    kept = _filter_article_urls(candidates, listing)
    assert kept == ["https://measureschool.com/blog/server-side-gtm-guide"]


def test_filter_dedupes_and_strips_query_fragment():
    listing = "https://b.com/blog"
    candidates = [
        "https://b.com/blog/post-one?utm=x",
        "https://b.com/blog/post-one#section",
        "https://b.com/blog/post-one/",
    ]
    assert _filter_article_urls(candidates, listing) == ["https://b.com/blog/post-one"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_web_crawler.py -v`
Expected: FAIL with `ImportError: cannot import name '_filter_article_urls'`.

- [ ] **Step 3: Add the filter helper**

In `backend/services/web_crawler.py`, keep the existing imports and the
`_BLOCKED_SEGMENTS`, `_BLOCKED_EXTENSIONS`, `_SLUG_RE` constants. Add this function
(place it after `_SLUG_RE`):

```python
def _filter_article_urls(candidates: list[str], listing_url: str) -> list[str]:
    """Keep only same-domain URLs strictly under the listing path prefix that look like
    articles (slug last segment, no blocked segment/extension). Dedupes, strips query/frag."""
    parsed_listing = urlparse(listing_url)
    base_netloc = parsed_listing.netloc
    listing_path = parsed_listing.path.rstrip("/")
    prefix = listing_path + "/"

    kept: list[str] = []
    seen: set[str] = set()
    for cand in candidates:
        clean = str(cand).split("?")[0].split("#")[0].rstrip("/")
        parsed = urlparse(clean)
        if parsed.netloc != base_netloc:
            continue
        path = parsed.path.rstrip("/")
        if not path or path == listing_path or not path.startswith(prefix):
            continue
        segments = [s for s in path.split("/") if s]
        if any(s in _BLOCKED_SEGMENTS for s in segments):
            continue
        _, ext = os.path.splitext(segments[-1])
        if ext.lower() in _BLOCKED_EXTENSIONS:
            continue
        if not _SLUG_RE.match(segments[-1]):
            continue
        if clean not in seen:
            seen.add(clean)
            kept.append(clean)
    return kept
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/services/test_web_crawler.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/web_crawler.py backend/tests/services/test_web_crawler.py
git commit -m "feat(crawler): path-prefix article-URL filter"
```

---

## Task 2: Layered article discovery (sitemap → feed → link-scrape)

**Files:**
- Modify: `backend/services/web_crawler.py`
- Test: `backend/tests/services/test_web_crawler.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/services/test_web_crawler.py`:

```python
import services.web_crawler as wc


def test_discovery_uses_sitemap_when_it_yields_two_or_more(monkeypatch):
    listing = "https://b.com/blog"
    monkeypatch.setattr(wc, "_fetch_sitemap_urls",
                        lambda u: ["https://b.com/blog/a", "https://b.com/blog/b"])
    monkeypatch.setattr(wc, "_fetch_feed_urls", lambda u: (_ for _ in ()).throw(AssertionError("feed should not run")))
    monkeypatch.setattr(wc, "_scrape_listing_links", lambda u: (_ for _ in ()).throw(AssertionError("scrape should not run")))
    out = wc._discover_article_urls(listing, max_articles=10)
    assert out == ["https://b.com/blog/a", "https://b.com/blog/b"]


def test_discovery_falls_back_to_feed_then_scrape(monkeypatch):
    listing = "https://b.com/blog"
    monkeypatch.setattr(wc, "_fetch_sitemap_urls", lambda u: ["https://b.com/blog"])      # 0 after filter
    monkeypatch.setattr(wc, "_fetch_feed_urls", lambda u: ["https://b.com/services"])     # 0 after filter
    monkeypatch.setattr(wc, "_scrape_listing_links",
                        lambda u: ["https://b.com/blog/x", "https://b.com/blog/y"])
    out = wc._discover_article_urls(listing, max_articles=10)
    assert out == ["https://b.com/blog/x", "https://b.com/blog/y"]


def test_discovery_caps_at_max_articles(monkeypatch):
    listing = "https://b.com/blog"
    monkeypatch.setattr(wc, "_fetch_sitemap_urls",
                        lambda u: [f"https://b.com/blog/post-{i}" for i in range(10)])
    out = wc._discover_article_urls(listing, max_articles=3)
    assert len(out) == 3


def test_discovery_layer_errors_are_non_fatal(monkeypatch):
    listing = "https://b.com/blog"
    monkeypatch.setattr(wc, "_fetch_sitemap_urls", lambda u: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(wc, "_fetch_feed_urls", lambda u: [])
    monkeypatch.setattr(wc, "_scrape_listing_links",
                        lambda u: ["https://b.com/blog/x", "https://b.com/blog/y"])
    out = wc._discover_article_urls(listing, max_articles=10)
    assert out == ["https://b.com/blog/x", "https://b.com/blog/y"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_web_crawler.py -k discovery -v`
Expected: FAIL with `AttributeError: module 'services.web_crawler' has no attribute '_discover_article_urls'`.

- [ ] **Step 3: Add discovery functions and the layer wrappers**

In `backend/services/web_crawler.py`, update the trafilatura import near the top:

```python
import trafilatura
from trafilatura import feeds as _tf_feeds
from trafilatura import sitemaps as _tf_sitemaps
```

Then **delete** the old `_is_article_url` and `_collect_urls` functions and add:

```python
def _fetch_sitemap_urls(listing_url: str) -> list[str]:
    return _tf_sitemaps.sitemap_search(listing_url) or []


def _fetch_feed_urls(listing_url: str) -> list[str]:
    return _tf_feeds.find_feed_urls(listing_url) or []


def _scrape_listing_links(listing_url: str) -> list[str]:
    """Absolute <a href> links from the listing page (raw, unfiltered)."""
    raw = trafilatura.fetch_url(listing_url)
    if not raw:
        return []
    try:
        tree = lxhtml.fromstring(raw.encode() if isinstance(raw, str) else raw)
    except Exception:
        return []
    parsed = urlparse(listing_url)
    out: list[str] = []
    for href in tree.xpath("//a/@href"):
        clean = str(href)
        if not clean.startswith("http"):
            if clean.startswith("/"):
                clean = f"{parsed.scheme}://{parsed.netloc}{clean}"
            else:
                continue
        out.append(clean)
    return out


def _safe_layer(fetch) -> list[str]:
    try:
        return fetch() or []
    except Exception:
        return []


def _discover_article_urls(listing_url: str, max_articles: int) -> list[str]:
    """Layered discovery: sitemap -> feed -> link-scrape. Each layer is filtered; the first
    layer yielding >=2 filtered articles wins, else the largest non-empty filtered set."""
    best: list[str] = []
    for fetch in (
        lambda: _fetch_sitemap_urls(listing_url),
        lambda: _fetch_feed_urls(listing_url),
        lambda: _scrape_listing_links(listing_url),
    ):
        filtered = _filter_article_urls(_safe_layer(fetch), listing_url)
        if len(filtered) >= 2:
            return filtered[:max_articles]
        if len(filtered) > len(best):
            best = filtered
    return best[:max_articles]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/services/test_web_crawler.py -v`
Expected: PASS (all 7 tests).

- [ ] **Step 5: Point `crawl_url` at the new discovery**

In `backend/services/web_crawler.py`, inside `crawl_url`, replace the line:

```python
    urls = _collect_urls(url, max_articles)
```

with:

```python
    urls = _discover_article_urls(url, max_articles)
```

(The rest of `crawl_url` — the single-page fallback, per-article extraction, the
`len(text.strip()) >= 100` guard and `time.sleep(0.5)` — is unchanged.)

- [ ] **Step 6: Run the full crawler test file**

Run: `cd backend && python -m pytest tests/services/test_web_crawler.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/services/web_crawler.py backend/tests/services/test_web_crawler.py
git commit -m "feat(crawler): layered sitemap/feed/link article discovery"
```

---

## Task 3: Crawl request — folder + max_articles=100

**Files:**
- Modify: `backend/api/crawl.py`
- Test: `backend/tests/api/test_crawl_api.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/api/test_crawl_api.py`:

```python
from unittest.mock import patch
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from main import app
from services.wiki_store import WikiStore
from models.wiki_models import Source
from models.ingest_models import IngestResult


@pytest.fixture
def client():
    return TestClient(app)


def _fake_ingest_factory(store):
    """Returns an ingest_source stand-in that writes a real Source so set_source_folder works."""
    def _fake_ingest(file_path, store):  # signature matches ingest_source(file_path=, store=)
        slug = "scraped-article"
        store.write_source(Source(
            id="src_900", title="Scraped", type="txt", raw_path="raw/x/parsed.md",
            ingested_at=datetime(2026, 6, 9), summary="s",
            key_takeaways=[], questions=[], tags=[],
        ), slug=slug)
        return IngestResult(
            source_id="src_900", slug=slug, status="ok",
            entities_created=0, entities_merged=0, concepts_created=0, concepts_merged=0,
            claims_added=0, edges_added=0, conflicts=[], duration_ms=1.0, llm_calls=0,
        )
    return _fake_ingest


def test_crawl_assigns_folder_to_scraped_source(client, tmp_path):
    store = WikiStore(root=tmp_path)
    fake_crawl = {"articles": [{"title": "A", "url": "http://x/a", "text": "body " * 50}], "error": None}
    with patch("api.crawl.crawl_url", return_value=fake_crawl), \
         patch("api.crawl._get_store", return_value=store), \
         patch("api.crawl.ingest_source", side_effect=_fake_ingest_factory(store)):
        resp = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 5, "folder": "Blog PORTA"})
        # consume the streamed body
        _ = resp.text
    assert resp.status_code == 200
    assert store.read_source("scraped-article").folder == "Blog PORTA"


def test_crawl_without_folder_leaves_source_unfiled(client, tmp_path):
    store = WikiStore(root=tmp_path)
    fake_crawl = {"articles": [{"title": "A", "url": "http://x/a", "text": "body " * 50}], "error": None}
    with patch("api.crawl.crawl_url", return_value=fake_crawl), \
         patch("api.crawl._get_store", return_value=store), \
         patch("api.crawl.ingest_source", side_effect=_fake_ingest_factory(store)):
        resp = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 5})
        _ = resp.text
    assert store.read_source("scraped-article").folder is None


def test_crawl_folder_assignment_failure_is_non_fatal(client, tmp_path):
    store = WikiStore(root=tmp_path)
    fake_crawl = {"articles": [{"title": "A", "url": "http://x/a", "text": "body " * 50}], "error": None}
    with patch("api.crawl.crawl_url", return_value=fake_crawl), \
         patch("api.crawl._get_store", return_value=store), \
         patch("api.crawl.ingest_source", side_effect=_fake_ingest_factory(store)), \
         patch.object(store, "set_source_folder", side_effect=RuntimeError("disk error")):
        resp = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 5, "folder": "Blog"})
        body = resp.text
    assert resp.status_code == 200
    assert '"status": "ok"' in body  # article still reported ok despite folder failure


def test_crawl_max_articles_accepts_100_rejects_101(client):
    with patch("api.crawl.crawl_url", return_value={"articles": [], "error": "stop"}):
        ok = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 100})
    assert ok.status_code == 200
    bad = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 101})
    assert bad.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_crawl_api.py -v`
Expected: FAIL — `test_crawl_assigns_folder_to_scraped_source` (folder is None, field ignored) and `test_crawl_max_articles_accepts_100_rejects_101` (100 rejected with 422 under the current `le=20`).

- [ ] **Step 3: Add folder + raise the bound + assign folder**

In `backend/api/crawl.py`, update imports and the request model:

```python
from typing import Iterator, Optional
```

```python
class CrawlRequest(BaseModel):
    url: str
    max_articles: int = Field(default=5, ge=1, le=100)
    folder: Optional[str] = None
```

In `_generate_crawl_events`, in the success branch (where `ingest_result.status != "error"`),
assign the folder right after computing `ingested += 1` and before the `article_done` yield:

```python
            else:
                ingested += 1
                if req.folder:
                    try:
                        store.set_source_folder(ingest_result.slug, req.folder)
                    except Exception:
                        pass  # non-fatal: source is ingested, just unfiled
                yield _sse({
                    "event": "article_done", "index": i,
                    "title": article["title"], "status": "ok",
                    "slug": ingest_result.slug,
                })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_crawl_api.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the backend suite (no regressions)**

Run: `cd backend && python -m pytest tests/ -q --ignore=tests/services/retrieval/test_retrieval_pipeline.py --ignore=tests/services/retrieval/test_answer_generator.py`
Expected: all pass (the two ignored files are pre-existing failures unrelated to this work).

- [ ] **Step 6: Commit**

```bash
git add backend/api/crawl.py backend/tests/api/test_crawl_api.py
git commit -m "feat(crawl): optional folder + max_articles up to 100"
```

---

## Task 4: Frontend client — folder argument

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add `folder` to `crawlAndIngestStream`**

In `frontend/src/api/client.ts`, change the `crawlAndIngestStream` signature and body. Replace:

```typescript
  crawlAndIngestStream: async (
    url: string,
    maxArticles: number,
    onEvent: (event: import("../types").CrawlSSEEvent) => void,
  ): Promise<void> => {
    const res = await fetch(`${BASE}/crawl/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, max_articles: maxArticles }),
    });
```

with:

```typescript
  crawlAndIngestStream: async (
    url: string,
    maxArticles: number,
    onEvent: (event: import("../types").CrawlSSEEvent) => void,
    folder?: string | null,
  ): Promise<void> => {
    const res = await fetch(`${BASE}/crawl/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, max_articles: maxArticles, folder: folder || null }),
    });
```

(The rest of the function — the SSE reader loop — is unchanged.)

- [ ] **Step 2: Typecheck (no new errors)**

Run: `cd frontend && npx tsc -b 2>&1 | grep -E "error TS" | wc -l`
Expected: `18` (the pre-existing baseline; this change adds none). If higher, fix the new error.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(crawl): pass folder through crawlAndIngestStream"
```

---

## Task 5: Frontend — folder input + 1–100 slider in the crawl form

**Files:**
- Modify: `frontend/src/components/wiki/SourcesPanel.tsx`

- [ ] **Step 1: Add crawl-folder state**

In `SourcesPanel.tsx`, next to the other crawl states (`crawlUrl`, `crawlMax`, …), add:

```typescript
  const [crawlFolder, setCrawlFolder] = useState("");
```

- [ ] **Step 2: Pass the folder into the crawl call**

In `handleCrawl`, change the `api.crawlAndIngestStream` call to pass the folder as the 4th arg:

```typescript
      await api.crawlAndIngestStream(crawlUrl.trim(), crawlMax, (evt) => {
        // ...existing event handler body unchanged...
      }, crawlFolder.trim() || null);
```

- [ ] **Step 3: Replace the max-articles number input with a 1–100 slider and add the folder input**

In the URL-import `<details>` block, replace the existing max-articles row:

```tsx
            <div className="flex items-center gap-2">
              <label className="text-xs text-muted-foreground shrink-0">Maks. artykułów:</label>
              <input
                type="number"
                min={1}
                max={20}
                value={crawlMax}
                onChange={(e) => setCrawlMax(Number(e.target.value))}
                className="w-16 text-xs border border-border rounded px-2 py-1 bg-background"
              />
            </div>
```

with:

```tsx
            <div className="flex items-center gap-2">
              <label className="text-xs text-muted-foreground shrink-0">Maks. artykułów:</label>
              <input
                type="range"
                min={1}
                max={100}
                value={crawlMax}
                onChange={(e) => setCrawlMax(Number(e.target.value))}
                className="flex-1 accent-primary"
              />
              <span className="text-xs font-medium w-7 text-right tabular-nums">{crawlMax}</span>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-muted-foreground shrink-0">Folder na wyniki:</label>
              <input
                list="crawl-folder-options"
                value={crawlFolder}
                onChange={(e) => setCrawlFolder(e.target.value)}
                placeholder="(opcjonalnie) nowy lub istniejący"
                className="flex-1 min-w-0 text-xs border border-border rounded px-2 py-1 bg-background focus:outline-none focus:ring-1 focus:ring-primary/40"
              />
              <datalist id="crawl-folder-options">
                {Array.from(new Set(sources.map((s) => s.folder).filter((f): f is string => !!f)))
                  .sort((a, b) => a.localeCompare(b))
                  .map((f) => <option key={f} value={f} />)}
              </datalist>
            </div>
```

- [ ] **Step 4: Typecheck (no new errors)**

Run: `cd frontend && npx tsc -b 2>&1 | grep -E "error TS" | wc -l`
Expected: `18` (pre-existing baseline). If higher, fix the new error.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/wiki/SourcesPanel.tsx
git commit -m "feat(sources): crawl folder input + 1-100 article slider"
```

---

## Task 6: Live validation against the two real blogs

**Files:** none (manual verification with servers running).

- [ ] **Step 1: Ensure servers are running**

Backend (reload) on :8001, frontend on :5174/:5175. (See `ux_round3_resume` memory for the
non-standard port setup; `frontend/.env.local` points `VITE_API_BASE` at :8001.)

- [ ] **Step 2: Probe discovery quality (no ingest) from the backend shell**

Run a throwaway python snippet from `backend/`:

```python
from services.web_crawler import _discover_article_urls
for u in ["https://www.porta.com.pl/otworzsiena/wnetrza", "https://measureschool.com/blog/"]:
    found = _discover_article_urls(u, max_articles=5)
    print(u, "->", len(found)); [print("  ", x) for x in found]
```

Expected: porta returns real article URLs under `/otworzsiena/wnetrza/<slug>` (NOT `/kontakt`,
the hub, or the listing). measureschool returns blog post URLs under `/blog/<slug>` via a
fallback layer — if it returns 0, note the cause (sitemap genuinely absent) for follow-up; do
not block the plan on measureschool.

- [ ] **Step 3: End-to-end scrape through the UI**

In the Sources panel → "Importuj z URL / bloga": paste the porta URL, set the slider to ~5,
type a folder name (e.g. `Blog PORTA`), run. Confirm: progress bar advances, articles ingest,
and the new folder chip + badges appear in the Sources list. Open one ingested source's raw
text and confirm it is an article body, not a list of titles.

- [ ] **Step 4: Clean up any throwaway probe file**

Remove any temporary script created in Step 2.

---

## Self-review notes

- Spec A (discovery): Tasks 1–2. Spec B (folder UX): Tasks 3–5. Spec C (slider/bound): Tasks 3, 5.
- Spec testing (mocked discovery, folder threading, bounds): Tasks 1–3. Live validation: Task 6.
- Names are consistent across tasks: `_filter_article_urls`, `_discover_article_urls`,
  `_fetch_sitemap_urls`, `_fetch_feed_urls`, `_scrape_listing_links`, `crawlAndIngestStream(..., folder?)`,
  `crawlFolder`.
- Out of scope (separate plans): corpus rebuild, gold-set evaluation.
