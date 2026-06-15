# Phase 0 Research: Skill Picker

**Feature**: 001-skill-picker | **Date**: 2026-06-15

This document resolves the technical unknowns implied by the Technical Context. There were
no `NEEDS CLARIFICATION` markers in the spec; the items below are technology/dependency
decisions needed before design.

## R1. Embedding model and engine

- **Decision**: Use vLLM in pooling/embedding mode with `intfloat/e5-small-v2`, applying
  the e5 prefix convention: `query: <task>` for incoming queries and `passage: <name. desc>`
  for stored skill matching text. Normalize vectors to unit length.
- **Rationale**: Matches the existing `test_embedding.py` smoke test (already proven to run
  on this CPU/macOS workspace), keeps vLLM as the centerpiece (Constitution IV), and the
  query/passage asymmetry of e5 fits the "task query vs. skill description" use case well.
  384-dim vectors are small and fast for brute-force cosine.
- **Alternatives considered**:
  - Larger e5 / bge models — better recall but slower to load and embed on CPU; unnecessary
    for tens–hundreds of skills and a live demo.
  - Non-vLLM embedding libraries (sentence-transformers) — rejected: violates Constitution IV
    (vLLM must be the embedding backbone) and undercuts the conference demo's purpose.

## R2. Similarity metric and index

- **Decision**: Cosine similarity via brute-force dot product over L2-normalized vectors
  stored in a single NumPy matrix; return top-K above a configurable threshold.
- **Rationale**: At ≤ a few hundred skills, a normalized matrix-vector product is sub-millisecond
  and trivially deterministic (FR-013), keeping well under the < 1s budget (SC-002). No ANN
  index, no extra service — honors YAGNI (Constitution V).
- **Alternatives considered**:
  - FAISS / hnswlib (ANN) — rejected: adds a dependency and nondeterminism risk for a pool
    size where brute force is already instant.
  - A vector database (Chroma, Qdrant, pgvector) — rejected: operational overhead conflicts
    with "runnable with minimal setup"; revisit only if pool grows to millions.

## R3. Shared pool storage (source of truth)

- **Decision**: Filesystem-backed pool: one JSON record per skill (or a single JSON file)
  under a pool directory, plus an embedding cache sidecar (`.npz`) holding vectors keyed by
  skill id and stamped with an `embedding_signature` (model id + config). The directory is
  the single source of truth a team shares (e.g. via a shared volume or git).
- **Rationale**: Zero infrastructure, human-readable, portable/exportable (FR-014), and
  easy to demo. Separating the JSON record (metadata + full description) from the vector
  cache lets selection read only metadata + vectors and load full descriptions lazily
  (Constitution II).
- **Alternatives considered**:
  - SQLite — viable and still single-file, but JSON is more transparent for a demo and for
    manual team edits; can migrate later without changing the contract.
  - Embedding vectors inline in JSON — rejected: bloats records and slows the metadata read
    path; a binary sidecar keeps the hot path lean.

## R4. Index/pool consistency on change

- **Decision**: On add/update, (re)embed only the changed skill and update its cache entry;
  on remove, delete the record and its cache entry. The in-memory index is (re)built from
  the pool + cache at service start and refreshed when the pool changes. If a cached vector's
  `embedding_signature` does not match the active model, that skill is re-embedded.
- **Rationale**: Guarantees present skills are discoverable and removed ones are not (FR-011,
  SC-004), and enforces the "model change ⇒ re-embed, never silent mismatch" rule
  (Constitution IV).
- **Alternatives considered**:
  - Full pool re-embed on every change — rejected: wasteful; only the changed skill needs work.
  - Lazy re-embed at query time — rejected: pushes latency into the < 1s selection budget.

## R5. Interface shape (select-then-load)

- **Decision**: Two distinct operations. `select(query, k, threshold)` returns candidate
  metadata + scores only. `load(skill_id)` returns exactly one skill's full description.
  Exposed over both a FastAPI HTTP API (team-shared service) and a CLI (local/demo).
- **Rationale**: Encodes Constitution II at the interface boundary — there is no API path
  that returns all full descriptions for selection. The split maps cleanly to the agent's
  real workflow (rank, then fetch the chosen one).
- **Alternatives considered**:
  - Single endpoint returning full descriptions for top-K — rejected: weakens the context-
    efficiency guarantee and tempts callers to over-fetch.
  - CLI-only — rejected: the shared team pool (P2) needs a service multiple members can hit.

## R6. Retrieval-quality validation approach

- **Decision**: Maintain a small labeled fixture of `query → expected skill id` pairs; an
  integration test asserts the expected skill lands in top-K for ≥ 90% of pairs (SC-001).
- **Rationale**: Makes the core value testable and demonstrable (Constitution V), and turns
  SC-001 into an executable check rather than a claim.
- **Alternatives considered**:
  - Manual/eyeball validation only — rejected: not repeatable, can silently regress.

## Open questions

None. All Technical Context items are resolved; ready for Phase 1 design.
