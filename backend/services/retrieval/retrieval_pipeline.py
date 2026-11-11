import time
import uuid
from models.retrieval_models import QueryTrace, StageTrace, Selection
from services.wiki_store import WikiStore
from services.retrieval.intent_parser import parse_intent
from services.retrieval.candidate_filter import filter_candidates
from services.retrieval.semantic_retrieval import semantic_candidates, merge_candidates
from services.semantic_index import load_claim_index
from services.retrieval.selection import select_candidates
from services.retrieval.context_assembly import assemble_context
from services.retrieval.answer_generator import generate_answer
from services.retrieval.agent_fallback import run_agent_fallback
from services.llm_service import record_query

# Questions that gather or weigh facts across documents need more of each node's claims.
_WIDE_FORMS = {"list", "table"}
_WIDE_INTENTS = {"comparison", "synthesis"}


def claim_budget(intent) -> int:
    """Claims per selected node passed to the answer model."""
    if intent.expected_answer_form in _WIDE_FORMS or intent.intent_type in _WIDE_INTENTS:
        return 25
    return 8


def run_retrieval(question: str, store: WikiStore) -> QueryTrace:
    """
    Orchestrates the 5-stage retrieval pipeline with agent fallback.
    Fallback triggers when:
      - Stage 2 returns 0 candidates, OR
      - Stage 3 selection confidence < 0.5, OR
      - Stage 5 answer confidence < 0.6.
    """
    t_total = time.time()
    query_id = f"q_{uuid.uuid4().hex[:8]}"
    stages = []
    total_llm_calls = 0
    agent_trace = None

    # Stage 1
    t = time.time()
    intent = parse_intent(question)
    total_llm_calls += 1
    stages.append(StageTrace(
        stage=1, name="Intent Parser",
        duration_ms=(time.time() - t) * 1000, llm_called=True,
        input_summary=f"question: {question[:80]}",
        output_summary=(
            f"intent_type={intent.intent_type}, "
            f"entities={intent.entity_mentions}, "
            f"concepts={intent.concept_mentions}"
        ),
    ))

    # Stage 2 — hybrid: lexical structural scoring + semantic claim recall (when an
    # embedding index exists), merged. Semantic recall is what lets natural-language and
    # partial-name queries find the right node and carry the relevant claims.
    t = time.time()
    lexical = filter_candidates(intent, store)
    vs = load_claim_index(store)
    n_semantic = 0
    if vs is not None and len(vs) > 0:
        semantic = semantic_candidates(question, store, vector_store=vs)
        n_semantic = len(semantic)
        candidates = merge_candidates(lexical, semantic)[:20]
    else:
        candidates = lexical
    stages.append(StageTrace(
        stage=2, name="Candidate Filter",
        duration_ms=(time.time() - t) * 1000, llm_called=False,
        input_summary=f"intent_type={intent.intent_type}",
        output_summary=f"{len(candidates)} candidates ({n_semantic} semantic + {len(lexical)} lexical)",
    ))

    if not candidates:
        agent_trace = run_agent_fallback(
            question, store,
            trigger_reason="Stage 2 returned 0 candidates",
        )

    # Stage 3
    t = time.time()
    if candidates:
        selection = select_candidates(question, candidates)
        total_llm_calls += 1
        llm_called_s3 = True
    else:
        selection = Selection(selected=[], confidence=0.0, reasoning="No candidates found.")
        llm_called_s3 = False
    stages.append(StageTrace(
        stage=3, name="Selection",
        duration_ms=(time.time() - t) * 1000, llm_called=llm_called_s3,
        input_summary=f"{len(candidates)} candidates",
        output_summary=f"{len(selection.selected)} selected, confidence={selection.confidence:.2f}",
    ))

    if agent_trace is None and candidates and selection.confidence < 0.5:
        agent_trace = run_agent_fallback(
            question, store,
            trigger_reason=f"Stage 3 confidence too low ({selection.confidence:.2f} < 0.5)",
        )

    # Stage 4
    t = time.time()
    context, context_chars = assemble_context(
        question, selection, candidates, store, max_claims=claim_budget(intent),
    )
    stages.append(StageTrace(
        stage=4, name="Context Assembly",
        duration_ms=(time.time() - t) * 1000, llm_called=False,
        input_summary=f"{len(selection.selected)} selected artifacts",
        output_summary=f"{context_chars} chars assembled",
    ))

    # Stage 5
    answer_result = generate_answer(question, context)
    answer = answer_result.answer
    total_llm_calls += 1
    stages.append(StageTrace(
        stage=5, name="Answer Generator",
        duration_ms=answer_result.llm_ms, llm_called=True,
        input_summary=f"{context_chars} chars context",
        output_summary=f"confidence={answer.confidence:.2f}, sources={len(answer.sources)}",
    ))

    if agent_trace is None and answer.confidence < 0.6:
        agent_trace = run_agent_fallback(
            question, store,
            trigger_reason=f"Stage 5 answer confidence too low ({answer.confidence:.2f} < 0.6)",
        )

    # The fallback runs precisely because the pipeline answer was judged weak — when it
    # produced a fresh answer, that is the one the caller should get.
    if agent_trace is not None and agent_trace.final_answer is not None:
        answer = agent_trace.final_answer

    total_duration_ms = (time.time() - t_total) * 1000
    # gpt-4o-mini pricing: $0.15/1M input tokens, $0.60/1M output tokens
    cost_usd = (answer_result.prompt_tokens * 0.15 + answer_result.completion_tokens * 0.60) / 1_000_000
    record_query(
        query=question,
        retrieval_ms=max(0.0, total_duration_ms - answer_result.llm_ms),
        llm_ms=answer_result.llm_ms,
        prompt_tokens=answer_result.prompt_tokens,
        completion_tokens=answer_result.completion_tokens,
        estimated_cost_usd=cost_usd,
    )

    return QueryTrace(
        query_id=query_id,
        question=question,
        intent=intent,
        candidates_count=len(candidates),
        selected_count=len(selection.selected),
        context_chars=context_chars,
        answer=answer,
        stages=stages,
        total_duration_ms=total_duration_ms,
        total_llm_calls=total_llm_calls,
        agent_trace=agent_trace,
    )
