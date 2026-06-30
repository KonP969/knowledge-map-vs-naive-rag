"""Locate a claim's verbatim text inside a source's raw text — robust to PDF extraction
artifacts (extra spaces/newlines inside words). Returns (start, end) into the raw text, or
None when it genuinely can't be found."""
from typing import List, Optional, Tuple


def locate_span(raw: str, text: str) -> Optional[Tuple[int, int]]:
    if not text or not raw:
        return None

    # 1. exact substring
    idx = raw.find(text)
    if idx >= 0:
        return idx, idx + len(text)

    # 2. whitespace-insensitive: compare with all whitespace stripped, then map back to the
    #    original raw offsets. Handles "Pe nguin" vs "Penguin", broken lines, etc.
    raw_chars: List[str] = []
    raw_map: List[int] = []  # position in stripped string -> position in raw
    for i, ch in enumerate(raw):
        if not ch.isspace():
            raw_chars.append(ch)
            raw_map.append(i)
    stripped_raw = "".join(raw_chars)
    stripped_text = "".join(ch for ch in text if not ch.isspace())
    if not stripped_text:
        return None

    j = stripped_raw.find(stripped_text)
    if j < 0:
        return None
    start = raw_map[j]
    end = raw_map[j + len(stripped_text) - 1] + 1
    return start, end
