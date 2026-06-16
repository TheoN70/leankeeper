Turn a blind-review evaluation into concrete corrections for a Mathlib PR.

This skill consumes the review report produced by `/eval-pr` and proposes, for each flagged issue, a before/after correction justified by a `BASE_CONTEXT` rule. It is **diff-scoped and not compile-verified**: the eval pipeline only exposes truncated unified diff hunks (not full source files), and there is no local mathlib4 working tree to build against. The output is a review-ready proposal a human applies to the Lean source.

## Prerequisites

- `results/pr_$ARGUMENTS_result.md` must exist. If not, run `/eval-pr $ARGUMENTS` first.
- `eval/pr_$ARGUMENTS_context.md` must exist. If not, regenerate it:

```bash
cd /home/administrateur/Bureau/Boulot/leankeeper/leankeeper && python -m leankeeper rag eval-context --pr $ARGUMENTS --output eval
```

## Step 1: Read the blind review

Read `results/pr_$ARGUMENTS_result.md`. Collect every flagged issue under its category: **Naming**, **Generality**, **Style**, **API**, **Attributes**. Sections marked "No issues." have nothing to fix.

## Step 2: Read the PR diffs

Read `eval/pr_$ARGUMENTS_context.md`. This holds the per-file unified diff hunks the reviewer saw. Use it to locate the exact lines each issue refers to. Note: hunks are truncated to ~2000 chars/file — if an issue points at code not present in the hunk, you cannot see it.

## Step 3: Produce corrections

For each flagged issue, write a correction that maps to a specific `BASE_CONTEXT` rule:

- **Naming** → §2 (capitalization, symbol dictionary, name structure, predicates)
- **Generality** → §3 (weakest typeclass)
- **Style** → §5 (formatting, tactic mode, `by` placement, line length)
- **API** → §4 (companion lemmas, docstrings) and §12 (verify a lemma exists before naming it)
- **Attributes** → §4.3 (`@[simp]`, `@[ext]`, `@[to_additive]`, `@[simps]`, ...)

Rules:
- Quote the **original** snippet verbatim from the diff.
- Write the **corrected** snippet.
- Cite the violated `BASE_CONTEXT` section in one line.
- Correct only what is visible in the hunk. If a fix needs unseen code (full proof body, other declarations), state that explicitly instead of guessing a rewrite.

## Step 4: Write the fix report

Write `results/pr_$ARGUMENTS_fix.md`:

```markdown
# Fix Proposal: PR #$ARGUMENTS — <PR title>

> Diff-scoped, **not compile-verified** — only truncated diff hunks are available, and there is
> no local mathlib4 working tree to build against. Apply manually to the Lean source, then compile.

## Summary
<1-2 sentences: how many issues addressed, any that couldn't be fixed from the hunk>

## Naming
### Issue: <short description>
**Original**
```lean
<quoted original>
```
**Corrected**
```lean
<corrected code>
```
**Rule:** BASE_CONTEXT §2 — <which rule>

## Generality
<same block shape, or "No issues.">

## Style
<...>

## API
<...>

## Attributes
<...>

## Could not fix from the available hunk
<list issues whose fix needs code not present in the diff, or "None.">
```

Keep the 5 category headers even when empty, mirroring `result.md` for traceability.

## Done

`results/pr_$ARGUMENTS_fix.md` is a review-ready proposal — there is **no auto-apply and no compilation**. A human applies it to the Lean source and verifies it compiles (e.g. `exact?`/`lake build`, BASE_CONTEXT §12).
