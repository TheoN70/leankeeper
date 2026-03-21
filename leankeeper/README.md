# LeanKeeper — Mathlib Dataset

Extraction and structuring of public data from the [Mathlib](https://github.com/leanprover-community/mathlib4) project for training an AI agent specialized in Mathlib conventions.

## Quickstart

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create the PostgreSQL database

```bash
createdb leankeeper
```

### 3. Set environment variables

```bash
export DATABASE_URL="postgresql://user:pass@localhost/leankeeper"
export GITHUB_READ_ONLY_TOKEN="ghp_..."        # GitHub token (Settings > Developer settings > Personal access tokens)
export ZULIP_EMAIL="you@email.com"             # Lean Zulip account (https://leanprover.zulipchat.com)
export ZULIP_API_KEY="..."                     # API key (Settings > Your bots)
```

### 4. Initialize the database and run your first extraction

```bash
# Tables are auto-created on first run. Verify with:
python -m leankeeper stats

# Start extracting (GitHub is the most useful source):
python -m leankeeper extract github
```

The GitHub extraction takes ~1h10 and populates PRs, reviews, and issue comments. Extractors are idempotent — you can interrupt and re-run safely.

## Usage

```bash
# GitHub extraction (PRs, reviews, comments) — ~1h10
python -m leankeeper extract github

# Review comments only
python -m leankeeper extract github-reviews

# Git extraction (commits, stats) — ~1h
python -m leankeeper extract git

# Zulip extraction (messages) — ~2-4h
python -m leankeeper extract zulip

# All at once (except patches and PR files)
python -m leankeeper extract all

# Database stats
python -m leankeeper stats

# Export a table to JSONL
python -m leankeeper export review_comments data/review_comments.jsonl
```

### Optional extractions (heavy)

```bash
# Files modified per PR with patches (~20K REST requests, ~10h)
python -m leankeeper extract github-files

# Full Git diffs (10-50 GB)
python -m leankeeper extract git-patches

# Git diffs since a date
python -m leankeeper extract git-patches --since 2024-01-01
```

## Database schema

See [`DB_ARCHITECTURE.md`](../DB_ARCHITECTURE.md) for full documentation.

### Git sources
- **commits** — SHA, author, date, message, insertions/deletions
- **commit_files** — files modified per commit, with optional patch

### GitHub sources
- **pull_requests** — title, description, author, state, dates, branches
- **pull_request_labels** — labels per PR
- **pull_request_files** — files modified per PR with patches
- **reviews** — top-level reviews (approved/changes_requested/commented)
- **review_comments** — inline code comments *(most valuable)*
- **issue_comments** — general PR conversation comments

### Zulip sources
- **zulip_channels** — extracted channels (streams)
- **zulip_messages** — messages with channel, topic, sender, markdown content

### Lean sources *(planned)*
- **declarations** — theorems, definitions, instances, classes
- **imports** — file dependency graph
- **typeclass_instances** — typeclass instances
- **typeclass_parents** — typeclass hierarchy

## Project structure

```
leankeeper/
├── __init__.py
├── __main__.py          # CLI
├── config.py            # Configuration
├── requirements.txt
├── models/
│   ├── __init__.py
│   └── database.py      # SQLAlchemy models
├── extractors/
│   ├── __init__.py
│   ├── github.py        # GitHub extractor (GraphQL + REST)
│   ├── git.py           # Git extractor (commits, diffs)
│   └── zulip.py         # Zulip extractor (messages)
└── data/                # Generated data directory
```

## Documentation

For detailed documentation, see the [project wiki](https://github.com/TheoN70/leankeeper/wiki).

## License

Apache 2.0 — aligned with the Mathlib license.
