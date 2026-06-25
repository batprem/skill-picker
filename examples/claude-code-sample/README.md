# Claude Code sample — skill-picker integration

A minimal, self-contained **Claude Code project** that wires up
[skill-picker](../../README.md) so an agent retrieves the *right* skill by vector similarity
instead of loading every skill's body into context every turn.

It shows the two-tier shape skill-picker shares with the Agent Skills (`SKILL.md`) standard:

| `SKILL.md` | skill-picker | What it's for |
|---|---|---|
| frontmatter `description` | `--description` | **short text, embedded → drives selection** |
| markdown body | `--body` | **full instructions, loaded only after a skill is picked** |

## Layout

```
examples/claude-code-sample/
├── .claude/
│   ├── settings.json        # permissions so skill-picker runs without prompts
│   └── commands/
│       └── pick-skill.md     # /pick-skill <task> — shortlist skills for a task
├── skills/                   # example skills in Agent Skills (SKILL.md) format
│   ├── git-bisect-helper/SKILL.md
│   ├── k8s-debug/SKILL.md
│   ├── pdf-table-extract/SKILL.md
│   ├── regex-builder/SKILL.md
│   └── sql-explainer/SKILL.md
├── logs/app.log              # sample log file for the regex-builder demo prompt
├── seed.py                   # ingest the SKILL.md files into the pool
└── data/skills.db            # the shared SQLite pool (created by seed.py; git-ignored)
```

Picking goes through the **HTTP service** here, so a whole team can share one running pool. The
one-time seeding still uses the CLI.

```bash
# 0. Install skill-picker (from the repo root). The console command must be on PATH.
#    e.g.  uv pip install -e . --no-deps   (see the top-level README)

# 1. From this directory, seed the pool from the SKILL.md files (one-time, CLI).
cd examples/claude-code-sample
python seed.py                 # frontmatter description -> --description, body -> --body

# 2. Start the shared service (keep it running in its own terminal).
skill-picker serve --pool data/skills.db --port 8000
#    low-RAM machine: add  --gpu-memory-utilization 0.12
#    offline / no model load: add  --embedder hashing

# 3. Select skills for a task over HTTP (metadata + scores only; no bodies loaded).
curl -s localhost:8000/v1/select -H 'content-type: application/json' \
  -d '{"query": "my pods keep crashing in the cluster", "k": 3}'

# 4. Load the full body of just the chosen skill over HTTP.
curl -s localhost:8000/v1/skills/k8s-debug
```

Or, inside Claude Code launched from this directory (with the service running), run the slash
command:

```
/pick-skill my pods keep crashing in the cluster
```

`.claude/settings.json` pre-allows the `curl` (and `skill-picker`) commands so the agent isn't
prompted for permission on every call. The `content-type: application/json` header is required —
without it the API rejects the body with HTTP 422.

## Example questions to try

Each query below shares **no keywords** with its target skill — matching is semantic, via the
vLLM embeddings. Run them with `/pick-skill <question>` (service running) or by `curl`ing
`POST /v1/select`. The expected top pick is shown.

| Ask | Expected top skill |
|---|---|
| my pods keep crashing in the cluster | `k8s-debug` |
| why is my deployment stuck and never becomes ready? | `k8s-debug` |
| find which change introduced this regression | `git-bisect-helper` |
| narrow down the commit that broke the build | `git-bisect-helper` |
| speed up a slow database report | `sql-explainer` |
| the query does a full table scan — what index do I add? | `sql-explainer` |
| pull the data out of a scanned invoice document | `pdf-table-extract` |
| turn the tables in this document into a spreadsheet | `pdf-table-extract` |
| match every email address in a log file | `regex-builder` |
| write a pattern to capture dates from free text | `regex-builder` |

Quick check from the shell (service running on port 8000):

```bash
curl -s localhost:8000/v1/select -H 'content-type: application/json' \
  -d '{"query": "why is my deployment stuck and never becomes ready?", "k": 3}'
```

The response is metadata + scores only. Note that e5 cosine scores cluster high (≈0.7–0.9); the
**ranking** is the signal, not the absolute spread.

### Worked example: "match every email address in a log file"

`logs/app.log` is a sample log with email addresses in varied shapes (plus-addressing,
subdomains, mixed case, an apostrophe local-part, one URL-encoded `%40`, one inside a query
string) plus noise lines with no email. Use it to actually run the skill the query selects:

```
/pick-skill match every email address in a log file        # → selects regex-builder
```

Then apply the loaded skill to the file, e.g. extract the matches:

```bash
grep -oE '[A-Za-z0-9._%+'"'"'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' logs/app.log | sort -u
```

It's a deliberately imperfect starting pattern — the `regex-builder` body walks through hardening
it (the `%40`-encoded address won't match as-is; mixed-case duplicates collapse under `sort -u`
only if you lowercase first), which is the point of loading the skill.

## Notes

- **CPU memory**: on the CPU backend vLLM reserves a fraction of *total* RAM (despite the flag
  name `--gpu-memory-utilization`). On a constrained machine, add e.g.
  `--gpu-memory-utilization 0.12` to `select`/`reindex`/`serve`.
- **Offline**: append `--embedder hashing` to skip the model load — deterministic but lexical,
  for development only (production selection uses vLLM).
- Re-running `seed.py` is idempotent per id: it skips skills that already exist. Delete
  `data/skills.db` to start fresh.
