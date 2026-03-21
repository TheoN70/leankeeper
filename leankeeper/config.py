"""
LeanKeeper — Configuration.
"""

from pathlib import Path
import os

# ──────────────────────────────────────────────
# Chemins
# ──────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────
# Base de données
# ──────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")

# ──────────────────────────────────────────────
# GitHub
# ──────────────────────────────────────────────

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # gh token avec permissions repo:read
GITHUB_REPO_OWNER = "leanprover-community"
GITHUB_REPO_NAME = "mathlib4"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_REST_URL = "https://api.github.com"

# Rate limiting
GITHUB_REQUESTS_PER_HOUR = 5000  # Avec token authentifié
GITHUB_SLEEP_BETWEEN_PAGES = 0.5  # Secondes entre chaque page

# ──────────────────────────────────────────────
# Git
# ──────────────────────────────────────────────

GIT_CLONE_URL = "https://github.com/leanprover-community/mathlib4.git"
GIT_CLONE_DIR = DATA_DIR / "mathlib4.git"

# Limiter la taille des diffs stockés (en caractères)
# Les diffs très volumineux (fichiers générés, etc.) sont tronqués
MAX_PATCH_SIZE = 100_000

# ──────────────────────────────────────────────
# Zulip
# ──────────────────────────────────────────────

ZULIP_BASE_URL = "https://leanprover.zulipchat.com/api/v1"
ZULIP_EMAIL = os.getenv("ZULIP_EMAIL")  # Email du compte Zulip
ZULIP_API_KEY = os.getenv("ZULIP_API_KEY")  # Clé API Zulip (Settings > Your bots)

# Channels à extraire (par ordre de priorité)
ZULIP_CHANNELS = [
    "general",
    "mathlib4",
    "new members",
    "Is there code for X?",
    "maths",
    "FLT",
    "Machine Learning for Theorem Proving",
    "lean4",
    "Carleson",
    "sphere eversion",
    "Equational",
    "condensed mathematics",
]

# ──────────────────────────────────────────────
# Extraction
# ──────────────────────────────────────────────

# Taille des batchs pour les insertions en base
BATCH_SIZE = 500

# Logs
LOG_LEVEL = "INFO"
