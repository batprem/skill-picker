# Contract: HTTP API (shared service)

**Feature**: 001-skill-picker | **Date**: 2026-06-15

The team-shared service over the single source-of-truth pool. The contract deliberately
splits **select** (metadata + scores) from **load** (one full description) so no path
returns the full descriptions of the whole pool for selection (Constitution II).

Base path: `/v1`. Content type: `application/json`.

---

## POST /v1/select

Rank skills by similarity to a task query. Returns metadata + scores only.

**Request body**:

```json
{
  "query": "parse a PDF and extract tables",
  "k": 5,
  "threshold": 0.2
}
```

- `query` (string, required, non-empty)
- `k` (integer, optional, default 5, ≥ 1)
- `threshold` (number, optional, default 0.0, in [-1.0, 1.0])

**200 Response**:

```json
{
  "query": "parse a PDF and extract tables",
  "candidates": [
    { "id": "pdf-table-extract", "name": "PDF Table Extractor", "score": 0.83 },
    { "id": "doc-parser", "name": "Document Parser", "score": 0.61 }
  ]
}
```

- `candidates` ordered by descending `score`, length ≤ `k`, every `score` ≥ `threshold`.
- Empty `candidates` (`[]`) is returned for an empty pool or when nothing meets `threshold`
  (200, not an error).
- Response MUST NOT contain `full_description` for any skill.

**400** if `query` is empty or `k`/`threshold` out of range.

---

## GET /v1/skills/{id}

Load exactly one skill's full description after selection.

**200 Response**:

```json
{
  "id": "pdf-table-extract",
  "name": "PDF Table Extractor",
  "match_text": "Extract tables from PDF files into structured rows.",
  "full_description": "…full skill content…",
  "tags": ["pdf", "extraction"],
  "updated_at": "2026-06-15T10:00:00Z"
}
```

**404** if no skill with `id` exists (e.g. it was removed — consistency, FR-011).

---

## POST /v1/skills

Add a skill to the shared pool (FR-007). Embeds and caches its vector.

**Request body**:

```json
{
  "id": "pdf-table-extract",
  "name": "PDF Table Extractor",
  "match_text": "Extract tables from PDF files into structured rows.",
  "full_description": "…full skill content…",
  "tags": ["pdf", "extraction"]
}
```

- `id`, `name`, `full_description` required; `match_text` optional (derived from
  `full_description` if omitted); `tags` optional.

**201** returns the created record. **409** if `id` already exists.

---

## PUT /v1/skills/{id}

Update an existing skill (FR-008). Re-embeds if `name`/`match_text` changed.

**Request body**: any subset of `name`, `match_text`, `full_description`, `tags`. `id` is
immutable and ignored if present.

**200** returns the updated record. **404** if not found.

---

## DELETE /v1/skills/{id}

Remove a skill (FR-009). Deletes record and cache entry; afterwards it is not returned by
`/select` or `/skills/{id}`.

**204** on success. **404** if not found.

---

## GET /v1/skills

List skill **metadata only** (id, name, match_text, tags, updated_at) — never
`full_description`. Supports inspection and export tooling (FR-014).

**200 Response**:

```json
{
  "skills": [
    { "id": "pdf-table-extract", "name": "PDF Table Extractor",
      "match_text": "Extract tables from PDF files…", "tags": ["pdf"],
      "updated_at": "2026-06-15T10:00:00Z" }
  ],
  "count": 1,
  "embedding_signature": "e5-small-v2@pooling"
}
```

---

## GET /v1/health

Liveness + active embedding model signature (Constitution IV observability).

**200 Response**:

```json
{ "status": "ok", "embedding_signature": "e5-small-v2@pooling", "pool_size": 42 }
```

---

## Cross-cutting contract rules

- Identical (pool, query, k, threshold) MUST yield identical `candidates` ordering (FR-013).
- No selection-time response includes full descriptions of non-selected skills
  (Constitution II) — enforced by the select/load split.
- All embeddings (skills and queries) share one `embedding_signature`; on model change the
  service re-embeds affected skills rather than serving mismatched vectors (Constitution IV).
