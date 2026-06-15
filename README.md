# Skill Picker

Vector-similarity skill selection for coding agents, backed by vLLM embeddings.

Coding agents normally load every skill's name and description to decide which to use,
which floods the context window. Skill Picker instead embeds each skill's matching metadata
into a vector (via vLLM), ranks skills by similarity to the incoming task, and returns a
short scored shortlist — loading the full description only for the skill the agent actually
picks. The pool is a single shared source of truth a whole team can reuse — stored as one
zero-deployment SQLite file (`data/skills.db`) holding both skills and their cached vectors.

See [`specs/001-skill-picker/`](specs/001-skill-picker/) for the spec, plan, and design.

## Install

The workspace builds vLLM from source into `.venv` (CPU/macOS). Install the package and its
remaining dependencies without disturbing that build:

```bash
uv pip install -e . --no-deps          # installs the skill-picker console command
uv pip install -e ".[dev]" --no-deps   # adds pytest + httpx for the test suite
```

## Usage

```bash
# Add skills to the shared pool (SQLite file data/skills.db by default)
skill-picker add --id git-bisect-helper --name "Git Bisect Helper" \
  --description "Guide a git bisect session to locate a regression commit."

# Rank skills for a task — returns metadata + scores only, no full descriptions
skill-picker select "find which commit broke the build" -k 3

# Load the full description of just the chosen skill
skill-picker show git-bisect-helper

# Inspect / manage the pool
skill-picker list
skill-picker remove git-bisect-helper

# Run the shared HTTP service for the team
skill-picker serve --port 8000
```

`select`, `reindex`, and `serve` take `--embedder`:

- `--embedder vllm` (default): production path — embeds via vLLM (Constitution requirement).
  On a memory-constrained CPU you may need to lower the reserved-RAM fraction; the embedder
  forwards `gpu_memory_utilization` (which sizes CPU RAM on the CPU backend).
- `--embedder hashing`: deterministic offline lexical embedder for dev/tests only — no model
  load, not semantic. Useful for trying the workflow without spinning up vLLM.

## Test

```bash
.venv/bin/python -m pytest -q
```

The suite runs offline (hashing embedder); the selection pipeline is identical to the vLLM
path. See [`specs/001-skill-picker/quickstart.md`](specs/001-skill-picker/quickstart.md) for
an end-to-end walkthrough and the success-criteria checklist.
