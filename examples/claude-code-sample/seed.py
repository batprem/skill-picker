#!/usr/bin/env python
"""Seed a skill-picker pool from the example SKILL.md files (Agent Skills format).

Demonstrates the field mapping skill-picker shares with the SKILL.md standard:

    frontmatter `description`  ->  skill-picker --description  (embedded; drives selection)
    markdown body              ->  skill-picker --body         (loaded only by show/load)

Run from this directory:  python seed.py
Override the binary with:  SKILL_PICKER=/path/to/skill-picker python seed.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = HERE / "data" / "skills.db"
SKILL_PICKER = os.environ.get("SKILL_PICKER", "skill-picker")


def parse_skill_md(text: str) -> tuple[dict[str, str], str]:
    """Split YAML frontmatter (simple key: value lines) from the markdown body."""
    if not text.startswith("---"):
        raise ValueError("SKILL.md must start with a '---' frontmatter block")
    _, frontmatter, body = text.split("---", 2)
    meta: dict[str, str] = {}
    for line in frontmatter.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip("'\"")
    return meta, body.strip()


def main() -> None:
    POOL.parent.mkdir(parents=True, exist_ok=True)
    skill_files = sorted((HERE / "skills").glob("*/SKILL.md"))
    if not skill_files:
        raise SystemExit("no skills/*/SKILL.md files found")

    for path in skill_files:
        meta, body = parse_skill_md(path.read_text())
        skill_id = path.parent.name
        result = subprocess.run(
            [
                SKILL_PICKER, "add", "--pool", str(POOL),
                "--id", skill_id,
                "--name", meta["name"],
                "--description", meta["description"],  # frontmatter -> embedded selection text
                "--body", body,                        # markdown body -> lazy-loaded full text
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"seeded  {skill_id}")
        elif "already exists" in (result.stdout + result.stderr).lower():
            print(f"skip    {skill_id} (already in pool)")
        else:
            print(f"FAILED  {skill_id}: {result.stderr.strip() or result.stdout.strip()}")

    print(f"\npool: {POOL}")


if __name__ == "__main__":
    main()
