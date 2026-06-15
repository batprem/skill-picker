"""SQLite-backed skill pool (single source of truth) and embedding vector cache.

Both live in one SQLite file: the ``skills`` table holds records, the ``vectors`` table
holds cached embeddings as BLOBs. The metadata read path never selects ``full_description``,
so full text is loaded only on demand (Constitution II/III).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .db import connect
from .errors import SkillExistsError, SkillNotFoundError
from .models import Skill, SkillInput, SkillMetadata, derive_match_text, now_iso


def _row_to_skill(row) -> Skill:
    return Skill(
        id=row["id"],
        name=row["name"],
        match_text=row["match_text"],
        full_description=row["full_description"],
        tags=json.loads(row["tags"]),
        updated_at=row["updated_at"],
    )


class VectorCache:
    """SQLite-backed cache of L2-normalized skill vectors, keyed by skill id.

    A cached vector is valid only if both the embedding ``signature`` and the
    ``source_hash`` of the embedded text still match (Constitution IV).
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._conn = connect(self.db_path)
        row = self._conn.execute("SELECT signature, dim FROM vectors LIMIT 1").fetchone()
        self.signature: str | None = row["signature"] if row else None
        self.dim: int | None = row["dim"] if row else None

    def get(self, skill_id: str, source_hash: str, signature: str) -> np.ndarray | None:
        row = self._conn.execute(
            "SELECT vector FROM vectors WHERE skill_id=? AND signature=? AND source_hash=?",
            (skill_id, signature, source_hash),
        ).fetchone()
        if row is None:
            return None
        return np.frombuffer(row["vector"], dtype=np.float32)

    def put(self, skill_id: str, vector: np.ndarray, source_hash: str, signature: str) -> None:
        # A different active model invalidates the whole cache (Constitution IV).
        if self.signature is not None and signature != self.signature:
            self._conn.execute("DELETE FROM vectors")
        self.signature = signature
        self.dim = int(len(vector))
        blob = np.asarray(vector, dtype=np.float32).tobytes()
        self._conn.execute(
            "INSERT OR REPLACE INTO vectors (skill_id, signature, source_hash, dim, vector) "
            "VALUES (?, ?, ?, ?, ?)",
            (skill_id, signature, source_hash, self.dim, blob),
        )

    def delete(self, skill_id: str) -> None:
        self._conn.execute("DELETE FROM vectors WHERE skill_id=?", (skill_id,))

    def save(self) -> None:
        """Commit staged vector writes."""
        self._conn.commit()

    def ids(self) -> list[str]:
        rows = self._conn.execute("SELECT skill_id FROM vectors").fetchall()
        return [r["skill_id"] for r in rows]


class SkillPool:
    """The shared collection of skills; the single source of truth (Constitution III)."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._conn = connect(self.db_path)

    def exists(self, skill_id: str) -> bool:
        return self._conn.execute("SELECT 1 FROM skills WHERE id=?", (skill_id,)).fetchone() is not None

    def get(self, skill_id: str) -> Skill:
        row = self._conn.execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
        if row is None:
            raise SkillNotFoundError(skill_id)
        return _row_to_skill(row)

    def add(self, data: SkillInput) -> Skill:
        if self.exists(data.id):
            raise SkillExistsError(data.id)
        skill = Skill(
            id=data.id,
            name=data.name,
            match_text=data.match_text or derive_match_text(data.full_description),
            full_description=data.full_description,
            tags=list(data.tags),
            updated_at=now_iso(),
        )
        self._insert(skill)
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
        self._insert(skill)
        return skill

    def remove(self, skill_id: str) -> None:
        cur = self._conn.execute("DELETE FROM skills WHERE id=?", (skill_id,))
        if cur.rowcount == 0:
            raise SkillNotFoundError(skill_id)
        self._conn.commit()

    def list_full(self) -> list[Skill]:
        rows = self._conn.execute("SELECT * FROM skills ORDER BY id").fetchall()
        return [_row_to_skill(r) for r in rows]

    def list_metadata(self) -> list[SkillMetadata]:
        """Skill metadata only — never selects full_description (Constitution II)."""
        rows = self._conn.execute(
            "SELECT id, name, match_text, tags, updated_at FROM skills ORDER BY id"
        ).fetchall()
        return [
            SkillMetadata(
                id=r["id"],
                name=r["name"],
                match_text=r["match_text"],
                tags=json.loads(r["tags"]),
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

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
            self._insert(skill)
            count += 1
        return count

    def _insert(self, skill: Skill) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO skills (id, name, match_text, full_description, tags, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                skill.id,
                skill.name,
                skill.match_text,
                skill.full_description,
                json.dumps(skill.tags),
                skill.updated_at,
            ),
        )
        self._conn.commit()
