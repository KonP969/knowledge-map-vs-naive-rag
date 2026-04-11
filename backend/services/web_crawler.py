"""Web crawler service — listing-page-first, sitemap fallback."""
import re
import asyncio
from typing import AsyncGenerator, Optional, List
from urllib.parse import urljoin, urlparse


def _is_listing_url(url: str) -> bool:
    """Returns True if URL looks like a category/listing page (non-root path)."""
    path = urlparse(url).path.rstrip("/")
    return bool(path) and path != ""


def _get_urls_from_listing_sync(start_url: str, max_articles: int) -> List[str]:
    """
    Crawl a listing/category page and follow pagination to collect article URLs.
    Respects order as seen on the page (top to bottom, page 1 first).
    """
    from trafilatura import fetch_url
    from lxml import html

    parsed_start = urlparse(start_url)
    base_domain = f"{parsed_start.scheme}://{parsed_start.netloc}"
    listing_path = parsed_start.path.rstrip("/")

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
        for href in tree.xpath("//a/@href"):
            parsed = urlparse(href)
            # Must be same domain
            if parsed.netloc != parsed_start.netloc:
                continue
            # Must be "deeper" than listing path
            link_path = parsed.path.rstrip("/")
            if not link_path.startswith(listing_path + "/"):
                continue
            # Must have at least one more path segment
            suffix = link_path[len(listing_path):].strip("/")
            if not suffix or "/" in suffix.lstrip("/"):
                # skip sub-sub-paths and pagination paths
                pass
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean not in seen and clean != start_url:
                seen.add(clean)
                collected.append(clean)

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


def _fetch_and_extract_sync(url: str) -> Optional[dict]:
    import trafilatura
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
