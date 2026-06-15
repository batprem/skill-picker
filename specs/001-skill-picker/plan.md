# Implementation Plan: Skill Picker

**Branch**: `001-skill-picker` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-skill-picker/spec.md`

## Summary

Skill Picker is a vector-similarity skill-selection service for coding agents. Skills
(name + short matching description + full description) live in a single shared pool. Each
skill's matching metadata is embedded into a vector via vLLM; at query time the incoming
task is embedded the same way and the most similar skills are returned as a ranked,
score-bearing candidate list bounded by K and a relevance threshold. Full descriptions
are loaded lazily, only for selected skills — never the whole pool — directly addressing
context overload (the P1 pain point) while a shared, consistent pool serves a whole team
(the P2 pain point).

Technical approach: a small Python service exposing a select-then-load HTTP API plus a
CLI, backed by a filesystem source-of-truth pool and an in-memory cosine-similarity index
rebuilt from cached embeddings. vLLM runs in pooling/embedding mode with the `e5-small-v2`
model (matching the existing `test_embedding.py` reference), applying the e5 `query:` /
`passage:` prefix convention so query and skill embeddings are comparable.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.13`, per existing `pyproject.toml`)
**Primary Dependencies**: vLLM (pooling/embedding runner), NumPy (cosine similarity),
FastAPI + Uvicorn (shared HTTP service / API contract), Pydantic (schemas/validation),
Typer or argparse (CLI)
**Storage**: SQLite source of truth — a single `.db` file with a `skills` table (records)
and a `vectors` table (cached embeddings as BLOBs, stamped with model signature +
source hash). No server, no deployment; chosen so the demo is zero-ops and portable
**Testing**: pytest (unit + integration); a tiny labeled query→skill fixture set for
retrieval-quality assertions
**Target Platform**: Linux/macOS server, CPU-only (workspace builds vLLM for macOS CPU)
**Project Type**: Single project — backend service + CLI in one package
**Performance Goals**: Selection returns a ranked candidate list in < 1s for a pool of
≥ 100 skills (SC-002); embedding is precomputed/cached so selection is query-embed + a
brute-force cosine scan
**Constraints**: Query and index embeddings MUST come from the same vLLM model/config
(Constitution IV); selection MUST NOT load full descriptions of non-selected skills
(Constitution II); deterministic results for identical inputs (FR-013)
**Scale/Scope**: Tens to a few hundred skills (demo + near-term team use); brute-force
cosine over normalized vectors is sufficient — no ANN index needed at this scale

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Derived from `.specify/memory/constitution.md` v1.0.0:

| Principle | Gate | Status |
|-----------|------|--------|
| I. Vector-First Skill Selection | Selection ranks by vector similarity over embedded metadata; no bulk-load-and-decide path exists | PASS — design embeds name+short-desc and ranks by cosine |
| II. Context Efficiency (NON-NEGOTIABLE) | Only metadata participates in search; full descriptions load lazily for top-K only; K configurable with small default | PASS — `select` returns metadata+scores; separate `load` endpoint fetches one full description |
| III. Shared Skill Pool Integrity | Single shared source of truth; stable id/name/description; add/update/remove keeps index consistent | PASS — SQLite database is the single source; index rebuilds from pool; removed skills are not returned |
| IV. vLLM as the Embedding Backbone | All embeddings via vLLM, same model+config for index and query; model signature recorded; model change triggers re-embed | PASS — single embedding component used both sides; model signature stored with cache; mismatch triggers re-embed |
| V. Demo-Ready Simplicity & Observability | Runnable end-to-end with minimal setup; YAGNI; selection path surfaces candidates + scores | PASS — single package, brute-force index, scores returned in every selection response |

**Initial Constitution Check: PASS** — no violations; Complexity Tracking not required.

**Post-Design Constitution Check (after Phase 1): PASS** — data model separates
`match_text` from `full_description`; contracts expose `select` (metadata+scores) and
`load` (single full description) as distinct operations, enforcing Principle II at the
interface level. Cache carries an `embedding_signature` enforcing Principle IV. No new
violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-skill-picker/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── http-api.md      # select-then-load HTTP contract
│   └── cli.md           # CLI command contract
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```text
src/
└── skill_picker/
    ├── __init__.py
    ├── models.py          # Skill, SkillMetadata, Candidate, SelectionResult (Pydantic)
    ├── db.py              # SQLite connection + schema (skills + vectors tables)
    ├── embedding.py       # vLLM embedding wrapper (e5 prefixes, model signature)
    ├── pool.py            # SkillPool + VectorCache: SQLite-backed source of truth
    ├── index.py           # In-memory cosine index built from cached embeddings
    ├── service.py         # Selection service: select() + load() orchestration
    ├── api.py             # FastAPI app exposing the HTTP contract
    └── cli.py             # CLI entry point (add/update/remove/select/load/serve)

tests/
├── unit/                  # pool CRUD, cosine ranking, threshold/K, model signature
├── integration/          # select-then-load flow, add→query→remove consistency
└── fixtures/             # sample skills + labeled query→skill pairs (retrieval quality)

data/
└── skills.db             # default shared pool (SQLite: skills + cached vectors)
```

**Structure Decision**: Single project (Option 1). The feature is one cohesive package
`src/skill_picker/` exposing both a FastAPI service (the shared, team-facing source of
truth) and a CLI (local authoring + demo). This keeps the demo runnable with minimal
setup (Constitution V) while the service layer is shared by both entrypoints, avoiding
duplicated selection logic.

## Complexity Tracking

> No constitution violations. Section intentionally empty.
