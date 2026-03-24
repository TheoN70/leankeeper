# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LeanKeeper is an AI agent specialized for Mathlib (Lean 4's community math library). The goal is to produce contributions that pass human review — not just proofs that compile, but code that respects Mathlib's conventions, typeclass hierarchy, naming, API patterns, and design standards.

The core metric is: **"does it pass Mathlib review?"**, not "does it compile?".

The ultimate goal of LeanKeeper is to enable **refactoring of complex functional Lean proofs** that compile but do not meet Mathlib standards (i.e., proofs that would be rejected in PR review). LeanKeeper transforms these valid-but-non-idiomatic proofs into contributions that conform to Mathlib's conventions and pass review.

## Key Concepts

- **Lean 4**: proof assistant where compilation = correctness
- **Mathlib**: ~2M lines, ~210K theorems, organized as a DAG with a typeclass hierarchy (`Monoid → Group → Ring → Field`, etc.)
- **The problem**: AI companies dump massive compilable code that doesn't meet Mathlib quality standards (wrong generality level, missing API lemmas, broken naming conventions), poisoning the design space
- **LeanKeeper's role**: act as a "good junior Mathlib contributor" — explore the typeclass hierarchy, propose well-integrated definitions with standard API, follow naming conventions, and submit clean ~200-line PRs

## Mathlib Contribution Guidelines (synthesized from `contribute/`)

The full guidelines are in the `contribute/` directory. Key rules summarized below.

### Naming conventions (`contribute/naming.md`)

- **Capitalization**: `Prop` terms (theorems) use `snake_case`. Types/classes use `UpperCamelCase`. Functions named like their return type. Other terms use `lowerCamelCase`. When `UpperCamelCase` appears in `snake_case`, use `lowerCamelCase` (e.g. `neZero_iff` for `NeZero`).
- **Spelling**: American English (`factorization`, not `factorisation`).
- **Symbol dictionary**: `∨`→`or`, `∧`→`and`, `→`→`of`/`imp`, `↔`→`iff`, `¬`→`not`, `+`→`add`, `*`→`mul`, `-`→`neg`/`sub`, `⁻¹`→`inv`, `∣`→`dvd`, `≤`→`le`/`ge`, `<`→`lt`/`gt`, `⊔`→`sup`, `⊓`→`inf`, `⊥`→`bot`, `⊤`→`top`, `∈`→`mem`, `∪`→`union`, `∩`→`inter`.
- **Descriptive names**: conclusion first, hypotheses with `_of_`. Example: `C_of_A_of_B` for `A → B → C`. Hypotheses listed in order they appear, not reverse.
- **Abbreviations**: `pos` for `zero_lt`, `neg` for `lt_zero`, `nonpos` for `le_zero`, `nonneg` for `zero_le`.
- **Dot notation**: use namespace dots for projection notation (`And.symm`, `Eq.trans`, `LE.trans`).
- **Axiomatic names**: `refl`, `irrefl`, `symm`, `trans`, `antisymm`, `comm`, `assoc`, `left_comm`, `right_comm`, `inj`.
- **Structural lemmas**: `.ext` with `@[ext]` for extensionality. `.ext_iff` for biconditional. `_injective` for `Function.Injective f`, `_inj` for `f x = f y ↔ x = y`.
- **Predicates as suffixes**: most predicates as prefixes (`isClosed_Icc`), except: `_injective`, `_surjective`, `_bijective`, `_monotone`, `_antitone`, `_strictMono`.
- **Prop-valued classes**: nouns get `Is` prefix (`IsTopologicalRing`), adjectives may omit it (`Normal`).
- **Variable conventions**: `α β γ` for types, `x y z` for elements, `h h₁` for assumptions, `G` for groups, `R` for rings, `K`/`𝕜` for fields, `E` for vector spaces.

### Style guide (`contribute/style.md`)

- **Line length**: max 100 characters.
- **Header**: copyright, `module` keyword on its own line, `public import`s grouped, then `import`s grouped alphabetically.
- **Module docstring**: `/-! -/` after imports with title, summary, main results, notation, implementation notes, references, tags.
- **Indentation**: 2 spaces for proof body, 4 spaces for multiline theorem statement continuation. `by` at end of previous line (not on its own line).
- **Declarations**: all top-level (flush-left). Explicit types for all arguments and return types.
- **Instances**: use `where` syntax.
- **Hypotheses**: prefer left of colon over universal quantifiers when proof introduces them.
- **Anonymous functions**: prefer `fun x ↦` over `fun x =>` and `λ`. `↦` preferred in source.
- **Tactic mode**: one tactic per line. Focusing dot `·` not indented, contents indented. Short proofs can use semicolons on one line.
- **`simp`**: terminal `simp` calls should NOT be squeezed (not replaced by `simp?` output).
- **`calc`**: relations aligned, `_` left-justified, `calc` at end of previous line.
- **Whitespace**: prefer `<|` over `$`. Use `|>` for dot notation chains. Space after `←` in `rw`.
- **No empty lines inside declarations**.
- **Normal forms**: settle on one standard form for equivalent statements (e.g. `s.Nonempty`).
- **Deprecation**: use `@[deprecated (since := "YYYY-MM-DD")]` with alias. Deprecations can be deleted after 6 months.
- **Transparency**: definitions `semireducible` by default. Use structure wrappers instead of `irreducible`.
- **Performance**: benchmark with `!bench` on PRs that touch classes, instances, simp lemmas, imports.

### Documentation (`contribute/doc.md`)

- Every definition and major theorem requires a doc string (`/-- -/`).
- Doc strings should convey mathematical meaning (allowed to lie slightly about implementation).
- Module docstring required: title, summary, main results, notation, implementation notes, references.
- Use backticks for Lean names, LaTeX `$ $` for math.
- Sectioning comments with `/-! -/` and `###` headers.

### PR conventions (`contribute/commit.md`)

- Title format: `<type>(<scope>): <subject>` where type is `feat`/`fix`/`doc`/`style`/`refactor`/`chore`/`perf`/`ci`.
- Subject: imperative present tense, no capitalization, no trailing dot.
- Dependencies: `- [ ] depends on: #XXXX` in description.

### PR review criteria (`contribute/pr-review.md`)

Reviewers check (from easiest to hardest):
1. **Style**: code formatting, naming conventions, PR title/description
2. **Documentation**: docstrings, cross-references, proof sketches in comments
3. **Location**: declarations in right files, no duplicates, minimal imports, reasonable file length (<1000 lines)
4. **Improvements**: split long proofs, better tactics (e.g. `gcongr` over `mul_le_mul_of_nonneg_left`), simpler proof structure
5. **Library integration**: sensible API, sufficient generality, fits mathlib design

## Development

### Setup

```bash
pip install -r leankeeper/requirements.txt
```

Dependencies: `sqlalchemy>=2.0`, `requests>=2.31`, `sentence-transformers>=2.2.2`, `pgvector>=0.2.4`, `anthropic>=0.40`.

### Configuration

All credentials are loaded from environment variables (see `leankeeper/config.py`):
- `DATABASE_URL` — PostgreSQL connection string (required)
- `GITHUB_READ_ONLY_TOKEN` — GitHub personal access token
- `ZULIP_EMAIL` / `ZULIP_API_KEY` — Zulip account credentials
- `ANTHROPIC_API_KEY` — For RAG chat with Claude (default LLM backend)
- `LLM_BACKEND` — `claude` (default), `openai`, or `ollama`
- `EMBEDDING_MODEL` — Sentence-transformers model (default: `all-MiniLM-L6-v2`)

### CLI Commands

All commands run from the repo root via `python -m leankeeper`:

```bash
# Full extraction (first run)
python -m leankeeper extract github          # PRs, reviews, issue comments (~1h)
python -m leankeeper extract github-reviews  # Review comments inline only (~2h30)
python -m leankeeper extract git             # Commits and stats (~10min)
python -m leankeeper extract zulip           # Zulip messages (~1h)
python -m leankeeper extract all             # All above (excludes patches and PR files)

# Full incremental update (extract + index, one command)
python -m leankeeper update

# Or manually:
python -m leankeeper extract all --update
python -m leankeeper rag index --update

# Heavy extractions (optional)
python -m leankeeper extract lean             # Lean declarations from bare repo (~4min)
python -m leankeeper extract github-files    # Files modified per PR (~15h, ~20K REST requests)
python -m leankeeper extract git-patches     # Full diffs (10-50 GB)
python -m leankeeper extract git-patches --since 2024-01-01

# Database inspection
python -m leankeeper stats

# Check database size
psql -d leankeeper -c "SELECT pg_size_pretty(pg_database_size('leankeeper'));"

# Export a table to JSONL
python -m leankeeper export <table> <output_path>
# Tables: commits, commit_files, pull_requests, pr_files, reviews, review_comments, issue_comments, zulip_channels, zulip_messages

# RAG
python -m leankeeper rag init                           # Initialize pgvector extension
python -m leankeeper rag index                          # Index all tables (~1h on CPU)
python -m leankeeper rag index --table review_comments  # Index specific table (~30min)
python -m leankeeper rag index --update                 # Only index new rows
python -m leankeeper rag search "naming convention"     # Semantic search
python -m leankeeper rag context "my query" -o ctx.md   # Generate context for Claude Code
python -m leankeeper rag context "query" --no-project   # Without project conventions
python -m leankeeper rag chat                           # Interactive RAG chat (contributor mode)
python -m leankeeper rag chat --mode reviewer           # Reviewer mode
python -m leankeeper rag chat --backend ollama          # Use local LLM
python -m leankeeper rag backfill-dates                  # Backfill created_at on existing embeddings
python -m leankeeper rag eval --limit 5                  # Test RAG on historical PRs
python -m leankeeper rag delete --table zulip_messages   # Delete embeddings for a table
python -m leankeeper rag delete --table reviews --id 42 # Delete a specific embedding
python -m leankeeper rag delete                         # Delete all (with confirmation)
python -m leankeeper rag status                         # Show embedding counts
```

## Architecture

The project has completed **Phase 1 (Dataset)** and is now in **Phase 2 (RAG + Conventions)** — a retrieval-augmented generation system that leverages the extracted data to assist contributors and reviewers.

### Package structure (`leankeeper/`)

- **`__main__.py`** — CLI entry point with subcommands: `extract`, `stats`, `export`, `rag`
- **`config.py`** — All configuration: paths, API URLs/tokens, rate limits, extraction params. Credentials loaded from environment variables.
- **`models/database.py`** — SQLAlchemy ORM models and `init_db()`. Uses `BigInteger` for external IDs (GitHub, Zulip) to handle IDs > 2^31. Defines all tables including future Lean-specific ones (declarations, imports, typeclasses) not yet populated.
- **`extractors/`** — One extractor class per data source, each taking a `session_factory` from `init_db()`:
  - **`github.py`** (`GitHubExtractor`) — GraphQL for PRs/reviews/issue comments in bulk, REST for inline review comments (with `diff_hunk`) and per-PR file patches. Handles rate limiting and network errors with automatic retry (3 attempts with backoff). Detects Bors-merged PRs via `[Merged by Bors]` title prefix.
  - **`git.py`** (`GitExtractor`) — Clones mathlib4 as bare repo, extracts commits via `git log` parsing, stats via `--numstat`, optional full patches via `-p`. Uses subprocess.
  - **`zulip.py`** (`ZulipExtractor`) — Extracts channels and messages via Zulip REST API with backward pagination from newest.
  - **`lean.py`** (`LeanExtractor`) — Parses Lean 4 source files from the bare mathlib4 repo to extract declarations (theorems, definitions, lemmas, instances, classes, structures) with type signatures and docstrings. Regex-based parsing, ~215K declarations in ~4 min.
- **`migrations/`** — Database migration scripts (run individually as modules).
- **`rag/`** — Retrieval-Augmented Generation system:
  - **`embedder.py`** — Local embedding generation using sentence-transformers (`all-MiniLM-L6-v2`)
  - **`store.py`** — pgvector operations: indexing, semantic search, status. Embeddings stored in a separate `embeddings` table.
  - **`llm.py`** — Pluggable LLM backends: Claude (default), OpenAI, Ollama (local)
  - **`retriever.py`** — High-level RAG pipeline: retrieve context → build prompt → generate response
  - **`prompt.py`** — System prompts for contributor and reviewer modes

### Database

PostgreSQL with SQLAlchemy ORM. External IDs (GitHub, Zulip) use `BigInteger` (64-bit). Tables auto-created by `init_db()`. Full schema documentation in [`DB_ARCHITECTURE.md`](DB_ARCHITECTURE.md).

### Data flow

All extractors follow the same pattern: `Extractor(session_factory)` → `extract_all()` → upsert into PostgreSQL via SQLAlchemy sessions, committed in batches (`BATCH_SIZE=500`). Extractors are idempotent — re-running updates existing records (upsert). Use `--update` for incremental updates that only fetch new/changed data.

### Training Data Sources

All public and extractible via GitHub and Zulip APIs:
- Mathlib Git repository (commits, diffs)
- GitHub PRs with review comments (~36K PRs, ~20K+ merged via Bors)
- Lean Zulip discussions on design decisions
- Mathlib4 GitHub wiki (19 pages, cloned in `mathlib4.wiki/`)
- Linter/CI results
- Import dependency graph

### Documentation

- **[Project wiki](https://github.com/TheoN70/leankeeper/wiki)** — Published as a separate GitHub wiki repo (`wiki/` directory). Covers quickstart, architecture, data sources, training pairs, Mathlib conventions, and roadmap.
- **[`DB_ARCHITECTURE.md`](DB_ARCHITECTURE.md)** — Full database schema documentation.

### Language

The project language is English. All code, comments, docstrings, log messages, and CLI output are in English.
