"""A tiny flat cosine-similarity vector store.

Backs the semantic-recall layer over the knowledge graph: a few thousand claim vectors fit
comfortably in a NumPy matrix, so an exact cosine scan is instant and needs no external vector
DB. Persisted as a single .npz (matrix + id array)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import numpy as np


class VectorStore:
    def __init__(self) -> None:
        self._ids: List[str] = []
        self._matrix: np.ndarray | None = None  # shape (n, dim), float32

    def add(self, ids: List[str], vectors: List[List[float]]) -> None:
        if len(ids) != len(vectors):
            raise ValueError("ids and vectors must have the same length")
        if not ids:
            return
        block = np.asarray(vectors, dtype=np.float32)
        self._matrix = block if self._matrix is None else np.vstack([self._matrix, block])
        self._ids.extend(ids)

    def search(self, query: List[float], top_k: int) -> List[Tuple[str, float]]:
        if self._matrix is None or len(self._ids) == 0 or top_k <= 0:
            return []
        q = np.asarray(query, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        mat_norms = np.linalg.norm(self._matrix, axis=1)
        mat_norms[mat_norms == 0] = 1e-12
        sims = (self._matrix @ q) / (mat_norms * q_norm)
        k = min(top_k, len(self._ids))
        # argpartition for the top-k, then sort those by score desc
        idx = np.argpartition(-sims, k - 1)[:k]
        idx = idx[np.argsort(-sims[idx])]
        return [(self._ids[i], float(sims[i])) for i in idx]

    def save(self, path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        matrix = self._matrix if self._matrix is not None else np.zeros((0, 0), dtype=np.float32)
        np.savez(path, matrix=matrix, ids=np.array(self._ids, dtype=object))

    @classmethod
    def load(cls, path) -> "VectorStore":
        data = np.load(Path(path), allow_pickle=True)
        vs = cls()
        vs._ids = list(data["ids"])
        matrix = data["matrix"]
        vs._matrix = matrix.astype(np.float32) if matrix.size else None
        return vs

    @property
    def ids(self) -> List[str]:
        return list(self._ids)

    def __len__(self) -> int:
        return len(self._ids)

    def __contains__(self, _id: str) -> bool:
        return _id in self._ids
