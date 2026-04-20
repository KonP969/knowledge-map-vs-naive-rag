# Robust Blog Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix URL-collection bugs and add probe-first failure detection in `web_crawler.py`.

**Architecture:** Add two pure helper functions (`_is_article_url`, `_detect_failure_cause`) and one orchestration helper (`_probe_articles`), then wire them into the existing `_get_urls_from_listing_sync` and `crawl_blog`. No new dependencies.

**Tech Stack:** Python 3.9, trafilatura, pytest, unittest.mock

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `.worktrees/feature/scaffolding/backend/services/web_crawler.py` | Modify | Main crawler — all logic changes |
| `.worktrees/feature/scaffolding/backend/tests/test_web_crawler.py` | Create | Unit tests for new helpers + integration |

---

## Task 1: Heuristic URL filter — `_is_article_url`

**Files:**
- Modify: `.worktrees/feature/scaffolding/backend/services/web_crawler.py`
- Create: `.worktrees/feature/scaffolding/backend/tests/test_web_crawler.py`

- [ ] **Step 1: Create test file with failing tests for `_is_article_url`**

Create `.worktrees/feature/scaffolding/backend/tests/__init__.py` (empty).

Create `.worktrees/feature/scaffolding/backend/tests/test_web_crawler.py`:

```python
import pytest
from services.web_crawler import _is_article_url

NETLOC = "example.com"

# --- URLs that should be accepted ---
@pytest.mark.parametrize("url", [
    "https://example.com/gtm-tutorial/",
    "https://example.com/gtm-tutorial",
    "https://example.com/blog/gtm-tutorial/",
    "https://example.com/post/analytics-guide",
    "https://example.com/how-to-use-google-analytics",
    "https://example.com/seo-tips-2024",
])
def test_is_article_url_accepts_articles(url):
    assert _is_article_url(url, NETLOC) is True


# --- URLs that should be rejected ---
@pytest.mark.parametrize("url,reason", [
    ("https://other.com/article/", "wrong domain"),
    ("https://example.com/", "root only"),
    ("https://example.com/page/2/", "pagination"),
    ("https://example.com/blog/page/3/", "pagination under blog"),
    ("https://example.com/tag/analytics/", "tag segment"),
    ("https://example.com/category/seo/", "category segment"),
    ("https://example.com/author/john/", "author segment"),
    ("https://example.com/wp-admin/", "admin segment"),
    ("https://example.com/feed/", "feed segment"),
    ("https://example.com/search/", "search segment"),
    ("https://example.com/cart/", "cart segment"),
    ("https://example.com/shop/", "shop segment"),
    ("https://example.com/file.pdf", "pdf extension"),
    ("https://example.com/image.jpg", "jpg extension"),
    ("https://example.com/sitemap.xml", "xml extension"),
    ("https://example.com/a/b/c/", "too deep — 3 segments"),
    ("https://example.com/ab/", "slug too short — under 5 chars"),
])
def test_is_article_url_rejects_non_articles(url, reason):
    assert _is_article_url(url, NETLOC) is False, f"Should reject: {reason}"
```

- [ ] **Step 2: Run tests — verify they FAIL**

```
cd .worktrees/feature/scaffolding/backend
.\.venv\Scripts\Activate.ps1
pytest tests/test_web_crawler.py::test_is_article_url_accepts_articles tests/test_web_crawler.py::test_is_article_url_rejects_non_articles -v
```

Expected: `ImportError` or `AttributeError` — `_is_article_url` doesn't exist yet.

- [ ] **Step 3: Implement `_is_article_url` in `web_crawler.py`**

Add after the existing imports at the top of `web_crawler.py` (after `from urllib.parse import ...`):

```python
import os

_BLOCKED_SEGMENTS = frozenset({
    "tag", "category", "author", "wp-admin", "feed",
    "search", "cart", "shop", "page",
})
_BLOCKED_EXTENSIONS = frozenset({
    ".pdf", ".jpg", ".jpeg", ".png", ".gif",
    ".zip", ".xml", ".svg", ".webp",
})
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{3,}$")  # min 5 chars total


def _is_article_url(url: str, base_netloc: str) -> bool:
    """True if URL looks like a blog article (heuristic)."""
    parsed = urlparse(url)
    if parsed.netloc != base_netloc:
        return False
    path = parsed.path.rstrip("/")
    if not path:
        return False
    segments = [s for s in path.split("/") if s]
    if not segments or len(segments) > 2:
        return False
    if any(s in _BLOCKED_SEGMENTS for s in segments):
        return False
    _, ext = os.path.splitext(segments[-1])
    if ext.lower() in _BLOCKED_EXTENSIONS:
        return False
    if not _SLUG_RE.match(segments[-1]):
        return False
    return True
```

- [ ] **Step 4: Run tests — verify they PASS**

```
pytest tests/test_web_crawler.py::test_is_article_url_accepts_articles tests/test_web_crawler.py::test_is_article_url_rejects_non_articles -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```
git add .worktrees/feature/scaffolding/backend/services/web_crawler.py .worktrees/feature/scaffolding/backend/tests/
git commit -m "feat: add _is_article_url heuristic filter"
```

---

## Task 2: Update listing crawler

Replace the old `startswith`-based filter with `_is_article_url` and add a no-new-URLs pagination guard.

**Files:**
- Modify: `.worktrees/feature/scaffolding/backend/services/web_crawler.py`
- Modify: `.worktrees/feature/scaffolding/backend/tests/test_web_crawler.py`

- [ ] **Step 1: Add failing tests for listing crawler**

Append to `tests/test_web_crawler.py`:

```python
from unittest.mock import patch
from services.web_crawler import _get_urls_from_listing_sync

LISTING_HTML_PAGE1 = b"""
<html><head><link rel="next" href="https://measureschool.com/blog/page/2/"/></head>
<body>
  <a href="https://measureschool.com/gtm-tutorial/">GTM Tutorial</a>
  <a href="https://measureschool.com/google-analytics-guide/">GA Guide</a>
  <a href="https://measureschool.com/blog/page/2/">Page 2</a>
  <a href="https://measureschool.com/tag/analytics/">Tag</a>
</body></html>
"""

LISTING_HTML_PAGE2 = b"""
<html><body>
  <a href="https://measureschool.com/conversion-tracking/">Conversion</a>
  <a href="https://measureschool.com/gtm-tutorial/">GTM Tutorial</a>
</body></html>
"""

LISTING_HTML_DUPE = b"""
<html><body>
  <a href="https://measureschool.com/gtm-tutorial/">GTM Tutorial</a>
</body></html>
"""


def test_listing_collects_root_level_articles():
    """Articles at root level (not under /blog/) are collected."""
    responses = [LISTING_HTML_PAGE1, LISTING_HTML_DUPE]

    def fake_fetch(url):
        return responses.pop(0).decode() if responses else None

    with patch("services.web_crawler.fetch_url", side_effect=fake_fetch):
        urls = _get_urls_from_listing_sync("https://measureschool.com/blog/", 10)

    assert "https://measureschool.com/gtm-tutorial/" in urls
    assert "https://measureschool.com/google-analytics-guide/" in urls


def test_listing_rejects_tag_and_pagination_links():
    """Tag pages and /page/N links are not collected."""
    responses = [LISTING_HTML_PAGE1, LISTING_HTML_DUPE]

    def fake_fetch(url):
        return responses.pop(0).decode() if responses else None

    with patch("services.web_crawler.fetch_url", side_effect=fake_fetch):
        urls = _get_urls_from_listing_sync("https://measureschool.com/blog/", 10)

    assert not any("/tag/" in u for u in urls)
    assert not any("/page/" in u for u in urls)


def test_listing_stops_when_no_new_urls():
    """Pagination stops when a page yields no new URLs (duplicate guard)."""
    call_count = {"n": 0}

    def fake_fetch(url):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return LISTING_HTML_PAGE1.decode()
        # Page 2 has only duplicates → no new URLs → should stop
        return LISTING_HTML_DUPE.decode()

    with patch("services.web_crawler.fetch_url", side_effect=fake_fetch):
        urls = _get_urls_from_listing_sync("https://measureschool.com/blog/", 10)

    # Should have fetched page 1 + page 2, then stopped (not page 3)
    assert call_count["n"] == 2
```

- [ ] **Step 2: Run tests — verify they FAIL**

```
pytest tests/test_web_crawler.py::test_listing_collects_root_level_articles tests/test_web_crawler.py::test_listing_rejects_tag_and_pagination_links tests/test_web_crawler.py::test_listing_stops_when_no_new_urls -v
```

Expected: FAIL (old filter rejects root-level articles).

- [ ] **Step 3: Rewrite the URL-collection inner loop in `_get_urls_from_listing_sync`**

Replace the block from `# --- collect article links from this page ---` through `seen.add(clean)` / `collected.append(clean)` with:

```python
        # --- collect article links from this page ---
        count_before = len(collected)
        for href in tree.xpath("//a/@href"):
            clean = href.split("?")[0].split("#")[0].rstrip("/")
            if not clean.startswith("http"):
                continue
            if clean not in seen and clean != start_url.rstrip("/"):
                parsed_href = urlparse(clean)
                if _is_article_url(clean, parsed_start.netloc):
                    seen.add(clean)
                    collected.append(clean)

        # --- pagination guard: stop if no new URLs on this page ---
        if page_num > 1 and len(collected) == count_before:
            break
```

- [ ] **Step 4: Run tests — verify they PASS**

```
pytest tests/test_web_crawler.py::test_listing_collects_root_level_articles tests/test_web_crawler.py::test_listing_rejects_tag_and_pagination_links tests/test_web_crawler.py::test_listing_stops_when_no_new_urls -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```
git add .worktrees/feature/scaffolding/backend/services/web_crawler.py .worktrees/feature/scaffolding/backend/tests/test_web_crawler.py
git commit -m "feat: replace url filter with heuristic, add pagination guard"
```

---

## Task 3: Failure cause detection

**Files:**
- Modify: `.worktrees/feature/scaffolding/backend/services/web_crawler.py`
- Modify: `.worktrees/feature/scaffolding/backend/tests/test_web_crawler.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_web_crawler.py`:

```python
from services.web_crawler import _detect_failure_cause, _probe_articles

def test_detect_cloudflare():
    raw = "<html>Just a moment... cf-ray: abc123 cloudflare</html>"
    msg = _detect_failure_cause(raw)
    assert "Cloudflare" in msg


def test_detect_js_required():
    raw = "<html><body></body></html>"  # very short
    msg = _detect_failure_cause(raw)
    assert "JavaScript" in msg


def test_detect_none_response():
    msg = _detect_failure_cause(None)
    assert "połączenia" in msg


def test_detect_generic_fallback():
    raw = "<html>" + "x" * 600 + "</html>"  # long enough, no CF markers
    msg = _detect_failure_cause(raw)
    assert "Nie udało się" in msg


def test_probe_returns_true_on_success():
    """Probe returns True when at least one article extracts successfully."""
    good_html = "<html><body><article>" + "word " * 200 + "</article></body></html>"

    with patch("services.web_crawler.trafilatura") as mock_traf:
        mock_traf.fetch_url.return_value = good_html
        mock_traf.extract.return_value = "# Title\n" + "word " * 100

        success, last_raw = _probe_articles(["https://example.com/article-one/"])

    assert success is True
    assert last_raw is None


def test_probe_returns_false_and_raw_on_failure():
    """Probe returns False and the last raw content when all articles fail."""
    with patch("services.web_crawler.trafilatura") as mock_traf:
        mock_traf.fetch_url.return_value = "<html>cf-ray cloudflare checking your browser</html>"
        mock_traf.extract.return_value = None

        success, last_raw = _probe_articles([
            "https://example.com/a/",
            "https://example.com/b/",
            "https://example.com/c/",
        ])

    assert success is False
    assert last_raw is not None
    assert "cloudflare" in last_raw.lower()
```

- [ ] **Step 2: Run tests — verify they FAIL**

```
pytest tests/test_web_crawler.py::test_detect_cloudflare tests/test_web_crawler.py::test_detect_js_required tests/test_web_crawler.py::test_detect_none_response tests/test_web_crawler.py::test_detect_generic_fallback tests/test_web_crawler.py::test_probe_returns_true_on_success tests/test_web_crawler.py::test_probe_returns_false_and_raw_on_failure -v
```

Expected: `ImportError` — functions not yet defined.

- [ ] **Step 3: Add `_detect_failure_cause` and `_probe_articles` to `web_crawler.py`**

Add before `_fetch_and_extract_sync`:

```python
_CF_MARKERS = ("cf-ray", "cloudflare", "checking your browser", "just a moment")
_JS_THRESHOLD = 500  # chars


def _detect_failure_cause(raw: Optional[str]) -> str:
    """Return a human-readable message explaining why content could not be fetched."""
    if raw is None:
        return "Nie udało się nawiązać połączenia ze stroną. Sprawdź URL lub spróbuj później."
    lower = raw.lower()
    if any(m in lower for m in _CF_MARKERS):
        return "Strona używa ochrony Cloudflare — crawler nie obsługuje tej strony."
    if len(raw.strip()) < _JS_THRESHOLD:
        return "Strona wymaga JavaScript do renderowania treści."
    return "Nie udało się pobrać treści artykułów. Sprawdź URL lub spróbuj później."


def _probe_articles(urls: List[str], n: int = 3) -> tuple:
    """
    Fetch first n URLs and attempt extraction.
    Returns (any_success: bool, last_raw: Optional[str]).
    last_raw is None when any_success is True.
    """
    import trafilatura as _traf
    last_raw: Optional[str] = None
    for url in urls[:n]:
        raw = _traf.fetch_url(url)
        last_raw = raw
        if raw:
            text = _traf.extract(
                raw,
                output_format="markdown",
                include_comments=False,
                include_tables=True,
                with_metadata=False,
            )
            if text and len(text.strip()) >= 100:
                return True, None
    return False, last_raw
```

Note: `_probe_articles` imports `trafilatura` locally so the mock in tests can patch `services.web_crawler.trafilatura`. Update `_fetch_and_extract_sync` the same way — replace `import trafilatura` at the top of that function with a module-level import. Add at the top of `web_crawler.py` (with other imports):

```python
import trafilatura
```

And remove the local `import trafilatura` from inside `_fetch_and_extract_sync`. Then update `_fetch_and_extract_sync` to use `trafilatura.fetch_url` and `trafilatura.extract` (already the case).

- [ ] **Step 4: Run tests — verify they PASS**

```
pytest tests/test_web_crawler.py::test_detect_cloudflare tests/test_web_crawler.py::test_detect_js_required tests/test_web_crawler.py::test_detect_none_response tests/test_web_crawler.py::test_detect_generic_fallback tests/test_web_crawler.py::test_probe_returns_true_on_success tests/test_web_crawler.py::test_probe_returns_false_and_raw_on_failure -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```
git add .worktrees/feature/scaffolding/backend/services/web_crawler.py .worktrees/feature/scaffolding/backend/tests/test_web_crawler.py
git commit -m "feat: add _detect_failure_cause and _probe_articles"
```

---

## Task 4: Wire probe into `crawl_blog`

**Files:**
- Modify: `.worktrees/feature/scaffolding/backend/services/web_crawler.py`
- Modify: `.worktrees/feature/scaffolding/backend/tests/test_web_crawler.py`

- [ ] **Step 1: Add failing integration test**

Append to `tests/test_web_crawler.py`:

```python
import asyncio
from services.web_crawler import crawl_blog


def test_crawl_blog_aborts_on_probe_failure():
    """crawl_blog yields error_fatal when all probe articles fail."""

    async def run():
        with patch("services.web_crawler._get_urls_sync", return_value=[
            "https://example.com/a/",
            "https://example.com/b/",
            "https://example.com/c/",
        ]):
            with patch("services.web_crawler._probe_articles", return_value=(False, "cf-ray cloudflare")):
                events = []
                async for event in crawl_blog("https://example.com/blog/", 10):
                    events.append(event)
                return events

    events = asyncio.run(run())
    assert len(events) == 1
    assert events[0]["type"] == "error_fatal"
    assert "Cloudflare" in events[0]["message"]


def test_crawl_blog_proceeds_when_probe_succeeds():
    """crawl_blog yields start event and articles when probe succeeds."""

    async def run():
        with patch("services.web_crawler._get_urls_sync", return_value=[
            "https://example.com/article-one/",
        ]):
            with patch("services.web_crawler._probe_articles", return_value=(True, None)):
                with patch("services.web_crawler._fetch_and_extract_sync",
                           return_value={"title": "Article One", "text": "# Article One\n" + "word " * 100}):
                    events = []
                    async for event in crawl_blog("https://example.com/blog/", 10):
                        events.append(event)
                    return events

    events = asyncio.run(run())
    types = [e["type"] for e in events]
    assert "start" in types
    assert "article" in types
    assert "error_fatal" not in types
```

- [ ] **Step 2: Run tests — verify they FAIL**

```
pytest tests/test_web_crawler.py::test_crawl_blog_aborts_on_probe_failure tests/test_web_crawler.py::test_crawl_blog_proceeds_when_probe_succeeds -v
```

Expected: FAIL — `crawl_blog` doesn't call `_probe_articles` yet.

- [ ] **Step 3: Add probe call to `crawl_blog`**

Replace the body of `crawl_blog` with:

```python
async def crawl_blog(base_url: str, max_articles: int) -> AsyncGenerator[dict, None]:
    """Async generator — yields progress dicts for SSE."""
    try:
        urls = await asyncio.to_thread(_get_urls_sync, base_url, max_articles)
    except Exception as exc:
        yield {"type": "error_fatal", "message": f"Błąd podczas wykrywania URL-i: {exc}"}
        return

    if not urls:
        yield {
            "type": "error_fatal",
            "message": "Nie znaleziono artykułów. Sprawdź URL lub czy strona ma sitemap.xml.",
        }
        return

    any_success, last_raw = await asyncio.to_thread(_probe_articles, urls)
    if not any_success:
        cause = _detect_failure_cause(last_raw)
        yield {"type": "error_fatal", "message": cause}
        return

    yield {"type": "start", "total": len(urls)}

    for i, url in enumerate(urls):
        try:
            result = await asyncio.to_thread(_fetch_and_extract_sync, url)
        except Exception:
            result = None
        if result is None:
            yield {"type": "error", "current": i + 1, "total": len(urls), "url": url}
        else:
            yield {"type": "article", "current": i + 1, "total": len(urls), "url": url, **result}
        await asyncio.sleep(1.0)
```

- [ ] **Step 4: Run ALL tests — verify they PASS**

```
pytest tests/test_web_crawler.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```
git add .worktrees/feature/scaffolding/backend/services/web_crawler.py .worktrees/feature/scaffolding/backend/tests/test_web_crawler.py
git commit -m "feat: wire probe-first strategy into crawl_blog"
```

---

## Done

All changes are in `web_crawler.py` and `tests/test_web_crawler.py` only. No schema, API, or dependency changes.

Manual smoke test after implementation:
1. Start backend: `uvicorn main:app --reload --port 8000`
2. Start frontend: `npm run dev`
3. Open http://localhost:5173 → Documents → From URL
4. Enter `https://measureschool.com/blog/` → verify articles are collected
5. Enter `https://www.analyticsmania.com/blog/` → verify articles are collected
6. Enter a Cloudflare-protected URL → verify clear error message appears in UI
