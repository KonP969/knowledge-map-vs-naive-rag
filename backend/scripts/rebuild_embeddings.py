"""Embed every claim in a vault and persist the claim-embedding index.

    python scripts/rebuild_embeddings.py                       # WIKI_DATA_DIR or wiki_data/default
    python scripts/rebuild_embeddings.py --vault wiki_data/.example
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
load_dotenv(_BACKEND / ".env")

from services.wiki_store import WikiStore
from services.semantic_index import build_claim_index, claim_index_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.getenv("WIKI_DATA_DIR", "wiki_data/default"))
    args = ap.parse_args()

    store = WikiStore(root=Path(args.vault))
    n_claims = len(store.read_all_claims())
    print(f"embedding {n_claims} claims in {args.vault}…", flush=True)
    vs = build_claim_index(store)
    print(f"done: {len(vs)} vectors -> {claim_index_path(store)}", flush=True)


if __name__ == "__main__":
    main()
