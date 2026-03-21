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

## Development

### Setup

```bash
pip install -r leankeeper/requirements.txt
```

Dependencies: `sqlalchemy>=2.0`, `requests>=2.31`.

### Configuration

Edit `leankeeper/config.py` to set API credentials before running extractors:
- `GITHUB_TOKEN` — GitHub personal access token with `repo:read`
- `ZULIP_EMAIL` / `ZULIP_API_KEY` — Zulip account credentials

Database defaults to SQLite at `leankeeper/data/leankeeper.db`. Set `DATABASE_URL` in config.py for PostgreSQL.

### CLI Commands

All commands run from the repo root via `python -m leankeeper`:

```bash
# Extraction
python -m leankeeper extract github         # PRs, reviews, comments (~3-5h)
python -m leankeeper extract git            # Commits and stats (~1h)
python -m leankeeper extract zulip          # Zulip messages (~2-4h)
python -m leankeeper extract all            # All above (excludes patches and PR files)

# Heavy extractions (optional)
python -m leankeeper extract github-files   # Files modified per PR (~10h, ~20K REST requests)
python -m leankeeper extract git-patches    # Full diffs (10-50 GB)
python -m leankeeper extract git-patches --since 2024-01-01

# Database inspection
python -m leankeeper stats

# Export a table to JSONL
python -m leankeeper export <table> <output_path>
# Tables: commits, commit_files, pull_requests, pr_files, reviews, review_comments, issue_comments, zulip_channels, zulip_messages
```

## Architecture

The project is currently in **Phase 1 (Dataset)** — building extractors to collect training data from Mathlib's public sources.

### Package structure (`leankeeper/`)

- **`__main__.py`** — CLI entry point with three subcommands: `extract`, `stats`, `export`
- **`config.py`** — All configuration: paths, API URLs/tokens, rate limits, extraction params
- **`models/database.py`** — SQLAlchemy ORM models and `init_db()`. Defines all tables including future Lean-specific ones (declarations, imports, typeclasses) not yet populated
- **`extractors/`** — One extractor class per data source, each taking a `session_factory` from `init_db()`:
  - **`github.py`** (`GitHubExtractor`) — GraphQL for PRs/reviews/issue comments in bulk, REST for inline review comments (with `diff_hunk`) and per-PR file patches. Handles rate limiting with automatic retry.
  - **`git.py`** (`GitExtractor`) — Clones mathlib4 as bare repo, extracts commits via `git log` parsing, stats via `--numstat`, optional full patches via `-p`. Uses subprocess.
  - **`zulip.py`** (`ZulipExtractor`) — Extracts channels and messages via Zulip REST API with backward pagination from newest.

### Data flow

All extractors follow the same pattern: `Extractor(session_factory)` → `extract_all()` → upsert into SQLite via SQLAlchemy sessions, committed in batches (`BATCH_SIZE=500`). Extractors are idempotent — they skip already-existing records.

### Training Data Sources

All public and extractible via GitHub and Zulip APIs:
- Mathlib Git repository (commits, diffs)
- GitHub PRs with review comments (~20K+ merged PRs)
- Lean Zulip discussions on design decisions
- Linter/CI results
- Import dependency graph

### Language

Codebase comments and logs are in French. CLI output and database schema use English identifiers.
