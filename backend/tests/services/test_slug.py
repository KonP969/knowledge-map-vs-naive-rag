import pytest
from services._slug import slugify, ensure_unique


def test_slugify_lowercase_hyphenated():
    assert slugify("Hello World") == "hello-world"


def test_slugify_strips_diacritics():
    assert slugify("Łazienka — sypialnia") == "lazienka-sypialnia"


def test_slugify_collapses_whitespace():
    assert slugify("  multiple   spaces  ") == "multiple-spaces"


def test_slugify_strips_punctuation():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_preserves_digits():
    assert slugify("Q1 2023 Report") == "q1-2023-report"


def test_slugify_empty_input_raises():
    with pytest.raises(ValueError):
        slugify("")


def test_ensure_unique_appends_suffix_if_taken():
    assert ensure_unique("foo", existing={"foo", "foo-2"}) == "foo-3"


def test_ensure_unique_returns_same_if_free():
    assert ensure_unique("foo", existing={"bar"}) == "foo"
