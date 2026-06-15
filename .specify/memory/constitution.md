<!--
SYNC IMPACT REPORT
==================
Version change: (template / unversioned) → 1.0.0
Bump rationale: Initial ratification. All template placeholders replaced with
concrete, project-specific principles and governance for the "skill-picker" project.

Modified principles: N/A (initial adoption)
Renamed principles:
  - [PRINCIPLE_1_NAME] → I. Vector-First Skill Selection
  - [PRINCIPLE_2_NAME] → II. Context Efficiency (NON-NEGOTIABLE)
  - [PRINCIPLE_3_NAME] → III. Shared Skill Pool Integrity
  - [PRINCIPLE_4_NAME] → IV. vLLM as the Embedding Backbone
  - [PRINCIPLE_5_NAME] → V. Demo-Ready Simplicity & Observability

Added sections:
  - Technology & Architecture Constraints (was [SECTION_2_NAME])
  - Development Workflow & Quality Gates (was [SECTION_3_NAME])

Removed sections: None

Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no change needed (generic Constitution Check gate)
  - .specify/templates/spec-template.md ✅ no change needed (no constitution-coupled sections)
  - .specify/templates/tasks-template.md ✅ no change needed (principle-driven task types already covered)
  - .specify/templates/commands/*.md ✅ none present; no agent-specific references to fix

Follow-up TODOs: None
-->

# Skill-Picker Constitution

## Core Principles

### I. Vector-First Skill Selection

Skill selection MUST be driven by vector similarity over embedded skill metadata,
not by loading every skill into the agent's context. Each skill's `name` and
`description` MUST be embedded into a vector representation and stored in a queryable
index. At selection time, the system MUST embed the incoming task/query and retrieve
the most similar skills by similarity score, returning a ranked candidate set.

Rationale: Similarity-based retrieval is the core thesis of the project — it replaces
"load all and let the model decide" with "retrieve the relevant few", which is what
makes efficient skill loading possible at all.

### II. Context Efficiency (NON-NEGOTIABLE)

The system MUST NOT require loading all skills' full descriptions to make a selection.
Only lightweight metadata participates in the similarity search; the full skill
description MUST be loaded lazily, and only for the top-K selected skills. K MUST be
configurable with a small, sensible default. Any change that reintroduces bulk loading
of full skill bodies for selection is a violation and MUST be rejected.

Rationale: Avoiding context overload is the user-facing pain point being solved. If
full descriptions are loaded eagerly, the project delivers no value over the status quo.

### III. Shared Skill Pool Integrity

The skill pool MUST be a single shared source of truth that a whole team can read from
and contribute to. Every skill MUST have a stable identifier, a `name`, and a
`description`. Adding, updating, or removing a skill MUST keep the vector index
consistent with the pool — a skill present in the pool MUST be discoverable by search,
and a removed skill MUST NOT be returned. Skill records MUST be serializable and
portable so they can be shared rather than re-authored per user.

Rationale: A reusable team skill pool is an explicit goal; without index/pool
consistency, search results silently drift from reality and trust collapses.

### IV. vLLM as the Embedding Backbone

All embeddings (both for indexed skills and for incoming queries) MUST be produced
through vLLM, using the same embedding model and configuration on both sides so that
similarity scores are meaningful. The embedding model identifier and relevant runtime
settings MUST be recorded alongside the index. Changing the embedding model invalidates
existing vectors and MUST trigger a re-embedding of the pool, not a silent mismatch.

Rationale: This is a vLLM conference demo; vLLM is the centerpiece, and query/index
embeddings must come from one consistent source or cosine similarity is meaningless.

### V. Demo-Ready Simplicity & Observability

The project MUST remain runnable end-to-end as a demonstration with minimal setup.
Features MUST follow YAGNI: prefer the simplest design that proves the thesis. The
selection path MUST be observable — the system MUST be able to surface, for a given
query, the candidate skills and their similarity scores so the retrieval decision can
be inspected and explained to an audience.

Rationale: The deliverable is a conference demo. A clear, inspectable, low-friction
run is more valuable than breadth of features, and visible scores make the value
tangible to viewers.

## Technology & Architecture Constraints

- Language/runtime: Python `>=3.12,<3.13`, consistent with the existing workspace
  (`pyproject.toml`).
- Embedding engine: vLLM in pooling/embedding mode (see `test_embedding.py` for the
  reference embedding invocation pattern).
- Similarity: cosine similarity (or an equivalent, documented metric) over normalized
  vectors is the default for ranking candidates.
- Skill record shape: at minimum `id`, `name`, `description`; the full description MAY
  live separately from the searchable metadata to support lazy loading (Principle II).
- Portability: the skill pool and its index MUST be storable and shareable without
  requiring each consumer to recompute embeddings from scratch when the model is
  unchanged.

## Development Workflow & Quality Gates

- Every feature MUST trace back to one of the two stated pains: (a) reducing context
  load during skill selection, or (b) enabling a shared team skill pool. Features that
  serve neither MUST be justified explicitly or dropped.
- Changes affecting selection behavior MUST include a way to demonstrate retrieval
  quality (e.g., a query returns the expected skill within top-K with its score),
  consistent with Principle V observability.
- Any change touching the embedding model or index format MUST document the migration
  / re-embedding impact (Principle IV).
- Code review MUST verify the Context Efficiency principle (II) is not regressed:
  selection paths must not eagerly load full skill bodies for non-selected skills.

## Governance

This constitution supersedes other practices for the skill-picker project. When a
practice and this document conflict, this document wins until formally amended.

- Amendments MUST be made by editing this file, with a Sync Impact Report recorded at
  the top and a version bump per the policy below.
- Versioning policy (semantic):
  - MAJOR: backward-incompatible governance changes, or removal/redefinition of a
    principle.
  - MINOR: a new principle or section is added, or guidance is materially expanded.
  - PATCH: clarifications, wording, or non-semantic refinements.
- Compliance review: pull requests and reviews MUST verify adherence to the Core
  Principles, with particular attention to Principle II (Context Efficiency) and
  Principle III (Shared Skill Pool Integrity). Unjustified added complexity MUST be
  rejected per Principle V.

**Version**: 1.0.0 | **Ratified**: 2026-06-15 | **Last Amended**: 2026-06-15
