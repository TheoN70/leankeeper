# LeanKeeper — RAG Evaluation System

## Purpose

The evaluation system tests whether the RAG reviewer produces feedback that matches what real Mathlib reviewers said on historical PRs. This is an objective, automated test that answers: "does the RAG identify the same issues as human reviewers?"

## How it works

### Overview

```
Database (historical PRs)
        │
        ▼
1. Select merged PRs that had CHANGES_REQUESTED
        │
        ▼
2. For each PR, build context (title + body + diffs)
        │
        ▼
3. Run RAG reviewer (with temporal cutoff)
        │
        ▼
4. Compare RAG feedback vs actual reviewer comments
        │
        ▼
5. Display report
```

### Step 1 — PR Selection (`select_test_prs`)

**File:** `leankeeper/rag/eval.py`, line 29

The evaluator queries the database for PRs that meet all of these criteria:
- State is `merged` (the PR was accepted)
- Has at least one review with `state = 'CHANGES_REQUESTED'` (the reviewer found problems)
- Has review comments (inline feedback to compare against)
- Has PR files extracted (full diffs available via `extract github-files`)

SQL query:
```sql
SELECT DISTINCT r.pr_number
FROM reviews r
JOIN pull_requests pr ON pr.number = r.pr_number
WHERE r.state = 'CHANGES_REQUESTED'
AND pr.state = 'merged'
AND EXISTS (SELECT 1 FROM review_comments rc WHERE rc.pr_number = r.pr_number)
AND EXISTS (SELECT 1 FROM pull_request_files pf WHERE pf.pr_number = r.pr_number)
```

From the eligible PRs, a random sample of N is selected (default: 30, configurable with `--limit`).

**Why these PRs?** They are the most informative for testing. The reviewer identified concrete issues, documented them in comments, the author fixed them, and the PR was merged. We have both the "problem" (the code) and the "answer" (the reviewer's feedback).

### Step 2 — Context Building (`build_pr_context`)

**File:** `leankeeper/rag/eval.py`, line 56

For each selected PR, builds the text that the RAG will see — simulating what a reviewer would see when opening the PR:

1. **PR title** — e.g. `"PR #12345: Generalize foo to CommMonoid"`
2. **PR description (body)** — the author's explanation, truncated to 1000 characters
3. **File diffs** — for each file in `pull_request_files`:
   - File path and status (added/modified/removed)
   - The patch (diff), truncated to 2000 characters per file

The total context is truncated to 8000 characters if too long for the LLM.

**What is excluded:** the actual review comments. These are the ground truth we compare against — including them would be cheating.

### Step 3 — Ground Truth Collection (`get_actual_feedback`)

**File:** `leankeeper/rag/eval.py`, line 79

Reads all `review_comments` for the PR from the database, ordered by creation date. Each comment includes:
- `author` — who wrote it (e.g. `YaelDillies`, `sgouezel`)
- `filepath` — which file was commented on
- `body` — the comment text
- `line` — which line number

Filters out:
- Bot comments (`github-actions[bot]`)
- Very short comments (< 20 characters, e.g. "LGTM", "thanks")

### Step 4 — RAG Review (`run_eval`)

**File:** `leankeeper/rag/eval.py`, line 101

Calls the RAG pipeline (`retriever.ask()`) with:

- **Query:** `"Review this Mathlib PR:\n\n{context}"` — the PR context from step 2
- **Mode:** `reviewer` — searches `review_comments` and `reviews` tables
- **Limit:** 10 similar examples retrieved
- **Temporal cutoff (`before_date`):** the PR's `created_at` date

#### Temporal data leakage prevention

The `before_date` parameter ensures the RAG only uses embeddings with `created_at` before the PR was submitted. This simulates what the system would have known at the time — no data from the future can leak in.

This prevents two types of leakage:
1. **Direct leakage:** the PR's own review comments appearing in search results
2. **Indirect leakage:** later PRs or Zulip discussions that reference or were influenced by this PR

#### What happens inside `ask()`

1. The query is embedded using `all-MiniLM-L6-v2` (local, CPU)
2. pgvector searches the `embeddings` table for the 10 most similar vectors where `created_at < pr_date` and `source_table IN ('review_comments', 'reviews')`
3. Results are formatted as context examples
4. The reviewer system prompt is built with these examples
5. The LLM (Claude by default) generates review feedback

### Step 5 — Report (`report`)

**File:** `leankeeper/rag/eval.py`, line 151

For each PR, displays side by side:

```
══════════════════════════════════════════════════════════════
  PR #12345: Generalize foo to CommMonoid
══════════════════════════════════════════════════════════════

── Actual reviewer feedback (3 comments) ──
  eric-wieser on Mathlib/Algebra/Foo.lean:
    should be foo_comm not comm_foo

  sgouezel on Mathlib/Algebra/Foo.lean:
    this only needs Semiring

  YaelDillies on Mathlib/Algebra/Foo.lean:
    use simp instead of rw chain

── RAG reviewer feedback ──
  The naming should follow dot-notation: Foo.comm...
  Consider weakening CommMonoid — the proof doesn't use...
```

Then a summary:
```
══════════════════════════════════════════════════════════════
  Evaluation Summary
══════════════════════════════════════════════════════════════
  Evaluated: 28 PRs
  Skipped: 2 PRs
  Avg actual comments per PR: 4.2
```

### Step 6 — Export (optional)

**File:** `leankeeper/rag/eval.py`, line 186

With `--export results.jsonl`, saves all results as JSON Lines. Each line contains:
```json
{
  "pr_number": 12345,
  "title": "PR #12345: Generalize foo to CommMonoid",
  "actual_comments": [
    {"author": "eric-wieser", "filepath": "Mathlib/Algebra/Foo.lean", "body": "...", "line": 42}
  ],
  "actual_count": 3,
  "rag_feedback": "The naming should follow..."
}
```

This allows offline analysis, comparison across different RAG configurations, and tracking improvement over time.

## Usage

### Option A: LLM API evaluation

Runs the full pipeline automatically — generates context, calls an LLM for review, compares.

```bash
python -m leankeeper rag eval --limit 5                # 5 PRs with Claude API (~$0.15)
python -m leankeeper rag eval --pr 12345               # Specific PR
python -m leankeeper rag eval --backend ollama          # Free with local model
python -m leankeeper rag eval --export results.jsonl    # Save results
```

### Option B: Claude Code evaluation (recommended, free)

Instead of calling an external LLM, use Claude Code itself. This is free (subscription) and produces better results because Claude Code has full project context.

**Step 1 — Generate context files (no LLM):**

```bash
python -m leankeeper rag eval-context --pr 12345       # Single PR
python -m leankeeper rag eval-context --limit 5        # 5 random PRs
python -m leankeeper rag eval-context --output eval/   # Custom output dir
```

This creates three files per PR in `eval/`:

| File | Content | Purpose |
|------|---------|---------|
| `pr_<N>_context.md` | PR title + body + file diffs | What a reviewer sees |
| `pr_<N>_rag.md` | System prompt + 10 similar review examples | RAG context (temporally filtered) |
| `pr_<N>_actual.md` | Actual reviewer comments | Ground truth for comparison |

**Step 2 — Use Claude Code skills:**

```
/eval-pr 12345     # Evaluate a single PR
/eval-batch 5      # Evaluate 5 PRs with summary
```

These skills automatically:
1. Run `eval-context` to generate the files
2. Read the RAG context (reviewer examples from similar past PRs)
3. Read the PR diffs (what the reviewer would see)
4. Review the PR against Mathlib conventions
5. Read the actual reviewer comments (ground truth)
6. Compare: hits (same issue), misses (issue not caught), false positives (issue not real)

**Design principle — separation of concerns:**

```
eval-context (Python, local)          Claude Code (LLM, free)
├── Read PRs from PostgreSQL          ├── Read generated .md files
├── Search pgvector embeddings        ├── Apply Mathlib conventions
├── Format as markdown files          ├── Produce review
└── No LLM call needed                └── Compare with actual feedback
```

The data pipeline (Python) is deterministic and reproducible. The reasoning (Claude Code) is flexible and uses the full project context including CLAUDE.md with all Mathlib contribution guidelines.

## Prerequisites

1. **PR files must be extracted:**
   ```bash
   python -m leankeeper extract github-files  # ~15h
   ```

2. **Embeddings must be indexed with dates:**
   ```bash
   python -m leankeeper rag init              # Ensures created_at column exists
   python -m leankeeper rag backfill-dates    # For existing embeddings
   ```

3. **For Option A only — LLM backend configured:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."      # For Claude API
   # or
   export LLM_BACKEND=ollama                  # For local model
   ```
   Option B (Claude Code) needs no additional configuration.

## Metrics and Excel template

### `results/results.xlsx`

A structured Excel spreadsheet for recording evaluation results. Generated by `python gen_results_template.py`.

**Sheet "Raw Data"** — filled by the agent (one row per PR):

| Columns | Content |
|---------|---------|
| A: PR # | PR number |
| B: Title | PR title |
| C-G: Actual | Did the real reviewer flag this category? (1/0) |
| H-L: RAG | Did the RAG flag this category? (1/0) |

Categories: **Naming**, **Generality**, **Style**, **API**, **Attributes**

**Sheet "Summary"** — auto-computed via formulas:

| Metric | Formula | Meaning |
|--------|---------|---------|
| TP (True Positive) | Both Actual=1 and RAG=1 | Correctly flagged |
| FP (False Positive) | Actual=0 but RAG=1 | Incorrectly flagged |
| FN (False Negative) | Actual=1 but RAG=0 | Missed by RAG |
| **Precision** | TP / (TP + FP) | Of what RAG flags, how much is correct |
| **Recall** | TP / (TP + FN) | Of what reviewers flag, how much RAG catches |
| **F1-Score** | 2×P×R / (P+R) | Harmonic mean of Precision and Recall |

Metrics are computed per category and overall. The agent fills the raw data, the spreadsheet does the math.

### Evaluation workflow

1. Run `/eval-batch 30` (or `/eval-pr <number>` for a single PR)
2. The agent reviews each PR, compares with actual feedback, and fills `results/results.xlsx`
3. The agent writes per-PR reports to `results/pr_<N>_result.md`
4. The agent reads the Summary sheet and writes `results/summary.md`
5. Open `results/results.xlsx` in a spreadsheet app to verify the computed metrics

## How to interpret results

**Good signs:**
- RAG identifies the same *type* of issue as the reviewer (e.g. both flag naming)
- RAG suggests the right *direction* even if the specific fix differs
- RAG provides relevant examples from similar past PRs

**Bad signs:**
- RAG flags issues the reviewer didn't mention (false positives)
- RAG misses issues the reviewer flagged (false negatives)
- RAG gives generic advice not grounded in the specific PR code

**Expected failure modes:**
- **Proof strategy:** the RAG cannot evaluate mathematical proof approaches
- **Deep typeclass reasoning:** knowing which typeclass is "weakest sufficient" requires understanding the proof, not just patterns
- **Novel code:** PRs introducing entirely new concepts may not have similar past reviews

## Iterating on results

After running the evaluation, use the results to improve the RAG:

| Observation | Action |
|-------------|--------|
| RAG misses naming issues | Add more naming-focused examples to embeddings |
| RAG flags wrong generality level | Improve typeclass-related Zulip discussion indexing |
| RAG gives generic advice | Improve text builders to include more code context |
| Low relevance from Zulip results | Filter short/uninformative Zulip messages |
| RAG parrot similar but irrelevant PRs | Tune embedding model or increase retrieval limit |

## Architecture

```
leankeeper/rag/eval.py
├── RAGEvaluator
│   ├── select_test_prs()          → SQL query on reviews + pull_requests + pull_request_files
│   ├── build_pr_context()         → Reads PullRequest + PullRequestFile from DB
│   ├── get_actual_feedback()      → Reads ReviewComment from DB (ground truth)
│   ├── generate_context_files()   → Writes 3 .md files per PR (no LLM call)
│   ├── run_eval()                 → Calls retriever.ask() with before_date (Option A)
│   ├── run_batch()                → Loops run_eval() over multiple PRs
│   ├── report()                   → Prints side-by-side comparison
│   └── export()                   → Writes JSONL file
│
│   Depends on:
│   ├── leankeeper/rag/retriever.py  → ask() with before_date parameter
│   ├── leankeeper/rag/store.py      → search() with temporal filtering
│   ├── leankeeper/rag/prompt.py     → SYSTEM_REVIEWER prompt template
│   └── leankeeper/rag/llm.py       → LLM backend (Option A only)

.claude/commands/
├── eval-pr.md      → Claude Code skill: evaluate a single PR
└── eval-batch.md   → Claude Code skill: evaluate multiple PRs

eval/                → Generated context files (gitignored)
├── pr_<N>_context.md  → PR diffs
├── pr_<N>_rag.md      → RAG system prompt + examples
└── pr_<N>_actual.md   → Actual reviewer comments
```
