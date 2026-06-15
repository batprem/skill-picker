"""T029 / SC-002: selection returns in under 1s for a pool of >= 100 skills.

Uses the offline HashingEmbedder; this isolates the selection pipeline (cache + cosine
scan) from model inference cost.
"""

from __future__ import annotations

import time

from skill_picker.models import SkillInput

WORDS = "alpha beta gamma delta epsilon zeta eta theta iota kappa".split()


def test_select_under_one_second_for_100_skills(service):
    for i in range(120):
        w = WORDS[i % len(WORDS)]
        service.pool.add(
            SkillInput(id=f"skill-{i:03d}", name=f"Skill {i}", full_description=f"{w} task number {i}")
        )

    # Warm the cache/index so we measure steady-state selection latency.
    service.select("warm up", k=5)

    start = time.perf_counter()
    result = service.select("alpha task", k=5)
    elapsed = time.perf_counter() - start

    assert result.candidates
    assert elapsed < 1.0, f"selection took {elapsed:.3f}s"
