Evaluate a Mathlib PR against review conventions using LeanKeeper's RAG system.

## Step 1: Generate context files

Run this command to generate the evaluation context files for PR $ARGUMENTS:

```bash
cd /home/administrateur/Bureau/Boulot/leankeeper/leankeeper && python -m leankeeper rag eval-context --pr $ARGUMENTS --output eval
```

## Step 2: Read the RAG context

Read the file `eval/pr_$ARGUMENTS_rag.md`. This contains:
- The reviewer system prompt with Mathlib conventions
- Similar review examples retrieved from 152K historical review comments (temporally filtered to before this PR was created)

## Step 3: Read the PR context

Read the file `eval/pr_$ARGUMENTS_context.md`. This contains the PR title, description, and file diffs — exactly what a real reviewer would see.

## Step 4: Review the PR

Based on the RAG context and the PR diffs, review this PR as a Mathlib reviewer would. Check for:
- **Naming convention** violations (see the examples in the RAG context)
- **Generality** issues (hypotheses that could be weakened)
- **Missing API** lemmas (ext, ext_iff, map, etc.)
- **Style** issues (proof tactics, formatting)
- **Documentation** (docstrings, module docs)

Provide specific, actionable feedback with code suggestions where possible.

## Step 5: Compare with actual reviewers

Read the file `eval/pr_$ARGUMENTS_actual.md`. This contains what the real Mathlib reviewers actually said.

Compare your review with the actual feedback:
- Which issues did you catch that the reviewers also caught? (hits)
- Which issues did you miss? (misses)
- Which issues did you flag that the reviewers didn't mention? (false positives)

## Step 6: Write results

Write a structured evaluation report to `results/pr_$ARGUMENTS_result.md` with:
- Your review
- The comparison with actual feedback
- A score summary (hits / misses / false positives)
