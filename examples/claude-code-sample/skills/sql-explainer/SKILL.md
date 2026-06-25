---
name: SQL Query Explainer
description: Explain and optimize SQL queries, suggesting indexes.
---

# SQL Query Explainer

Use this skill to understand why a query is slow and how to speed it up.

## Approach

1. **Read the plan**: run `EXPLAIN` (or `EXPLAIN ANALYZE` to get real timings and row
   counts). Compare estimated vs actual rows — large gaps mean stale statistics.
2. **Find the cost**: look for sequential scans on large tables, nested-loop joins over
   big inputs, and expensive sorts/hashes that spill to disk.
3. **Index the predicates**: add indexes on columns used in `WHERE`, `JOIN`, and
   `ORDER BY`. A composite index should lead with the most selective equality column.
4. **Avoid index killers**: functions on indexed columns (`WHERE lower(email)=...`),
   leading wildcards (`LIKE '%x'`), and implicit type casts prevent index use.
5. **Re-measure**: re-run `EXPLAIN ANALYZE` after each change; keep only indexes that
   actually move the plan (every index adds write cost).

## Output

State the bottleneck in one sentence, the concrete `CREATE INDEX` / rewrite to apply, and
the expected effect on the plan.
