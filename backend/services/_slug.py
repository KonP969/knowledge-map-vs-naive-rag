import re
import unicodedata

_CHAR_MAP = str.maketrans({
    "Ł": "l", "ł": "l",
    "Ø": "o", "ø": "o",
    "Đ": "d", "đ": "d",
    "Ð": "d", "ð": "d",
    "Æ": "ae", "æ": "ae",
    "Þ": "th", "þ": "th",
    "ß": "ss",
})


def slugify(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("Cannot slugify empty string")

    text = text.translate(_CHAR_MAP)
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    cleaned = re.sub(r"[^a-z0-9\s-]", "", lowered)
    collapsed = re.sub(r"[\s-]+", "-", cleaned).strip("-")

    if not collapsed:
        raise ValueError(f"Slugification of {text!r} produced empty result")
    return collapsed


def ensure_unique(slug: str, existing: set[str]) -> str:
    if slug not in existing:
        return slug
    n = 2
    while f"{slug}-{n}" in existing:
        n += 1
    return f"{slug}-{n}"
