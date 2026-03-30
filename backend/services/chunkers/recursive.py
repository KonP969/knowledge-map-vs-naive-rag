from typing import List, Dict, Any, Optional


def chunk_recursive(
    text: str,
    separators: Optional[List[str]] = None,
    chunk_size: int = 500,
) -> List[Dict[str, Any]]:
    """Recursively split text using a list of separators (priority order)."""
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    if not text:
        return []

    if len(text) <= chunk_size:
        return [{"content": text, "index": 0, "start_char": 0, "end_char": len(text)}]

    # Find the first separator that produces splits
    separator = ""
    for sep in separators:
        if sep and sep in text:
            separator = sep
            break

    if separator:
        parts = text.split(separator)
    else:
        parts = list(text)  # character split

    chunks = []
    current = ""
    current_start = 0
    global_offset = 0

    for i, part in enumerate(parts):
        piece = part + (separator if i < len(parts) - 1 else "")
        if len(current) + len(piece) <= chunk_size:
            current += piece
        else:
            if current:
                chunks.append({
                    "content": current,
                    "index": len(chunks),
                    "start_char": current_start,
                    "end_char": current_start + len(current),
                })
                global_offset = current_start + len(current)
                current_start = global_offset
            current = piece

        if not current_start and not current:
            current_start = global_offset

    if current:
        chunks.append({
            "content": current,
            "index": len(chunks),
            "start_char": current_start,
            "end_char": current_start + len(current),
        })

    return chunks
