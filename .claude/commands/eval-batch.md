Evaluate multiple Mathlib PRs against review conventions using LeanKeeper's RAG system.

The number of PRs to evaluate is: $ARGUMENTS (default: 5 if not specified).

## Step 1: Generate context files for all PRs

```bash
cd /home/administrateur/Bureau/Boulot/leankeeper/leankeeper && python -m leankeeper rag eval-context --limit $ARGUMENTS --output eval
```

This generates 3 files per PR in the `eval/` directory (context, rag, actual).

## Step 2: List generated PRs

```bash
ls eval/pr_*_context.md 2>/dev/null | sed 's/.*pr_\(.*\)_context.md/\1/'
```

## Step 3: For each PR, evaluate

For each PR number found:

1. Read `eval/pr_<number>_rag.md` (RAG context with reviewer examples)
2. Read `eval/pr_<number>_context.md` (PR diffs)
3. Review the PR against Mathlib conventions (naming, generality, API, style, docs)
4. Read `eval/pr_<number>_actual.md` (actual reviewer comments)
5. Compare your review with the actual feedback
6. Note: hits (same issue flagged), misses (issue you didn't catch), false positives (issue you flagged but reviewers didn't)

## Step 4: Summary

After evaluating all PRs, provide a summary:
- Total PRs evaluated
- Average category hit rate (what % of real reviewer issues did you also identify?)
- Most commonly missed category
- Most common false positive category
- Overall assessment of RAG quality
