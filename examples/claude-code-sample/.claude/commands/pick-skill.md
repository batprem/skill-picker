---
description: Shortlist the most relevant skills for a task via the skill-picker HTTP service, then load only the top pick.
argument-hint: <task description>
allowed-tools: Bash(curl:*)
---
A task has come in: **$ARGUMENTS**

Ranked skill candidates from the skill-picker service (metadata + similarity scores only —
no bodies loaded yet):

!`curl -s localhost:8000/v1/select -H 'content-type: application/json' -d "{\"query\": \"$ARGUMENTS\", \"k\": 3}"`

Pick the single best-matching candidate above, then load **only that one** skill's full body
over HTTP with `curl -s localhost:8000/v1/skills/<id>` and follow its instructions to handle
the task. Do not load the other candidates' bodies — selecting first is the whole point.

> Requires the service to be running: `skill-picker serve --pool data/skills.db --port 8000`
> (add `--gpu-memory-utilization 0.12` on a low-RAM machine, or `--embedder hashing` offline).
