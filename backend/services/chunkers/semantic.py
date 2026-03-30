import re
from typing import List, Dict, Any


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences on . ! ? boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


def chunk_semantic(text: str, max_sentences: int = 5) -> List[Dict[str, Any]]:
    """Group sentences into chunks, respecting sentence boundaries."""
    if not text:
        return []

    sentences = _split_sentences(text)
    chunks = []
    current_sentences: List[str] = []
    current_start = 0
    pos = 0

    for sentence in sentences:
        sent_start = text.find(sentence, pos)
        if sent_start == -1:
            sent_start = pos

        if len(current_sentences) >= max_sentences:
            content = " ".join(current_sentences)
            chunks.append({
                "content": content,
                "index": len(chunks),
                "start_char": current_start,
                "end_char": current_start + len(content),
            })
            current_sentences = []
            current_start = sent_start

        current_sentences.append(sentence)
        pos = sent_start + len(sentence)

    if current_sentences:
        content = " ".join(current_sentences)
        chunks.append({
            "content": content,
            "index": len(chunks),
            "start_char": current_start,
            "end_char": current_start + len(content),
        })

    return chunks
