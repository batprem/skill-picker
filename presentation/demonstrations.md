# Skill Picker — Live Demo Runbook

Companion to `skill-picker-talk.md` (slides 15–19, ~8 min). Every command here was run and
verified on the demo machine. Real `intfloat/e5-small-v2` embeddings via vLLM in pooling mode.

> **The one gotcha:** vLLM lives in `.venv`, so run **`.venv/bin/skill-picker`** (not a bare
> `skill-picker`). On the CPU backend `gpu_memory_utilization` is the fraction of *total* RAM
> reserved — on this ~18 GiB Mac with little free RAM, pass **`--gpu-memory-utilization 0.12`**
> or the engine refuses to start. Each fresh CLI call reloads the engine (~25–30 s), so for a
> smooth demo **pre-warm `serve` once** (Step 0) and drive the HTTP API.

---

## Step 0 — Pre-flight (before you go on stage)

```bash
cd /Users/premchotipanit/Documents/vllm

# Fresh demo pool so the run is reproducible
rm -f data/demo.db data/demo.db-wal data/demo.db-shm

# Seed 5 skills (no model load — add is cheap)
.venv/bin/skill-picker add --pool data/demo.db --id git-bisect-helper \
  --name "Git Bisect Helper" \
  --description "Guide a git bisect session to locate a regression commit."
.venv/bin/skill-picker add --pool data/demo.db --id sql-explainer \
  --name "SQL Query Explainer" \
  --description "Explain and optimize SQL queries, suggesting indexes."
.venv/bin/skill-picker add --pool data/demo.db --id pdf-table-extract \
  --name "PDF Table Extractor" \
  --description "Extract tables from PDF files into structured rows and export as CSV."
.venv/bin/skill-picker add --pool data/demo.db --id k8s-debug \
  --name "Kubernetes Debugger" \
  --description "Diagnose failing pods, crashloops, and networking issues in a Kubernetes cluster."
.venv/bin/skill-picker add --pool data/demo.db --id regex-builder \
  --name "Regex Builder" \
  --description "Construct and explain regular expressions for text matching and extraction."

# Warm the engine + cache all passage vectors once (~30 s). Keep this terminal running.
.venv/bin/skill-picker serve --pool data/demo.db --embedder vllm \
  --gpu-memory-utilization 0.12 --port 8000
```

Leave `serve` running in a background terminal. Open a **second** terminal for the live `curl`s
so the audience sees instant responses (the model is already warm and vectors are cached in the
SQLite file).

> **Notes:** Mention adds are instant and land in one SQLite file (zero deployment). Embeddings
> are computed lazily and cached in the same `.db`, so the first `select` is what populates them.

**Maps to the `SKILL.md` standard.** `--description` is the short frontmatter-style text that
gets *embedded and matched* (selection); `--body` is the full content loaded only after a skill
is picked. The five seeds above pass only `--description`, so the body falls back to it — fine for
a toy. To ingest a real skill, keep selection cheap and load the body lazily:

```bash
.venv/bin/skill-picker add --pool data/demo.db --id git-bisect-helper \
  --name "Git Bisect Helper" \
  --description "Guide a git bisect session to locate a regression commit." \  # frontmatter description → embedded
  --body @skills/git-bisect-helper/SKILL.md                                    # full body → lazy-loaded only
```

---

## Step 1 — Show the shared pool (slide 16)

```bash
.venv/bin/skill-picker list --pool data/demo.db
```

Expected:

```
id                      tags                    name
git-bisect-helper                               Git Bisect Helper
k8s-debug                                       Kubernetes Debugger
pdf-table-extract                               PDF Table Extractor
regex-builder                                   Regex Builder
sql-explainer                                   SQL Query Explainer
```

> **Notes:** `list` shows metadata only — never full descriptions. The pool is one file anyone
> on the team can point at.

---

## Step 2 — Select + scores, the money moment (slide 17)

Run **four** task queries. None share keywords with the skill names — the match is purely
semantic. Verified output and scores:

```bash
curl -s localhost:8000/v1/select -H 'content-type: application/json' \
  -d '{"query":"find which commit broke the build","k":3}'
```
→ **git-bisect-helper** 0.82 · regex-builder 0.81 · k8s-debug 0.80

```bash
curl -s localhost:8000/v1/select -H 'content-type: application/json' \
  -d '{"query":"speed up a slow database report","k":3}'
```
→ **sql-explainer** 0.81 · git-bisect-helper 0.80 · pdf-table-extract 0.80

```bash
curl -s localhost:8000/v1/select -H 'content-type: application/json' \
  -d '{"query":"my pods keep crashing in the cluster","k":3}'
```
→ **k8s-debug 0.86** · git-bisect-helper 0.74 · regex-builder 0.74

```bash
curl -s localhost:8000/v1/select -H 'content-type: application/json' \
  -d '{"query":"pull data out of a scanned invoice document","k":3}'
```
→ **pdf-table-extract** 0.82 · git-bisect-helper 0.78 · regex-builder 0.78

> **Notes:** Point at the scores — observable and explainable. Best contrast is the k8s query:
> "pods / crashing / cluster" → **Kubernetes Debugger** at **0.86** with a clear margin, with
> zero shared words. The response contains **only** `id`, `name`, `score` — **no**
> `full_description`. e5 cosines cluster high (0.74–0.86); the *ranking* is the point, not the
> absolute spread.

---

## Step 3 — Lazy load, the whole thesis in one call (slide 18)

```bash
curl -s localhost:8000/v1/skills/k8s-debug
```

This is the **only** path that returns full text — and only for the one chosen skill:

```json
{
  "id": "k8s-debug",
  "name": "Kubernetes Debugger",
  "full_description": "Diagnose failing pods, crashloops, and networking issues in a Kubernetes cluster.",
  ...
}
```

CLI equivalent (if you prefer terminal over curl):

```bash
.venv/bin/skill-picker show k8s-debug --pool data/demo.db
```

> **Notes:** The thesis in one command — `select` ranks on metadata; `load` fetches full text
> for the winner only. Contrast with "read every skill's description every turn." There is **no
> API path** that returns all full descriptions for selection, so you can't regress by accident.

---

## Step 4 — Observability / shared service (slide 19)

```bash
curl -s localhost:8000/v1/health
```

→ surfaces the **embedding signature** (`intfloat/e5-small-v2@pooling`) and pool size. Same
selection core over HTTP is how a whole team shares one pool. End the demo here on a high note.

> **Notes:** The signature is the consistency guarantee — change the model and cached vectors
> invalidate and re-embed automatically (slide 14). Health = observability for free.

---

## Fallbacks if the live demo misbehaves

- **Engine won't start / OOM** (`Available memory ... less than desired CPU memory utilization`):
  lower the reservation further (`--gpu-memory-utilization 0.10`) or close other apps to free
  RAM. The worker checks *free* RAM at startup, after the parent already used ~0.8 GiB.
- **No time / no GPU-RAM headroom:** swap `--embedder vllm` for `--embedder hashing` — a
  deterministic offline lexical embedder, no model load. Ranking is keyword-ish (not semantic),
  so say so; use it only as a structural fallback to show the select/load flow.
- **Total failure:** play the pre-recorded terminal capture (record Steps 1–4 beforehand).
- **Cold-start stall:** never run a bare `select --embedder vllm` live (25–30 s reload each
  call) — always drive the warm `serve` from Step 0.
```
