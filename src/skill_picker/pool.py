"""Filesystem-backed skill pool (single source of truth) and embedding vector cache.

Each skill is a JSON record at ``<pool>/<id>.json``. Embedding vectors live in a sidecar
(``.vectors.npy`` + ``.vectors.json``) so the metadata read path never carries vectors and
full descriptions are loaded only on demand (Constitution II/III).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .errors import SkillExistsError, SkillNotFoundError
from .models import Skill, SkillInput, SkillMetadata, derive_match_text, now_iso


class VectorCache:
    """Persisted cache of L2-normalized skill vectors, keyed by skill id.

    A cached vector is valid only if both the embedding ``signature`` and the
    ``source_hash`` of the embedded text still match (Constitution IV).
    """

    def __init__(self, directory: str | Path):
        self.dir = Path(directory)
        self.vec_path = self.dir / ".vectors.npy"
        self.meta_path = self.dir / ".vectors.json"
        self.signature: str | None = None
        self.dim: int | None = None
        self._vectors: dict[str, np.ndarray] = {}
        self._hashes: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if not self.meta_path.exists() or not self.vec_path.exists():
            return
        meta = json.loads(self.meta_path.read_text())
        self.signature = meta.get("signature")
        self.dim = meta.get("dim")
        ids = meta.get("ids", [])
        self._hashes = dict(meta.get("hashes", {}))
        mat = np.load(self.vec_path)
        self._vectors = {sid: mat[i] for i, sid in enumerate(ids)}

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        ids = list(self._vectors)
        if ids:
            mat = np.stack([self._vectors[i] for i in ids]).astype(np.float32)
        else:
            mat = np.zeros((0, self.dim or 0), dtype=np.float32)
        np.save(self.vec_path, mat)
        self.meta_path.write_text(
            json.dumps(
                {"signature": self.signature, "dim": self.dim, "ids": ids, "hashes": self._hashes},
                indent=2,
            )
        )

    def get(self, skill_id: str, source_hash: str, signature: str) -> np.ndarray | None:
        if signature != self.signature:
            return None
        if self._hashes.get(skill_id) != source_hash:
            return None
        return self._vectors.get(skill_id)

    def put(self, skill_id: str, vector: np.ndarray, source_hash: str, signature: str) -> None:
        # A different active model invalidates the whole cache (Constitution IV).
        if self.signature is not None and signature != self.signature:
            self._vectors.clear()
            self._hashes.clear()
        self.signature = signature
        self.dim = int(len(vector))
        self._vectors[skill_id] = np.asarray(vector, dtype=np.float32)
        self._hashes[skill_id] = source_hash

    def delete(self, skill_id: str) -> None:
        self._vectors.pop(skill_id, None)
        self._hashes.pop(skill_id, None)

    def ids(self) -> list[str]:
        return list(self._vectors)


class SkillPool:
    """The shared collection of skills; the single source of truth (Constitution III)."""

    def __init__(self, directory: str | Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, skill_id: str) -> Path:
        return self.dir / f"{skill_id}.json"

    def exists(self, skill_id: str) -> bool:
        return self._path(skill_id).exists()

    def get(self, skill_id: str) -> Skill:
        path = self._path(skill_id)
        if not path.exists():
            raise SkillNotFoundError(skill_id)
        return Skill.model_validate_json(path.read_text())

    def _write(self, skill: Skill) -> None:
        self._path(skill.id).write_text(skill.model_dump_json(indent=2))

    def add(self, data: SkillInput) -> Skill:
        if self.exists(data.id):
            raise SkillExistsError(data.id)
        match_text = data.match_text or derive_match_text(data.full_description)
        skill = Skill(
            id=data.id,
            name=data.name,
            match_text=match_text,
            full_description=data.full_description,
            tags=list(data.tags),
            updated_at=now_iso(),
        )
        self._write(skill)
        return skill

    def update(
        self,
        skill_id: str,
        *,
        name: str | None = None,
        match_text: str | None = None,
        full_description: str | None = None,
        tags: list[str] | None = None,
    ) -> Skill:
        skill = self.get(skill_id)
        if name is not None:
            skill.name = name
        if full_description is not None:
            skill.full_description = full_description
        if match_text is not None:
            skill.match_text = match_text
        elif full_description is not None:
            # Keep matching text in sync when description changes and none was given.
            skill.match_text = derive_match_text(full_description)
        if tags is not None:
            skill.tags = list(tags)
        skill.updated_at = now_iso()
        self._write(skill)
        return skill

    def remove(self, skill_id: str) -> None:
        path = self._path(skill_id)
        if not path.exists():
            raise SkillNotFoundError(skill_id)
        path.unlink()

    def list_full(self) -> list[Skill]:
        skills = [Skill.model_validate_json(p.read_text()) for p in self._record_paths()]
        return sorted(skills, key=lambda s: s.id)

    def list_metadata(self) -> list[SkillMetadata]:
        """Skill metadata only — never carries full_description (Constitution II)."""
        return [
            SkillMetadata(
                id=s.id, name=s.name, match_text=s.match_text, tags=s.tags, updated_at=s.updated_at
            )
            for s in self.list_full()
        ]

    def _record_paths(self) -> list[Path]:
        return [p for p in self.dir.glob("*.json") if not p.name.startswith(".")]

    def export(self) -> list[dict]:
        """Portable serialization of the whole pool (FR-014)."""
        return [s.model_dump() for s in self.list_full()]

    def import_(self, records: list[dict], *, overwrite: bool = False) -> int:
        """Load records from an export. Returns the number of skills written."""
        count = 0
        for rec in records:
            skill = Skill.model_validate(rec)
            if self.exists(skill.id) and not overwrite:
                continue
            self._write(skill)
            count += 1
        return count
