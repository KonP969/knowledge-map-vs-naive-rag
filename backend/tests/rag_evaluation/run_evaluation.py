import argparse
import os
import sys
import time
import signal
from datetime import datetime
from typing import List, Dict, Optional

from dotenv import load_dotenv

# Znajdz .env: najpierw w katalogu backend (ROOT), potem w worktree
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, ".."))
_ENV_CANDIDATES = [
    os.path.join(_BACKEND_DIR, ".env"),
    os.path.join(_REPO_ROOT, ".worktrees", "feature", "scaffolding", "backend", ".env"),
]
for _env_path in _ENV_CANDIDATES:
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        break

from .rag_client import ask, get_documents, get_chunks, get_last_query_metrics, health_check
from .cost_guard import CostGuard
from .question_generator import generate_questions
from .evaluator import evaluate
from .report_generator import generate_report, save_partial_results

REPORTS_DIR = os.path.join(_SCRIPT_DIR, "reports")
PARTIAL_SAVE_EVERY = 5


def _build_output_path(output_dir: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(output_dir, f"{ts}_report.md")


def _get_db_stats() -> Dict:
    documents = get_documents()
    n_chunks_total = 0
    for doc in documents:
        try:
            chunks = get_chunks(doc["id"])
            n_chunks_total += len(chunks)
        except Exception:
            pass
    return {"n_documents": len(documents), "n_chunks_total": n_chunks_total}


def run_evaluation(
    n_questions: int = 20,
    max_cost: float = 1.00,
    output_dir: str = REPORTS_DIR,
) -> Optional[str]:
    print("=" * 60)
    print("RAG Evaluation — Learning Lab")
    print("=" * 60)

    # 1. Sprawdz backend
    print("\n[1/5] Sprawdzam backend...")
    if not health_check():
        print("BLAD: Backend nie odpowiada na http://localhost:8000/health")
        print("Uruchom backend: uvicorn main:app --reload --port 8000")
        return None
    print("  Backend dziala.")

    # 2. Sprawdz klucz API
    if not os.getenv("OPENAI_API_KEY"):
        print("BLAD: Brak OPENAI_API_KEY w srodowisku.")
        print(f"Sprawdzono lokalizacje .env: {_ENV_CANDIDATES}")
        print("Ustaw zmienna: $env:OPENAI_API_KEY = 'sk-...'")
        return None

    # 3. Statystyki bazy
    print("\n[2/5] Pobieram informacje o bazie danych...")
    db_stats = _get_db_stats()
    print(f"  Dokumenty: {db_stats['n_documents']} | Chunki: {db_stats['n_chunks_total']}")
    if db_stats["n_documents"] == 0:
        print("BLAD: Brak dokumentow w bazie. Wgraj dokumenty przez frontend.")
        return None

    # 4. Generowanie pytan
    cost_guard = CostGuard(threshold_usd=0.10, max_usd=max_cost)
    output_path = _build_output_path(output_dir)
    start_time = time.time()
    start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n[3/5] Generuje {n_questions} pytan testowych...")
    try:
        questions = generate_questions(n_total=n_questions, cost_guard=cost_guard)
    except RuntimeError as e:
        print(f"BLAD: {e}")
        return None
    if not questions:
        print("BLAD: Nie udalo sie wygenerowac pytan.")
        return None
    print(f"  Wygenerowano {len(questions)} pytan.")

    # 5. Petla ewaluacji
    print(f"\n[4/5] Ewaluacja ({len(questions)} pytan)...")
    results: List[Dict] = []
    interrupted = False

    def handle_interrupt(sig, frame):
        nonlocal interrupted
        interrupted = True
        print("\n\nPrzerwano (Ctrl+C). Zapisuje wyniki...")

    signal.signal(signal.SIGINT, handle_interrupt)

    for i, question in enumerate(questions):
        if interrupted:
            break
        if cost_guard.should_stop():
            print(f"\nOSIAGNIETO LIMIT (${cost_guard.total_cost:.3f} >= ${max_cost}). Zatrzymuje.")
            break

        q_num = i + 1
        print(f"\n  [{q_num}/{len(questions)}] {question['query'][:70]}...")
        query_start = time.time()

        # RAG query
        try:
            answer, retrieved_chunks = ask(question["query"], top_k=8)
        except Exception as e:
            print(f"    BLAD RAG: {e}")
            results.append(_error_result(question, str(e)))
            continue

        # Koszt RAG z metrics sesji
        rag_cost = 0.0
        metrics = get_last_query_metrics()
        if metrics and metrics.get("query") == question["query"]:
            rag_cost = metrics.get("estimated_cost_usd", 0.0)

        warning = cost_guard.add_rag_cost(rag_cost)
        if warning:
            print(f"  {warning}")
            if not cost_guard.prompt_user_to_continue():
                interrupted = True
                break

        # Ocena przez LLM
        print(f"    Oceniam...")
        eval_result = evaluate(
            query=question["query"],
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            expected_topics=question.get("expected_topics", []),
            cost_guard=cost_guard,
        )

        duration_s = time.time() - query_start
        result = {
            "id": question["id"],
            "query": question["query"],
            "answer": answer,
            "retrieved_chunks": retrieved_chunks,
            "expected_topics": question.get("expected_topics", []),
            "difficulty": question.get("difficulty", "medium"),
            "document_name": question.get("document_name", "?"),
            "rag_cost_usd": rag_cost,
            "correctness": eval_result["correctness"],
            "helpfulness": eval_result["helpfulness"],
            "faithfulness": eval_result["faithfulness"],
            "avg_score": eval_result["avg_score"],
            "explanation": eval_result["explanation"],
            "issues": eval_result["issues"],
            "eval_cost_usd": eval_result["eval_cost_usd"],
            "duration_s": duration_s,
        }
        results.append(result)

        print(
            f"    C:{eval_result['correctness']}/10 "
            f"H:{eval_result['helpfulness']}/10 "
            f"F:{eval_result['faithfulness']}/10 "
            f"| ${rag_cost + eval_result['eval_cost_usd']:.4f}"
        )

        if q_num % PARTIAL_SAVE_EVERY == 0:
            save_partial_results(results, output_path)
            print(f"    (Checkpoint: {q_num} pytan)")

        if cost_guard.should_stop():
            print(f"\n  Limit kosztow osiagniety po pytaniu {q_num}.")
            break

    # 6. Generuj raport
    print(f"\n[5/5] Generuje raport Markdown...")
    total_duration = time.time() - start_time

    config = {
        "model": os.getenv("CHAT_MODEL", "gpt-4o-mini"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "n_documents": db_stats["n_documents"],
        "n_chunks_total": db_stats["n_chunks_total"],
        "n_questions": len(results),
        "total_duration_s": total_duration,
        "start_time": start_datetime,
    }

    try:
        report_path = generate_report(
            results=results,
            config=config,
            output_path=output_path,
            cost_guard=cost_guard,
        )
        print(f"\nRaport zapisany: {report_path}")
        print(f"Koszty: {cost_guard.summary()}")
        print("=" * 60)
        return report_path
    except Exception as e:
        print(f"BLAD generowania raportu: {e}")
        save_partial_results(results, output_path)
        fallback = output_path.replace(".md", "_partial.json")
        print(f"Zapisano czesciowe wyniki: {fallback}")
        return None


def _error_result(question: Dict, error_msg: str) -> Dict:
    return {
        "id": question["id"],
        "query": question["query"],
        "answer": f"(BLAD: {error_msg})",
        "retrieved_chunks": [],
        "expected_topics": question.get("expected_topics", []),
        "difficulty": question.get("difficulty", "medium"),
        "document_name": question.get("document_name", "?"),
        "rag_cost_usd": 0.0,
        "correctness": 0, "helpfulness": 0, "faithfulness": 0,
        "avg_score": 0.0,
        "explanation": error_msg,
        "issues": [error_msg],
        "eval_cost_usd": 0.0,
        "duration_s": 0.0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Automatyczna ewaluacja systemu RAG — Learning Lab"
    )
    parser.add_argument(
        "--questions", type=int, default=20, metavar="N",
        help="Liczba pytan testowych (domyslnie: 20)",
    )
    parser.add_argument(
        "--max-cost", type=float, default=1.00, metavar="USD",
        help="Maksymalny koszt ewaluacji w USD (domyslnie: 1.00)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=REPORTS_DIR,
        help="Folder wyjsciowy raportow",
    )
    args = parser.parse_args()

    result = run_evaluation(
        n_questions=args.questions,
        max_cost=args.max_cost,
        output_dir=args.output_dir,
    )
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
