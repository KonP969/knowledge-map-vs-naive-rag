"""
Hard RAG evaluation — edge cases:
  out_of_scope : pytania których odpowiedzi nie ma w bazie
  synthesis    : pytania wymagające syntezy z wielu dokumentów
  ambiguous    : pytania bez kontekstu / bardzo ogólne
  multi_hop    : pytania wymagające rozumowania przez kilka konceptów
"""
import os
import time
from datetime import datetime
from typing import List, Dict, Optional

from dotenv import load_dotenv

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, ".."))
for _env_path in [
    os.path.join(_BACKEND_DIR, ".env"),
    os.path.join(_REPO_ROOT, ".worktrees", "feature", "scaffolding", "backend", ".env"),
]:
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        break

from .rag_client import ask, get_last_query_metrics, health_check
from .cost_guard import CostGuard
from .evaluator import evaluate

REPORTS_DIR = os.path.join(_SCRIPT_DIR, "reports")

TYPE_LABEL = {
    "out_of_scope": "OUT OF SCOPE",
    "synthesis":    "SYNTEZA",
    "ambiguous":    "NIEJEDNOZNACZNE",
    "multi_hop":    "MULTI-HOP",
}

HARD_QUESTIONS: List[Dict] = [
    # ── OUT OF SCOPE (3) ────────────────────────────────────────────
    {
        "id": 1,
        "query": "Jaka jest cena drzwi PORTA NATURA CLASSIC w rozmiarze 80 cm?",
        "type": "out_of_scope",
        "note": "Ceny produktów nie są w artykułach blogowych — system powinien odmówić odpowiedzi.",
        "expected_topics": ["System powinien odmówić — tej informacji nie ma w artykułach"],
    },
    {
        "id": 2,
        "query": "Jak samodzielnie zamontować ościeżnicę regulowaną PORTA SYSTEM krok po kroku?",
        "type": "out_of_scope",
        "note": "Instrukcja montażu nie powinna być w bazie artykułów blogowych.",
        "expected_topics": ["System powinien odmówić — tej informacji nie ma w artykułach"],
    },
    {
        "id": 3,
        "query": "Jakie są standardowe wymiary drzwi wewnętrznych w Polsce według normy budowlanej?",
        "type": "out_of_scope",
        "note": "Normy budowlane nie są treścią artykułów o aranżacji wnętrz.",
        "expected_topics": ["System powinien odmówić lub zaznaczyć brak tej informacji w bazie"],
    },
    # ── SYNTHESIS (3) ───────────────────────────────────────────────
    {
        "id": 4,
        "query": "Jakie elementy wspólne łączą styl boho i styl vintage według artykułów w bazie?",
        "type": "synthesis",
        "note": "Wymaga jednoczesnej syntezy artykułu o boho i artykułu o vintage/retro.",
        "expected_topics": [
            "boho", "vintage", "drewno", "dodatki dekoracyjne", "meble",
            "Odpowiedź powinna syntetyzować informacje z WIELU dokumentów",
        ],
    },
    {
        "id": 5,
        "query": "W których stylach wnętrzarskich opisanych w artykułach polecane są drzwi ukryte PORTA HIDE?",
        "type": "synthesis",
        "note": "PORTA HIDE pojawia się w wielu artykułach — dobra odpowiedź wymaga syntezy.",
        "expected_topics": [
            "PORTA HIDE", "minimalizm", "skandynawski", "nowoczesny",
            "Odpowiedź powinna syntetyzować informacje z WIELU dokumentów",
        ],
    },
    {
        "id": 6,
        "query": "Jakie kolory ścian są polecane zarówno do sypialni, jak i do łazienki?",
        "type": "synthesis",
        "note": "Cross-document: artykuł o sypialni + artykuł o łazience — kolory wspólne dla obu.",
        "expected_topics": [
            "kolory", "sypialnia", "łazienka", "biel", "pastele", "beż",
            "Odpowiedź powinna syntetyzować informacje z WIELU dokumentów",
        ],
    },
    # ── AMBIGUOUS (2) ───────────────────────────────────────────────
    {
        "id": 7,
        "query": "Jakie drzwi do salonu?",
        "type": "ambiguous",
        "note": "Pytanie skrajnie ogólne — brak stylu, koloru, preferencji. Jak system reaguje?",
        "expected_topics": [
            "salon", "drzwi",
            "Pytanie niejednoznaczne — dobra odpowiedź pyta o kontekst lub daje przekrojowy przegląd",
        ],
    },
    {
        "id": 8,
        "query": "Co jest teraz modne?",
        "type": "ambiguous",
        "note": "Skrajnie ogólne — system powinien doprecyzować zakres lub podać przegląd trendów.",
        "expected_topics": [
            "trendy", "kolory", "styl",
            "Pytanie niejednoznaczne — dobra odpowiedź pyta o kontekst lub daje przekrojowy przegląd",
        ],
    },
    # ── MULTI-HOP (2) ───────────────────────────────────────────────
    {
        "id": 9,
        "query": (
            "Mam białe ściany i urządzam mieszkanie w stylu skandynawskim. "
            "Jakie konkretne modele drzwi PORTA będą najlepsze i dlaczego?"
        ),
        "type": "multi_hop",
        "note": "Wymaga: artykuł o białym pokoju + styl skandynawski + konkretne produkty PORTA.",
        "expected_topics": [
            "białe ściany", "skandynawski", "PORTA HIDE", "minimalizm",
            "Odpowiedź wymaga rozumowania i połączenia informacji z kilku artykułów",
        ],
    },
    {
        "id": 10,
        "query": (
            "Jaki kolor drzwi pasowałby zarówno do łazienki w stylu francuskim, "
            "jak i do nowoczesnego salonu?"
        ),
        "type": "multi_hop",
        "note": "Cross-style: artykuł o łazience francuskiej + artykuł o nowoczesnym stylu.",
        "expected_topics": [
            "styl francuski", "nowoczesny", "kolor drzwi", "łazienka", "salon",
            "Odpowiedź wymaga rozumowania i połączenia informacji z kilku artykułów",
        ],
    },
]


def run_hard_evaluation() -> Optional[str]:
    print("=" * 60)
    print("RAG Hard Evaluation — Edge Cases")
    print("=" * 60)

    if not health_check():
        print("BLAD: Backend nie odpowiada na http://localhost:8000/health")
        return None
    if not os.getenv("OPENAI_API_KEY"):
        print("BLAD: Brak OPENAI_API_KEY")
        return None

    cost_guard = CostGuard(threshold_usd=0.10, max_usd=0.50)
    start_time = time.time()
    start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M")
    results: List[Dict] = []

    for q in HARD_QUESTIONS:
        label = TYPE_LABEL.get(q["type"], q["type"])
        print(f"\n  [{q['id']}/10] [{label}] {q['query'][:60]}...")
        query_start = time.time()

        try:
            answer, retrieved_chunks = ask(q["query"], top_k=8)
        except Exception as e:
            print(f"    BLAD RAG: {e}")
            continue

        rag_cost = 0.0
        metrics = get_last_query_metrics()
        if metrics and metrics.get("query") == q["query"]:
            rag_cost = metrics.get("estimated_cost_usd", 0.0)
        cost_guard.add_rag_cost(rag_cost)

        print("    Oceniam...")
        eval_result = evaluate(
            query=q["query"],
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            expected_topics=q["expected_topics"],
            cost_guard=cost_guard,
        )

        duration_s = time.time() - query_start
        results.append({
            "id": q["id"],
            "query": q["query"],
            "answer": answer,
            "retrieved_chunks": retrieved_chunks,
            "type": q["type"],
            "note": q["note"],
            "difficulty": "hard",
            "document_name": "?",
            "rag_cost_usd": rag_cost,
            "correctness": eval_result["correctness"],
            "helpfulness": eval_result["helpfulness"],
            "faithfulness": eval_result["faithfulness"],
            "avg_score": eval_result["avg_score"],
            "explanation": eval_result["explanation"],
            "issues": eval_result["issues"],
            "eval_cost_usd": eval_result["eval_cost_usd"],
            "duration_s": duration_s,
        })
        print(
            f"    C:{eval_result['correctness']}/10 "
            f"H:{eval_result['helpfulness']}/10 "
            f"F:{eval_result['faithfulness']}/10 "
            f"| ${rag_cost + eval_result['eval_cost_usd']:.4f}"
        )

    total_duration = time.time() - start_time
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = os.path.join(REPORTS_DIR, f"{ts}_hard_test_report.md")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    content = _build_report(results, start_datetime, total_duration, cost_guard)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\nRaport zapisany: {report_path}")
    print(f"Koszty: {cost_guard.summary()}")
    print("=" * 60)
    return report_path


# ── Report builder ────────────────────────────────────────────────────────────

def _avg(data: List[Dict], key: str) -> float:
    vals = [r[key] for r in data if r.get(key) is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _build_report(
    results: List[Dict],
    start_datetime: str,
    total_duration: float,
    cost_guard: CostGuard,
) -> str:
    duration = f"{int(total_duration // 60)}m {int(total_duration % 60)}s"
    total_rag = sum(r.get("rag_cost_usd", 0) for r in results)
    total_eval = sum(r.get("eval_cost_usd", 0) for r in results)
    avg_c = _avg(results, "correctness")
    avg_h = _avg(results, "helpfulness")
    avg_f = _avg(results, "faithfulness")
    avg_all = round((avg_c + avg_h + avg_f) / 3, 2)

    parts = []

    # ── Header ──────────────────────────────────────────────────────
    parts.append(f"# Raport Hard Evaluation — Edge Cases — {start_datetime}")

    # ── Intro ────────────────────────────────────────────────────────
    parts.append(
        "## O teście\n\n"
        "Standardowa ewaluacja (22 pytania EASY/MEDIUM) uzyskała Avg Overall **9.4/10**, "
        "ale pytania były generowane *z własnych dokumentów*, co zawyżało wyniki. "
        "Ten test sprawdza cztery scenariusze trudne produkcyjnie:\n\n"
        "| Kategoria | Opis | Oczekiwane zachowanie |\n"
        "|-----------|------|----------------------|\n"
        "| **OUT OF SCOPE** | Odpowiedź nie istnieje w bazie | Odmowa bez halucynacji |\n"
        "| **SYNTEZA** | Odpowiedź rozproszona po wielu artykułach | Łączenie informacji z wielu źródeł |\n"
        "| **NIEJEDNOZNACZNE** | Pytanie bez kontekstu | Prośba o doprecyzowanie lub przekrojowy przegląd |\n"
        "| **MULTI-HOP** | Wnioskowanie przez kilka konceptów | Łączenie logiczne wielu faktów |"
    )

    # ── Config ───────────────────────────────────────────────────────
    parts.append(
        f"## Konfiguracja\n"
        f"- Pytania: {len(results)} | Czas: {duration}\n"
        f"- Koszt: RAG ${total_rag:.4f} | Eval ${total_eval:.4f} | Łącznie **${total_rag + total_eval:.4f}**"
    )

    # ── Overall summary ──────────────────────────────────────────────
    parts.append(
        f"## Podsumowanie Ogólne\n"
        f"| Metryka | Ten test (edge cases) | Poprzedni test (EASY/MEDIUM) |\n"
        f"|---------|----------------------|------------------------------|\n"
        f"| Avg Correctness  | {avg_c:.1f} / 10 | 9.9 / 10 |\n"
        f"| Avg Helpfulness  | {avg_h:.1f} / 10 | 8.3 / 10 |\n"
        f"| Avg Faithfulness | {avg_f:.1f} / 10 | 10.0 / 10 |\n"
        f"| **Avg Overall**  | **{avg_all:.1f} / 10** | **9.4 / 10** |"
    )

    # ── Per-category breakdown ───────────────────────────────────────
    cat_rows = []
    for cat in ["out_of_scope", "synthesis", "ambiguous", "multi_hop"]:
        sub = [r for r in results if r["type"] == cat]
        if not sub:
            continue
        c = _avg(sub, "correctness")
        h = _avg(sub, "helpfulness")
        f = _avg(sub, "faithfulness")
        overall = round((c + h + f) / 3, 2)
        cat_rows.append(
            f"| {TYPE_LABEL[cat]} | {len(sub)} "
            f"| {c:.1f} | {h:.1f} | {f:.1f} | **{overall:.1f}** |"
        )
    parts.append(
        "## Wyniki wg Kategorii\n"
        "| Kategoria | N | Correctness | Helpfulness | Faithfulness | Overall |\n"
        "|-----------|---|-------------|-------------|--------------|--------|\n"
        + "\n".join(cat_rows)
    )

    # ── Results table ────────────────────────────────────────────────
    rows = []
    for r in results:
        q_short = (r["query"][:45] + "...") if len(r["query"]) > 45 else r["query"]
        q_short = q_short.replace("|", "\\|")
        rows.append(
            f"| {r['id']} | {TYPE_LABEL.get(r['type'], r['type'])} | {q_short} "
            f"| {r['correctness']}/10 | {r['helpfulness']}/10 "
            f"| {r['faithfulness']}/10 | {r['avg_score']:.1f} |"
        )
    parts.append(
        "## Tabela Wyników\n"
        "| # | Typ | Pytanie | C | H | F | Avg |\n"
        "|---|-----|---------|---|---|---|-----|\n"
        + "\n".join(rows)
    )

    # ── Detailed results ─────────────────────────────────────────────
    detail_parts = ["## Szczegółowe Wyniki"]
    for r in results:
        chunks = r.get("retrieved_chunks", [])
        chunk_lines = []
        for i, c in enumerate(chunks[:5], 1):
            preview = c.get("content", "")[:120].replace("\n", " ")
            chunk_lines.append(
                f"- [{i}] **{c.get('document_name', '?')}** "
                f"(score: {c.get('score', 0):.3f}): {preview}..."
            )
        if len(chunks) > 5:
            chunk_lines.append(f"- *(i {len(chunks)-5} więcej)*")
        chunks_str = "\n".join(chunk_lines) if chunk_lines else "*(brak)*"
        issues_str = (
            "\n".join(f"  - {iss}" for iss in r.get("issues", []))
            if r.get("issues") else "  *(brak)*"
        )

        detail_parts.append(
            f"### Test {r['id']} — {TYPE_LABEL.get(r['type'], r['type'])}\n"
            f"> **Cel testu:** {r['note']}\n\n"
            f"**Pytanie:** {r['query']}\n\n"
            f"**Odpowiedź systemu:**\n{r.get('answer', '(brak)')}\n\n"
            f"**Pobrane źródła ({len(chunks)} fragmentów):**\n{chunks_str}\n\n"
            f"**Ocena:** Correctness: {r['correctness']}/10 | "
            f"Helpfulness: {r['helpfulness']}/10 | "
            f"Faithfulness: {r['faithfulness']}/10 | "
            f"Avg: {r['avg_score']:.1f}\n\n"
            f"**Wyjaśnienie sędziego:** {r.get('explanation', '')}\n\n"
            f"**Problemy:**\n{issues_str}\n\n"
            f"**Koszty:** RAG: ${r.get('rag_cost_usd', 0):.4f} | "
            f"Eval: ${r.get('eval_cost_usd', 0):.4f} | "
            f"Czas: {r.get('duration_s', 0):.1f}s"
        )
    parts.append("\n\n---\n\n".join(detail_parts))

    # ── Analysis ─────────────────────────────────────────────────────
    oos = [r for r in results if r["type"] == "out_of_scope"]
    hallucinated = [r for r in oos if r["faithfulness"] < 7]
    refused_ok = [r for r in oos if r["faithfulness"] >= 9 and r["correctness"] >= 6]

    syn = [r for r in results if r["type"] == "synthesis"]
    good_syn = [r for r in syn if r["avg_score"] >= 7.5]

    amb = [r for r in results if r["type"] == "ambiguous"]
    mh = [r for r in results if r["type"] == "multi_hop"]

    note_oos = (
        "**UWAGA:** Dla pytań OUT OF SCOPE wynik C:7 H:3 F:10 oznacza *poprawne zachowanie* "
        "— system odmówił bez halucynacji. Halucynacja byłaby F<7."
    )

    parts.append(
        f"## Analiza Wyników\n\n"
        f"{note_oos}\n\n"
        f"### Out of Scope ({len(oos)} pytań)\n"
        f"- Poprawna odmowa (F≥9 i C≥6): **{len(refused_ok)}/{len(oos)}**\n"
        f"- Halucynacje (F<7): **{len(hallucinated)}/{len(oos)}**\n\n"
        f"### Synteza ({len(syn)} pytań)\n"
        f"- Satysfakcjonujące (Avg≥7.5): **{len(good_syn)}/{len(syn)}**\n\n"
        f"### Niejednoznaczne ({len(amb)} pytań)\n"
        f"- Avg: {_avg(amb, 'avg_score'):.1f}/10\n\n"
        f"### Multi-Hop ({len(mh)} pytań)\n"
        f"- Avg: {_avg(mh, 'avg_score'):.1f}/10\n\n"
        f"### Wnioski końcowe\n"
        f"Edge-case Overall: **{avg_all:.1f}/10** vs standardowy test: **9.4/10**. "
        + (
            "Różnica wskazuje konkretne obszary wymagające poprawy."
            if avg_all < 8.5
            else "Wyniki są satysfakcjonujące nawet na pytaniach trudnych."
        )
    )

    return "\n\n".join(parts)


if __name__ == "__main__":
    run_hard_evaluation()
