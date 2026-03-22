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


def main():
    parser = argparse.ArgumentParser(description="LeanKeeper — Mathlib Dataset")
    parser.add_argument("--db", default=DATABASE_URL, help="Database URL")
    subparsers = parser.add_subparsers(dest="command")

    # extract
    extract_parser = subparsers.add_parser("extract", help="Extract data")
    extract_parser.add_argument(
        "target",
        choices=["github", "github-reviews", "github-files", "git", "git-patches", "zulip", "all"],
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    session_factory = init_db(args.db)

    if args.command == "extract":
        cmd_extract(args, session_factory)
    elif args.command == "stats":
        cmd_stats(args, session_factory)
    elif args.command == "export":
        cmd_export(args, session_factory)


if __name__ == "__main__":
    main()
