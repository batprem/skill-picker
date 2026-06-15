"""T020 [US2]: pool CRUD, metadata excludes full_description, cache invalidation."""

from __future__ import annotations

import pytest

from skill_picker.errors import SkillExistsError, SkillNotFoundError
from skill_picker.models import SkillInput


def test_add_and_get_roundtrip(pool):
    pool.add(SkillInput(id="x", name="X", full_description="full text here"))
    got = pool.get("x")
    assert got.id == "x"
    assert got.full_description == "full text here"


def test_match_text_derived_when_absent(pool):
    pool.add(SkillInput(id="x", name="X", full_description="a b c d e"))
    assert pool.get("x").match_text == "a b c d e"


def test_explicit_match_text_preserved(pool):
    pool.add(SkillInput(id="x", name="X", full_description="long body", match_text="short"))
    assert pool.get("x").match_text == "short"


def test_duplicate_add_raises(pool):
    pool.add(SkillInput(id="x", name="X", full_description="t"))
    with pytest.raises(SkillExistsError):
        pool.add(SkillInput(id="x", name="X2", full_description="t2"))


def test_list_metadata_has_no_full_description(pool):
    pool.add(SkillInput(id="x", name="X", full_description="secret full text"))
    meta = pool.list_metadata()
    assert len(meta) == 1
    assert "full_description" not in meta[0].model_dump()


def test_update_changes_match_text_when_description_changes(pool):
    pool.add(SkillInput(id="x", name="X", full_description="old description"))
    before = pool.get("x")
    updated = pool.update("x", full_description="brand new description")
    assert updated.match_text == "brand new description"
    assert updated.updated_at >= before.updated_at


def test_remove_then_get_raises(pool):
    pool.add(SkillInput(id="x", name="X", full_description="t"))
    pool.remove("x")
    with pytest.raises(SkillNotFoundError):
        pool.get("x")


def test_remove_missing_raises(pool):
    with pytest.raises(SkillNotFoundError):
        pool.remove("nope")


def test_export_import_roundtrip(pool, tmp_path):
    from skill_picker.pool import SkillPool

    pool.add(SkillInput(id="x", name="X", full_description="one"))
    pool.add(SkillInput(id="y", name="Y", full_description="two"))
    records = pool.export()

    other = SkillPool(tmp_path / "other")
    written = other.import_(records)
    assert written == 2
    assert {s.id for s in other.list_full()} == {"x", "y"}


def test_cache_invalidates_on_text_change(pool):
    from skill_picker.embedding import HashingEmbedder
    from skill_picker.pool import VectorCache
    from skill_picker.service import SelectionService, _source_hash
    from skill_picker.embedding import passage_text

    svc = SelectionService(pool, HashingEmbedder(dim=128), VectorCache(pool.dir))
    pool.add(SkillInput(id="x", name="Name One", full_description="alpha beta"))
    svc.select("alpha", k=3)  # triggers embed + cache
    sig = svc.embedding_signature
    h_old = _source_hash(passage_text("Name One", "alpha beta"))
    assert svc.cache.get("x", h_old, sig) is not None

    pool.update("x", full_description="gamma delta")
    svc.select("gamma", k=3)  # re-syncs, re-embeds new text
    h_new = _source_hash(passage_text("Name One", "gamma delta"))
    assert svc.cache.get("x", h_new, sig) is not None
    # The old text hash is no longer the cached source for x.
    assert svc.cache.get("x", h_old, sig) is None
