---
name: Regex Builder
description: Construct and explain regular expressions for text matching and extraction.
---

# Regex Builder

Use this skill to design, explain, and harden regular expressions.

## Approach

1. **Pin down the spec**: collect 3–5 strings that MUST match and 3–5 that MUST NOT.
   They become your test cases.
2. **Build incrementally**: anchor the pattern (`^`, `$`, `\b`), then add character
   classes and quantifiers piece by piece, checking against the test set each step.
3. **Prefer specific over greedy**: use `[^"]*` instead of `.*` between delimiters, and
   lazy quantifiers (`*?`) when matching up to the next marker, to avoid overreach.
4. **Capture what you need**: use groups `(...)` for extraction and named groups
   `(?P<name>...)` for readable output; use non-capturing `(?:...)` for pure grouping.
5. **Explain it**: annotate each token so a reader can maintain it later.

## Cautions

- Avoid catastrophic backtracking from nested quantifiers like `(a+)+`; restructure or
  use possessive/atomic groups where supported.
- Watch flavor differences (PCRE vs RE2 vs JavaScript) for lookbehind and named groups.
