Evaluate multiple Mathlib PRs against review conventions using LeanKeeper's RAG system.

The number of PRs to evaluate is: $ARGUMENTS (default: 5 if not specified).

## Step 1: Generate context files for all PRs

```bash
cd /home/administrateur/Bureau/Boulot/leankeeper/leankeeper && python -m leankeeper rag eval-context --limit $ARGUMENTS --output eval
```

This cleans the `eval/` directory and generates 3 files per PR (context, rag, actual).

## Step 2: Read the index

Read `eval/index.md` to see which PRs were generated.

## Step 3: Reset the Excel spreadsheet

Ensure `results/results.xlsx` exists (if not, run `python gen_results_template.py`). Clear any previous data rows in the "Raw Data" sheet (keep headers).

## Step 4: For each PR, evaluate

For each PR number listed in `eval/index.md`:

1. Read `eval/pr_<number>_rag.md` (BASE_CONTEXT + RAG context with reviewer examples)
2. Read `eval/pr_<number>_context.md` (PR diffs)
3. Review the PR against Mathlib conventions. For each issue, classify into: **Naming**, **Generality**, **Style**, **API**, **Attributes**
4. Read `eval/pr_<number>_actual.md` (actual reviewer comments)
5. For each of the 5 categories, determine:
   - **Actual**: did the real reviewer flag this category? (1=yes, 0=no)
   - **RAG**: did you flag this category? (1=yes, 0=no)
6. Write results to `results/pr_<number>_result.md`
7. Add a row to `results/results.xlsx` "Raw Data" sheet:
   - Column A: PR number
   - Column B: PR title
   - Columns C-G: Actual (Naming, Generality, Style, API, Attributes) — 1 or 0
   - Columns H-L: RAG (Naming, Generality, Style, API, Attributes) — 1 or 0

## Step 5: Write summary

After evaluating all PRs:

1. Read the "Summary" sheet of `results/results.xlsx` — it auto-computes Precision, Recall, and F1-Score per category and overall
2. Write `results/summary.md` with:
   - Total PRs evaluated
   - Per-category Precision / Recall / F1 (from the Excel)
   - Overall Precision / Recall / F1
   - Most commonly missed category
   - Most common false positive category
   - Recommendations for improvement
