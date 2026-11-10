import pytest

from services.openai_client import MISSING_KEY_MESSAGE, MissingAPIKeyError, make_client


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_key_raises_an_actionable_error(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", value)
    with pytest.raises(MissingAPIKeyError, match="backend/.env"):
        make_client()


def test_key_present_builds_a_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert make_client().api_key == "sk-test"


def test_message_names_the_env_var():
    assert "OPENAI_API_KEY" in MISSING_KEY_MESSAGE
