"""Embed every claim in the active store and persist the claim-embedding index.

Run from backend/:  python scripts/rebuild_embeddings.py
"""
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
    store = WikiStore(root=Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default")))
    n_claims = len(store.read_all_claims())
    print(f"embedding {n_claims} claims…", flush=True)
    vs = build_claim_index(store)
    print(f"done: {len(vs)} vectors -> {claim_index_path(store)}", flush=True)


if __name__ == "__main__":
    main()
