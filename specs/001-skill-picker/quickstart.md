# Quickstart: Skill Picker

**Feature**: 001-skill-picker | **Date**: 2026-06-15

A 5-minute path to a working demo of vector-similarity skill selection backed by vLLM.

## Prerequisites

- Python 3.12 (`>=3.12,<3.13`) — matches the workspace `pyproject.toml`.
- vLLM available and able to run in pooling/embedding mode on CPU (the existing
  `test_embedding.py` already proves this works in this workspace).
- First run downloads the `intfloat/e5-small-v2` model.

## 1. Install

```bash
# from repo root
uv sync            # or: pip install -e .
```

Dependencies: `vllm`, `numpy`, `fastapi`, `uvicorn`, `pydantic`, plus the CLI lib.

## 2. Seed the shared pool

```bash
skill-picker add --id pdf-table-extract \
  --name "PDF Table Extractor" \
  --description "Extract tables from PDF files into structured rows and export as CSV."

skill-picker add --id sql-explainer \
  --name "SQL Query Explainer" \
  --description "Explain and optimize SQL queries, suggesting indexes."

skill-picker add --id git-bisect-helper \
  --name "Git Bisect Helper" \
  --description "Guide a git bisect session to locate a regression commit."
```

Records land in `data/skills/` (the shared source of truth); embeddings are cached there.

## 3. Select skills for a task (the core demo)

```bash
skill-picker select "find which commit broke the build" -k 3
```

Expected: `git-bisect-helper` ranks first with the highest score. Only candidate metadata
and scores are returned — no full descriptions yet (context-efficient selection).

```text
score   id                  name
0.79    git-bisect-helper   Git Bisect Helper
0.34    sql-explainer       SQL Query Explainer
0.21    pdf-table-extract   PDF Table Extractor
```

## 4. Load the chosen skill's full description

```bash
skill-picker show git-bisect-helper
```

This is the only step that returns a full description — and only for the one selected skill.

## 5. Run the shared service (team use)

```bash
skill-picker serve --port 8000
```

Then from any teammate:

```bash
curl -s localhost:8000/v1/select \
  -H 'content-type: application/json' \
  -d '{"query":"speed up a slow database report","k":3,"threshold":0.2}'

curl -s localhost:8000/v1/skills/sql-explainer
```

## Validation checklist (maps to Success Criteria)

- [ ] **SC-001 / US1**: For the labeled fixture queries, the intended skill is in the top-K
      (target ≥ 90%). Run: `pytest tests/integration -k retrieval_quality`.
- [ ] **SC-002**: `select` returns in < 1s for a pool of ≥ 100 skills.
- [ ] **SC-003 / Constitution II**: `select` output and `/v1/select` responses contain no
      `full_description`; full text comes only from `show` / `GET /v1/skills/{id}`.
- [ ] **SC-004 / US2**: After `add`/`update`/`remove`, the next `select` reflects the change.
      Run: `pytest tests/integration -k pool_consistency`.
- [ ] **SC-005**: Two clients issuing the same query against the same pool get identical
      ranked results.
- [ ] **SC-006 / US3**: Every candidate shows a similarity score for inspection.

## Notes

- Changing the embedding model invalidates cached vectors; run `skill-picker reindex` to
  re-embed the pool (the active model signature is shown by `GET /v1/health`).
- Point every team member's `--pool` at one shared directory to share the same skills.
