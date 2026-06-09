# Spec — Crawler quality + scrape UX (Sub-project 1)

**Date:** 2026-06-09
**Status:** Approved design, pending implementation plan
**Context:** Part of the "increase source quality" effort. Source corpus quality is the
root cause of poor RAG answers (garbage-in → garbage-out). This sub-project fixes blog
scraping so the corpus can be rebuilt with real article content.

## Problem

Trial scrapes of two real blogs proved the crawler's **article discovery** is broken:

- `https://www.porta.com.pl/otworzsiena/wnetrza` → collected `/otworzsiena/kontakt`,
  `/otworzsiena` (hub), `/otworzsiena/wnetrza` (the listing page itself). Extracted
  "content" was lists of article *titles* (teasers), not article bodies.
- `https://measureschool.com/blog/` → collected `/services`, `/services/...` (marketing
  pages), not blog posts.

Root cause: `web_crawler._collect_urls` takes the first N `<a href>` links in DOM order
that match a loose slug regex, so menu / nav / footer links win over real articles, and
`_is_article_url` cannot distinguish an article from a nav page.

Evidence that a fix is reachable: `trafilatura.sitemaps.sitemap_search` returns **149 real
article URLs** for the porta blog (all under `/otworzsiena/wnetrza/<descriptive-slug>`).
For measureschool it returns only 1 (sitemap not exposed at that path), so a fallback is
required.

## Scope

In scope (Sub-project 1):
- **A. Crawler article discovery** — robust, standards-based.
- **B. Folder-on-scrape UX** — assign scraped sources to a new or existing folder.
- **C. Article-count slider** to ~100.

Out of scope (later sub-projects, separate specs):
- **Sub-project 2** — corpus rebuild (reset, ingest manual catalog fragments, run the
  fixed scrape into folders).
- **Sub-project 3** — lightweight gold-set evaluation tool (`/api/retrieval/query` runner +
  hand-written gold questions + reuse of `tests/rag_evaluation/evaluator.py`).

## A. Crawler article discovery

Layered discovery in `services/web_crawler.py`, replacing `_collect_urls`:

1. **Sitemap first** — `trafilatura.sitemaps.sitemap_search(listing_url)`.
2. **Feed fallback** — try `trafilatura.feeds.find_feed_urls(listing_url)`.
3. **Link-scrape fallback** — scrape `<a href>` links from the listing page (current
   behaviour).

Each layer's output is passed through the robustness filter below; **the count compared
against the "fewer than 2" threshold is the number of URLs that survive the filter**, not
the raw count. Layers run in order and stop at the first that yields ≥2 filtered articles
(porta: sitemap gives ~148 → used; measureschool: sitemap gives 0 filtered → feed → link
fallback). If every layer yields <2, the largest non-empty filtered set is used.

**Robustness rule (applied to every discovery path):** keep a URL only if all hold:
- same registrable domain as the listing URL;
- its path is **strictly under the listing path prefix** (e.g. listing `/otworzsiena/wnetrza`
  → keep `/otworzsiena/wnetrza/<slug>`, drop `/otworzsiena`, `/otworzsiena/kontakt`,
  `/services/...`);
- it is not the listing page itself;
- no blocked path segment (existing `_BLOCKED_SEGMENTS`) and no blocked extension.

`max_articles` is applied **after** discovery (cap the candidate list). Article bodies are
still extracted with `trafilatura.extract(..., output_format="markdown")`, and the existing
thin-content guard (`len(text.strip()) >= 100`) and per-article `time.sleep(0.5)` politeness
are kept. The single-page-is-an-article fallback (when discovery yields nothing) is retained.

**Edge cases:** listing URL with a trailing slash; listing at domain root (prefix = "/",
which then relies on blocked-segments + slug rules); sitemap entries on a different
subdomain (dropped by the same-domain check).

## B. Folder-on-scrape UX

The folders feature (`Source.folder`, `set_source_folder`, `POST /api/wiki/sources/folder`)
already exists. Thread an optional folder through the crawl:

- **Backend:** `CrawlRequest` gains `folder: Optional[str] = None`. In
  `_generate_crawl_events`, after a successful `ingest_source`, call
  `store.set_source_folder(ingest_result.slug, req.folder)` when `folder` is set. Empty/None
  → no folder (current behaviour).
- **Frontend (`SourcesPanel` crawl form):** add a **"Folder na wyniki"** input backed by a
  `<datalist>` of existing folder names (derived from loaded sources, same as the #2 filter
  chips). The user can type a **new** name or pick an **existing** one — a single control
  covers "new vs existing folder". Its value is passed as `folder` in the crawl request.
- **Client:** `crawlAndIngestStream` gains a `folder` argument included in the POST body.

Data flow: crawl form (folder) → POST `/api/crawl/ingest` {url, max_articles, folder} →
per article: ingest → `set_source_folder(slug, folder)` → SSE `article_done` (unchanged
shape) → on completion the Sources list refresh shows the new folder chip + badges.

## C. Article-count slider

- **Backend:** `CrawlRequest.max_articles` bound `le=20` → `le=100`.
- **Frontend:** the max-articles control becomes a slider (range 1–100) with the numeric
  value shown; the existing SSE progress bar already scales to any N.

## Error handling

- Discovery returning nothing after all fallbacks → existing `fatal_error` SSE with the
  human-readable cause from `_detect_failure_cause`.
- Folder assignment failure for one article must not abort the stream: wrap
  `set_source_folder` so a failure is non-fatal (the source is still ingested; it simply
  lands without a folder). The article is still reported `ok`.
- Sitemap/feed network errors are caught and fall through to the next discovery layer.

## Testing

Backend (TDD, deterministic — network mocked):
- Discovery filter: given a candidate URL list + listing URL, only path-prefix /
  same-domain / non-listing / non-blocked URLs survive (covers porta-style nav, measure
  `/services`, cross-subdomain).
- Layering: sitemap returns ≥2 → used directly; sitemap <2 → feed tried; both empty →
  link-scrape fallback. (Mock `sitemap_search` / `find_feed_urls` / `fetch_url`.)
- `max_articles` caps the discovered list.
- Crawl folder threading: `CrawlRequest` accepts `folder`; after ingest each created
  source has `folder` set; `folder=None` leaves it unset; a `set_source_folder` error is
  non-fatal and the article still reports `ok`.
- `max_articles` accepts 100 and rejects >100.

Live validation (manual, before merge): run the real crawl against both blogs — porta must
yield real article bodies (not title lists); measureschool must yield blog posts via the
fallback (or be diagnosed if its sitemap is genuinely absent).

Frontend: verified via the running app (Playwright driver) — slider to 100, folder input
with datalist, scrape assigns results to the chosen folder (chip + badges appear).

## Components touched

- `backend/services/web_crawler.py` — discovery rewrite (`_collect_urls` → layered +
  path-prefix filter helper).
- `backend/api/crawl.py` — `CrawlRequest.folder`, `max_articles` bound, folder assignment.
- `backend/tests/services/test_web_crawler.py` (+ `tests/api/test_crawl_api.py` if present)
  — discovery + folder tests.
- `frontend/src/api/client.ts` — `crawlAndIngestStream(url, max, onEvent, folder?)`.
- `frontend/src/components/wiki/SourcesPanel.tsx` — folder input + slider in the crawl form.
