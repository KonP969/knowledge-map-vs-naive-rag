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
