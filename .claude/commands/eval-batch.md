Evaluate multiple Mathlib PRs against review conventions using LeanKeeper's RAG system.

The number of PRs to evaluate is: $ARGUMENTS (default: 5 if not specified).

## Step 1: Generate context files for all PRs

```bash
cd /home/administrateur/Bureau/Boulot/leankeeper/leankeeper && python -m leankeeper rag eval-context --limit $ARGUMENTS --output eval
```

This cleans the `eval/` directory and generates 3 files per PR (context, rag, actual).

## Step 2: Read the index

Read `eval/index.md` to see which PRs were generated.

## Step 3: Create results directory

```bash
mkdir -p results
```

## Step 4: For each PR, evaluate

For each PR number listed in `eval/index.md`:

1. Read `eval/pr_<number>_rag.md` (RAG context with reviewer examples)
2. Read `eval/pr_<number>_context.md` (PR diffs)
3. Review the PR against Mathlib conventions (naming, generality, API, style, docs)
4. Read `eval/pr_<number>_actual.md` (actual reviewer comments)
5. Compare your review with the actual feedback
6. Write results to `results/pr_<number>_result.md` with:
   - Your review
   - Comparison with actual feedback
   - Hits / misses / false positives

## Step 5: Write summary

After evaluating all PRs, write `results/summary.md` with:
- Total PRs evaluated
- Per-PR scores (hits, misses, false positives)
- Average category hit rate
- Most commonly missed category
- Most common false positive category
- Overall assessment of RAG quality
- Recommendations for improvement
