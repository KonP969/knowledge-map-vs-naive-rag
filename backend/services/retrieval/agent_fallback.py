import json
import os
import time
from typing import List, Optional

from openai import OpenAI

from models.retrieval_models import AgentToolCall, AgentTrace, Answer
from services.wiki_store import WikiStore
import services.retrieval.agent_tools as _tools

_client: Optional[OpenAI] = None
MAX_ITERATIONS = 8

# A tool result is appended verbatim to the prompt, so an unbounded one is a live
# grenade: read_index over a real vault produced 26 MB (~6.5M tokens) and the API
# rejected the whole request. Bound every result at the single place they pass.
MAX_TOOL_RESULT_CHARS = 12_000

_SYSTEM_PROMPT = (
    "You are a wiki search agent with access to tools to search a structured knowledge wiki. "
    "Use tools to gather information, then answer the user's question with evidence from the wiki. "
    "When you have gathered enough information, provide your final answer. "
    "Always cite which sources, claims, or nodes you used."
)

_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_index",
            "description": "Get wiki overview — list of all sources, entities, and concepts.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_entities",
            "description": "Search entities by name or aliases.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search query"},
                    "entity_type": {"type": "string", "description": "Optional entity type filter (Person, Org, Product, Place, Event)"},
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_concepts",
            "description": "Search concepts by name.",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_wiki_content",
            "description": "Full-text search over all wiki markdown files.",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "Full-text search over raw source content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "scope": {"type": "string", "description": "Search scope directory (default: raw)"},
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_node",
            "description": (
                "Get full content of a node by prefixed ID "
                "(e.g. 'entity:e_001', 'concept:c_001', 'source:src_001')."
            ),
            "parameters": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_claims",
            "description": "Get claims filtered by node_id, query text, or polarity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "query": {"type": "string"},
                    "polarity": {"type": "string", "enum": ["asserts", "denies"]},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_relations",
            "description": "Get edges for a node, with optional direction and relation type filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "direction": {"type": "string", "enum": ["in", "out"]},
                    "relation_type": {"type": "string"},
                },
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_source",
            "description": "Read source document content by source_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "section": {"type": "string"},
                },
                "required": ["source_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_log",
            "description": "Query the wiki activity log with a text filter string.",
            "parameters": {
                "type": "object",
                "properties": {"filter": {"type": "string"}},
                "required": ["filter"],
            },
        },
    },
]


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _dispatch_tool(name: str, args: dict, store: WikiStore) -> str:
    dispatch = {
        "read_index": lambda: _tools.read_index(store),
        "search_entities": lambda: _tools.search_entities(store, **args),
        "search_concepts": lambda: _tools.search_concepts(store, **args),
        "search_wiki_content": lambda: _tools.search_wiki_content(store, **args),
        "search_text": lambda: _tools.search_text(store, **args),
        "get_node": lambda: _tools.get_node(store, **args),
        "get_claims": lambda: _tools.get_claims(store, **args),
        "get_relations": lambda: _tools.get_relations(store, **args),
        "read_source": lambda: _tools.read_source(store, **args),
        "query_log": lambda: _tools.query_log(store, **args),
    }
    fn = dispatch.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        return _truncate(fn(), name)
    except Exception as exc:
        return json.dumps({"error": f"tool {name} failed: {exc}"})


def _truncate(result: str, name: str) -> str:
    if len(result) <= MAX_TOOL_RESULT_CHARS:
        return result
    return (
        result[:MAX_TOOL_RESULT_CHARS]
        + f"\n\n[truncated: {name} returned {len(result)} chars, "
        + f"capped at {MAX_TOOL_RESULT_CHARS}. Narrow the query instead of reading everything.]"
    )


def run_agent_fallback(
    question: str,
    store: WikiStore,
    trigger_reason: str,
    model: str = None,
) -> AgentTrace:
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    t_start = time.time()
    client = _get_client()
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_calls: List[AgentToolCall] = []
    final_answer: Optional[Answer] = None

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=_TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        choice = response.choices[0]
        msg = choice.message

        # Build assistant message dict for conversation history
        assistant_msg: dict = {"role": "assistant"}
        if msg.content:
            assistant_msg["content"] = msg.content
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if choice.finish_reason == "stop" or not msg.tool_calls:
            text = msg.content or ""
            final_answer = Answer(
                final_answer=text,
                sources=[],
                confidence=0.7,
                reasoning_steps=["Agent fallback completed"],
                related_questions=[],
            )
            break

        for tc in msg.tool_calls:
            t_tool = time.time()
            args = json.loads(tc.function.arguments or "{}")
            result = _dispatch_tool(tc.function.name, args, store)
            tool_calls.append(AgentToolCall(
                tool_name=tc.function.name,
                args=args,
                result_summary=result[:200],
                duration_ms=(time.time() - t_tool) * 1000,
            ))
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return AgentTrace(
        triggered=True,
        trigger_reason=trigger_reason,
        tool_calls=tool_calls,
        final_answer=final_answer,
        duration_ms=(time.time() - t_start) * 1000,
    )
