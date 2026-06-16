"""Command-line interface (specs/001-skill-picker/contracts/cli.md).

Mirrors the HTTP select/load split: `select` shows ranked candidates with scores;
`show` loads a single full description.
"""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Optional

import typer

from .errors import SkillExistsError, SkillNotFoundError
from .models import SkillInput
from .pool import SkillPool
from .service import SelectionService, build_service

app = typer.Typer(help="Skill Picker: vector-similarity skill selection (vLLM-backed).")

DEFAULT_POOL = "data/skills.db"

# Exit codes per contracts/cli.md: 0 ok, 2 usage, 3 not found, 4 conflict.
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_CONFLICT = 4


def _read_text(value: str) -> str:
    """Support '@path' to read text from a file."""
    if value.startswith("@"):
        return Path(value[1:]).read_text()
    return value


def _service(pool: str, embedder: str, gpu_memory_utilization: Optional[float] = None) -> SelectionService:
    kwargs: dict = {}
    # On the CPU backend vLLM reserves a fraction of RAM (despite the flag's name); on a
    # constrained machine pass a low value so the engine can start. Only forwarded to vllm.
    if embedder == "vllm" and gpu_memory_utilization is not None:
        kwargs["gpu_memory_utilization"] = gpu_memory_utilization
    return build_service(db_path=pool, embedder_name=embedder, **kwargs)


def _pool(pool: str) -> SkillPool:
    return SkillPool(pool)


@app.command()
def select(
    query: str = typer.Argument(..., help="Task description to find skills for."),
    top_k: int = typer.Option(5, "-k", "--top-k", help="Max candidates."),
    threshold: float = typer.Option(0.0, "-t", "--threshold", help="Min cosine score."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    pool: str = typer.Option(DEFAULT_POOL, "--pool", help="Shared SQLite pool file."),
    embedder: str = typer.Option("vllm", "--embedder", help="vllm (default) or hashing."),
    gpu_memory_utilization: Optional[float] = typer.Option(
        None, "--gpu-memory-utilization", help="vLLM CPU RAM fraction to reserve (lower on constrained machines)."
    ),
):
    """Rank skills by similarity to QUERY (metadata + scores only)."""
    result = _service(pool, embedder, gpu_memory_utilization).select(query, k=top_k, threshold=threshold)
    if json_out:
        typer.echo(result.model_dump_json(indent=2))
        return
    if not result.candidates:
        typer.echo("(no skills matched)")
        return
    typer.echo(f"{'score':<8}{'id':<24}name")
    for c in result.candidates:
        typer.echo(f"{c.score:<8.4f}{c.id:<24}{c.name}")


@app.command()
def show(
    skill_id: str = typer.Argument(..., help="Skill id to load."),
    pool: str = typer.Option(DEFAULT_POOL, "--pool"),
):
    """Load and print one skill's full description (post-selection step)."""
    try:
        skill = _pool(pool).get(skill_id)
    except SkillNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(EXIT_NOT_FOUND)
    typer.echo(f"# {skill.name}  ({skill.id})")
    if skill.tags:
        typer.echo(f"tags: {', '.join(skill.tags)}")
    typer.echo("")
    typer.echo(skill.full_description)


@app.command()
def add(
    id: str = typer.Option(..., "--id", help="Stable unique id."),
    name: str = typer.Option(..., "--name"),
    description: str = typer.Option(
        ...,
        "--description",
        help="Short selection text (≈ SKILL.md frontmatter description); embedded for matching. Text or @path.",
    ),
    body: Optional[str] = typer.Option(
        None,
        "--body",
        help="Full skill body (≈ SKILL.md body); returned only by show/load. Text or @path. Defaults to --description.",
    ),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated."),
    pool: str = typer.Option(DEFAULT_POOL, "--pool"),
):
    """Add a skill to the shared pool."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    match = _read_text(description)
    full = _read_text(body) if body is not None else match
    data = SkillInput(
        id=id,
        name=name,
        full_description=full,
        match_text=match,
        tags=tag_list,
    )
    try:
        _pool(pool).add(data)
    except SkillExistsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(EXIT_CONFLICT)
    typer.echo(f"added {id}")


@app.command()
def update(
    skill_id: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None, "--name"),
    description: Optional[str] = typer.Option(
        None, "--description", help="New short selection text (embedded for matching). Text or @path."
    ),
    body: Optional[str] = typer.Option(
        None, "--body", help="New full skill body (returned only by show/load). Text or @path."
    ),
    tags: Optional[str] = typer.Option(None, "--tags"),
    pool: str = typer.Option(DEFAULT_POOL, "--pool"),
):
    """Update an existing skill (re-embeds on next selection if the selection text changed)."""
    try:
        p = _pool(pool)
        fields: dict = {}
        if name is not None:
            fields["name"] = name
        if description is not None:
            fields["match_text"] = _read_text(description)
        if body is not None:
            fields["full_description"] = _read_text(body)
            if description is None:
                # Updating only the body must not let the selection text re-derive from it.
                fields["match_text"] = p.get(skill_id).match_text
        if tags is not None:
            fields["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
        p.update(skill_id, **fields)
    except SkillNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(EXIT_NOT_FOUND)
    typer.echo(f"updated {skill_id}")


@app.command()
def remove(
    skill_id: str = typer.Argument(...),
    pool: str = typer.Option(DEFAULT_POOL, "--pool"),
):
    """Remove a skill from the pool."""
    try:
        _pool(pool).remove(skill_id)
    except SkillNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(EXIT_NOT_FOUND)
    typer.echo(f"removed {skill_id}")


@app.command(name="list")
def list_skills(
    json_out: bool = typer.Option(False, "--json"),
    pool: str = typer.Option(DEFAULT_POOL, "--pool"),
):
    """List skill metadata only (never full descriptions)."""
    meta = _pool(pool).list_metadata()
    if json_out:
        typer.echo(_json.dumps([m.model_dump() for m in meta], indent=2))
        return
    if not meta:
        typer.echo("(pool is empty)")
        return
    typer.echo(f"{'id':<24}{'tags':<24}name")
    for m in meta:
        typer.echo(f"{m.id:<24}{','.join(m.tags):<24}{m.name}")


@app.command()
def reindex(
    pool: str = typer.Option(DEFAULT_POOL, "--pool"),
    embedder: str = typer.Option("vllm", "--embedder"),
    gpu_memory_utilization: Optional[float] = typer.Option(
        None, "--gpu-memory-utilization", help="vLLM CPU RAM fraction to reserve."
    ),
):
    """Rebuild the index, re-embedding stale or signature-mismatched skills."""
    size = _service(pool, embedder, gpu_memory_utilization).reindex()
    typer.echo(f"reindexed {size} skill(s)")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    pool: str = typer.Option(DEFAULT_POOL, "--pool"),
    embedder: str = typer.Option("vllm", "--embedder"),
    gpu_memory_utilization: Optional[float] = typer.Option(
        None, "--gpu-memory-utilization", help="vLLM CPU RAM fraction to reserve."
    ),
):
    """Start the shared HTTP service."""
    import uvicorn

    from .api import create_app

    uvicorn.run(create_app(_service(pool, embedder, gpu_memory_utilization)), host=host, port=port)


if __name__ == "__main__":
    app()
