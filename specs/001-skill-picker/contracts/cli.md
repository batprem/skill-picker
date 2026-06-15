# Contract: CLI

**Feature**: 001-skill-picker | **Date**: 2026-06-15

Local authoring + demo entrypoint over the same selection service as the HTTP API. Command
group: `skill-picker`. Human-readable output by default; `--json` for machine output.

The CLI honors the same select-then-load split as the HTTP contract (Constitution II): a
`select` shows ranked candidates with scores; a separate `show` loads one full description.

---

## `skill-picker select <query>`

Rank skills by similarity to a task query.

| Option | Default | Notes |
|--------|---------|-------|
| `-k, --top-k <int>` | 5 | Max candidates (≥ 1). |
| `-t, --threshold <float>` | 0.0 | Min cosine score, in [-1.0, 1.0]. |
| `--json` | off | Emit JSON SelectionResult instead of a table. |

**Human output** (observability — scores are shown, Constitution V):

```text
score   id                  name
0.83    pdf-table-extract   PDF Table Extractor
0.61    doc-parser          Document Parser
```

Exit `0` with an empty list message when nothing meets the threshold (not an error).

---

## `skill-picker show <id>`

Load and print one skill's full description (the post-selection step, FR-005).
Exit non-zero if `id` does not exist (FR-011).

---

## `skill-picker add`

Add a skill to the shared pool (FR-007).

| Option | Required | Notes |
|--------|----------|-------|
| `--id <id>` | yes | Stable unique id. |
| `--name <name>` | yes | Skill name. |
| `--description <text>` | yes | Full description (file path allowed via `@path`). |
| `--match-text <text>` | no | Short matching text; derived from description if omitted. |
| `--tags <a,b,c>` | no | Comma-separated tags. |

Embeds and caches the vector on add. Errors if `id` already exists.

---

## `skill-picker update <id>`

Update fields of an existing skill (FR-008); re-embeds if matching text changed. Same
options as `add` (all optional except the positional `id`).

---

## `skill-picker remove <id>`

Remove a skill from the pool (FR-009). Deletes record + cached vector.

---

## `skill-picker list`

List skill **metadata only** (id, name, tags) — never full descriptions. `--json` for
export-friendly output (FR-014).

---

## `skill-picker serve`

Start the FastAPI service exposing the HTTP contract.

| Option | Default |
|--------|---------|
| `--host <host>` | 127.0.0.1 |
| `--port <int>` | 8000 |
| `--pool <dir>` | `data/skills` |

---

## `skill-picker reindex`

Rebuild the in-memory index from the pool and re-embed any skill whose cached vector is
stale or whose `embedding_signature` no longer matches the active model (Constitution IV).

---

## Cross-cutting CLI rules

- `--pool <dir>` (global) selects the shared pool directory; defaults to `data/skills` so a
  team can point every member at one shared location.
- Identical inputs produce identical ranked output (FR-013).
- Exit codes: `0` success (incl. empty result), `2` usage error, `3` not found, `4` conflict.
