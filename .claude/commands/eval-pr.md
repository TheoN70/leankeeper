Evaluate a Mathlib PR against review conventions using LeanKeeper's RAG system.

## Step 1: Generate context files

Run this command to generate the evaluation context files for PR $ARGUMENTS:

```bash
cd /home/administrateur/Bureau/Boulot/leankeeper/leankeeper && python -m leankeeper rag eval-context --pr $ARGUMENTS --output eval
```

## Step 2: Read the RAG context

Read the file `eval/pr_$ARGUMENTS_rag.md`. This contains:
- The BASE_CONTEXT with all Mathlib conventions
- The reviewer system prompt
- Similar review examples retrieved from 152K historical review comments (temporally filtered to before this PR was created)

## Step 3: Read the PR context

Read the file `eval/pr_$ARGUMENTS_context.md`. This contains the PR title, description, and file diffs — exactly what a real reviewer would see.

## Step 4: Review the PR

Based on the RAG context and the PR diffs, review this PR as a Mathlib reviewer would. For each issue found, classify it into one of these 5 categories:
- **Naming**: convention violations (wrong capitalization, wrong symbol name, wrong order)
- **Generality**: over-specialized hypotheses (using Field when Semiring suffices)
- **Style**: proof tactics, formatting, indentation, line length
- **API**: missing companion lemmas, missing docstrings on definitions
- **Attributes**: missing or wrong `@[simp]`, `@[ext]`, `@[to_additive]`, `@[simps]`

Be direct and specific. Only flag issues a real Mathlib reviewer would flag (see BASE_CONTEXT section 9).

## Step 5: Compare with actual reviewers

Read the file `eval/pr_$ARGUMENTS_actual.md`. This contains what the real Mathlib reviewers actually said.

For each of the 5 categories, determine:
- **Actual**: did the real reviewer flag this category? (1=yes, 0=no)
- **RAG**: did you flag this category? (1=yes, 0=no)

## Step 6: Write results

Write a structured evaluation report to `results/pr_$ARGUMENTS_result.md` with:
- Your review
- The comparison with actual feedback
- Per-category classification (Actual vs RAG for each of: Naming, Generality, Style, API, Attributes)

## Step 7: Fill the Excel spreadsheet

Open `results/results.xlsx` and add a row in the "Raw Data" sheet for this PR:
- Column A: PR number ($ARGUMENTS)
- Column B: PR title
- Columns C-G (Actual): for each category (Naming, Generality, Style, API, Attributes), put 1 if the real reviewer flagged it, 0 if not
- Columns H-L (RAG): for each category, put 1 if you flagged it, 0 if not

The "Summary" sheet computes Precision, Recall, and F1-Score automatically from this data.
