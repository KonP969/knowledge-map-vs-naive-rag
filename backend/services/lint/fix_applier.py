import os
import uuid
from typing import Any, Dict, Optional

from openai import OpenAI

from models.lint_models import LintIssue, LlmQuestionsResult
from models.wiki_models import Edge, Span
from services.wiki_store import WikiStore


class FixError(Exception):
    """Raised when a fix cannot be applied."""


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _generate_questions(content: str, node_id: str, llm_client) -> list:
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    resp = llm_client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate 3-5 analytical questions that this knowledge node answers. "
                    "Questions should be specific, varied, and useful for retrieval."
                ),
            },
            {
                "role": "user",
                "content": f"Node: {node_id}\n\nContent:\n{content}",
            },
        ],
        response_format=LlmQuestionsResult,
    )
    result = resp.choices[0].message.parsed
    return result.questions if result else []


def apply_fix(
    store: WikiStore,
    issue: LintIssue,
    edit_payload: Optional[Dict[str, Any]] = None,
    llm_client=None,
) -> None:
    if not issue.auto_fixable:
        raise FixError(f"Issue {issue.id} ({issue.type}) is not auto-fixable")

    t = issue.type
    p = issue.payload

    if t == "dangling_source_ref":
        if p.get("kind") == "claim":
            store.delete_claim(p["claim_id"])
        elif p.get("kind") == "edge":
            store.delete_edge(p["edge_id"])
        else:
            raise FixError(f"Unknown payload.kind for dangling_source_ref: {p.get('kind')}")
        return

    if t == "dangling_node_ref":
        store.delete_edge(p["edge_id"])
        return

    if t == "corrupted_jsonl":
        path = store.root / "wiki" / p["file"]
        store.delete_jsonl_line(path, p["line_no"])
        return

    if t == "orphan_entity":
        store.delete_entity(p["slug"], p["entity_type"])
        return

    if t == "orphan_concept":
        store.delete_concept(p["slug"])
        return

    if t == "empty_description":
        if not edit_payload or "description" not in edit_payload:
            raise FixError("empty_description fix requires edit_payload['description']")
        new_text = edit_payload["description"]
        if p.get("kind") == "entity":
            store.update_entity_description(p["slug"], p["entity_type"], new_text)
        elif p.get("kind") == "concept":
            store.update_concept_description(p["slug"], new_text)
        else:
            raise FixError(f"empty_description fix not implemented for kind={p.get('kind')}")
        return

    if t == "empty_questions":
        if llm_client is None:
            llm_client = _get_client()
        node_id = p["node_id"]
        kind = node_id.split(":")[0]
        slug = p["slug"]
        if kind == "entity":
            node = store.read_entity(slug, p["entity_type"])
            content = f"Entity type: {node.type}\nDescription: {node.description}"
        elif kind == "concept":
            node = store.read_concept(slug)
            content = f"Definition: {node.definition}"
        else:
            node = store.read_source(slug)
            content = f"Summary: {node.summary}"
        questions = _generate_questions(content, node_id, llm_client)
        if not questions:
            raise FixError("LLM returned no questions")
        if kind == "entity":
            store.update_entity_questions(slug, p["entity_type"], questions)
        elif kind == "concept":
            store.update_concept_questions(slug, questions)
        else:
            store.update_source_questions(slug, questions)
        return

    if t == "unmarked_contradiction":
        edge = Edge(
            id=f"e_{uuid.uuid4().hex[:8]}",
            **{"from": f"claim:{p['claim_a_id']}"},
            to=f"claim:{p['claim_b_id']}",
            relation="contradicts",
            source_id=p["source_id"],
            span=Span(start=0, end=0, text="[lint-generated]"),
            confidence=1.0,
        )
        store.append_edge(edge)
        return

    if t == "stale_summary":
        store.update_source_summary(p["slug"], p["proposed_summary"])
        return

    raise FixError(f"No fix implemented for type {t}")
