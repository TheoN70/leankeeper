"""
LeanKeeper — RAG evaluation on already-reviewed PRs.

Takes PRs that received CHANGES_REQUESTED, passes them through the RAG reviewer,
and compares RAG output vs actual reviewer feedback.
"""

import json
import logging
import random

from sqlalchemy import text

from leankeeper.models.database import (
    PullRequest,
    PullRequestFile,
    Review,
    ReviewComment,
)
from leankeeper.rag.retriever import ask

logger = logging.getLogger(__name__)


class RAGEvaluator:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def select_test_prs(self, limit: int = 30) -> list[int]:
        """Select merged PRs that had CHANGES_REQUESTED reviews."""
        with self.session_factory() as session:
            results = session.execute(text("""
                SELECT DISTINCT r.pr_number
                FROM reviews r
                JOIN pull_requests pr ON pr.number = r.pr_number
                WHERE r.state = 'CHANGES_REQUESTED'
                AND pr.state = 'merged'
                AND EXISTS (
                    SELECT 1 FROM review_comments rc
                    WHERE rc.pr_number = r.pr_number
                )
                AND EXISTS (
                    SELECT 1 FROM pull_request_files pf
                    WHERE pf.pr_number = r.pr_number
                )
            """)).fetchall()

        pr_numbers = [r[0] for r in results]
        logger.info(f"Found {len(pr_numbers)} eligible PRs")

        if len(pr_numbers) > limit:
            pr_numbers = random.sample(pr_numbers, limit)

        return pr_numbers

    def build_pr_context(self, pr_number: int) -> str:
        """Build the text context for a PR (title + body + diffs)."""
        with self.session_factory() as session:
            pr = session.get(PullRequest, pr_number)
            if not pr:
                return ""

            parts = [f"PR #{pr.number}: {pr.title}"]
            if pr.body:
                body = pr.body[:1000] if len(pr.body) > 1000 else pr.body
                parts.append(f"\nDescription:\n{body}")

            files = session.query(PullRequestFile).filter_by(pr_number=pr_number).all()
            if files:
                parts.append(f"\nFiles changed ({len(files)}):")
                for f in files:
                    parts.append(f"\n--- {f.filepath} ({f.status}) ---")
                    if f.patch:
                        patch = f.patch[:2000] if len(f.patch) > 2000 else f.patch
                        parts.append(patch)

        return "\n".join(parts)

    def get_actual_feedback(self, pr_number: int) -> list[dict]:
        """Get actual reviewer comments for a PR."""
        with self.session_factory() as session:
            comments = (
                session.query(ReviewComment)
                .filter_by(pr_number=pr_number)
                .order_by(ReviewComment.created_at)
                .all()
            )

            return [
                {
                    "author": c.author,
                    "filepath": c.filepath,
                    "body": c.body,
                    "line": c.line,
                }
                for c in comments
                # Skip bot comments and very short ones
                if c.author != "github-actions[bot]" and len(c.body.strip()) > 20
            ]

    def run_eval(self, pr_number: int, backend: str = None) -> dict:
        """Run RAG reviewer on a PR and return comparison data."""
        logger.info(f"Evaluating PR #{pr_number}...")

        # Build context (what the RAG sees)
        context = self.build_pr_context(pr_number)
        if not context:
            return {"pr_number": pr_number, "error": "No context available"}

        # Get actual feedback (ground truth)
        actual = self.get_actual_feedback(pr_number)
        if not actual:
            return {"pr_number": pr_number, "error": "No reviewer comments"}

        # Get the PR creation date for temporal filtering
        with self.session_factory() as session:
            pr = session.get(PullRequest, pr_number)
            pr_date = pr.created_at if pr else None

        # Truncate context if too long for the LLM
        if len(context) > 8000:
            context = context[:8000] + "\n... [truncated]"

        # Run RAG reviewer (only use data from before the PR was created)
        rag_feedback = ask(
            self.session_factory,
            f"Review this Mathlib PR:\n\n{context}",
            mode="reviewer",
            limit=10,
            backend=backend,
            before_date=pr_date,
        )

        return {
            "pr_number": pr_number,
            "title": context.split("\n")[0],
            "actual_comments": actual,
            "actual_count": len(actual),
            "rag_feedback": rag_feedback,
        }

    def run_batch(self, pr_numbers: list[int], backend: str = None) -> list[dict]:
        """Run eval on multiple PRs."""
        results = []
        for i, pr_number in enumerate(pr_numbers, 1):
            logger.info(f"[{i}/{len(pr_numbers)}] PR #{pr_number}")
            result = self.run_eval(pr_number, backend=backend)
            results.append(result)
        return results

    def report(self, results: list[dict]):
        """Print evaluation report."""
        for r in results:
            if "error" in r:
                print(f"\n══ PR #{r['pr_number']}: SKIPPED ({r['error']}) ══")
                continue

            print(f"\n{'═' * 60}")
            print(f"  {r['title']}")
            print(f"{'═' * 60}")

            print(f"\n── Actual reviewer feedback ({r['actual_count']} comments) ──")
            for c in r["actual_comments"][:5]:  # Show max 5
                filepath = c["filepath"] or "general"
                body = c["body"][:200]
                print(f"  {c['author']} on {filepath}:")
                print(f"    {body}")
                print()

            print(f"── RAG reviewer feedback ──")
            feedback = r["rag_feedback"][:1500] if len(r["rag_feedback"]) > 1500 else r["rag_feedback"]
            print(f"  {feedback}")
            print()

        # Summary
        evaluated = [r for r in results if "error" not in r]
        skipped = [r for r in results if "error" in r]
        print(f"\n{'═' * 60}")
        print(f"  Evaluation Summary")
        print(f"{'═' * 60}")
        print(f"  Evaluated: {len(evaluated)} PRs")
        print(f"  Skipped: {len(skipped)} PRs")
        print(f"  Avg actual comments per PR: {sum(r['actual_count'] for r in evaluated) / max(len(evaluated), 1):.1f}")
        print()

    def export(self, results: list[dict], path: str):
        """Export results to JSONL."""
        with open(path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        logger.info(f"Results exported to {path}")
