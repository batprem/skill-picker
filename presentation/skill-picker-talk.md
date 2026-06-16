# Skill Picker — Conference Talk Deck

**Talk**: Skill Picker — Vector-Similarity Skill Selection with vLLM
**Audience**: vLLM conference (ML infra / LLM engineers)
**Length**: 25–30 min (≈18 min content + ≈8 min live demo + Q&A)
**Goal**: Show how vLLM embeddings solve agent context overload, with a real live demo

This markdown is the source draft. Each slide has a headline, sparse on-slide content, and
speaker notes. Designed to be rebuilt 1:1 in Canva.

### Time budget (≈27 min)

| Segment | Slides | Time |
|---|---|---|
| Hook + problem | 1–5 | ~6 min |
| The idea + why vLLM | 6–10 | ~6 min |
| Architecture + design | 11–14 | ~5 min |
| **Live demo** | 15–19 | ~8 min |
| Results, build story, wrap | 20–24 | ~5 min |
| Q&A | — | leftover |

---

## Slide 1 — Title

**Skill Picker**
Vector-Similarity Skill Selection with vLLM

*Stop loading every skill. Retrieve the right one.*

`<presenter name> · vLLM Conference 2026`

> **Notes**: Hook — "Coding agents are drowning in their own skills. Let's fix that with the
> thing this whole conference is about: vLLM." Set energy, promise a live demo.

---

## Slide 2 — Agenda

**What we'll cover**

- The problem: agent context overload
- The idea: embed & retrieve skills
- Why vLLM is the right engine
- Architecture & the key design trick
- **Live demo**
- Results, and how it was built

> **Notes**: 30 seconds. Signal the demo is coming so people stay. Keep it moving.

---

## Slide 3 — The Problem

**Agents pick skills by loading *all* of them**

- An agent (Claude Code, etc.) has dozens–hundreds of skills
- To choose one, it reads **every** skill's name + description into context
- That happens **every turn**, before any real work starts

> **Notes**: This is the pain. The more capable your agent (more skills), the worse the
> selection step scales. It's O(all skills) on every turn.

---

## Slide 4 — Quantify the Pain

**Selection cost grows with the catalog, not the task**

- 100 skills × full descriptions ≈ thousands of tokens up front
- Linear growth: 2× the skills → 2× the selection overhead
- Irrelevant skills crowd out the actual task context

> **Notes**: Make it concrete with token math. Infra audience feels the cost/latency angle
> instantly. Emphasize it scales the *wrong* way.

---

## Slide 5 — The Second Pain

**Every team re-invents its skill list**

- No shared source of truth across a team
- Skills get copy-pasted, drift, go stale
- We want: one pool everyone draws from

> **Notes**: Two pains: (1) context overload, (2) no shared pool. We solve both. Sets up the
> "shared team pool" payoff later.

---

## Slide 6 — The Idea

**Embed once. Retrieve the few. Load lazily.**

1. Embed each skill's *name + short description* into a vector (via vLLM)
2. At query time, embed the **task**, rank skills by cosine similarity
3. Return a short scored shortlist — load the **full** description only for the pick

> **Notes**: The "aha": selection becomes O(top-K), not O(all). Metadata is searched; full
> text is fetched on demand.

---

## Slide 7 — Mental Model

**Treat skills like a corpus**

- This is RAG — but for the agent's own **capabilities**, not documents
- The query is the task; the documents are the skills
- Same retrieval machinery, applied inward

> **Notes**: Anchor to something they know (RAG), then twist it. The novelty is *what* you
> retrieve: tools/skills, not knowledge.

---

## Slide 8 — Why vLLM

**vLLM is the embedding backbone**

- Pooling/embedding mode — not just text generation
- One engine you already run, now doing retrieval
- Same model + config on **both** sides → comparable scores

> **Notes**: The vLLM-conference heart. Many forget vLLM does pooling/embeddings. One engine
> for serve + embed is operationally clean.

---

## Slide 9 — The Model

**`intfloat/e5-small-v2` in pooling mode**

- 384-dim, small, runs on **CPU**
- e5 convention: `query:` for tasks, `passage:` for skills
- The query/passage asymmetry fits "task vs. skill" perfectly

> **Notes**: Explain the prefix convention — it's why e5 fits. Small + CPU = easy to demo and
> deploy. Swappable model (see signature later).

---

## Slide 10 — One Model, Both Sides

**Comparable scores require one embedder**

- Skills embedded as `passage:` → cached vectors
- Task embedded as `query:` at request time
- Cosine is only meaningful if both come from the **same** model+config

> **Notes**: Set up the correctness point that the signature (slide 13) will enforce. This is
> a subtle bug magnet in DIY retrieval.

---

## Slide 11 — Architecture

**Small, boring, fast**

```
task query ─► vLLM embed (query:) ─┐
                                   ▼
   skill pool ─► vLLM embed (passage:) ─► vector cache ─► cosine index
   (SQLite, shared)                                          │
                                                  top-K + scores ─► agent
                                                  agent loads ONE full desc
```

> **Notes**: Walk the data flow once, slowly. Pool → cache → index → scored shortlist → lazy
> load. Note each skill is embedded once (cache).

---

## Slide 12 — SQLite, but No Vector DB

**Storage is a database; search isn't**

- **Storage**: one **SQLite** file (skills + cached vectors) — zero deployment, one artifact
- **Search**: brute-force cosine in memory — sub-millisecond at 100s of skills
- No specialized vector DB / ANN: deterministic, zero ops, no tuning
- Revisit ANN only at millions of items (YAGNI)

> **Notes**: Clear up the apparent contradiction: we *do* use a database (SQLite) for
> durable, zero-ops storage, but the *index* is just normalized vectors + a dot product. No
> Pinecone/FAISS needed at this scale. SQLite was chosen precisely to avoid deployment.

---

## Slide 13 — The Key Trick

**`select` and `load` are separate operations**

- `select(query)` → returns **id + name + score** only. **Never** full text.
- `load(id)` → returns exactly **one** full description, after the agent decides

➡️ Context efficiency is enforced at the **interface**, not by convention

> **Notes**: The design insight worth stealing. There's no API path that returns all full
> descriptions for selection — so you *can't* regress to the old way by accident.

---

## Slide 14 — Staying Consistent

**Embeddings can't silently drift**

- Each cached vector is stamped with an **embedding signature** (model + config)
- Change the model → vectors invalidate → automatic re-embed
- Add / update / remove a skill → reflected in the next query

> **Notes**: Closes the loop from slide 10. Signature makes "same model both sides" an
> invariant, not a hope. Mention re-embed on model swap.

---

## Slide 15 — Live Demo: Setup 🎬

**The scenario**

- A small shared pool of skills (git, sql, pdf, …)
- We'll select, inspect scores, lazy-load, then hit the service
- Real vLLM embeddings under the hood

> **Notes**: DEMO STARTS. Have terminal ready, font large. Recorded fallback queued. State
> what they're about to see so the payoff lands.

---

## Slide 16 — Demo 1: Seed the Pool

**Add skills to the shared pool**

```
$ skill-picker add --id git-bisect-helper --name "Git Bisect Helper" \
    --description "Guide a git bisect session to locate a regression commit." \
    --body @skills/git-bisect-helper/SKILL.md
$ skill-picker list
```

> **Notes**: Show that adding is cheap and the pool is one SQLite file (zero deployment).
> Mention embeddings are computed lazily / cached in the same DB — adding doesn't block. Call
> out the SKILL.md mapping: `--description` is the short frontmatter text we *embed and match*;
> `--body` is the full content loaded only after selection. Same two-tier shape as real skills.

---

## Slide 17 — Demo 2: Select + Scores

**One task, ranked candidates**

```
$ skill-picker select "find which commit broke the build" -k 3
score   id                  name
0.83    git-bisect-helper   Git Bisect Helper
0.34    sql-explainer       SQL Query Explainer
0.21    pdf-table-extract   PDF Table Extractor
```

> **Notes**: The money moment. Point at the scores — observable, explainable. 0.83 on the
> match is a *real* vLLM e5 number. No full descriptions returned here.

---

## Slide 18 — Demo 3: Lazy Load

**Load the full text only for the winner**

```
$ skill-picker show git-bisect-helper
# Git Bisect Helper  (git-bisect-helper)
Guide a git bisect session to locate a regression commit.
```

> **Notes**: This is the whole thesis in one command — full description fetched only for the
> chosen skill, not the pool. Contrast with "load everything".

---

## Slide 19 — Demo 4: Shared Service

**The team-facing API**

```
$ skill-picker serve --port 8000
$ curl localhost:8000/v1/select -H 'content-type: application/json' \
    -d '{"query":"speed up a slow report","k":3}'
$ curl localhost:8000/v1/health      # model signature + pool size
```

> **Notes**: Show the same core over HTTP — this is how a team shares one pool. Health
> endpoint surfaces the embedding signature (observability). End demo on a high note.

---

## Slide 20 — Results

**It works, and it's measurable**

- **0.83** cosine between a task query and its matching skill (real e5-small-v2)
- **< 1s** selection for 100+ skills
- **≥ 80%** less content needed to choose a skill vs. loading everything
- **32** passing tests (retrieval quality, context efficiency, consistency, perf)

> **Notes**: Tie each number to a slide: 0.83 → vLLM works; <1s → brute force is fine; 80% →
> the point; tests → it's real.

---

## Slide 21 — Shared Team Pool

**One pool, whole team**

- Portable, shareable store: one SQLite file (skills + cached vectors), zero deployment
- Add a skill once → everyone selects from the same current set
- HTTP service + CLI over the same selection core; export/import for portability

> **Notes**: Payoff for pain #2. Point teammates at one directory or run the service.

---

## Slide 22 — How It Was Built

**Spec-first, working in one session**

- Constitution → spec → plan → tasks → implementation
- The constitution *encoded* the guardrails (context efficiency, vLLM-only embeddings)
- Those rules became tests, not just prose

> **Notes**: Nice hallway-track story. The design principles were written down first and then
> enforced in code/tests. Optional depth if running ahead of time.

---

## Slide 23 — Takeaways

**Steal these three ideas**

1. Treat your agent's **skills like a corpus** — embed & retrieve, don't bulk-load
2. **vLLM does embeddings too** — pooling mode, one engine, consistent scores
3. Enforce efficiency at the **interface** (select vs. load), not by discipline

> **Notes**: The transferable lesson. Generalizes to tools, prompts, memories — anything an
> agent over-loads.

---

## Slide 24 — Thank You / Q&A

**Skill Picker**

- Repo / slides: `<link>`
- Questions?

> **Notes**: Offer the repo. Likely Qs: why not a vector DB (slide 12), model choice (e5,
> swappable), scaling to millions (ANN then), determinism (normalized + tie-break by id).

---

## Appendix — Backup slides (if asked)

### A1 — Why not a vector DB?
At tens–hundreds of skills, brute-force cosine is instant and deterministic. A DB/ANN adds
ops overhead and nondeterminism for zero benefit at this scale. Revisit at millions.

### A2 — Why e5-small-v2?
Small (384-dim), CPU-friendly, strong retrieval quality, query/passage prefixes match the
task-vs-skill use case. Swappable — the signature forces a clean re-embed on change.

### A3 — Determinism
Normalized vectors, stable tie-break by id, same model both sides → identical inputs give
identical ranked output (testable, demoable).

### A4 — CPU memory note
On the CPU backend, vLLM's `gpu_memory_utilization` sizes reserved RAM; lower it on
constrained machines if engine startup reports insufficient memory.
