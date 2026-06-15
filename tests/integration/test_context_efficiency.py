"""T013 [US1] / SC-003 / Constitution II: selection never carries full descriptions."""

from __future__ import annotations


def test_select_result_has_no_full_description(seeded_service):
    result = seeded_service.select("extract tables from a pdf", k=3)
    assert result.candidates
    for c in result.candidates:
        assert not hasattr(c, "full_description")
        assert "full_description" not in c.model_dump()
    # Belt and suspenders: full text must not appear anywhere in the serialized result.
    assert "full_description" not in result.model_dump_json()


def test_listing_metadata_has_no_full_description(seeded_service):
    for meta in seeded_service.pool.list_metadata():
        assert "full_description" not in meta.model_dump()


def test_load_returns_exactly_one_full_description(seeded_service):
    skill = seeded_service.load("pdf-table-extract")
    assert skill.id == "pdf-table-extract"
    assert skill.full_description.strip()
