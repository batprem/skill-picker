# Feature Specification: Skill Picker

**Feature Branch**: `001-skill-picker`
**Created**: 2026-06-15
**Status**: Draft
**Input**: User description: "skill-picker: A skill-selection service for coding agents (like Claude Code). It stores each agent skill's name and description, embeds them into vectors using vLLM, and at query time embeds the incoming task and retrieves the most relevant skills by vector similarity, then loads only the full descriptions of the top-K selected skills. Pain points: agents currently must load every skill's name and description to pick a skill, which overloads the context window; and teams want a shared skill pool reusable from one source of truth."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retrieve relevant skills for a task without loading everything (Priority: P1)

A coding agent receives a task and needs to decide which skill(s) to use. Instead of
pulling every skill's name and description into its context, the agent sends the task
description to the skill picker and receives a short, ranked list of the most relevant
skills, each with a similarity score. The agent then requests the full description only
for the skill(s) it decides to use.

**Why this priority**: This is the core value of the product — efficient, relevance-based
skill selection that avoids context overload. Without it, nothing else matters.

**Independent Test**: Populate the pool with a known set of skills, submit a task query
whose intent clearly matches one skill, and confirm that skill appears at or near the top
of the returned ranked list with a similarity score, while non-matching skills rank lower
or are excluded. No full descriptions are returned in this step.

**Acceptance Scenarios**:

1. **Given** a populated skill pool and a task query, **When** the agent requests skill
   selection, **Then** the system returns a ranked list of at most K candidate skills,
   each with an identifier, name, and similarity score, ordered by descending relevance.
2. **Given** a returned candidate list, **When** the agent requests the full description
   for a selected skill identifier, **Then** the system returns that skill's full
   description and only that skill's full description.
3. **Given** a task query with no sufficiently relevant skill, **When** selection runs,
   **Then** the system returns an empty (or below-threshold) result rather than forcing
   an irrelevant match.

---

### User Story 2 - Maintain a shared team skill pool (Priority: P2)

A team member adds, updates, or removes a skill in a single shared pool so that everyone
on the team selects from the same, current set of skills. When a skill is added or
changed, it becomes discoverable through selection; when removed, it stops appearing in
results.

**Why this priority**: The shared, consistent pool is the second stated pain point and
makes the picker useful beyond a single user, but selection (P1) must exist first.

**Independent Test**: Add a new skill to the pool, run a query matching it, and confirm
it is returned; then remove it and confirm the same query no longer returns it.

**Acceptance Scenarios**:

1. **Given** the shared pool, **When** a member adds a skill with a name and description,
   **Then** the skill becomes selectable by relevant queries without any other member
   re-importing or re-processing it manually.
2. **Given** an existing skill, **When** a member updates its name or description,
   **Then** subsequent selections reflect the updated content.
3. **Given** an existing skill, **When** a member removes it, **Then** it no longer
   appears in any selection results.
4. **Given** two team members querying the same pool, **When** both submit the same
   query, **Then** they receive consistent selection results from the same source.

---

### User Story 3 - Inspect and explain a selection decision (Priority: P3)

A presenter or developer submits a query and views the candidate skills together with
their similarity scores, so the retrieval decision can be understood, demonstrated, and
trusted — for example, on stage at a conference demo.

**Why this priority**: Observability makes the value tangible and supports the demo goal,
but it is an enhancement on top of working selection.

**Independent Test**: Submit a query and confirm the response surfaces, for each
candidate, the score that ranked it, in a form a human can read and compare.

**Acceptance Scenarios**:

1. **Given** a query, **When** selection runs, **Then** the response exposes each
   candidate's similarity score alongside its name so the ranking can be inspected.
2. **Given** two queries, **When** compared, **Then** the difference in which skills are
   selected is explainable by the reported scores.

---

### Edge Cases

- **Empty pool**: A query against a pool with no skills returns an empty result with a
  clear "no skills available" indication, not an error.
- **Duplicate or near-identical skills**: Two skills with very similar descriptions are
  both eligible; ranking still returns a deterministic order for the same inputs.
- **Very long skill description**: Long descriptions are handled without failing; only
  the metadata used for matching participates in ranking.
- **Query matching nothing well**: When no candidate exceeds the relevance threshold, the
  system returns nothing above threshold rather than a forced low-confidence pick.
- **Stale results after change**: After a skill is added/updated/removed, subsequent
  queries must reflect the change rather than returning outdated results.
- **Ties in similarity score**: When candidates have equal scores, ordering is stable and
  reproducible for identical inputs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store skills, each having a stable unique identifier, a name,
  and a description.
- **FR-002**: System MUST distinguish lightweight matching metadata (name and a short
  description used for relevance) from the full skill description used after selection.
- **FR-003**: System MUST accept a free-text task query and return a ranked list of the
  most relevant skills, limited to a configurable maximum count K with a small sensible
  default.
- **FR-004**: System MUST include a relevance/similarity score with each returned
  candidate and order candidates by descending relevance.
- **FR-005**: System MUST allow retrieving the full description of a selected skill by its
  identifier, returning only that skill's full content.
- **FR-006**: System MUST NOT require the requester to load all skills' full descriptions
  in order to perform a selection.
- **FR-007**: System MUST support adding a new skill to the shared pool such that it
  becomes selectable by relevant queries without manual per-user reprocessing.
- **FR-008**: System MUST support updating an existing skill's name or description, with
  subsequent selections reflecting the change.
- **FR-009**: System MUST support removing a skill, after which it no longer appears in
  selection results.
- **FR-010**: System MUST serve a single shared pool so that multiple team members
  selecting against it receive results from the same source of truth.
- **FR-011**: System MUST keep selection results consistent with the current pool —
  present skills are discoverable and removed skills are not returned.
- **FR-012**: System MUST support a configurable relevance threshold below which
  candidates are excluded, and MUST return an empty result when nothing qualifies.
- **FR-013**: System MUST behave deterministically for identical inputs (same pool, same
  query, same configuration produce the same ranked result).
- **FR-014**: System MUST allow skills and their stored representation to be exported and
  shared so the pool can be reused rather than re-authored per user.

### Key Entities *(include if feature involves data)*

- **Skill**: A reusable agent capability. Key attributes: unique identifier, name, short
  matching description (used for relevance), full description (loaded only after
  selection). Belongs to the shared pool.
- **Skill Pool**: The shared collection of all skills serving as the single source of
  truth for a team. Supports add, update, remove, and query operations.
- **Selection Query**: An incoming task description submitted to find relevant skills.
- **Selection Result**: An ordered set of candidate skills (each with identifier, name,
  and similarity score), bounded by K and by the relevance threshold.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a labeled set of test queries, the intended skill appears within the
  top-K results at least 90% of the time.
- **SC-002**: A selection request returns its ranked candidate list in under 1 second for
  a pool of at least 100 skills.
- **SC-003**: Performing a selection transfers only candidate metadata plus, at most, the
  full descriptions of the K selected skills — never the full descriptions of the entire
  pool — reducing the content needed to choose a skill by at least 80% compared to loading
  every skill's full description.
- **SC-004**: After a skill is added, updated, or removed, the change is reflected in
  selection results within one selection cycle (the next query).
- **SC-005**: Two team members issuing the same query against the shared pool receive
  identical ranked results.
- **SC-006**: A viewer can read each returned candidate's similarity score and correctly
  explain why one skill ranked above another in at least 90% of demo queries.

## Assumptions

- Skill content (name and description) is authored by team members and is trusted; the
  feature does not perform content moderation or access control beyond serving the shared
  pool.
- A "short matching description" is available or derivable for each skill; where only a
  full description exists, the matching text may be derived from it.
- The pool size for the demo and near-term use is on the order of tens to a few hundred
  skills, not millions.
- Relevance is judged by semantic similarity between the task query and skill matching
  metadata; exact keyword match is not required.
- Consumers (coding agents) can make a second request to fetch a full description after
  seeing the ranked candidates (a two-step select-then-load interaction is acceptable).
- A consistent embedding approach is used for both stored skills and incoming queries so
  that scores are comparable (the specific model/engine is an implementation concern
  governed by the project constitution).
