"""T018/T024/T028: HTTP contract — select/load split, CRUD, health."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from skill_picker.api import create_app
from skill_picker.embedding import HashingEmbedder
from skill_picker.models import SkillInput
from skill_picker.pool import SkillPool, VectorCache
from skill_picker.service import SelectionService


@pytest.fixture
def client(tmp_path, sample_skills):
    pool = SkillPool(tmp_path / "skills")
    svc = SelectionService(pool, HashingEmbedder(dim=512), VectorCache(pool.dir))
    for rec in sample_skills:
        pool.add(SkillInput(**rec))
    return TestClient(create_app(svc))


def test_select_returns_scores_without_full_description(client):
    resp = client.post("/v1/select", json={"query": "extract tables from a pdf", "k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["candidates"]
    assert "full_description" not in resp.text
    assert all("score" in c for c in body["candidates"])


def test_get_skill_returns_full_description(client):
    resp = client.get("/v1/skills/pdf-table-extract")
    assert resp.status_code == 200
    assert resp.json()["full_description"].strip()


def test_get_missing_skill_404(client):
    assert client.get("/v1/skills/does-not-exist").status_code == 404


def test_add_conflict_and_crud_flow(client):
    new = {"id": "new-skill", "name": "New", "full_description": "do a new thing"}
    assert client.post("/v1/skills", json=new).status_code == 201
    assert client.post("/v1/skills", json=new).status_code == 409  # duplicate

    assert client.put("/v1/skills/new-skill", json={"name": "Renamed"}).status_code == 200
    assert client.get("/v1/skills/new-skill").json()["name"] == "Renamed"

    assert client.delete("/v1/skills/new-skill").status_code == 204
    assert client.get("/v1/skills/new-skill").status_code == 404


def test_list_metadata_excludes_full_description(client):
    resp = client.get("/v1/skills")
    assert resp.status_code == 200
    assert "full_description" not in resp.text
    assert resp.json()["count"] == 5


def test_health_reports_signature_and_pool_size(client):
    body = client.get("/v1/health").json()
    assert body["status"] == "ok"
    assert body["embedding_signature"].startswith("hashing-bow@")
    assert body["pool_size"] == 5
