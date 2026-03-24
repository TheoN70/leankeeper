"""
LeanKeeper — RAG evaluation on already-reviewed PRs.

Takes PRs that received CHANGES_REQUESTED, passes them through the RAG reviewer,
and compares RAG output vs actual reviewer feedback.
"""

import json
import logging
import os
import random

from sqlalchemy import text

from leankeeper.models.database import (
    PullRequest,
    PullRequestFile,
    Review,
    ReviewComment,
)
from leankeeper.rag.retriever import ask, _format_context
from leankeeper.rag.prompt import build_reviewer_prompt
from leankeeper.rag import store

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

    def generate_context_files(self, pr_number: int, output_dir: str = "eval") -> dict | None:
        """Generate evaluation context files for a PR (no LLM call).

        Creates three .md files:
        - pr_<number>_context.md — PR diffs (what the reviewer sees)
        - pr_<number>_rag.md — RAG system prompt + retrieved examples
        - pr_<number>_actual.md — Actual reviewer comments (ground truth)
        """
        os.makedirs(output_dir, exist_ok=True)

        # PR context
        context = self.build_pr_context(pr_number)
        if not context:
            logger.warning(f"PR #{pr_number}: no context available")
            return None

        # Actual feedback
        actual = self.get_actual_feedback(pr_number)
        if not actual:
            logger.warning(f"PR #{pr_number}: no reviewer comments")
            return None

        # PR date for temporal filtering
        with self.session_factory() as session:
            pr = session.get(PullRequest, pr_number)
            pr_date = pr.created_at if pr else None
            pr_title = pr.title if pr else ""
            pr_author = pr.author if pr else ""

        # Truncate context for RAG query
        query_context = context[:8000] if len(context) > 8000 else context

        # RAG retrieval (no LLM call)
        sources = ["review_comments", "reviews"]
        results = store.search(
            self.session_factory, query_context,
            source_tables=sources, limit=10, before_date=pr_date,
        )
        rag_examples = _format_context(results) if results else "(No relevant examples found.)"
        rag_prompt = build_reviewer_prompt(rag_examples)

        # Write files
        ctx_path = os.path.join(output_dir, f"pr_{pr_number}_context.md")
        rag_path = os.path.join(output_dir, f"pr_{pr_number}_rag.md")
        actual_path = os.path.join(output_dir, f"pr_{pr_number}_actual.md")

        with open(ctx_path, "w", encoding="utf-8") as f:
            f.write(f"# PR #{pr_number}: {pr_title}\n\n")
            f.write(f"**Author:** {pr_author}\n\n")
            f.write("## PR Content (what the reviewer sees)\n\n")
            f.write(context)

        with open(rag_path, "w", encoding="utf-8") as f:
            f.write(f"# RAG Context for PR #{pr_number}\n\n")
            f.write("## Instructions\n\n")
            f.write(rag_prompt)
            f.write(f"\n\n## PR to Review\n\n")
            f.write(query_context)

        with open(actual_path, "w", encoding="utf-8") as f:
            f.write(f"# Actual Reviewer Feedback for PR #{pr_number}\n\n")
            f.write(f"**{len(actual)} comments from real Mathlib reviewers.**\n\n")
            f.write("---\n\n")
            for i, c in enumerate(actual, 1):
                filepath = c["filepath"] or "general"
                f.write(f"### Comment {i} — {c['author']} on `{filepath}`\n\n")
                f.write(f"{c['body']}\n\n")

        logger.info(f"PR #{pr_number}: files written to {output_dir}/")
        return {
            "pr_number": pr_number,
            "context": ctx_path,
            "rag": rag_path,
            "actual": actual_path,
        }
