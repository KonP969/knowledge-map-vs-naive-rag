import re
import unicodedata

# Cap slug length so raw/<slug>/parsed.md stays under the Windows MAX_PATH (260) limit —
# long PDF filenames (e.g. book titles) otherwise produce 150+ char slugs that fail to write.
_MAX_SLUG_LEN = 80

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

    if len(collapsed) > _MAX_SLUG_LEN:
        truncated = collapsed[:_MAX_SLUG_LEN]
        if "-" in truncated:
            truncated = truncated.rsplit("-", 1)[0]  # cut back to the last whole word
        collapsed = truncated.strip("-") or collapsed[:_MAX_SLUG_LEN].strip("-")
    return collapsed


def ensure_unique(slug: str, existing: set[str]) -> str:
    if slug not in existing:
        return slug
    n = 2
    while f"{slug}-{n}" in existing:
        n += 1
    return f"{slug}-{n}"
