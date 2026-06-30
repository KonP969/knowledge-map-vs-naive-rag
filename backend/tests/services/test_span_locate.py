from services.span_locate import locate_span


def test_exact_match():
    assert locate_span("hello world foo", "world") == (6, 11)


def test_not_found_returns_none():
    assert locate_span("hello world", "xyz") is None


def test_empty_text_returns_none():
    assert locate_span("abc", "") is None


def test_whitespace_insensitive_locates_through_pdf_artifacts():
    # PDF extraction inserts spaces inside words; the LLM's verbatim is clean.
    raw = "...You are supporting writers. Pe nguin supports copyright. Thank you..."
    loc = locate_span(raw, "Penguin supports copyright")
    assert loc is not None
    # the located span in the raw, with spaces removed, equals the clean text (spaces removed)
    assert raw[loc[0]:loc[1]].replace(" ", "") == "Penguinsupportscopyright"


def test_whitespace_insensitive_handles_newlines():
    raw = "line one\nPenguin\nsupports copyright\nline four"
    loc = locate_span(raw, "Penguin supports copyright")
    assert loc is not None
    assert "supports" in raw[loc[0]:loc[1]]
