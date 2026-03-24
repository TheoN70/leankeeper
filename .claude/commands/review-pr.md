Review a Mathlib PR from pre-generated context files (no comparison, no Excel).

**Prerequisite**: context files must already exist. Generate them with:
```bash
cd /home/administrateur/Bureau/Boulot/leankeeper/leankeeper && python -m leankeeper rag eval-context --pr $ARGUMENTS --output eval
```

## Step 1: Read the RAG context

Read the file `eval/pr_$ARGUMENTS_rag.md`. This contains:
- The BASE_CONTEXT with all Mathlib conventions
- The reviewer system prompt
- Similar review examples retrieved from 152K historical review comments (temporally filtered to before this PR was created)

## Step 2: Read the PR context

Read the file `eval/pr_$ARGUMENTS_context.md`. This contains the PR title, description, and file diffs — exactly what a real reviewer would see.

## Step 3: Review the PR

Based on the RAG context and the PR diffs, review this PR as a Mathlib reviewer would. For each issue found, classify it into one of these 5 categories:
- **Naming**: convention violations (wrong capitalization, wrong symbol name, wrong order)
- **Generality**: over-specialized hypotheses (using Field when Semiring suffices)
- **Style**: proof tactics, formatting, indentation, line length
- **API**: missing companion lemmas, missing docstrings on definitions
- **Attributes**: missing or wrong `@[simp]`, `@[ext]`, `@[to_additive]`, `@[simps]`

Be direct and specific. Only flag issues a real Mathlib reviewer would flag (see BASE_CONTEXT section 9).

## Step 4: Write the review

Write the structured review to `results/pr_$ARGUMENTS_review.md` with the following format:

```markdown
# Review: PR #$ARGUMENTS — <PR title>

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
```

For each issue, quote the relevant code and explain what should change and why, referencing the specific convention from BASE_CONTEXT.
