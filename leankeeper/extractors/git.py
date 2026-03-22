"""
LeanKeeper — Git extractor.

Extracts commits and diffs from the locally cloned git repository.
"""

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from leankeeper.config import BATCH_SIZE, GIT_CLONE_DIR, GIT_CLONE_URL, MAX_PATCH_SIZE
from leankeeper.models.database import Commit, CommitFile

logger = logging.getLogger(__name__)


class GitExtractor:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.repo_dir = GIT_CLONE_DIR

    def _run_git(self, *args, **kwargs) -> str:
        """Run a git command in the repository."""
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            timeout=kwargs.get("timeout", 300),
        )
        if result.returncode != 0 and not kwargs.get("allow_failure"):
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout

    # ──────────────────────────────────────────
    # Clone
    # ──────────────────────────────────────────

    def clone_or_update(self):
        """Clone the repository if it doesn't exist, otherwise fetch."""
        if self.repo_dir.exists():
            logger.info("Existing repository, fetching...")
            self._run_git("fetch", "--all")
        else:
            logger.info(f"Cloning {GIT_CLONE_URL}...")
            subprocess.run(
                ["git", "clone", "--bare", GIT_CLONE_URL, str(self.repo_dir)],
                check=True,
                timeout=3600,
            )
        logger.info("Repository ready.")

    # ──────────────────────────────────────────
    # Commit extraction
    # ──────────────────────────────────────────

    def extract_commits(self, update_only: bool = False):
        """Extract all commits with metadata."""
        # In update mode, only fetch commits since the latest in DB
        since = None
        if update_only:
            with self.session_factory() as session:
                from sqlalchemy import func
                latest = session.query(func.max(Commit.date)).scalar()
                if latest:
                    since = latest.strftime("%Y-%m-%d")
                    logger.info(f"Update mode: fetching commits since {since}")

        logger.info("Extracting commits...")

        # Format: sha\x00author_name\x00author_email\x00date_iso\x00message
        SEP = "\x00"
        log_format = f"%H{SEP}%an{SEP}%ae{SEP}%aI{SEP}%s"

        args = ["log", "--all", f"--format={log_format}"]
        if since:
            args.append(f"--since={since}")

        output = self._run_git(
            *args,
            timeout=600,
        )

        lines = output.strip().split("\n")
        logger.info(f"{len(lines)} commits found")

        count = 0
        with self.session_factory() as session:
            for line in lines:
                if not line.strip():
                    continue

                parts = line.split(SEP)
                if len(parts) < 5:
                    continue

                sha, author_name, author_email, date_str, message = parts[0], parts[1], parts[2], parts[3], parts[4]

                if session.get(Commit, sha):
                    continue

                session.add(Commit(
                    sha=sha,
                    author_name=author_name,
                    author_email=author_email,
                    date=_parse_git_date(date_str),
                    message=message,
                ))
                count += 1

                if count % BATCH_SIZE == 0:
                    session.commit()
                    logger.info(f"Commits: {count} inserted")

            session.commit()

        logger.info(f"Commits done: {count} new commits")

    # ──────────────────────────────────────────
    # Per-commit stats extraction (without patch)
    # ──────────────────────────────────────────

    def extract_commit_stats(self, update_only: bool = False):
        """Extract insertions/deletions per commit (--numstat)."""
        since = None
        if update_only:
            with self.session_factory() as session:
                from sqlalchemy import func
                latest = session.query(func.max(Commit.date)).scalar()
                if latest:
                    since = latest.strftime("%Y-%m-%d")

        logger.info(f"Extracting per-commit stats{f' (since {since})' if since else ''}...")

        args = ["log", "--all", "--numstat", "--format=COMMIT:%H"]
        if since:
            args.append(f"--since={since}")

        output = self._run_git(
            *args,
            timeout=1800,
        )

        current_sha = None
        batch = []

        with self.session_factory() as session:
            for line in output.split("\n"):
                line = line.strip()
                if not line:
                    continue

                if line.startswith("COMMIT:"):
                    # Flush previous batch
                    if batch:
                        self._save_commit_files(session, current_sha, batch)
                        batch = []
                    current_sha = line[7:]
                    continue

                if current_sha and "\t" in line:
                    parts = line.split("\t")
                    if len(parts) == 3:
                        additions, deletions, filepath = parts
                        batch.append({
                            "filepath": filepath,
                            "additions": int(additions) if additions != "-" else 0,
                            "deletions": int(deletions) if deletions != "-" else 0,
                        })

            # Last batch
            if batch and current_sha:
                self._save_commit_files(session, current_sha, batch)

            session.commit()

        logger.info("Per-commit stats done")

    def _save_commit_files(self, session, sha: str, files: list[dict]):
        """Save commit files and update commit totals."""
        commit = session.get(Commit, sha)
        if not commit:
            return

        total_ins = 0
        total_del = 0

        for f in files:
            # Check if already present
            existing = (
                session.query(CommitFile)
                .filter_by(commit_sha=sha, filepath=f["filepath"])
                .first()
            )
            if not existing:
                session.add(CommitFile(
                    commit_sha=sha,
                    filepath=f["filepath"],
                    additions=f["additions"],
                    deletions=f["deletions"],
                ))
            total_ins += f["additions"]
            total_del += f["deletions"]

        commit.insertions = total_ins
        commit.deletions = total_del

    # ──────────────────────────────────────────
    # Patch extraction (large, optional)
    # ──────────────────────────────────────────

    def extract_commit_patches(self, since: str = None):
        """
        Extract full diffs per commit.
        WARNING: very large (10-50 GB). Use since to limit.

        Args:
            since: ISO date (e.g. "2024-01-01") — only extract commits after this date.
        """
        logger.info(f"Extracting patches{f' since {since}' if since else ''}...")

        args = ["log", "--all", "-p", "--format=COMMIT:%H"]
        if since:
            args.append(f"--since={since}")

        output = self._run_git(*args, timeout=7200)

        current_sha = None
        current_file = None
        current_patch_lines = []
        count = 0

        with self.session_factory() as session:
            for line in output.split("\n"):
                if line.startswith("COMMIT:"):
                    # Save previous file
                    if current_sha and current_file:
                        self._save_patch(session, current_sha, current_file, current_patch_lines)
                        count += 1
                    current_sha = line[7:]
                    current_file = None
                    current_patch_lines = []
                    continue

                if line.startswith("diff --git"):
                    # New file in the same commit
                    if current_sha and current_file:
                        self._save_patch(session, current_sha, current_file, current_patch_lines)
                        count += 1
                    # Extract the b/... path
                    parts = line.split(" b/")
                    current_file = parts[-1] if len(parts) > 1 else None
                    current_patch_lines = [line]
                    continue

                if current_file is not None:
                    current_patch_lines.append(line)

                if count % BATCH_SIZE == 0 and count > 0:
                    session.commit()
                    logger.info(f"Patches: {count} files processed")

            # Last file
            if current_sha and current_file:
                self._save_patch(session, current_sha, current_file, current_patch_lines)

            session.commit()

        logger.info(f"Patches done: {count} files")

    def _save_patch(self, session, sha: str, filepath: str, patch_lines: list[str]):
        """Update the patch of an existing CommitFile."""
        patch = "\n".join(patch_lines)
        if len(patch) > MAX_PATCH_SIZE:
            patch = patch[:MAX_PATCH_SIZE] + "\n... [truncated]"

        existing = (
            session.query(CommitFile)
            .filter_by(commit_sha=sha, filepath=filepath)
            .first()
        )
        if existing:
            existing.patch = patch
        # If the CommitFile doesn't exist yet, don't create without stats

    # ──────────────────────────────────────────
    # Orchestrator
    # ──────────────────────────────────────────

    def extract_all(self, include_patches: bool = False, patches_since: str = None, update_only: bool = False):
        """
        Full extraction.

        Args:
            include_patches: if True, extract full diffs (large).
            patches_since: ISO date to limit patches.
            update_only: if True, only fetch new commits since last extraction.
        """
        self.clone_or_update()
        self.extract_commits(update_only=update_only)
        self.extract_commit_stats(update_only=update_only)
        if include_patches:
            self.extract_commit_patches(since=patches_since)


# ──────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────


def _parse_git_date(s: str) -> datetime:
    """Parse an ISO git date."""
    return datetime.fromisoformat(s)
