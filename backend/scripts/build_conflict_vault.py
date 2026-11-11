# -*- coding: utf-8 -*-
"""Builds a SEPARATE vault for the contradiction benchmark.

Copies a source vault (default: wiki_data/default, the 15 PORTA articles) to
wiki_data/bench_conflict and ingests the fixture docs from
tests/rag_evaluation/fixtures/conflict/ — each one contradicts facts already in
the corpus. The source vault is never touched.

    cd backend
    python scripts/build_conflict_vault.py
    python scripts/run_gold_eval.py      --vault wiki_data/bench_conflict --questions porta_conflict
    python scripts/run_naive_baseline.py --vault wiki_data/bench_conflict --questions porta_conflict
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from services.ingest_pipeline import ingest_source  # noqa: E402
from services.wiki_store import WikiStore  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "rag_evaluation" / "fixtures" / "conflict"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="wiki_data/default")
    ap.add_argument("--target", default="wiki_data/bench_conflict")
    ap.add_argument("--force", action="store_true", help="rebuild if the target already exists")
    args = ap.parse_args()

    src, dst = Path(args.source), Path(args.target)
    if not (src / "raw").is_dir():
        print("ERROR: %s has no raw/ — not a vault" % src, file=sys.stderr)
        return 1
    if dst.exists():
        if not args.force:
            print("ERROR: %s exists (use --force to rebuild)" % dst, file=sys.stderr)
            return 1
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print("copied %s -> %s" % (src, dst))

    store = WikiStore(root=dst)
    for doc in sorted(FIXTURES.glob("*.md")):
        res = ingest_source(doc, store)
        print("ingest %-36s %s | claims=%d conflicts_detected=%d%s"
              % (doc.name, res.status, res.claims_added, len(res.conflicts),
                 " | " + res.error if res.error else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
