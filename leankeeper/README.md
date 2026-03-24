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
# Full extraction (first run)
python -m leankeeper extract github          # PRs, reviews, comments (~1h10)
python -m leankeeper extract github-reviews  # Review comments inline only
python -m leankeeper extract git             # Commits and stats (~10min)
python -m leankeeper extract zulip           # Zulip messages (~1h)
python -m leankeeper extract lean             # Lean declarations (~4min)
python -m leankeeper extract all             # All above (except patches and PR files)

# Full incremental update (extract + index, one command)
python -m leankeeper update

# Database stats
python -m leankeeper stats

# Export a table to JSONL
python -m leankeeper export review_comments data/review_comments.jsonl
```

### RAG (Retrieval-Augmented Generation)

```bash
# Setup (requires postgresql-16-pgvector system package)
python -m leankeeper rag init

# Index data into embeddings (~30min per 150K rows on CPU)
python -m leankeeper rag index                          # All tables
python -m leankeeper rag index --table review_comments  # Specific table
python -m leankeeper rag index --update                 # Only new rows

# Semantic search
python -m leankeeper rag search "naming convention for CommMonoid"

# Generate context for Claude Code (no API cost)
python -m leankeeper rag context "my query" -o rag_context.md
python -m leankeeper rag context "my query" --no-project  # Without project conventions

# Interactive chat (requires ANTHROPIC_API_KEY)
python -m leankeeper rag chat                           # Contributor mode
python -m leankeeper rag chat --mode reviewer           # Reviewer mode
python -m leankeeper rag chat --backend ollama          # Use local LLM

# Delete embeddings
python -m leankeeper rag delete --table zulip_messages   # Delete all Zulip embeddings
python -m leankeeper rag delete --table reviews --id 42  # Delete a specific one
python -m leankeeper rag delete                          # Delete all (with confirmation)

# Evaluation (generate context files, no LLM needed)
python -m leankeeper rag eval-context --pr 12345       # Single PR
python -m leankeeper rag eval-context --limit 5        # 5 random PRs
# Then use Claude Code: /eval-pr 12345 or /eval-batch 5

# Status
python -m leankeeper rag status
```

### Optional extractions (heavy)

```bash
# Files modified per PR with patches (~20K REST requests, ~15h)
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
│   ├── zulip.py         # Zulip extractor (messages)
│   └── lean.py          # Lean declaration extractor (from bare repo)
├── rag/
│   ├── __init__.py
│   ├── embedder.py      # Local embeddings (sentence-transformers)
│   ├── store.py         # pgvector indexing and search
│   ├── llm.py           # Pluggable LLM backends (Claude, OpenAI, Ollama)
│   ├── retriever.py     # RAG pipeline (retrieve + generate)
│   └── prompt.py        # System prompts (contributor/reviewer modes)
└── data/                # Generated data directory
```

## Documentation

For detailed documentation, see the [project wiki](https://github.com/TheoN70/leankeeper/wiki).

## License

Apache 2.0 — aligned with the Mathlib license.
