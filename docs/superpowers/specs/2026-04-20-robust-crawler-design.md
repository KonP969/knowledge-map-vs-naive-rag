# Robust Blog Crawler — Design Spec
Date: 2026-04-20

## Problem

The current `web_crawler.py` fails on blogs like `measureschool.com/blog/` and `analyticsmania.com/blog/` due to:

1. **Bug**: `pass` instead of `continue` — every link is collected regardless of the filter condition
2. **Flawed URL filter**: assumes articles live under `/{listing_path}/{slug}`, but many blogs host articles at root level (e.g. `measureschool.com/gtm-tutorial/`)
3. **No early failure detection**: crawls all URLs before surfacing that content is inaccessible

## Scope

Improve `web_crawler.py` only. No new dependencies, no Playwright, no API changes.

---

## Design

### 1. URL Collection — Heuristic Filter

Replace the `startswith(listing_path)` filter with a domain-scoped heuristic:

**Accept a link if ALL of:**
- Same domain as `start_url`
- Path has 1–2 segments (e.g. `/slug` or `/blog/slug`)
- Last segment looks like a slug: matches `[a-z0-9][a-z0-9\-]{4,}` (min 5 chars, alphanumeric + hyphens)
- Not an obvious non-article path

**Reject if ANY of:**
- Path matches `/page/\d+`
- Segment is: `tag`, `category`, `author`, `wp-admin`, `feed`, `search`, `cart`, `shop`
- Extension is: `.pdf`, `.jpg`, `.png`, `.gif`, `.zip`, `.xml`
- URL is identical to `start_url`

This captures root-level articles (`/gtm-tutorial/`) and sub-path articles (`/blog/gtm-tutorial/`) equally.

### 2. Probe-First Strategy

Before crawling all URLs, probe the first 3 candidates:

```
collect URLs
  └─ probe first 3
       ├─ 0 successes → detect cause → yield error_fatal → stop
       └─ ≥1 success  → proceed with remaining URLs
```

**Failure cause detection** (checked in order against raw HTTP response):
| Signal | Message |
|---|---|
| Body contains `cf-ray`, `cloudflare`, `checking your browser` | "Strona używa ochrony Cloudflare — crawler nie obsługuje tej strony." |
| HTTP status 403 | "Dostęp zabroniony (403). Strona blokuje automatyczne pobieranie." |
| HTTP status 429 | "Strona ogranicza ruch (429). Spróbuj ponownie za kilka minut." |
| HTTP 200 but body empty / < 100 chars | "Strona wymaga JavaScript do renderowania treści." |
| Any other failure | "Nie udało się pobrać treści artykułów. Sprawdź URL lub spróbuj później." |

Probe requests use the same `trafilatura.fetch_url` — no new HTTP client needed. The raw downloaded string is inspected before passing to `trafilatura.extract`.

### 3. Pagination Guard

Add a duplicate-content check: if page N returns the same set of links as page N-1, stop paginating (avoids infinite loop on sites that return a 200 for non-existent `/page/999`).

### 4. Overall Flow

```
crawl_blog(base_url, max_articles)
  1. _get_urls_sync(base_url, max_articles)
       a. _get_urls_from_listing_sync  ← new heuristic filter + pagination guard
       b. fallback: _get_urls_from_sitemap_sync  (unchanged)
  2. Probe first 3 URLs
       → 0 success: detect cause, yield error_fatal, return
       → ≥1 success: continue
  3. Iterate remaining URLs
       → per-URL error: yield error (non-fatal, crawl continues)
```

---

## Files Changed

- `backend/services/web_crawler.py` — only file modified
- No schema changes, no new endpoints, no new dependencies

## Out of Scope

- Playwright / headless browser support
- Cloudflare bypass
- JS-rendered pages
- Retry with exponential backoff (not needed given scope)
