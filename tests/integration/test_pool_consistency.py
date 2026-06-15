"""T019 [US2] / SC-004: add/update/remove are reflected in the next selection cycle."""

from __future__ import annotations

from skill_picker.models import SkillInput


def _ids(result):
    return [c.id for c in result.candidates]


def test_add_makes_skill_selectable(service):
    service.pool.add(SkillInput(id="x", name="PDF Tables", full_description="extract tables from pdf files"))
    assert "x" in _ids(service.select("extract tables from pdf", k=5))


def test_update_is_reflected_in_selection(service):
    service.pool.add(SkillInput(id="x", name="PDF Tables", full_description="extract tables from pdf files"))
    assert "x" in _ids(service.select("extract tables from pdf", k=5))

    service.pool.update("x", name="SQL Optimizer", full_description="optimize sql database queries")
    assert "x" in _ids(service.select("optimize sql query", k=5))


def test_remove_makes_skill_undiscoverable(service):
    service.pool.add(SkillInput(id="x", name="PDF Tables", full_description="extract tables from pdf files"))
    assert "x" in _ids(service.select("extract tables from pdf", k=5))

    service.pool.remove("x")
    assert "x" not in _ids(service.select("extract tables from pdf", k=5))


def test_empty_pool_returns_empty_result(service):
    result = service.select("anything at all", k=5)
    assert result.candidates == []
