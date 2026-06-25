---
name: Git Bisect Helper
description: Guide a git bisect session to locate a regression commit.
---

# Git Bisect Helper

Use this skill to find the exact commit that introduced a regression.

## Steps

1. Confirm a reliable reproduction and a known-good past commit.
2. Start the session: `git bisect start`, then `git bisect bad` on the current
   broken commit and `git bisect good <known-good-sha>`.
3. At each step, build/run the reproduction and mark the checked-out commit
   `git bisect good` or `git bisect bad`. Git halves the range each time.
4. Automate when the check is scriptable: `git bisect run ./repro.sh` (exit 0 =
   good, non-zero = bad). This is fastest for flaky-free, deterministic repros.
5. When git reports "<sha> is the first bad commit", inspect it with
   `git show <sha>` to confirm the change that caused the regression.
6. Always end with `git bisect reset` to return to your original HEAD.

## Tips

- Keep the test cheap and deterministic; a slow or flaky check wastes log2(N) runs.
- If some commits don't build, mark them `git bisect skip` rather than guessing.
