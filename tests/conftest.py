"""Shared pytest fixtures.

Tests use the deterministic offline HashingEmbedder so the suite runs without loading
vLLM. The selection pipeline (pool, cache, index, service, API) is identical regardless of
embedder; only the vectors differ.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_picker.embedding import HashingEmbedder
from skill_picker.models import SkillInput
from skill_picker.pool import SkillPool, VectorCache
from skill_picker.service import SelectionService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_skills() -> list[dict]:
    return json.loads((FIXTURES / "sample_skills.json").read_text())


@pytest.fixture
def labeled_queries() -> list[dict]:
    return json.loads((FIXTURES / "labeled_queries.json").read_text())


@pytest.fixture
def pool(tmp_path) -> SkillPool:
    return SkillPool(tmp_path / "skills")


@pytest.fixture
def embedder() -> HashingEmbedder:
    return HashingEmbedder(dim=512)


@pytest.fixture
def service(pool, embedder) -> SelectionService:
    return SelectionService(pool, embedder, VectorCache(pool.dir))


@pytest.fixture
def seeded_service(service, sample_skills) -> SelectionService:
    for rec in sample_skills:
        service.pool.add(SkillInput(**rec))
    return service
