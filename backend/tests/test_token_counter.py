from services.token_counter import count_tokens


def test_count_tokens_basic():
    n = count_tokens("Hello world")
    assert isinstance(n, int)
    assert n > 0


def test_count_tokens_empty():
    assert count_tokens("") == 0
