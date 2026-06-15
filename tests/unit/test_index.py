"""T014 [US1]: cosine ranking, threshold, k limit, and tie-break determinism."""

from __future__ import annotations

import numpy as np

from skill_picker.index import Index


def _v(*xs) -> np.ndarray:
    return np.array(xs, dtype=np.float32)


def test_ranking_order_and_k_limit():
    idx = Index()
    idx.build([
        ("a", "A", _v(1.0, 0.0)),
        ("b", "B", _v(0.0, 1.0)),
        ("c", "C", _v(0.7071, 0.7071)),
    ])
    res = idx.select(_v(1.0, 0.0), k=2, threshold=0.0)
    assert [c.id for c in res] == ["a", "c"]
    assert res[0].score >= res[1].score


def test_threshold_excludes_low_scores():
    idx = Index()
    idx.build([("a", "A", _v(1.0, 0.0)), ("b", "B", _v(0.0, 1.0))])
    res = idx.select(_v(1.0, 0.0), k=5, threshold=0.5)
    assert [c.id for c in res] == ["a"]


def test_tie_break_is_deterministic_by_id():
    same = _v(1.0, 0.0)
    idx = Index()
    idx.build([("z", "Z", same), ("a", "A", same)])
    res = idx.select(_v(1.0, 0.0), k=5, threshold=0.0)
    assert [c.id for c in res] == ["a", "z"]


def test_empty_index_returns_empty():
    idx = Index()
    assert idx.select(_v(1.0, 0.0), k=5, threshold=0.0) == []
