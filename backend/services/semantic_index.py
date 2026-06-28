"""Build and load the claim-embedding index — the bridge between the wiki graph and the
semantic (vector) world. Each claim's verbatim text becomes a vector; retrieval searches these
to find facts by meaning, then expands via the graph."""
from pathlib import Path
from typing import Optional

from services.embeddings_service import EmbedFn, embed_texts
from services.vector_store import VectorStore
from services.wiki_store import WikiStore


def claim_index_path(store: WikiStore) -> Path:
    return store.root / "wiki" / "embeddings" / "claims.npz"


def build_claim_index(store: WikiStore, *, embed_fn: Optional[EmbedFn] = None) -> VectorStore:
    """Embed every claim's text and persist a VectorStore keyed by claim id."""
    claims = store.read_all_claims()
    vs = VectorStore()
    if claims:
        vectors = embed_texts([c.text for c in claims], embed_fn=embed_fn)
        vs.add([c.id for c in claims], vectors)
    vs.save(claim_index_path(store))
    return vs


def load_claim_index(store: WikiStore) -> Optional[VectorStore]:
    path = claim_index_path(store)
    if not path.exists():
        return None
    return VectorStore.load(path)


def add_claims_to_index(store: WikiStore, claims, *, embed_fn: Optional[EmbedFn] = None) -> VectorStore:
    """Incrementally embed and append new claims to the (possibly absent) index.
    Claims already present are skipped, so it is safe to call with overlapping sets."""
    vs = load_claim_index(store) or VectorStore()
    existing = set(vs.ids)
    new = [c for c in claims if c.id not in existing]
    if new:
        vectors = embed_texts([c.text for c in new], embed_fn=embed_fn)
        vs.add([c.id for c in new], vectors)
        vs.save(claim_index_path(store))
    return vs
