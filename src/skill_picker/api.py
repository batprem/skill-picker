"""FastAPI app exposing the shared HTTP contract (specs/.../contracts/http-api.md).

The select/load split is enforced here: /v1/select never returns full descriptions;
full text is served only by GET /v1/skills/{id}.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .errors import SkillExistsError, SkillNotFoundError
from .models import SelectionResult, SkillInput
from .service import SelectionService


class SelectRequest(BaseModel):
    query: str
    k: int = 5
    threshold: float = 0.0


class SkillUpdate(BaseModel):
    name: str | None = None
    match_text: str | None = None
    full_description: str | None = None
    tags: list[str] | None = None


class MetadataList(BaseModel):
    skills: list[dict]
    count: int
    embedding_signature: str


def create_app(service: SelectionService) -> FastAPI:
    app = FastAPI(title="Skill Picker", version="0.1.0")

    @app.post("/v1/select", response_model=SelectionResult)
    def select(req: SelectRequest) -> SelectionResult:
        try:
            return service.select(req.query, k=req.k, threshold=req.threshold)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/v1/skills/{skill_id}")
    def get_skill(skill_id: str):
        try:
            return service.load(skill_id).model_dump()
        except SkillNotFoundError:
            raise HTTPException(status_code=404, detail=f"skill not found: {skill_id}")

    @app.post("/v1/skills", status_code=201)
    def add_skill(skill: SkillInput):
        try:
            created = service.pool.add(skill)
        except SkillExistsError:
            raise HTTPException(status_code=409, detail=f"skill exists: {skill.id}")
        return created.model_dump()

    @app.put("/v1/skills/{skill_id}")
    def update_skill(skill_id: str, fields: SkillUpdate):
        try:
            updated = service.pool.update(skill_id, **fields.model_dump(exclude_none=True))
        except SkillNotFoundError:
            raise HTTPException(status_code=404, detail=f"skill not found: {skill_id}")
        return updated.model_dump()

    @app.delete("/v1/skills/{skill_id}", status_code=204)
    def delete_skill(skill_id: str):
        try:
            service.pool.remove(skill_id)
        except SkillNotFoundError:
            raise HTTPException(status_code=404, detail=f"skill not found: {skill_id}")

    @app.get("/v1/skills", response_model=MetadataList)
    def list_skills() -> MetadataList:
        meta = service.pool.list_metadata()
        return MetadataList(
            skills=[m.model_dump() for m in meta],
            count=len(meta),
            embedding_signature=service.embedding_signature,
        )

    @app.get("/v1/health")
    def health():
        return {
            "status": "ok",
            "embedding_signature": service.embedding_signature,
            "pool_size": service.pool_size(),
        }

    return app
