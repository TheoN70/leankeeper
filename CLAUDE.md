# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LeanKeeper is an AI agent specialized for Mathlib (Lean 4's community math library). The goal is to produce contributions that pass human review — not just proofs that compile, but code that respects Mathlib's conventions, typeclass hierarchy, naming, API patterns, and design standards.

The core metric is: **"does it pass Mathlib review?"**, not "does it compile?".

## Key Concepts

- **Lean 4**: proof assistant where compilation = correctness
- **Mathlib**: ~2M lines, ~210K theorems, organized as a DAG with a typeclass hierarchy (`Monoid → Group → Ring → Field`, etc.)
- **The problem**: AI companies dump massive compilable code that doesn't meet Mathlib quality standards (wrong generality level, missing API lemmas, broken naming conventions), poisoning the design space
- **LeanKeeper's role**: act as a "good junior Mathlib contributor" — explore the typeclass hierarchy, propose well-integrated definitions with standard API, follow naming conventions, and submit clean ~200-line PRs

## Training Data Sources

All public and extractible via GitHub and Zulip APIs:
- Mathlib Git repository (commits, diffs)
- GitHub PRs with review comments (~20K+ merged PRs)
- Lean Zulip discussions on design decisions
- Linter/CI results
- Import dependency graph
