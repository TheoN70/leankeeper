# leankeeper (package)

Python package implémentant LeanKeeper. Vision, conventions Mathlib et liste complète
des commandes CLI : voir le [`CLAUDE.md` racine](../CLAUDE.md). Ce fichier est une carte
de navigation interne au package.

## Commandes essentielles

```bash
pip install -r requirements.txt      # setup (depuis ce dossier)
python -m leankeeper extract all     # extraction complète
python -m leankeeper update          # update incrémental (extract seul ; indexation RAG séparée)
python -m leankeeper lean show <name> # énoncé + preuve d'une déclaration (git show HEAD)
python -m leankeeper rag search "…"  # recherche sémantique
python -m leankeeper stats           # inspection DB
```

Pas de suite de tests automatisée dans le repo — validation manuelle via les commandes CLI.

## Modules

| Fichier | Rôle |
|---------|------|
| `__main__.py` | Point d'entrée CLI : sous-commandes `extract`, `update`, `stats`, `export`, `lean`, `rag` |
| `config.py` | Config centrale : chemins, URLs/tokens API, rate limits. Credentials via env vars |
| `models/database.py` | Modèles ORM SQLAlchemy + `init_db()`. `BigInteger` pour IDs externes |
| `extractors/github.py` | PRs/reviews/commentaires via GraphQL + REST. Retry + détection Bors |
| `extractors/git.py` | Commits/stats/patches depuis le repo bare mathlib4 (subprocess) |
| `extractors/zulip.py` | Channels + messages via API REST Zulip (pagination arrière) |
| `extractors/lean.py` | Parse les déclarations Lean 4 (regex, ~215K decls) ; backend des requêtes `lean show`/`lean search` et de `rag fetch-file` (fichier entier au commit d'une PR via `git show`) |
| `rag/embedder.py` | Génération d'embeddings locale (sentence-transformers) |
| `rag/store.py` | Opérations pgvector : indexation, recherche, statut |
| `rag/llm.py` | Backends LLM enfichables : Claude (défaut), OpenAI, Ollama |
| `rag/retriever.py` | Pipeline RAG : retrieve → build prompt → generate |
| `rag/prompt.py` | System prompts modes contributor / reviewer |
| `rag/eval.py` | Évaluation du RAG sur PRs historiques |

## Fichiers critiques

- `config.py` — toute la config ; un mauvais env var casse l'extraction silencieusement.
- `models/database.py` — schéma DB partagé par tous les extractors. Voir [`../DB_ARCHITECTURE.md`](../DB_ARCHITECTURE.md).

## Docs

Brain partagé : [`../docs/`](../docs/) (glossaire, ADRs).
