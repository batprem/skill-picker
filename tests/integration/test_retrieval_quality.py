"""T012 [US1] / SC-001: intended skill lands in top-K for >= 90% of labeled queries.

Runs with the deterministic HashingEmbedder so it is reliable offline; the same assertion
holds for the vLLM embedder (the pipeline is identical).
"""

from __future__ import annotations

TOP_K = 3
TARGET_ACCURACY = 0.90


def test_intended_skill_in_top_k(seeded_service, labeled_queries):
    hits = 0
    for case in labeled_queries:
        result = seeded_service.select(case["query"], k=TOP_K)
        ids = [c.id for c in result.candidates]
        if case["expected_id"] in ids:
            hits += 1
    accuracy = hits / len(labeled_queries)
    assert accuracy >= TARGET_ACCURACY, f"accuracy {accuracy:.2f} below {TARGET_ACCURACY}"


def test_top_result_is_expected_for_clear_queries(seeded_service, labeled_queries):
    for case in labeled_queries:
        result = seeded_service.select(case["query"], k=TOP_K)
        assert result.candidates, f"no candidates for {case['query']!r}"
        assert result.candidates[0].id == case["expected_id"]
