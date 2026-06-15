# Phase 1 Data Model: Skill Picker

**Feature**: 001-skill-picker | **Date**: 2026-06-15

Derived from the Key Entities in [spec.md](./spec.md) and decisions in
[research.md](./research.md).

## Entity: Skill

The stored unit of a reusable agent capability. The single record holds both the
lightweight matching metadata and the heavyweight full description; readers choose which
part to load (Constitution II).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Stable unique identifier (slug or UUID). Immutable once created. |
| `name` | string | yes | Human-readable skill name. Part of matching text. |
| `match_text` | string | yes | Short description used for relevance. Defaults to a truncation of `full_description` if not provided. Part of matching text. |
| `full_description` | string | yes | Full skill content. Loaded ONLY after selection, never during search. |
| `tags` | string[] | no | Optional labels; not used for ranking in v1. |
| `updated_at` | string (ISO-8601) | yes | Last modification timestamp; supports cache invalidation/ordering. |

**Validation rules**:

- `id` MUST be unique within the pool and MUST NOT change on update (FR-001).
- `name` and `match_text` MUST be non-empty (they form the embedded matching text).
- The embedded "passage" text is composed deterministically as `passage: {name}. {match_text}`
  so re-embedding is reproducible (FR-013).
- `full_description` MUST NOT be required to perform a selection (FR-006).

**Derivations**:

- `match_text` (if absent) = first N characters of `full_description` (single, documented N).

## Entity: EmbeddingVector (cache entry)

A cached embedding for one skill's matching text. Stored in the sidecar cache, not in the
JSON record.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `skill_id` | string | yes | Foreign key → Skill.id |
| `vector` | float32[dim] | yes | L2-normalized embedding of the skill's passage text. |
| `embedding_signature` | string | yes | Identifies model + config (e.g. `e5-small-v2@pooling`). |
| `source_hash` | string | yes | Hash of the exact passage text embedded; detects stale vectors. |

**Validation rules**:

- A vector is valid for use only if `embedding_signature` matches the active model AND
  `source_hash` matches the current passage text; otherwise the skill MUST be re-embedded
  (Constitution IV, FR-008).
- All vectors in the active index MUST share one `embedding_signature` and one `dim`.

## Entity: SkillPool

The shared collection that is the single source of truth (Constitution III). Not a record
type — an aggregate with operations.

**Operations** (map to functional requirements):

- `add(skill)` → persists record, embeds, caches vector (FR-007)
- `update(id, fields)` → updates record, re-embeds if matching text changed (FR-008)
- `remove(id)` → deletes record + cache entry (FR-009)
- `get(id)` → returns full Skill record incl. `full_description` (FR-005)
- `list_metadata()` → returns id/name/match_text only (no full descriptions) for indexing
- `export()` / `import()` → portable serialization of the pool (FR-014)

**Invariants**:

- A skill present in the pool is discoverable by selection; a removed skill is never
  returned (FR-011).
- Changes are reflected in the next selection cycle (SC-004).

## Entity: SelectionQuery

Transient input to a selection. Not persisted.

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `query` | string | yes | — | Free-text task description. Embedded as `query: {query}`. |
| `k` | integer | no | 5 | Max candidates returned (small sensible default, FR-003). |
| `threshold` | float | no | 0.0 | Minimum cosine score to include a candidate (FR-012). |

**Validation rules**:

- `query` MUST be non-empty.
- `k` MUST be ≥ 1; `threshold` MUST be in `[-1.0, 1.0]` (cosine range).

## Entity: Candidate

One ranked result. Carries metadata + score only — no full description (Constitution II).

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | Skill.id (used by a subsequent `load`). |
| `name` | string | For display/inspection. |
| `score` | float | Cosine similarity to the query, in `[-1.0, 1.0]`. |

## Entity: SelectionResult

The response to a SelectionQuery.

| Field | Type | Notes |
|-------|------|-------|
| `candidates` | Candidate[] | Ordered by descending `score`, length ≤ `k`, all ≥ `threshold`. May be empty. |
| `query` | string | Echo of the input query (for inspection/observability, Constitution V). |

**Rules**:

- Ordering is stable for identical inputs; ties broken deterministically by `id` (FR-013).
- Empty `candidates` is a valid result (empty pool or nothing ≥ threshold), not an error.

## Relationships

```text
SkillPool 1 ──── * Skill 1 ──── 1 EmbeddingVector (cache)
SelectionQuery ──> [index over EmbeddingVectors] ──> SelectionResult ──> * Candidate ──(id)──> Skill
```

## State / lifecycle notes

- A Skill goes: created → (optionally) updated* → removed. Each create/update with changed
  matching text produces a fresh EmbeddingVector; remove deletes both record and vector.
- The in-memory index is a rebuildable projection of (pool metadata + valid cache vectors);
  it holds no authoritative state.
