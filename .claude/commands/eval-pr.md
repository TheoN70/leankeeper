Evaluate a Mathlib PR against review conventions using LeanKeeper's RAG system.

This skill performs a **blind review** — you do NOT read the actual reviewer comments. Classification happens without seeing ground truth.

## Step 1: Generate context files

Run this command to generate the evaluation context files for PR $ARGUMENTS:

```bash
cd /home/administrateur/Bureau/Boulot/leankeeper/leankeeper && python -m leankeeper rag eval-context --pr $ARGUMENTS --output eval
```

## Step 2: Read the convention context

Read the file `eval/pr_$ARGUMENTS_rag.md`. This contains:
- The BASE_CONTEXT with all Mathlib conventions
- The reviewer system prompt

(No vector retrieval: the review is grounded in the BASE_CONTEXT conventions, not in retrieved examples.)

## Step 3: Read the PR context

Read the file `eval/pr_$ARGUMENTS_context.md`. This contains the PR title, description, and file diffs — exactly what a real reviewer would see.

## Step 4: Review the PR (blind)

Based on the RAG context and the PR diffs, review this PR as a Mathlib reviewer would. For each issue found, classify it into one of these 5 categories:
- **Naming**: convention violations (wrong capitalization, wrong symbol name, wrong order)
- **Generality**: over-specialized hypotheses (using Field when Semiring suffices)
- **Style**: proof tactics, formatting, indentation, line length
- **API**: missing companion lemmas, missing docstrings on definitions
- **Attributes**: missing or wrong `@[simp]`, `@[ext]`, `@[to_additive]`, `@[simps]`

Be direct and specific. Only flag issues a real Mathlib reviewer would flag (see BASE_CONTEXT section 9).

**IMPORTANT: Do NOT read `eval/pr_$ARGUMENTS_actual.md`. This review must be blind.**

## Step 5: Auto-classify and write results

For each of the 5 categories, determine whether you flagged it (1=yes, 0=no).

Write a structured evaluation report to `results/pr_$ARGUMENTS_result.md` with:

```markdown
# Blind Review: PR #$ARGUMENTS — <PR title>

## Summary
<1-2 sentence overall assessment>

## Naming
<issues found, or "No issues.">

## Generality
<issues found, or "No issues.">

## Style
<issues found, or "No issues.">

## API
<issues found, or "No issues.">

## Attributes
<issues found, or "No issues.">

## Auto-Classification (RAG)

| Category | RAG |
|----------|-----|
| Naming | <0 or 1> |
| Generality | <0 or 1> |
| Style | <0 or 1> |
| API | <0 or 1> |
| Attributes | <0 or 1> |
```

For each issue, quote the relevant code and explain what should change and why, referencing the specific convention from BASE_CONTEXT.

After writing the result file, run `/compare-pr $ARGUMENTS` to compare with actual reviewer feedback and fill the Excel spreadsheet.
