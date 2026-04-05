"""Web crawler service using trafilatura — polite, sitemap-first."""
import re
import asyncio
from typing import AsyncGenerator


def _get_urls_sync(base_url: str, max_articles: int) -> list[str]:
    from trafilatura.sitemaps import sitemap_search
    urls = list(sitemap_search(base_url))
    if not urls:
        from trafilatura.spider import focused_crawler
        seen, _ = focused_crawler(base_url, max_seen_urls=max_articles * 3, max_known_urls=max_articles * 5)
        urls = list(seen)
    return urls[:max_articles]


def _fetch_and_extract_sync(url: str) -> dict | None:
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
    urls = await asyncio.to_thread(_get_urls_sync, base_url, max_articles)
    total = len(urls)

    if total == 0:
        yield {"type": "error_fatal", "message": "Nie znaleziono artykułów. Sprawdź URL lub czy strona ma sitemap.xml."}
        return

    yield {"type": "start", "total": total}

    for i, url in enumerate(urls):
        result = await asyncio.to_thread(_fetch_and_extract_sync, url)
        if result is None:
            yield {"type": "error", "current": i + 1, "total": total, "url": url}
        else:
            yield {"type": "article", "current": i + 1, "total": total, "url": url, **result}
        await asyncio.sleep(2.5)
