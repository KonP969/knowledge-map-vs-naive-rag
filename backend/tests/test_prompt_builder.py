from services.prompt_builder import build_prompt, DEFAULT_SYSTEM_PROMPT
from models.chunk import Chunk


def _make_chunk(content: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"c{idx}", document_id="doc1", content=content,
        index=idx, char_count=len(content), token_count=10,
        start_char=0, end_char=len(content),
    )


def test_build_prompt_contains_query():
    chunks = [_make_chunk("Some context text.")]
    result = build_prompt("What is X?", chunks, DEFAULT_SYSTEM_PROMPT)
    assert "What is X?" in result["full_prompt"]
    assert "What is X?" in result["user_query"]


def test_build_prompt_contains_chunks():
    chunks = [_make_chunk("Relevant fact about Y.")]
    result = build_prompt("Tell me about Y", chunks, DEFAULT_SYSTEM_PROMPT)
    assert "Relevant fact about Y." in result["context_block"]


def test_build_prompt_token_counts_positive():
    chunks = [_make_chunk("Some context.")]
    result = build_prompt("Query", chunks, DEFAULT_SYSTEM_PROMPT)
    assert result["token_counts"]["system"] > 0
    assert result["token_counts"]["context"] > 0
    assert result["token_counts"]["query"] > 0
    assert result["token_counts"]["total"] > 0


def test_build_prompt_empty_chunks():
    result = build_prompt("Question?", [], DEFAULT_SYSTEM_PROMPT)
    assert "Question?" in result["full_prompt"]
    assert result["token_counts"]["context"] == 0
