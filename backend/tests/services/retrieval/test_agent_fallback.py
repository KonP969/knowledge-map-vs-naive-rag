import json
import pytest
from unittest.mock import MagicMock, patch
from models.retrieval_models import AgentTrace, Answer
import services.retrieval.agent_fallback as _module


@pytest.fixture(autouse=True)
def reset_client():
    _module._client = None
    yield
    _module._client = None


def _make_stop_response(text: str):
    """Build a mock OpenAI response with finish_reason='stop'."""
    msg = MagicMock()
    msg.content = text
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "stop"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_tool_call_response(tool_name: str, args: dict, call_id: str = "call_1"):
    """Build a mock OpenAI response with a tool_call."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(args)

    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "tool_calls"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_run_agent_fallback_returns_agent_trace(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    stop_resp = _make_stop_response("The answer is X.")
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = stop_resp
        mock_get.return_value = mock_client
        result = run_agent_fallback("What is X?", store, "Stage 2 returned 0 candidates")
    assert isinstance(result, AgentTrace)
    assert result.triggered is True


def test_run_agent_fallback_trigger_reason_preserved(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_stop_response("ans")
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "Stage 3 confidence too low (0.3 < 0.5)")
    assert result.trigger_reason == "Stage 3 confidence too low (0.3 < 0.5)"


def test_run_agent_fallback_no_tool_calls_has_empty_tool_list(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_stop_response("ans")
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert result.tool_calls == []


def test_run_agent_fallback_stop_produces_final_answer(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_stop_response("The final answer is 42.")
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert result.final_answer is not None
    assert isinstance(result.final_answer, Answer)
    assert "42" in result.final_answer.final_answer


def test_run_agent_fallback_tool_call_then_stop(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    tool_resp = _make_tool_call_response("read_index", {})
    stop_resp = _make_stop_response("Found nothing.")
    with patch("services.retrieval.agent_fallback._get_client") as mock_get, \
         patch("services.retrieval.agent_fallback._dispatch_tool", return_value='{"sources":[]}') as mock_dispatch:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [tool_resp, stop_resp]
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "read_index"
    mock_dispatch.assert_called_once_with("read_index", {}, store)


def test_run_agent_fallback_tool_call_logged(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    tool_resp = _make_tool_call_response("search_entities", {"q": "bedroom"}, "call_abc")
    stop_resp = _make_stop_response("Done.")
    with patch("services.retrieval.agent_fallback._get_client") as mock_get, \
         patch("services.retrieval.agent_fallback._dispatch_tool", return_value="[]"):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [tool_resp, stop_resp]
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert result.tool_calls[0].args == {"q": "bedroom"}
    assert result.tool_calls[0].result_summary == "[]"


def test_run_agent_fallback_respects_max_iterations(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback, MAX_ITERATIONS
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    # Always return a tool call — loop must terminate at MAX_ITERATIONS
    always_tool = _make_tool_call_response("read_index", {})
    with patch("services.retrieval.agent_fallback._get_client") as mock_get, \
         patch("services.retrieval.agent_fallback._dispatch_tool", return_value="{}"):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = always_tool
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert mock_client.chat.completions.create.call_count == MAX_ITERATIONS
    assert result.triggered is True
    assert result.final_answer is None  # no stop response → no answer produced
    assert len(result.tool_calls) == MAX_ITERATIONS  # one tool call logged per iteration


def test_run_agent_fallback_duration_ms_positive(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_stop_response("ans")
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert result.duration_ms >= 0.0


def test_dispatch_tool_exception_returns_error_json(tmp_path):
    from services.retrieval.agent_fallback import _dispatch_tool
    from services.wiki_store import WikiStore
    import services.retrieval.agent_tools as _tools
    store = WikiStore(root=tmp_path)
    with patch.object(_tools, "read_index", side_effect=IOError("disk error")):
        result = json.loads(_dispatch_tool("read_index", {}, store))
    assert "error" in result
    assert "read_index" in result["error"]


def test_dispatch_tool_truncates_oversized_result(tmp_path):
    """A tool result goes straight into the prompt, so it must be bounded.

    read_index over a real vault returned 26 MB (~6.5M tokens) and the request was
    rejected outright — every question that fell through to the agent died there.
    """
    from services.retrieval.agent_fallback import _dispatch_tool, MAX_TOOL_RESULT_CHARS
    from services.wiki_store import WikiStore
    import services.retrieval.agent_tools as _tools
    store = WikiStore(root=tmp_path)
    huge = "x" * (MAX_TOOL_RESULT_CHARS * 3)
    with patch.object(_tools, "read_index", return_value=huge):
        result = _dispatch_tool("read_index", {}, store)
    assert len(result) <= MAX_TOOL_RESULT_CHARS + 200
    assert "truncated" in result.lower()


def test_dispatch_tool_leaves_small_result_untouched(tmp_path):
    from services.retrieval.agent_fallback import _dispatch_tool
    from services.wiki_store import WikiStore
    import services.retrieval.agent_tools as _tools
    store = WikiStore(root=tmp_path)
    with patch.object(_tools, "read_index", return_value='{"sources": []}'):
        result = _dispatch_tool("read_index", {}, store)
    assert result == '{"sources": []}'
