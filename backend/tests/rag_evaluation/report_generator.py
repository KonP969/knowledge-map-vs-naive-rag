import json
import os
from datetime import datetime
from typing import List, Dict, Optional

from openai import OpenAI

from .cost_guard import calc_openai_cost, CostGuard


def generate_report(
    results: List[Dict],
    config: Dict,
    output_path: str,
    cost_guard: Optional[CostGuard] = None,
) -> str:
    """
    Generuje raport Markdown i zapisuje do output_path.
    Zwraca sciezke zapisanego pliku.

    results: lista dict z polami:
      {id, query, answer, retrieved_chunks, expected_topics, difficulty,
       document_name, rag_cost_usd, correctness, helpfulness, faithfulness,
       avg_score, explanation, issues, eval_cost_usd, duration_s}
    config: {model, embedding_model, n_documents, n_chunks_total, n_questions,
             total_duration_s, start_time}
    """
    sections = [
        _header(config),
        _config_and_summary(results, config),
        _costs(results),
        _table(results),
        _top_bottom(results),
        _detailed(results),
        _conclusions(results, config, cost_guard),
    ]

    content = "\n\n".join(s for s in sections if s)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


def save_partial_results(results: List[Dict], output_path: str) -> None:
    """Zapisuje czesciowe wyniki jako JSON (checkpoint co 5 pytan)."""
    json_path = output_path.replace(".md", "_partial.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)


def _header(config: Dict) -> str:
    return f"# Raport Ewaluacji RAG — {config.get('start_time', datetime.now().strftime('%Y-%m-%d %H:%M'))}"


def _config_and_summary(results: List[Dict], config: Dict) -> str:
    total_s = config.get("total_duration_s", 0)
    duration = f"{int(total_s // 60)}m {int(total_s % 60)}s"

    avg_c = _avg(results, "correctness")
    avg_h = _avg(results, "helpfulness")
    avg_f = _avg(results, "faithfulness")
    avg_overall = round((avg_c + avg_h + avg_f) / 3.0, 2)

    return (
        f"## Konfiguracja\n"
        f"- Model: {config.get('model', 'gpt-4o-mini')}"
        f" | Embeddingi: {config.get('embedding_model', 'text-embedding-3-small')}\n"
        f"- Dokumenty w bazie: {config.get('n_documents', '?')}"
        f" | Chunki: {config.get('n_chunks_total', '?')}\n"
        f"- Pytania testowe: {len(results)} | Czas testu: {duration}\n\n"
        f"## Podsumowanie Wynikow\n"
        f"| Metryka | Wynik |\n"
        f"|---------|-------|\n"
        f"| Avg Correctness | {avg_c:.1f} / 10 |\n"
        f"| Avg Helpfulness | {avg_h:.1f} / 10 |\n"
        f"| Avg Faithfulness | {avg_f:.1f} / 10 |\n"
        f"| **Avg Overall** | **{avg_overall:.1f} / 10** |"
    )


def _costs(results: List[Dict]) -> str:
    total_rag = sum(r.get("rag_cost_usd", 0) for r in results)
    total_eval = sum(r.get("eval_cost_usd", 0) for r in results)
    total_all = total_rag + total_eval

    return (
        f"## Koszty\n"
        f"| | RAG Queries | Ewaluacja LLM | Lacznie |\n"
        f"|---|---|---|---|\n"
        f"| Koszt USD | ${total_rag:.4f} | ${total_eval:.4f} | **${total_all:.4f}** |"
    )


def _table(results: List[Dict]) -> str:
    if not results:
        return ""
    header = (
        "## Tabela Wynikow\n"
        "| # | Pytanie (skrot) | Correctness | Helpfulness | Faithfulness | Avg | Koszt |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for r in results:
        q_short = (r["query"][:50] + "...") if len(r["query"]) > 50 else r["query"]
        q_short = q_short.replace("|", "\\|")
        cost = r.get("rag_cost_usd", 0) + r.get("eval_cost_usd", 0)
        rows.append(
            f"| {r['id']} | {q_short} | {r['correctness']}/10 | "
            f"{r['helpfulness']}/10 | {r['faithfulness']}/10 | "
            f"{r['avg_score']:.1f} | ${cost:.4f} |"
        )
    return header + "\n".join(rows)


def _top_bottom(results: List[Dict]) -> str:
    if len(results) < 3:
        return ""
    sorted_r = sorted(results, key=lambda r: r.get("avg_score", 0), reverse=True)

    def fmt(r: Dict, rank: int) -> str:
        return (
            f"**{rank}. Test #{r['id']} — Avg: {r['avg_score']:.1f}/10** "
            f"(C:{r['correctness']} H:{r['helpfulness']} F:{r['faithfulness']})\n"
            f"- Pytanie: *{r['query'][:100]}*\n"
            f"- Wyjasnienie: {r.get('explanation', '')[:150]}"
        )

    top = "## Najlepsze Odpowiedzi (Top 3)\n\n" + "\n\n".join(
        fmt(r, i + 1) for i, r in enumerate(sorted_r[:3])
    )
    bottom = "## Najslabsze Odpowiedzi (Bottom 3)\n\n" + "\n\n".join(
        fmt(r, i + 1) for i, r in enumerate(sorted_r[-3:])
    )
    return top + "\n\n" + bottom


def _detailed(results: List[Dict]) -> str:
    parts = ["## Szczegolowe Wyniki"]
    for r in results:
        chunks = r.get("retrieved_chunks", [])
        chunk_lines = []
        for i, c in enumerate(chunks[:5], 1):
            preview = c.get("content", "")[:150].replace("\n", " ")
            chunk_lines.append(
                f"- [{i}] **{c.get('document_name', '?')}** "
                f"(score: {c.get('score', 0):.3f}): {preview}..."
            )
        if len(chunks) > 5:
            chunk_lines.append(f"- *(i {len(chunks) - 5} wiecej)*")
        chunks_str = "\n".join(chunk_lines) if chunk_lines else "*(brak)*"

        issues_list = r.get("issues", [])
        issues_str = (
            "\n".join(f"  - {issue}" for issue in issues_list)
            if issues_list else "  *(brak)*"
        )

        parts.append(
            f"### Test {r['id']} — {r.get('difficulty', 'medium').upper()}\n"
            f"**Pytanie:** {r['query']}\n\n"
            f"**Odpowiedz systemu:**\n"
            f"{r.get('answer', '(brak)')}\n\n"
            f"**Pobrane zrodla ({len(chunks)} fragmentow):**\n"
            f"{chunks_str}\n\n"
            f"**Ocena:** Correctness: {r['correctness']}/10"
            f" | Helpfulness: {r['helpfulness']}/10"
            f" | Faithfulness: {r['faithfulness']}/10"
            f" | Avg: {r['avg_score']:.1f}\n\n"
            f"**Wyjasnienie seedziego:** {r.get('explanation', '')}\n\n"
            f"**Problemy:**\n{issues_str}\n\n"
            f"**Koszty:** RAG: ${r.get('rag_cost_usd', 0):.4f}"
            f" | Eval: ${r.get('eval_cost_usd', 0):.4f}"
            f" | Czas: {r.get('duration_s', 0):.1f}s"
        )

    return "\n\n---\n\n".join(parts)


def _conclusions(
    results: List[Dict],
    config: Dict,
    cost_guard: Optional[CostGuard],
) -> str:
    """Generuje wnioski i rekomendacje przez LLM."""
    if not results:
        return "## Wnioski i Rekomendacje\n\nBrak danych."

    all_issues: List[str] = []
    for r in results:
        all_issues.extend(r.get("issues", []))
    issues_sample = "; ".join(all_issues[:8]) if all_issues else "brak"

    summary = (
        f"Wyniki ewaluacji RAG:\n"
        f"- Avg Correctness: {_avg(results, 'correctness'):.1f}/10\n"
        f"- Avg Helpfulness: {_avg(results, 'helpfulness'):.1f}/10\n"
        f"- Avg Faithfulness: {_avg(results, 'faithfulness'):.1f}/10\n"
        f"- Liczba testow: {len(results)}\n"
        f"- Najczestsze problemy: {issues_sample}\n"
        f"- Model: {config.get('model', 'gpt-4o-mini')}\n"
    )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jestes ekspertem od systemow RAG. Na podstawie wynikow ewaluacji "
                        "napisz konkretne wnioski i rekomendacje do poprawy systemu. "
                        "Odpowiedz po polsku w Markdown (bullet points, max 300 slow)."
                    ),
                },
                {"role": "user", "content": summary},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        if response.usage and cost_guard is not None:
            cost_guard.add_eval_cost(
                calc_openai_cost(
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )
            )
        text = response.choices[0].message.content
    except Exception as e:
        text = f"*(Nie udalo sie wygenerowac wnioskow: {e})*"

    return f"## Wnioski i Rekomendacje\n\n{text}"


def _avg(results: List[Dict], key: str) -> float:
    vals = [r.get(key, 0) for r in results if r.get(key) is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0.0
