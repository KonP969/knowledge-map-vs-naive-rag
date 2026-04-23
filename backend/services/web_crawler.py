"""Web crawler service — listing-page-first, sitemap fallback."""
import os
import re
import asyncio
from typing import AsyncGenerator, Optional, List, Tuple
from urllib.parse import urljoin, urlparse
import trafilatura
from trafilatura import fetch_url

_BLOCKED_SEGMENTS = frozenset({
    "tag", "category", "author", "wp-admin", "feed",
    "search", "cart", "shop", "page",
})
_BLOCKED_EXTENSIONS = frozenset({
    ".pdf", ".jpg", ".jpeg", ".png", ".gif",
    ".zip", ".xml", ".svg", ".webp",
})
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{3,}[a-z0-9]$")  # min 5 chars, no trailing hyphen


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


def _is_listing_url(url: str) -> bool:
    """Returns True if URL looks like a category/listing page (non-root path)."""
    path = urlparse(url).path.rstrip("/")
    return bool(path) and path != ""


def _get_urls_from_listing_sync(start_url: str, max_articles: int) -> List[str]:
    """
    Crawl a listing/category page and follow pagination to collect article URLs.
    Respects order as seen on the page (top to bottom, page 1 first).
    """
    from lxml import html

    parsed_start = urlparse(start_url)
    base_domain = f"{parsed_start.scheme}://{parsed_start.netloc}"

    collected: List[str] = []
    seen: set = set()
    page_url: Optional[str] = start_url
    page_num = 1

    while page_url and len(collected) < max_articles:
        downloaded = fetch_url(page_url)
        if not downloaded:
            break

        tree = html.fromstring(downloaded)
        tree.make_links_absolute(base_domain)

        # --- collect article links from this page ---
        count_before = len(collected)
        for href in tree.xpath("//a/@href"):
            clean = href.split("?")[0].split("#")[0].rstrip("/")
            if not clean.startswith("http"):
                continue
            if clean not in seen and clean != start_url.rstrip("/"):
                if _is_article_url(clean, parsed_start.netloc):
                    seen.add(clean)
                    collected.append(clean)

        # --- pagination guard: stop if no new URLs on this page ---
        if page_num > 1 and len(collected) == count_before:
            break

        # --- find next page ---
        # 1) <link rel="next"> (most reliable, used by WordPress etc.)
        rel_next = tree.xpath("//link[@rel='next']/@href")
        if not rel_next:
            rel_next = tree.xpath("//a[@rel='next']/@href")

        # 2) Common pagination patterns: /page/2, ?page=2, ?paged=2
        if not rel_next:
            next_page = page_num + 1
            candidates = [
                f"{start_url.rstrip('/')}/page/{next_page}/",
                f"{start_url.rstrip('/')}/page/{next_page}",
                f"{start_url}?page={next_page}",
                f"{start_url}?paged={next_page}",
                f"{start_url}&page={next_page}",
            ]
            # Also look for explicit next-page anchors in HTML
            next_anchors = tree.xpath(
                "//a[contains(@class,'next') or contains(@class,'Next') "
                "or contains(@aria-label,'next') or contains(@title,'Następna') "
                "or contains(@title,'Next') or contains(text(),'Następna') "
                "or contains(text(),'Next') or contains(text(),'›') or contains(text(),'»')]/@href"
            )
            if next_anchors:
                rel_next = [next_anchors[0]]
            else:
                # Try the /page/N pattern by fetching and checking if it differs
                rel_next = [candidates[0]]

        next_url = rel_next[0] if rel_next else None

        # Validate next URL — must be same domain and different from current
        if next_url:
            parsed_next = urlparse(next_url)
            if parsed_next.netloc and parsed_next.netloc != parsed_start.netloc:
                next_url = None
            if next_url == page_url:
                next_url = None

        page_url = next_url
        page_num += 1

        # Safety: don't crawl more than 20 listing pages
        if page_num > 20:
            break

    return collected[:max_articles]


def _get_urls_from_sitemap_sync(base_url: str, max_articles: int) -> List[str]:
    from trafilatura.sitemaps import sitemap_search
    urls = list(sitemap_search(base_url))
    if not urls:
        from trafilatura.spider import focused_crawler
        seen, _ = focused_crawler(
            base_url,
            max_seen_urls=max_articles * 3,
            max_known_urls=max_articles * 5,
        )
        urls = list(seen)
    return urls[:max_articles]


def _get_urls_sync(base_url: str, max_articles: int) -> List[str]:
    """Pick strategy: listing-page crawl for category URLs, sitemap for root domains."""
    if _is_listing_url(base_url):
        urls = _get_urls_from_listing_sync(base_url, max_articles)
        if urls:
            return urls
        # Fallback: maybe it was a root blog path — try sitemap
    return _get_urls_from_sitemap_sync(base_url, max_articles)


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


def _probe_articles(urls: List[str], n: int = 3) -> Tuple[bool, Optional[str]]:
    """
    Fetch first n URLs and attempt extraction.
    Returns (any_success: bool, last_raw: Optional[str]).
    last_raw is None when any_success is True.
    """
    last_raw: Optional[str] = None
    for url in urls[:n]:
        raw = trafilatura.fetch_url(url)
        last_raw = raw
        if raw:
            text = trafilatura.extract(
                raw,
                output_format="markdown",
                include_comments=False,
                include_tables=True,
                with_metadata=False,
            )
            if text and len(text.strip()) >= 100:
                return True, None
    return False, last_raw


def _fetch_and_extract_sync(url: str) -> Optional[dict]:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    text = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        with_metadata=False,
    )
    if not text or len(text.strip()) < 100:
        return None
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else url.rstrip("/").split("/")[-1]
    title = title[:120] or "article"
    return {"title": title, "text": text}


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
