"""
LeanKeeper — Configuration.
"""

from pathlib import Path
import os

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")

# ──────────────────────────────────────────────
# GitHub
# ──────────────────────────────────────────────

GITHUB_TOKEN = os.getenv("GITHUB_READ_ONLY_TOKEN")  # gh token with repo:read permissions
GITHUB_REPO_OWNER = "leanprover-community"
GITHUB_REPO_NAME = "mathlib4"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_REST_URL = "https://api.github.com"

# Rate limiting
GITHUB_REQUESTS_PER_HOUR = 5000  # With authenticated token
GITHUB_SLEEP_BETWEEN_PAGES = 0.5  # Seconds between each page

# ──────────────────────────────────────────────
# Git
# ──────────────────────────────────────────────

GIT_CLONE_URL = "https://github.com/leanprover-community/mathlib4.git"
GIT_CLONE_DIR = DATA_DIR / "mathlib4.git"

# Limit stored diff size (in characters)
# Very large diffs (generated files, etc.) are truncated
MAX_PATCH_SIZE = 100_000

# ──────────────────────────────────────────────
# Zulip
# ──────────────────────────────────────────────

ZULIP_BASE_URL = "https://leanprover.zulipchat.com/api/v1"
ZULIP_EMAIL = os.getenv("ZULIP_EMAIL")  # Zulip account email
ZULIP_API_KEY = os.getenv("ZULIP_API_KEY")  # Zulip API key (Settings > Your bots)

# Channels to extract (by priority)
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

# Batch size for database inserts
BATCH_SIZE = 500

# Logs
LOG_LEVEL = "INFO"

# ──────────────────────────────────────────────
# RAG
# ──────────────────────────────────────────────

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "384"))
RAG_BATCH_SIZE = int(os.getenv("RAG_BATCH_SIZE", "256"))

# LLM backend: claude, openai, ollama
LLM_BACKEND = os.getenv("LLM_BACKEND", "claude")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
