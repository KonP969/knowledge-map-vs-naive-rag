from typing import List, Dict, Any


def chunk_fixed_size(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
    """Split text into fixed-size chunks with optional overlap."""
    if not text:
        return []

    chunks = []
    step = max(1, chunk_size - overlap)
    index = 0
    pos = 0

    while pos < len(text):
        end = min(pos + chunk_size, len(text))
        content = text[pos:end]
        chunks.append({
            "content": content,
            "index": index,
            "start_char": pos,
            "end_char": end,
        })
        if end == len(text):
            break
        pos += step
        index += 1

    return chunks
