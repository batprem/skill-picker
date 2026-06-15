"""In-memory cosine-similarity index over normalized skill vectors.

Brute-force matrix-vector product; sufficient and deterministic for the target scale
(tens to a few hundred skills) per research R2.
"""

from __future__ import annotations

import numpy as np

from .models import Candidate


class Index:
    """Ranks skills by cosine similarity to a query vector."""

    def __init__(self):
        self._ids: list[str] = []
        self._names: list[str] = []
        self._mat: np.ndarray = np.zeros((0, 0), dtype=np.float32)

    def build(self, entries: list[tuple[str, str, np.ndarray]]) -> None:
        """Build from (id, name, normalized_vector) tuples."""
        self._ids = [e[0] for e in entries]
        self._names = [e[1] for e in entries]
        if entries:
            self._mat = np.stack([np.asarray(e[2], dtype=np.float32) for e in entries])
        else:
            self._mat = np.zeros((0, 0), dtype=np.float32)

    def __len__(self) -> int:
        return len(self._ids)

    def select(self, query_vec: np.ndarray, k: int, threshold: float) -> list[Candidate]:
        """Return up to k candidates with score >= threshold, ranked by descending score.

        Ties are broken deterministically by skill id (FR-013).
        """
        if len(self._ids) == 0:
            return []
        scores = self._mat @ np.asarray(query_vec, dtype=np.float32)
        ranked = sorted(
            zip(self._ids, self._names, scores.tolist()),
            key=lambda t: (-t[2], t[0]),
        )
        out: list[Candidate] = []
        for sid, name, score in ranked:
            if score < threshold:
                continue
            out.append(Candidate(id=sid, name=name, score=float(score)))
            if len(out) >= k:
                break
        return out
