"""
LeanKeeper — Extracteur Git.

Extrait les commits et diffs depuis le dépôt git cloné localement.
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
        """Exécute une commande git dans le dépôt."""
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
        """Clone le dépôt s'il n'existe pas, sinon fetch."""
        if self.repo_dir.exists():
            logger.info(f"Dépôt existant, fetch...")
            self._run_git("fetch", "--all")
        else:
            logger.info(f"Clone de {GIT_CLONE_URL}...")
            subprocess.run(
                ["git", "clone", "--bare", GIT_CLONE_URL, str(self.repo_dir)],
                check=True,
                timeout=3600,
            )
        logger.info("Dépôt prêt.")

    # ──────────────────────────────────────────
    # Extraction des commits
    # ──────────────────────────────────────────

    def extract_commits(self):
        """Extrait tous les commits avec métadonnées."""
        logger.info("Extraction des commits...")

        # Format: sha\x00author_name\x00author_email\x00date_iso\x00message
        SEP = "\x00"
        log_format = f"%H{SEP}%an{SEP}%ae{SEP}%aI{SEP}%s"

        output = self._run_git(
            "log", "--all", f"--format={log_format}",
            timeout=600,
        )

        lines = output.strip().split("\n")
        logger.info(f"{len(lines)} commits trouvés")

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
                    logger.info(f"Commits: {count} insérés")

            session.commit()

        logger.info(f"Commits terminé: {count} nouveaux commits")

    # ──────────────────────────────────────────
    # Extraction des stats par commit (sans patch)
    # ──────────────────────────────────────────

    def extract_commit_stats(self):
        """Extrait insertions/deletions par commit (--numstat)."""
        logger.info("Extraction des stats par commit...")

        output = self._run_git(
            "log", "--all", "--numstat", "--format=COMMIT:%H",
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
                    # Flush le batch précédent
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

            # Dernier batch
            if batch and current_sha:
                self._save_commit_files(session, current_sha, batch)

            session.commit()

        logger.info("Stats par commit terminées")

    def _save_commit_files(self, session, sha: str, files: list[dict]):
        """Sauvegarde les fichiers d'un commit et met à jour ses totaux."""
        commit = session.get(Commit, sha)
        if not commit:
            return

        total_ins = 0
        total_del = 0

        for f in files:
            # Vérifier si déjà présent
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
    # Extraction des patches (volumineux, optionnel)
    # ──────────────────────────────────────────

    def extract_commit_patches(self, since: str = None):
        """
        Extrait les diffs complets par commit.
        ATTENTION : très volumineux (10-50 Go). Utiliser since pour limiter.

        Args:
            since: date ISO (ex: "2024-01-01") — n'extrait que les commits après cette date.
        """
        logger.info(f"Extraction des patches{f' depuis {since}' if since else ''}...")

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
                    # Sauvegarder le fichier précédent
                    if current_sha and current_file:
                        self._save_patch(session, current_sha, current_file, current_patch_lines)
                        count += 1
                    current_sha = line[7:]
                    current_file = None
                    current_patch_lines = []
                    continue

                if line.startswith("diff --git"):
                    # Nouveau fichier dans le même commit
                    if current_sha and current_file:
                        self._save_patch(session, current_sha, current_file, current_patch_lines)
                        count += 1
                    # Extraire le chemin b/...
                    parts = line.split(" b/")
                    current_file = parts[-1] if len(parts) > 1 else None
                    current_patch_lines = [line]
                    continue

                if current_file is not None:
                    current_patch_lines.append(line)

                if count % BATCH_SIZE == 0 and count > 0:
                    session.commit()
                    logger.info(f"Patches: {count} fichiers traités")

            # Dernier fichier
            if current_sha and current_file:
                self._save_patch(session, current_sha, current_file, current_patch_lines)

            session.commit()

        logger.info(f"Patches terminé: {count} fichiers")

    def _save_patch(self, session, sha: str, filepath: str, patch_lines: list[str]):
        """Met à jour le patch d'un CommitFile existant."""
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
        # Si le CommitFile n'existe pas encore, on ne crée pas sans stats

    # ──────────────────────────────────────────
    # Orchestrateur
    # ──────────────────────────────────────────

    def extract_all(self, include_patches: bool = False, patches_since: str = None):
        """
        Extraction complète.

        Args:
            include_patches: si True, extrait les diffs complets (volumineux).
            patches_since: date ISO pour limiter les patches.
        """
        self.clone_or_update()
        self.extract_commits()
        self.extract_commit_stats()
        if include_patches:
            self.extract_commit_patches(since=patches_since)


# ──────────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────────


def _parse_git_date(s: str) -> datetime:
    """Parse une date ISO git."""
    return datetime.fromisoformat(s)
