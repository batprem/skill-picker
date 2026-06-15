"""Pydantic models for skill-picker (see specs/001-skill-picker/data-model.md)."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

#: Number of characters of full_description used to derive match_text when absent.
MATCH_TEXT_DERIVE_LEN = 200


def now_iso() -> str:
    """Current UTC time as an ISO-8601 'Z' timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def derive_match_text(full_description: str) -> str:
    """Derive a short matching text from a full description."""
    text = " ".join(full_description.split())
    return text[:MATCH_TEXT_DERIVE_LEN]


class SkillInput(BaseModel):
    """Payload for creating a skill. match_text is derived if omitted."""

    id: str
    name: str
    full_description: str
    match_text: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("id", "name", "full_description")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be non-empty")
        return v


class Skill(BaseModel):
    """A stored skill: matching metadata plus the full description."""

    id: str
    name: str
    match_text: str
    full_description: str
    tags: list[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=now_iso)


class SkillMetadata(BaseModel):
    """Lightweight skill view used for indexing/listing. No full_description."""

    id: str
    name: str
    match_text: str
    tags: list[str] = Field(default_factory=list)
    updated_at: str


class Candidate(BaseModel):
    """One ranked result: metadata + score only (Constitution II)."""

    id: str
    name: str
    score: float


class SelectionQuery(BaseModel):
    """A selection request."""

    query: str
    k: int = 5
    threshold: float = 0.0

    @field_validator("query")
    @classmethod
    def _query_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        return v

    @field_validator("k")
    @classmethod
    def _k_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("k must be >= 1")
        return v

    @field_validator("threshold")
    @classmethod
    def _threshold_range(cls, v: float) -> float:
        if not -1.0 <= v <= 1.0:
            raise ValueError("threshold must be in [-1.0, 1.0]")
        return v


class SelectionResult(BaseModel):
    """Response to a SelectionQuery: ranked candidates, query echoed for inspection."""

    query: str
    candidates: list[Candidate]
