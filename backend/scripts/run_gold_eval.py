# -*- coding: utf-8 -*-
"""Gold-set eval dla grafowego RAG — Phase 4 planu semantic-retrieval-over-graph.

Odpala kazde pytanie z gold-setu przez `run_retrieval` (bezposrednio, bez serwera),
sklada z cytowanych claimow "fragmenty zrodlowe" i oddaje je sedziemu-LLM z
`tests/rag_evaluation/evaluator.py`. Wynik: liczby zamiast wrazen.

    cd backend
    python scripts/run_gold_eval.py --dry-run          # nic nie kosztuje, pokazuje plan
    python scripts/run_gold_eval.py --limit 3          # 3 pytania, na probe
    python scripts/run_gold_eval.py                    # caly gold-set

Kazde pytanie to kilka wywolan LLM (pipeline) + jedno wywolanie sedziego, wiec
`CostGuard` pilnuje budzetu i pyta o zgode po przekroczeniu progu.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from models.retrieval_models import QueryTrace  # noqa: E402
from services.retrieval.retrieval_pipeline import run_retrieval  # noqa: E402
from services.wiki_store import WikiStore  # noqa: E402
from tests.rag_evaluation.cost_guard import CostGuard, calc_openai_cost  # noqa: E402
from tests.rag_evaluation.evaluator import evaluate  # noqa: E402
from tests.rag_evaluation.gold_questions import GOLD_QUESTIONS  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parent.parent / "tests" / "rag_evaluation" / "reports"


def build_chunks(trace: QueryTrace, store: WikiStore):
    """Zamienia cytowane claimy w liste fragmentow w formacie, ktorego chce evaluate().

    Sedzia ocenia faithfulness wzgledem tego, co system NAPRAWDE pokazal jako
    zrodlo — czyli wzgledem tresci cytowanych claimow, nie calych dokumentow.
    """
    claims_by_id = {c.id: c for c in store.read_all_claims()}
    titles = {}
    for slug in store.list_sources():
        src = store.read_source(slug)
        if src:
            titles[src.id] = src.title

    chunks = []
    for src_ref in trace.answer.sources:
        doc_name = titles.get(src_ref.source_id, src_ref.source_id)
        score = {"primary": 1.0, "supporting": 0.6}.get(src_ref.relevance, 0.3)
        for cid in src_ref.claim_ids:
            claim = claims_by_id.get(cid)
            if claim is None:
                continue
            chunks.append({
                "document_name": doc_name,
                "content": claim.text,
                "score": score,
                "claim_id": cid,
            })
    return chunks


def run_one(q, store, guard):
    trace = run_retrieval(q["question"], store)
    chunks = build_chunks(trace, store)

    # koszt samego pipeline'u nie jest raportowany per-query przez run_retrieval,
    # wiec liczymy go zachowawczo z liczby wywolan LLM (tylko do pilnowania budzetu)
    guard.add_rag_cost(calc_openai_cost(1500 * trace.total_llm_calls, 400 * trace.total_llm_calls))

    verdict = evaluate(
        query=q["question"],
        answer=trace.answer.final_answer,
        retrieved_chunks=chunks,
        expected_topics=q["expected_topics"],
        cost_guard=guard,
    )
    return {
        "id": q["id"],
        "category": q["category"],
        "language": q["language"],
        "question": q["question"],
        "answer": trace.answer.final_answer,
        "answer_confidence": trace.answer.confidence,
        "candidates_count": trace.candidates_count,
        "selected_count": trace.selected_count,
        "context_chars": trace.context_chars,
        "cited_claims": sum(len(s.claim_ids) for s in trace.answer.sources),
        "chunks_resolved": len(chunks),
        "agent_fallback": trace.agent_trace is not None,
        "llm_calls": trace.total_llm_calls,
        "duration_ms": round(trace.total_duration_ms, 1),
        **{k: verdict.get(k) for k in
           ("correctness", "helpfulness", "faithfulness", "avg_score", "explanation", "issues")},
    }


def summarize(rows):
    def avg(vals):
        vals = [v for v in vals if isinstance(v, (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    overall = {m: avg([r[m] for r in rows]) for m in ("correctness", "helpfulness", "faithfulness")}
    overall["avg_score"] = avg([r["avg_score"] for r in rows])

    per_cat = {}
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["category"]].append(r)
    for cat, rs in sorted(grouped.items()):
        per_cat[cat] = {
            "n": len(rs),
            **{m: avg([r[m] for r in rs]) for m in ("correctness", "helpfulness", "faithfulness")},
        }

    return {
        "overall": overall,
        "per_category": per_cat,
        "questions_with_zero_chunks": [r["id"] for r in rows if r["chunks_resolved"] == 0],
        "questions_with_fallback": [r["id"] for r in rows if r["agent_fallback"]],
    }


def write_report(rows, summary, guard):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")

    json_path = REPORTS_DIR / f"gold-eval-{stamp}.json"
    json_path.write_text(json.dumps(
        {"generated_at": stamp, "summary": summary, "results": rows,
         "total_cost_usd": round(guard.total_cost, 4)},
        ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Gold-set eval — {stamp}", "",
        f"Pytan: {len(rows)} | koszt: ${guard.total_cost:.4f}", "",
        "## Wynik ogolny", "",
        "| metryka | 0-10 |", "|---|---|",
    ]
    for k, v in summary["overall"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Wg kategorii", "",
              "| kategoria | n | correctness | helpfulness | faithfulness |", "|---|---|---|---|---|"]
    for cat, s in summary["per_category"].items():
        lines.append(f"| {cat} | {s['n']} | {s['correctness']} | {s['helpfulness']} | {s['faithfulness']} |")
    lines += ["", "## Per pytanie", "",
              "| id | kat. | corr | help | faith | fragm. | fallback |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['category']} | {r['correctness']} | {r['helpfulness']} | "
                     f"{r['faithfulness']} | {r['chunks_resolved']} | {'tak' if r['agent_fallback'] else ''} |")

    if summary["questions_with_zero_chunks"]:
        lines += ["", "**Pytania bez ani jednego rozwiazanego fragmentu:** "
                  + ", ".join(summary["questions_with_zero_chunks"])]

    md_path = REPORTS_DIR / f"gold-eval-{stamp}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default="wiki_data/default")
    ap.add_argument("--limit", type=int, help="odpal tylko N pierwszych pytan")
    ap.add_argument("--category", help="tylko jedna kategoria")
    ap.add_argument("--only", help="konkretne id pytan po przecinku (do wznawiania partiami)")
    ap.add_argument("--skip", type=int, default=0, help="pomin N pierwszych pytan")
    ap.add_argument("--max-usd", type=float, default=2.00)
    ap.add_argument("--dry-run", action="store_true", help="nie wola LLM, tylko pokazuje plan")
    args = ap.parse_args()

    questions = GOLD_QUESTIONS
    if args.category:
        questions = [q for q in questions if q["category"] == args.category]
    if args.only:
        wanted = [x.strip() for x in args.only.split(",") if x.strip()]
        questions = [q for q in questions if q["id"] in wanted]
    if args.skip:
        questions = questions[args.skip:]
    if args.limit:
        questions = questions[:args.limit]

    if args.dry_run:
        print("DRY RUN — %d pytan, zero wywolan LLM\n" % len(questions))
        for q in questions:
            print("  [%-13s] %-12s %s" % (q["category"], q["language"], q["question"]))
        return 0

    if not os.getenv("OPENAI_API_KEY"):
        print("BLAD: brak OPENAI_API_KEY (backend/.env)", file=sys.stderr)
        return 1

    store = WikiStore(args.vault)
    guard = CostGuard(max_usd=args.max_usd)
    rows = []

    for i, q in enumerate(questions, 1):
        print("[%d/%d] %s" % (i, len(questions), q["id"]), flush=True)
        try:
            row = run_one(q, store, guard)
        except Exception as e:  # jedno pytanie nie moze wywrocic calego przebiegu
            print("    BLAD: %s: %s" % (type(e).__name__, e), file=sys.stderr)
            continue
        rows.append(row)
        print("    corr=%s help=%s faith=%s | fragm=%d%s"
              % (row["correctness"], row["helpfulness"], row["faithfulness"],
                 row["chunks_resolved"], " | FALLBACK" if row["agent_fallback"] else ""), flush=True)
        if guard.should_stop():
            print("\nPrzerwano: przekroczony budzet %s" % guard.summary(), file=sys.stderr)
            break

    if not rows:
        print("Zero wynikow.", file=sys.stderr)
        return 1

    summary = summarize(rows)
    json_path, md_path = write_report(rows, summary, guard)

    print("\n" + "=" * 58)
    print("OGOLEM: corr=%(correctness)s help=%(helpfulness)s faith=%(faithfulness)s "
          "avg=%(avg_score)s" % summary["overall"])
    for cat, s in summary["per_category"].items():
        print("  %-14s n=%-2d corr=%-4s help=%-4s faith=%s"
              % (cat, s["n"], s["correctness"], s["helpfulness"], s["faithfulness"]))
    print("koszt: $%.4f" % guard.total_cost)
    print("raport: %s" % md_path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
