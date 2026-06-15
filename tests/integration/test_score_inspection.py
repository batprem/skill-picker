"""T026 [US3] / SC-006: every candidate carries an inspectable, comparable score."""

from __future__ import annotations


def test_candidates_carry_descending_scores(seeded_service):
    result = seeded_service.select("optimize a slow sql query", k=5)
    assert result.candidates
    scores = [c.score for c in result.candidates]
    assert all(isinstance(s, float) for s in scores)
    assert scores == sorted(scores, reverse=True)


def test_result_echoes_query_for_inspection(seeded_service):
    result = seeded_service.select("format a json document", k=3)
    assert result.query == "format a json document"
