# LeanKeeper — Dataset Mathlib

Extraction et structuration des données publiques du projet [Mathlib](https://github.com/leanprover-community/mathlib4) pour l'entraînement d'un agent IA spécialisé sur les conventions Mathlib.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Éditer `config.py` :

```python
GITHUB_TOKEN = "ghp_..."       # Token GitHub (Settings > Developer settings > Personal access tokens)
ZULIP_EMAIL = "you@email.com"  # Compte Zulip Lean (https://leanprover.zulipchat.com)
ZULIP_API_KEY = "..."          # Clé API (Settings > Your bots)
```

## Usage

```bash
# Extraction GitHub (PRs, reviews, comments) — ~3-5h
python -m leankeeper extract github

# Extraction Git (commits, stats) — ~1h
python -m leankeeper extract git

# Extraction Zulip (messages) — ~2-4h
python -m leankeeper extract zulip

# Tout d'un coup (sauf patches et PR files)
python -m leankeeper extract all

# Stats de la base
python -m leankeeper stats

# Export d'une table en JSONL
python -m leankeeper export review_comments data/review_comments.jsonl
```

### Extractions optionnelles (volumineuses)

```bash
# Fichiers modifiés par PR avec patches (~20K requêtes REST, ~10h)
python -m leankeeper extract github-files

# Diffs Git complets (10-50 Go)
python -m leankeeper extract git-patches

# Diffs Git depuis une date
python -m leankeeper extract git-patches --since 2024-01-01
```

## Schéma de la base

### Sources Git
- **commits** — SHA, auteur, date, message, insertions/deletions
- **commit_files** — fichiers modifiés par commit, avec patch optionnel

### Sources GitHub
- **pull_requests** — titre, description, auteur, état, dates, branches
- **pull_request_labels** — labels par PR
- **pull_request_files** — fichiers modifiés par PR avec patches
- **reviews** — reviews globales (approved/changes_requested/commented)
- **review_comments** — commentaires inline sur le code *(le plus précieux)*
- **issue_comments** — commentaires généraux sur les PRs

### Sources Zulip
- **zulip_channels** — channels (streams) extraits
- **zulip_messages** — messages avec channel, topic, auteur, contenu markdown

### Sources Lean *(à venir)*
- **declarations** — théorèmes, définitions, instances, classes
- **imports** — graphe de dépendances entre fichiers
- **typeclass_instances** — instances de typeclasses
- **typeclass_parents** — hiérarchie des typeclasses

## Structure du projet

```
leankeeper/
├── __init__.py
├── __main__.py          # CLI
├── config.py            # Configuration
├── requirements.txt
├── models/
│   ├── __init__.py
│   └── database.py      # Modèles SQLAlchemy
├── extractors/
│   ├── __init__.py
│   ├── github.py        # Extracteur GitHub (GraphQL + REST)
│   ├── git.py           # Extracteur Git (commits, diffs)
│   └── zulip.py         # Extracteur Zulip (messages)
└── data/
    └── leankeeper.db    # Base SQLite (générée)
```

## Licence

Apache 2.0 — aligné avec la licence de Mathlib.
