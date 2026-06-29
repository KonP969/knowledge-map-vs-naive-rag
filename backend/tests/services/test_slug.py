import pytest


def test_slugify_caps_long_filenames_at_word_boundary():
    from services._slug import slugify
    long_name = ("Atomic Habits The life-changing million copy bestseller -- James Clear "
                 "-- 2018 -- Random House Business -- 9781473537804 -- annas-archive")
    s = slugify(long_name)
    assert len(s) <= 80          # short enough to keep the raw/<slug>/ path under Windows MAX_PATH
    assert not s.endswith("-") and not s.startswith("-")
    assert s.startswith("atomic-habits")
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
