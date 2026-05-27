import os
import re
import time
from typing import Optional
from urllib.parse import urlparse

import lxml.html as lxhtml
import trafilatura

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


def _collect_urls(start_url: str, max_articles: int) -> list[str]:
    """Collect article URLs from blog listing page(s). Uses trafilatura.fetch_url."""
    parsed_start = urlparse(start_url)
    base_netloc = parsed_start.netloc
    seen: set[str] = set()
    collected: list[str] = []

    raw = trafilatura.fetch_url(start_url)
    if not raw:
        return []

    # Parse links from the page
    try:
        tree = lxhtml.fromstring(raw.encode() if isinstance(raw, str) else raw)
    except Exception:
        return []

    for href in tree.xpath("//a/@href"):
        clean = str(href).split("?")[0].split("#")[0].rstrip("/")
        if not clean.startswith("http"):
            # Make relative URL absolute
            if clean.startswith("/"):
                clean = f"{parsed_start.scheme}://{base_netloc}{clean}"
            else:
                continue
        clean = clean.rstrip("/")
        if clean not in seen and _is_article_url(clean, base_netloc):
            seen.add(clean)
            collected.append(clean)
            if len(collected) >= max_articles:
                break

    return collected


def _detect_failure_cause(raw: Optional[str]) -> str:
    """Return human-readable message why fetch failed."""
    if raw is None:
        return "Nie udało się nawiązać połączenia ze stroną. Sprawdź URL lub spróbuj później."
    lower = raw.lower()
    if any(m in lower for m in ("cf-ray", "cloudflare", "checking your browser", "just a moment")):
        return "Strona używa ochrony Cloudflare — crawler nie obsługuje tej strony."
    if len(raw.strip()) < 500:
        return "Strona wymaga JavaScript do renderowania treści."
    return "Nie udało się pobrać treści artykułów. Sprawdź URL lub spróbuj później."


def crawl_url(url: str, max_articles: int = 5) -> dict:
    """
    Crawl a blog URL and return extracted articles.
    Returns: {
        "articles": [{"url": str, "title": str, "text": str, "word_count": int}],
        "error": Optional[str]  # set if fatal error occurred
    }
    """
    parsed = urlparse(url)
    if not parsed.netloc:
        return {"articles": [], "error": "Nieprawidłowy URL."}

    # Probe first
    raw = trafilatura.fetch_url(url)
    if not raw:
        return {"articles": [], "error": "Nie udało się nawiązać połączenia ze stroną."}

    # Collect article URLs
    urls = _collect_urls(url, max_articles)
    if not urls:
        # Maybe the URL itself IS an article (single page)
        text = trafilatura.extract(raw, output_format="markdown", include_comments=False, include_tables=True)
        if text and len(text.strip()) >= 100:
            title = trafilatura.extract(raw, output_format="txt", include_comments=False) or url
            title = title.split("\n")[0][:100]
            return {"articles": [{"url": url, "title": title, "text": text, "word_count": len(text.split())}], "error": None}
        cause = _detect_failure_cause(raw)
        return {"articles": [], "error": cause}

    # Extract each article
    articles = []
    for article_url in urls[:max_articles]:
        time.sleep(0.5)  # polite delay
        raw_article = trafilatura.fetch_url(article_url)
        if not raw_article:
            continue
        text = trafilatura.extract(raw_article, output_format="markdown", include_comments=False, include_tables=True)
        if not text or len(text.strip()) < 100:
            continue
        # Extract title (first line of text or URL slug)
        title_raw = trafilatura.extract(raw_article, output_format="txt", include_comments=False)
        title = (title_raw or "").split("\n")[0].strip()[:100] or article_url.rstrip("/").split("/")[-1]
        articles.append({
            "url": article_url,
            "title": title,
            "text": text,
            "word_count": len(text.split()),
        })

    if not articles:
        return {"articles": [], "error": _detect_failure_cause(raw)}

    return {"articles": articles, "error": None}
