# -*- coding: utf-8 -*-
"""Naive-RAG baseline: the yardstick the knowledge-map pipeline has to beat.

Same raw sources, same gold questions, same models, same LLM judge as
`run_gold_eval.py` — only the retrieval differs:

    parsed.md -> fixed-size chunks (800 chars, 150 overlap)
              -> text-embedding-3-small -> top-5 cosine
              -> gpt-4o-mini (temperature 0) answers from those chunks only

It is a fair baseline, not a strawman: the prompt tells the model to admit
when the context doesn't contain the answer, just like the graph pipeline.

    cd backend
    python scripts/run_naive_baseline.py --questions porta_articles
    python scripts/run_naive_baseline.py --questions porta_multihop --top-k 5
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

import numpy as np  # noqa: E402
from openai import OpenAI  # noqa: E402

from tests.rag_evaluation.evaluator import evaluate  # noqa: E402
from tests.rag_evaluation.gold_questions import QUESTION_SETS  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parent.parent / "tests" / "rag_evaluation" / "reports"
EMBED_MODEL = "text-embedding-3-small"
SYSTEM = (
    "Answer the user's question using ONLY the context fragments. Answer in the language "
    "of the question. If the context does not contain the answer, reply exactly: "
    "'Nie znalazłem tej informacji w źródłach.'"
)


def load_chunks(vault: Path, size: int, overlap: int):
    chunks = []
    for d in sorted((vault / "raw").iterdir()):
        p = d / "parsed.md"
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip() if text else d.name
        i = 0
        while i < len(text):
            chunks.append({"doc": title, "text": text[i:i + size]})
            i += size - overlap
    return chunks


def embed(client, texts):
    vecs = []
    for i in range(0, len(texts), 100):
        r = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + 100])
        vecs += [e.embedding for e in r.data]
    v = np.array(vecs)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default="wiki_data/default")
    ap.add_argument("--questions", default="default", choices=sorted(QUESTION_SETS))
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--chunk-size", type=int, default=800)
    ap.add_argument("--overlap", type=int, default=150)
    args = ap.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY missing (backend/.env)", file=sys.stderr)
        return 1

    client = OpenAI()
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    chunks = load_chunks(Path(args.vault), args.chunk_size, args.overlap)
    matrix = embed(client, [c["text"] for c in chunks])
    print("chunks: %d | top-k: %d" % (len(chunks), args.top_k), flush=True)

    rows = []
    questions = QUESTION_SETS[args.questions]
    for i, q in enumerate(questions, 1):
        t0 = time.time()
        sims = matrix @ embed(client, [q["question"]])[0]
        top = np.argsort(-sims)[:args.top_k]
        ctx = [chunks[j] for j in top]
        context = "\n\n".join("[%d] (%s)\n%s" % (k + 1, c["doc"], c["text"]) for k, c in enumerate(ctx))
        resp = client.chat.completions.create(
            model=model, temperature=0,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": "Context:\n%s\n\nQuestion: %s" % (context, q["question"])}],
        )
        answer = resp.choices[0].message.content
        answer_secs = round(time.time() - t0, 1)
        judged = evaluate(
            q["question"], answer,
            [{"content": c["text"], "document_name": c["doc"], "score": float(sims[j])}
             for c, j in zip(ctx, top)],
            q["expected_topics"],
        )
        row = {"id": q["id"], "category": q["category"], "question": q["question"],
               "answer": answer, "answer_secs": answer_secs,
               "docs_in_context": len({c["doc"] for c in ctx})}
        row.update({k: judged.get(k) for k in
                    ("correctness", "helpfulness", "faithfulness", "avg_score", "explanation")})
        rows.append(row)
        print("[%d/%d] %s corr=%s help=%s faith=%s | %.1fs"
              % (i, len(questions), q["id"], row["correctness"], row["helpfulness"],
                 row["faithfulness"], answer_secs), flush=True)

    n = len(rows)
    overall = {m: round(sum(r[m] for r in rows) / n, 2)
               for m in ("correctness", "helpfulness", "faithfulness", "avg_score", "answer_secs")}
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / ("naive-baseline-%s-%s.json" % (args.questions, datetime.now().strftime("%Y-%m-%d-%H%M%S")))
    out.write_text(json.dumps({"args": vars(args), "overall": overall, "rows": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nOVERALL: corr=%(correctness)s help=%(helpfulness)s faith=%(faithfulness)s "
          "avg=%(avg_score)s | %(answer_secs)ss/answer" % overall)
    print("report:", out.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
