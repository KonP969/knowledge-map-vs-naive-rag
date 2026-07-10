import os
import re
import time
from typing import Optional
from urllib.parse import urlparse

import lxml.html as lxhtml
import trafilatura
from trafilatura import feeds as _tf_feeds
from trafilatura import sitemaps as _tf_sitemaps

_BLOCKED_SEGMENTS = frozenset({
    "tag", "tags", "category", "author", "wp-admin", "feed", "atom", "rss",
    "search", "cart", "shop", "page", "about",
})
_BLOCKED_EXTENSIONS = frozenset({
    ".pdf", ".jpg", ".jpeg", ".png", ".gif",
    ".zip", ".xml", ".svg", ".webp",
})
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{3,}$")  # min 5 chars total
# Relaxed article slug: multi-word hyphenated (e.g. 'ga4-regex-tutorial'). Distinguishes
# real posts from single-word nav pages ('services', 'about') when not prefix-gated.
_ARTICLE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")


def _filter_article_urls(
    candidates: list[str],
    listing_url: str,
    *,
    require_prefix: bool = True,
    slug_re: re.Pattern = _SLUG_RE,
    root_only: bool = False,
) -> list[str]:
    """Keep only same-domain URLs that look like articles (slug last segment, no blocked
    segment/extension). Dedupes, strips query/frag.

    With require_prefix (default) the path must sit under the listing path — the strict
    pass for well-structured blogs. With require_prefix=False the prefix rule is dropped
    (relaxed fallback for hub pages that link to root-level posts); pair it with the
    stricter _ARTICLE_SLUG_RE and root_only=True so section subpages (/services/x) and
    nav links don't leak in."""
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
        if not path or path == listing_path:
            continue
        if require_prefix and not path.startswith(prefix):
            continue
        segments = [s for s in path.split("/") if s]
        if root_only and len(segments) != 1:
            continue
        if any(s in _BLOCKED_SEGMENTS for s in segments):
            continue
        _, ext = os.path.splitext(segments[-1])
        if ext.lower() in _BLOCKED_EXTENSIONS:
            continue
        if not slug_re.match(segments[-1]):
            continue
        if clean not in seen:
            seen.add(clean)
            kept.append(clean)
    return kept


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
    """Discover article URLs newest-first.

    A blog listing page lists its articles in display order (newest first), so it is the
    primary, ordered source. The sitemap/feed (complete but unordered) only supplement the
    listing when it yields fewer than requested, or stand in as a fallback when the listing
    has no usable links (e.g. JS-rendered pages). Listing order is always preserved first."""
    listing_links = _safe_layer(lambda: _scrape_listing_links(listing_url))
    ordered = _filter_article_urls(listing_links, listing_url)
    if len(ordered) >= max_articles:
        return ordered[:max_articles]

    supplement: list[str] = []
    for fetch in (
        lambda: _fetch_sitemap_urls(listing_url),
        lambda: _fetch_feed_urls(listing_url),
    ):
        supplement = _filter_article_urls(_safe_layer(fetch), listing_url)
        if supplement:
            break

    seen = set(ordered)
    combined = ordered + [u for u in supplement if u not in seen]
    if combined:
        return combined[:max_articles]

    # Nothing under the listing prefix and no sitemap/feed: this is likely a hub page
    # (e.g. /blog) that links out to posts living at the domain root. Relaxed pass over
    # the listing links, gated by the multi-word slug rule to keep out nav pages.
    relaxed = _filter_article_urls(
        listing_links, listing_url,
        require_prefix=False, slug_re=_ARTICLE_SLUG_RE, root_only=True,
    )
    return relaxed[:max_articles]


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


def _extract_title(raw: str, url: str) -> str:
    """Best article title: page <title>/H1 metadata first, then the first body line,
    then the URL slug. First-line extraction alone mislabels articles that open with an
    intro sentence (their real title lives in the page metadata, not the body)."""
    try:
        meta = trafilatura.extract_metadata(raw)
    except Exception:
        meta = None
    if meta is not None and getattr(meta, "title", None):
        return meta.title.strip()[:100]

    body = trafilatura.extract(raw, output_format="txt", include_comments=False) or ""
    first_line = body.split("\n")[0].strip()[:100]
    if first_line:
        return first_line

    return url.rstrip("/").split("/")[-1]


def _extract_page_as_article(url: str, raw: str) -> Optional[dict]:
    """Extract an already-fetched page as a single article, or None if too thin."""
    text = trafilatura.extract(raw, output_format="markdown", include_comments=False, include_tables=True)
    if not text or len(text.strip()) < 100:
        return None
    return {"url": url, "title": _extract_title(raw, url), "text": text, "word_count": len(text.split())}


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
        return {"articles": [], "discovered": 0, "error": "Nieprawidłowy URL."}

    # Probe first
    raw = trafilatura.fetch_url(url)
    if not raw:
        return {"articles": [], "discovered": 0, "error": "Nie udało się nawiązać połączenia ze stroną."}

    # Collect article URLs
    urls = _discover_article_urls(url, max_articles)
    if not urls:
        # Maybe the URL itself IS an article (single page)
        single = _extract_page_as_article(url, raw)
        if single:
            return {"articles": [single], "discovered": 1, "error": None}
        cause = _detect_failure_cause(raw)
        return {"articles": [], "discovered": 0, "error": cause}

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
        articles.append({
            "url": article_url,
            "title": _extract_title(raw_article, article_url),
            "text": text,
            "word_count": len(text.split()),
        })

    if not articles:
        # Discovered links can all be bogus (nav anchors, image sub-pages) while the
        # URL itself is a perfectly good article — fall back to extracting the page.
        single = _extract_page_as_article(url, raw)
        if single:
            return {"articles": [single], "discovered": len(urls), "error": None}
        return {"articles": [], "discovered": len(urls), "error": _detect_failure_cause(raw)}

    return {"articles": articles, "discovered": len(urls), "error": None}
