from services.web_crawler import _filter_article_urls


def test_filter_keeps_only_urls_under_listing_prefix():
    listing = "https://www.porta.com.pl/otworzsiena/wnetrza"
    candidates = [
        "https://www.porta.com.pl/otworzsiena/wnetrza/10-sposobow-na-nowoczesne-wnetrza",
        "https://www.porta.com.pl/otworzsiena/wnetrza/5-popularnych-stylow",
        "https://www.porta.com.pl/otworzsiena/wnetrza",          # the listing itself
        "https://www.porta.com.pl/otworzsiena/kontakt",          # sibling nav, not under prefix
        "https://www.porta.com.pl/otworzsiena",                  # hub, not under prefix
        "https://other.com/otworzsiena/wnetrza/x",               # different domain
    ]
    kept = _filter_article_urls(candidates, listing)
    assert kept == [
        "https://www.porta.com.pl/otworzsiena/wnetrza/10-sposobow-na-nowoczesne-wnetrza",
        "https://www.porta.com.pl/otworzsiena/wnetrza/5-popularnych-stylow",
    ]


def test_filter_excludes_blocked_segments_and_extensions():
    listing = "https://measureschool.com/blog"
    candidates = [
        "https://measureschool.com/blog/server-side-gtm-guide",
        "https://measureschool.com/blog/page/2",                 # blocked segment 'page'
        "https://measureschool.com/blog/diagram.png",            # blocked extension
        "https://measureschool.com/services",                    # not under /blog
    ]
    kept = _filter_article_urls(candidates, listing)
    assert kept == ["https://measureschool.com/blog/server-side-gtm-guide"]


def test_filter_dedupes_and_strips_query_fragment():
    listing = "https://b.com/blog"
    candidates = [
        "https://b.com/blog/post-one?utm=x",
        "https://b.com/blog/post-one#section",
        "https://b.com/blog/post-one/",
    ]
    assert _filter_article_urls(candidates, listing) == ["https://b.com/blog/post-one"]


import services.web_crawler as wc


def test_discovery_uses_sitemap_when_it_yields_two_or_more(monkeypatch):
    listing = "https://b.com/blog"
    monkeypatch.setattr(wc, "_fetch_sitemap_urls",
                        lambda u: ["https://b.com/blog/article-alpha", "https://b.com/blog/article-bravo"])
    monkeypatch.setattr(wc, "_fetch_feed_urls", lambda u: (_ for _ in ()).throw(AssertionError("feed should not run")))
    monkeypatch.setattr(wc, "_scrape_listing_links", lambda u: (_ for _ in ()).throw(AssertionError("scrape should not run")))
    out = wc._discover_article_urls(listing, max_articles=10)
    assert out == ["https://b.com/blog/article-alpha", "https://b.com/blog/article-bravo"]


def test_discovery_falls_back_to_feed_then_scrape(monkeypatch):
    listing = "https://b.com/blog"
    monkeypatch.setattr(wc, "_fetch_sitemap_urls", lambda u: ["https://b.com/blog"])      # 0 after filter
    monkeypatch.setattr(wc, "_fetch_feed_urls", lambda u: ["https://b.com/services"])     # 0 after filter
    monkeypatch.setattr(wc, "_scrape_listing_links",
                        lambda u: ["https://b.com/blog/article-xray", "https://b.com/blog/article-yankee"])
    out = wc._discover_article_urls(listing, max_articles=10)
    assert out == ["https://b.com/blog/article-xray", "https://b.com/blog/article-yankee"]


def test_discovery_caps_at_max_articles(monkeypatch):
    listing = "https://b.com/blog"
    monkeypatch.setattr(wc, "_fetch_sitemap_urls",
                        lambda u: [f"https://b.com/blog/post-{i}" for i in range(10)])
    out = wc._discover_article_urls(listing, max_articles=3)
    assert len(out) == 3


def test_discovery_layer_errors_are_non_fatal(monkeypatch):
    listing = "https://b.com/blog"
    monkeypatch.setattr(wc, "_fetch_sitemap_urls", lambda u: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(wc, "_fetch_feed_urls", lambda u: [])
    monkeypatch.setattr(wc, "_scrape_listing_links",
                        lambda u: ["https://b.com/blog/article-xray", "https://b.com/blog/article-yankee"])
    out = wc._discover_article_urls(listing, max_articles=10)
    assert out == ["https://b.com/blog/article-xray", "https://b.com/blog/article-yankee"]
