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
    ("https://example.com/abcd/", "slug exactly 4 chars — under minimum 5"),
    ("https://example.com/gtm-tutorial-/", "slug ends with hyphen"),
])
def test_is_article_url_rejects_non_articles(url, reason):
    assert _is_article_url(url, NETLOC) is False, f"Should reject: {reason}"


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

    assert "https://measureschool.com/gtm-tutorial" in urls
    assert "https://measureschool.com/google-analytics-guide" in urls


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
