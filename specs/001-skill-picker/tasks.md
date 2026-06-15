---
description: "Task list for Skill Picker implementation"
---

# Tasks: Skill Picker

**Input**: Design documents from `/specs/001-skill-picker/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED. The constitution's Development Workflow requires a way to demonstrate
retrieval quality, and research R6 + quickstart define labeled fixtures. Test tasks here
are targeted (retrieval quality, pool consistency, context-efficiency), not exhaustive TDD.

**Organization**: Tasks are grouped by user story for independent implementation/testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3 (Setup/Foundational/Polish have no story label)
- All paths are relative to repo root

## Path Conventions

- Source: `src/skill_picker/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/fixtures/`
- Shared pool data: `data/skills/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies

- [ ] T001 Create source layout `src/skill_picker/` with `__init__.py`, and test dirs `tests/unit/`, `tests/integration/`, `tests/fixtures/` per plan.md
- [ ] T002 Add runtime dependencies (vllm, numpy, fastapi, uvicorn, pydantic, typer) and a `skill-picker` console-script entry point in `pyproject.toml`
- [ ] T003 [P] Add dev dependencies (pytest) and configure pytest in `pyproject.toml`
- [ ] T004 [P] Create default pool directory `data/skills/.gitkeep` and ignore the embedding cache sidecar in `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core shared components every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Define Pydantic models (Skill, SkillMetadata, Candidate, SelectionResult, SelectionQuery) in `src/skill_picker/models.py` per data-model.md
- [ ] T006 [P] Implement vLLM embedding wrapper in `src/skill_picker/embedding.py`: e5 `query:`/`passage:` prefixing, L2 normalization, and an `embedding_signature` (e.g. `e5-small-v2@pooling`) per research R1/R4
- [ ] T007 Implement filesystem `SkillPool` storage in `src/skill_picker/pool.py`: per-skill JSON records under the pool dir, `match_text` derivation from `full_description`, and `list_metadata()` that excludes `full_description` (FR-002, FR-006) — depends on T005
- [ ] T008 Implement embedding cache sidecar in `src/skill_picker/pool.py` (or `cache` helper): `.npz` keyed by skill id with `embedding_signature` + `source_hash` validity checks per data-model.md — depends on T006, T007
- [ ] T009 Implement in-memory cosine `Index` in `src/skill_picker/index.py`: normalized-vector matrix, brute-force top-K with threshold, deterministic tie-break by id (FR-004, FR-012, FR-013) — depends on T005
- [ ] T010 Implement `SelectionService` skeleton in `src/skill_picker/service.py` wiring pool + cache + index (build/refresh index from pool metadata + valid vectors) — depends on T007, T008, T009
- [ ] T011 [P] Create shared sample pool + labeled `query → expected skill id` fixtures in `tests/fixtures/` per quickstart.md/research R6

**Checkpoint**: Core embedding, storage, and index ready — user stories can begin

---

## Phase 3: User Story 1 - Relevance-based selection without loading everything (Priority: P1) 🎯 MVP

**Goal**: An agent submits a task query and gets a ranked candidate list (metadata + scores only), then loads the full description of just the chosen skill.

**Independent Test**: With a fixture pool, a query whose intent matches one skill returns that skill at/near the top with a score; no full descriptions appear in the selection response; a follow-up load returns exactly one full description.

### Tests for User Story 1

- [ ] T012 [P] [US1] Retrieval-quality integration test in `tests/integration/test_retrieval_quality.py`: asserts intended skill in top-K for ≥90% of fixture pairs (SC-001)
- [ ] T013 [P] [US1] Context-efficiency test in `tests/integration/test_context_efficiency.py`: asserts `select` output contains no `full_description` and `load` returns exactly one (SC-003, Constitution II)
- [ ] T014 [P] [US1] Unit test for cosine ranking/threshold/tie-break determinism in `tests/unit/test_index.py` (FR-004, FR-012, FR-013)

### Implementation for User Story 1

- [ ] T015 [US1] Implement `SelectionService.select(query, k, threshold)` in `src/skill_picker/service.py`: embed query, rank, return Candidates (metadata + scores only), default k=5 (FR-003, FR-004, FR-006)
- [ ] T016 [US1] Implement `SelectionService.load(skill_id)` in `src/skill_picker/service.py`: return one full Skill record (FR-005) — depends on T015
- [ ] T017 [P] [US1] Implement CLI `select` and `show` commands in `src/skill_picker/cli.py` with `-k`/`-t`/`--json` per contracts/cli.md — depends on T015, T016
- [ ] T018 [P] [US1] Implement HTTP `POST /v1/select` and `GET /v1/skills/{id}` in `src/skill_picker/api.py` per contracts/http-api.md (404 on missing id) — depends on T015, T016

**Checkpoint**: US1 fully functional — selection + lazy load work end-to-end and pass tests (MVP)

---

## Phase 4: User Story 2 - Maintain a shared team skill pool (Priority: P2)

**Goal**: Team members add/update/remove skills in one shared pool; changes are reflected in the next selection and removed skills never reappear.

**Independent Test**: Add a skill → query returns it; update its text → query reflects change; remove it → same query no longer returns it.

### Tests for User Story 2

- [ ] T019 [P] [US2] Pool-consistency integration test in `tests/integration/test_pool_consistency.py`: add→select, update→select, remove→select reflect changes within the next cycle (FR-007/008/009/011, SC-004)
- [ ] T020 [P] [US2] Unit test for pool CRUD + cache invalidation on text change in `tests/unit/test_pool.py` (FR-008, Constitution IV re-embed)

### Implementation for User Story 2

- [ ] T021 [US2] Implement `SkillPool.add/update/remove` with embed-on-change and cache update/delete in `src/skill_picker/pool.py` (FR-007, FR-008, FR-009) — depends on Foundational
- [ ] T022 [US2] Implement `reindex` in `src/skill_picker/service.py`: rebuild index, re-embed stale or signature-mismatched skills (Constitution IV) — depends on T021
- [ ] T023 [P] [US2] Implement CLI `add`, `update`, `remove`, `list`, `reindex` commands in `src/skill_picker/cli.py` per contracts/cli.md — depends on T021, T022
- [ ] T024 [P] [US2] Implement HTTP `POST/PUT/DELETE /v1/skills`, `GET /v1/skills` (metadata only) in `src/skill_picker/api.py` (201/200/204, 409 conflict, 404 missing) — depends on T021
- [ ] T025 [US2] Implement pool `export()`/`import()` for portable sharing in `src/skill_picker/pool.py` (FR-014) — depends on T021

**Checkpoint**: US1 and US2 both work independently — shared pool is fully manageable

---

## Phase 5: User Story 3 - Inspect and explain a selection decision (Priority: P3)

**Goal**: Queries surface candidate similarity scores in a human-readable, comparable form for demos.

**Independent Test**: A query shows each candidate's score; two queries' differing results are explainable by the reported scores.

### Tests for User Story 3

- [ ] T026 [P] [US3] Observability test in `tests/integration/test_score_inspection.py`: every candidate carries a comparable score and scores are exposed via CLI and API (SC-006)

### Implementation for User Story 3

- [ ] T027 [US3] Render a human-readable score table (score/id/name) for CLI `select` default output in `src/skill_picker/cli.py` per contracts/cli.md (Constitution V) — depends on T017
- [ ] T028 [P] [US3] Implement `GET /v1/health` returning status, `embedding_signature`, and `pool_size` in `src/skill_picker/api.py` (Constitution IV/V observability) — depends on T018

**Checkpoint**: All user stories independently functional and demonstrable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements spanning multiple stories

- [ ] T029 [P] Add a performance check that `select` returns in <1s for a pool of ≥100 skills in `tests/integration/test_performance.py` (SC-002)
- [ ] T030 [P] Validate quickstart end-to-end and update `specs/001-skill-picker/quickstart.md` if commands/paths drift
- [ ] T031 [P] Add input validation + friendly error messages/exit codes across CLI and API per contracts (usage/not-found/conflict)
- [ ] T032 [P] Add README usage section for skill-picker (install, seed pool, select, serve) in `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational; can then proceed in priority order or in parallel
- **Polish (Phase 6)**: Depends on the targeted user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational. Independently testable via fixture pool.
- **US2 (P2)**: Depends on Foundational. Independent of US1 (manages the pool US1 reads).
- **US3 (P3)**: Depends on Foundational; builds on US1's select output (T027 extends T017).

### Within Each User Story

- Tests before / alongside implementation
- Models → storage/index → service → interfaces (CLI/API)
- Story complete and testable before moving to the next priority

### Parallel Opportunities

- Setup: T003, T004 in parallel
- Foundational: T005, T006, T011 in parallel; then T007→T008, T009, then T010
- US1: T012, T013, T014 (tests) in parallel; T017, T018 (interfaces) in parallel after T015/T016
- US2: T019, T020 in parallel; T023, T024 in parallel after T021/T022
- Across stories: once Foundational is done, US1 and US2 can be built by different people in parallel

---

## Parallel Example: User Story 1

```bash
# Tests for US1 together:
Task: "Retrieval-quality integration test in tests/integration/test_retrieval_quality.py"
Task: "Context-efficiency test in tests/integration/test_context_efficiency.py"
Task: "Unit test for cosine ranking in tests/unit/test_index.py"

# Interfaces for US1 together (after service.select/load exist):
Task: "CLI select/show in src/skill_picker/cli.py"
Task: "HTTP select + get-skill in src/skill_picker/api.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: selection returns ranked scores, no full text leaks, load fetches one
5. Demo the core value (context-efficient selection)

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → test → demo (MVP: efficient selection)
3. US2 → test → demo (shared, manageable pool)
4. US3 → test → demo (inspectable scores on stage)
5. Polish (performance, quickstart, README)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps each task to its user story for traceability
- Constitution guardrail: never load all skills' full descriptions for selection (T013 enforces)
- Constitution guardrail: query and skill embeddings share one signature; model change re-embeds (T006, T022)
- Commit after each task or logical group; stop at any checkpoint to validate a story independently
