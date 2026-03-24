"""
LeanKeeper — CLI entry point.

Usage:
    python -m leankeeper extract github          # PRs, reviews, comments
    python -m leankeeper extract github-reviews  # Inline review comments only
    python -m leankeeper extract github-files    # Files modified per PR (slow)
    python -m leankeeper extract git             # Commits and stats
    python -m leankeeper extract git-patches     # Full diffs (large)
    python -m leankeeper extract zulip           # Zulip messages
    python -m leankeeper extract all             # All except patches and PR files
    python -m leankeeper stats                   # Show database stats
    python -m leankeeper export <table> <path>   # Export a table to JSONL
"""

import argparse
import json
import logging
import sys

from leankeeper.config import DATABASE_URL, LOG_LEVEL
from leankeeper.models.database import (
    Commit,
    CommitFile,
    Declaration,
    IssueComment,
    PullRequest,
    PullRequestFile,
    Review,
    ReviewComment,
    ZulipChannel,
    ZulipMessage,
    init_db,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("leankeeper")


def cmd_update(args, session_factory):
    """Full incremental update: extract new data + index new embeddings."""
    logger.info("Starting full update...")

    # Step 1: Extract new data
    from leankeeper.extractors.github import GitHubExtractor
    from leankeeper.extractors.git import GitExtractor
    from leankeeper.extractors.zulip import ZulipExtractor

    logger.info("── Updating GitHub PRs ──")
    extractor = GitHubExtractor(session_factory)
    extractor.extract_pull_requests(update_only=True)

    logger.info("── Updating review comments ──")
    extractor.extract_review_comments()

    logger.info("── Updating Git commits ──")
    git = GitExtractor(session_factory)
    git.extract_all(include_patches=False, update_only=True)

    logger.info("── Updating Zulip messages ──")
    zulip = ZulipExtractor(session_factory)
    zulip.extract_all(update_only=True)

    logger.info("── Updating Lean declarations ──")
    from leankeeper.extractors.lean import LeanExtractor
    lean = LeanExtractor(session_factory)
    lean.extract_all()

    # Step 2: Index new embeddings
    from leankeeper.rag.store import index_table, SOURCE_MODELS
    logger.info("── Indexing new embeddings ──")
    for table_name in SOURCE_MODELS:
        index_table(session_factory, table_name, update_only=True)

    logger.info("Full update done.")


def cmd_extract(args, session_factory):
    """Run extraction."""
    target = args.target
    update = getattr(args, "update", False)

    if target in ("github", "all"):
        from leankeeper.extractors.github import GitHubExtractor

        extractor = GitHubExtractor(session_factory)
        extractor.extract_all(include_pr_files=False, update_only=update)

    if target == "github-reviews":
        from leankeeper.extractors.github import GitHubExtractor

        extractor = GitHubExtractor(session_factory)
        extractor.extract_review_comments()

    if target == "github-files":
        from leankeeper.extractors.github import GitHubExtractor

        extractor = GitHubExtractor(session_factory)
        extractor.extract_pr_files()

    if target in ("git", "all"):
        from leankeeper.extractors.git import GitExtractor

        extractor = GitExtractor(session_factory)
        extractor.extract_all(include_patches=False, update_only=update)

    if target == "git-patches":
        from leankeeper.extractors.git import GitExtractor

        extractor = GitExtractor(session_factory)
        extractor.extract_all(include_patches=True, patches_since=args.since)

    if target in ("zulip", "all"):
        from leankeeper.extractors.zulip import ZulipExtractor

        extractor = ZulipExtractor(session_factory)
        extractor.extract_all(update_only=update)

    if target in ("lean", "all"):
        from leankeeper.extractors.lean import LeanExtractor

        extractor = LeanExtractor(session_factory)
        extractor.extract_all()


def cmd_stats(args, session_factory):
    """Display database statistics."""
    with session_factory() as session:
        tables = [
            ("Commits", Commit),
            ("Commit files", CommitFile),
            ("Pull requests", PullRequest),
            ("PR files", PullRequestFile),
            ("Reviews", Review),
            ("Review comments", ReviewComment),
            ("Issue comments", IssueComment),
            ("Zulip channels", ZulipChannel),
            ("Zulip messages", ZulipMessage),
            ("Declarations", Declaration),
        ]

        print("\n╔══════════════════════════════════════╗")
        print("║     LeanKeeper — Database Stats      ║")
        print("╠══════════════════════════════════════╣")

        total = 0
        for name, model in tables:
            count = session.query(model).count()
            total += count
            print(f"║  {name:<28} {count:>6} ║")

        print("╠══════════════════════════════════════╣")
        print(f"║  {'Total':<28} {total:>6} ║")
        print("╚══════════════════════════════════════╝")

        # Detailed stats
        print("\n── Pull Requests by state ──")
        for state in ("merged", "closed", "open"):
            count = session.query(PullRequest).filter_by(state=state).count()
            print(f"  {state}: {count}")

        print("\n── Review Comments: top reviewers ──")
        from sqlalchemy import func

        top = (
            session.query(ReviewComment.author, func.count(ReviewComment.id))
            .group_by(ReviewComment.author)
            .order_by(func.count(ReviewComment.id).desc())
            .limit(10)
            .all()
        )
        for author, count in top:
            print(f"  {author}: {count} comments")

        print()


def cmd_export(args, session_factory):
    """Export a table to JSONL."""
    from sqlalchemy import inspect

    table_map = {
        "commits": Commit,
        "commit_files": CommitFile,
        "pull_requests": PullRequest,
        "pr_files": PullRequestFile,
        "reviews": Review,
        "review_comments": ReviewComment,
        "issue_comments": IssueComment,
        "zulip_channels": ZulipChannel,
        "zulip_messages": ZulipMessage,
    }

    model = table_map.get(args.table)
    if not model:
        print(f"Unknown table: {args.table}")
        print(f"Available tables: {', '.join(table_map.keys())}")
        sys.exit(1)

    output_path = args.output
    logger.info(f"Exporting {args.table} to {output_path}...")

    columns = [c.key for c in inspect(model).mapper.column_attrs]

    count = 0
    with session_factory() as session:
        with open(output_path, "w", encoding="utf-8") as f:
            for row in session.query(model).yield_per(1000):
                obj = {}
                for col in columns:
                    val = getattr(row, col)
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    obj[col] = val
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                count += 1

    logger.info(f"Export done: {count} rows to {output_path}")


def cmd_rag(args, session_factory):
    """RAG commands."""
    action = args.action

    if action == "init":
        from leankeeper.rag.store import init_pgvector
        init_pgvector(session_factory)
        print("pgvector initialized. Ready to index.")

    elif action == "backfill-dates":
        from leankeeper.rag.store import SOURCE_DATE
        from sqlalchemy import text as sa_text

        date_joins = {
            "review_comments": ("review_comments", "id", "created_at"),
            "zulip_messages": ("zulip_messages", "id", "timestamp"),
            "pull_requests": ("pull_requests", "number", "created_at"),
            "reviews": ("reviews", "id", "submitted_at"),
            "issue_comments": ("issue_comments", "id", "created_at"),
        }

        with session_factory() as session:
            for source_table, (tbl, pk, date_col) in date_joins.items():
                result = session.execute(sa_text(f"""
                    UPDATE embeddings e
                    SET created_at = s.{date_col}
                    FROM {tbl} s
                    WHERE e.source_table = :source_table
                    AND e.source_id = CAST(s.{pk} AS TEXT)
                    AND e.created_at IS NULL
                """), {"source_table": source_table})
                print(f"  {source_table}: {result.rowcount} dates backfilled")
            session.commit()
        print("Backfill done.")

    elif action == "index":
        from leankeeper.rag.store import index_table, SOURCE_MODELS
        table = args.table
        update = args.update

        if table:
            index_table(session_factory, table, update_only=update)
        else:
            for t in SOURCE_MODELS:
                index_table(session_factory, t, update_only=update)

    elif action == "search":
        from leankeeper.rag.store import search
        query = " ".join(args.query)
        tables = [args.type] if args.type else None
        results = search(session_factory, query, source_tables=tables, limit=args.limit)

        for r in results:
            print(f"\n{'─' * 60}")
            print(f"[{r['source_table']}] similarity: {r['similarity']}")
            print(r["text"][:500])
        print()

    elif action == "context":
        from leankeeper.rag.retriever import build_context_md
        query = " ".join(args.query)
        include_project = not args.no_project
        output = build_context_md(session_factory, query, mode=args.mode,
                                  limit=args.limit, include_project=include_project)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Context written to {args.output}")
        else:
            print(output)

    elif action == "chat":
        from leankeeper.rag.retriever import ask
        mode = args.mode
        backend = args.backend
        print(f"LeanKeeper RAG — {mode} mode (type 'quit' to exit)\n")

        while True:
            try:
                query = input(">>> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if query.strip().lower() in ("quit", "exit", "q"):
                break
            if not query.strip():
                continue

            response = ask(session_factory, query, mode=mode, backend=backend)
            print(f"\n{response}\n")

    elif action == "delete":
        from leankeeper.rag.store import delete
        table = args.table
        source_id = getattr(args, "id", None)

        if not table and not source_id:
            confirm = input("Delete ALL embeddings? Type 'yes' to confirm: ")
            if confirm != "yes":
                print("Cancelled.")
                return

        count = delete(session_factory, source_table=table, source_id=source_id)
        target = f"{table}" if table else "all tables"
        if source_id:
            target = f"{table}/{source_id}"
        print(f"Deleted {count} embeddings from {target}")

    elif action == "eval":
        from leankeeper.rag.eval import RAGEvaluator
        evaluator = RAGEvaluator(session_factory)

        if args.pr:
            pr_numbers = [args.pr]
        else:
            pr_numbers = evaluator.select_test_prs(limit=args.limit)

        if not pr_numbers:
            print("No eligible PRs found. Run 'extract github-files' first.")
            return

        results = evaluator.run_batch(pr_numbers, backend=args.backend)
        evaluator.report(results)

        if args.export:
            evaluator.export(results, args.export)

    elif action == "status":
        from leankeeper.rag.store import status
        counts = status(session_factory)

        if not counts:
            print("No embeddings yet. Run: python -m leankeeper rag init && python -m leankeeper rag index")
            return

        print("\n── RAG Embeddings ──")
        total = 0
        for table, count in sorted(counts.items()):
            print(f"  {table}: {count}")
            total += count
        print(f"  Total: {total}")
        print()


def main():
    parser = argparse.ArgumentParser(description="LeanKeeper — Mathlib Dataset")
    parser.add_argument("--db", default=DATABASE_URL, help="Database URL")
    subparsers = parser.add_subparsers(dest="command")

    # update
    subparsers.add_parser("update", help="Full incremental update (extract + index new data)")

    # extract
    extract_parser = subparsers.add_parser("extract", help="Extract data")
    extract_parser.add_argument(
        "target",
        choices=["github", "github-reviews", "github-files", "git", "git-patches", "zulip", "lean", "all"],
        help="Data source to extract",
    )
    extract_parser.add_argument("--since", help="ISO date to limit (git-patches)")
    extract_parser.add_argument("--update", action="store_true", help="Incremental update (only fetch new/changed data)")

    # stats
    subparsers.add_parser("stats", help="Show database stats")

    # export
    export_parser = subparsers.add_parser("export", help="Export a table to JSONL")
    export_parser.add_argument("table", help="Table name")
    export_parser.add_argument("output", help="Output file path")

    # rag
    rag_parser = subparsers.add_parser("rag", help="RAG operations")
    rag_sub = rag_parser.add_subparsers(dest="action")

    rag_sub.add_parser("init", help="Initialize pgvector extension and embeddings table")
    rag_sub.add_parser("backfill-dates", help="Backfill created_at on existing embeddings")

    rag_index = rag_sub.add_parser("index", help="Index tables into embeddings")
    rag_index.add_argument("--table", help="Specific table to index (default: all)")
    rag_index.add_argument("--update", action="store_true", help="Only index new rows")

    rag_search = rag_sub.add_parser("search", help="Semantic search")
    rag_search.add_argument("query", nargs="+", help="Search query")
    rag_search.add_argument("--type", help="Filter by source table")
    rag_search.add_argument("--limit", type=int, default=5, help="Number of results")

    rag_context = rag_sub.add_parser("context", help="Generate RAG context as markdown")
    rag_context.add_argument("query", nargs="+", help="Query")
    rag_context.add_argument("--mode", choices=["contributor", "reviewer"], default="contributor", help="Mode")
    rag_context.add_argument("--limit", type=int, default=10, help="Number of examples")
    rag_context.add_argument("--no-project", action="store_true", help="Exclude project context (conventions, wiki)")
    rag_context.add_argument("--output", "-o", help="Output file (default: stdout)")

    rag_chat = rag_sub.add_parser("chat", help="Interactive RAG chat")
    rag_chat.add_argument("--mode", choices=["contributor", "reviewer"], default="contributor", help="Chat mode")
    rag_chat.add_argument("--backend", choices=["claude", "openai", "ollama"], help="LLM backend override")

    rag_eval = rag_sub.add_parser("eval", help="Evaluate RAG on already-reviewed PRs")
    rag_eval.add_argument("--limit", type=int, default=30, help="Number of PRs to evaluate")
    rag_eval.add_argument("--pr", type=int, help="Evaluate a specific PR number")
    rag_eval.add_argument("--backend", choices=["claude", "openai", "ollama"], help="LLM backend override")
    rag_eval.add_argument("--export", help="Export results to JSONL file")

    rag_delete = rag_sub.add_parser("delete", help="Delete embeddings")
    rag_delete.add_argument("--table", help="Source table to delete (default: all)")
    rag_delete.add_argument("--id", help="Specific source ID to delete")

    rag_sub.add_parser("status", help="Show embedding stats")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    session_factory = init_db(args.db)

    if args.command == "update":
        cmd_update(args, session_factory)
    elif args.command == "extract":
        cmd_extract(args, session_factory)
    elif args.command == "stats":
        cmd_stats(args, session_factory)
    elif args.command == "export":
        cmd_export(args, session_factory)
    elif args.command == "rag":
        if not args.action:
            rag_parser.print_help()
            sys.exit(1)
        cmd_rag(args, session_factory)


if __name__ == "__main__":
    main()
