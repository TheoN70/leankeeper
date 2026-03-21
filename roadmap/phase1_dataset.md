# LeanKeeper — Phase 1 : Extraction du dataset Mathlib

## Objectif

Constituer un jeu de données structuré à partir de l'intégralité des données publiques du projet Mathlib (GitHub + Zulip + Git), exploitable pour l'entraînement d'un agent IA spécialisé sur les conventions et la qualité Mathlib.

---

## 1. Inventaire des sources de données

### 1.1 Dépôt Git — `leanprover-community/mathlib4`

| Donnée | Volume estimé | Méthode d'extraction |
|--------|---------------|---------------------|
| Historique complet des commits | ~80 000 commits | `git clone --mirror` |
| Diffs par commit | ~80 000 diffs | `git log -p` / `git diff` |
| Messages de commit | ~80 000 messages | `git log --format` |
| Arbre des fichiers par version | snapshots | `git show` / `git checkout` |
| Blâme par fichier (dernier auteur par ligne) | ~5 000 fichiers .lean | `git blame` |

**Dépôts annexes à cloner :**
- `leanprover-community/mathlib4` (principal)
- `leanprover-community/batteries` (dépendance directe)
- `leanprover/lean4` (le compilateur, pour contexte)

### 1.2 API GitHub — PRs et reviews

| Donnée | Volume estimé | Endpoint API |
|--------|---------------|-------------|
| Pull Requests (métadonnées) | ~20 000+ PRs | `GET /repos/{repo}/pulls?state=all` |
| Corps des PRs (description markdown) | ~20 000 | inclus dans PR |
| Review comments (inline sur le code) | ~100 000+ | `GET /repos/{repo}/pulls/{id}/comments` |
| Issue comments (discussion générale) | ~50 000+ | `GET /repos/{repo}/issues/{id}/comments` |
| Reviews (approve/request changes) | ~40 000+ | `GET /repos/{repo}/pulls/{id}/reviews` |
| Labels par PR | ~20 000 | inclus dans PR |
| Fichiers modifiés par PR | ~20 000 | `GET /repos/{repo}/pulls/{id}/files` |
| Résultats CI (status checks) | ~20 000 | `GET /repos/{repo}/commits/{sha}/status` |
| Issues (bugs, feature requests) | ~5 000+ | `GET /repos/{repo}/issues` |

**Contraintes API GitHub :**
- Rate limit : 5 000 requêtes/heure avec token authentifié.
- Pagination : max 100 résultats par page.
- Pour ~20 000 PRs avec reviews/comments : prévoir ~200 000 requêtes → ~40 heures à plein régime.
- Alternative : **GitHub GraphQL API** — plus efficace, permet de batacher les requêtes.
- Alternative bis : **GH Archive** (gharchive.org) pour les événements historiques.

### 1.3 Zulip — Discussions communautaires

| Donnée | Volume estimé | Endpoint API |
|--------|---------------|-------------|
| Messages publics | ~500 000+ messages | `GET /messages` avec filtres |
| Channels pertinents | ~20 channels | `GET /streams` |
| Topics (fils de discussion) | ~10 000+ | `GET /users/me/{stream_id}/topics` |
| Réactions (emoji) | variable | inclus dans messages |

**Channels prioritaires :**
- `#general` — discussions de design, débats
- `#new members` — questions de débutants (utile pour le style pédagogique)
- `#mathlib4` — discussions techniques spécifiques à Mathlib
- `#FLT` — projet Fermat (exemple de formalisation à grande échelle)
- `#Machine Learning for Theorem Proving` — méta-discussions sur l'IA
- `#Is there code for X?` — recherches de lemmes existants (très utile pour la déduplication)

**Archive publique alternative :**
- `leanprover-community.github.io/archive/` — archive HTML statique, scrapable.

### 1.4 Données structurelles de Mathlib

| Donnée | Méthode |
|--------|---------|
| Graphe d'imports (DAG complet) | `lake exe graph` / parsing des `import` |
| Hiérarchie de typeclasses | extraction depuis les fichiers `Defs.lean` |
| Résultats des linters | exécution des linters Mathlib |
| Statistiques de compilation (temps par fichier) | CI logs |
| Declarations (théorèmes, définitions, instances) | `Lean.Environment` API ou parsing |

---

## 2. Schéma de données cible

### 2.1 Table `commits`

```
commit_sha: string (PK)
author_name: string
author_email: string
date: datetime
message: string
files_changed: list[string]
insertions: int
deletions: int
```

### 2.2 Table `pull_requests`

```
pr_number: int (PK)
title: string
body: string (markdown)
author: string
state: enum (merged, closed, open)
created_at: datetime
merged_at: datetime | null
merge_commit_sha: string | null
labels: list[string]
files_changed: list[{filename, patch, additions, deletions}]
base_branch: string
head_branch: string
```

### 2.3 Table `reviews`

```
review_id: int (PK)
pr_number: int (FK)
author: string
state: enum (approved, changes_requested, commented)
body: string
submitted_at: datetime
```

### 2.4 Table `review_comments` (le plus précieux)

```
comment_id: int (PK)
pr_number: int (FK)
author: string
body: string (markdown)
path: string (fichier commenté)
line: int
diff_hunk: string (contexte du diff)
created_at: datetime
in_reply_to_id: int | null
```

### 2.5 Table `zulip_messages`

```
message_id: int (PK)
channel: string
topic: string
sender: string
content: string (markdown)
timestamp: datetime
reactions: list[{emoji, count}]
```

### 2.6 Table `declarations` (extraite du code Lean)

```
name: string (PK, ex: "Finset.sum_comm")
kind: enum (theorem, def, instance, lemma, class, structure)
file: string
line: int
type_signature: string
docstring: string | null
imports: list[string] (dépendances directes)
typeclass_instances: list[string]
```

---

## 3. Pipeline d'extraction

### Étape 1 — Clone Git (jour 1)

```bash
# Clone miroir complet
git clone --mirror https://github.com/leanprover-community/mathlib4.git
cd mathlib4.git

# Export de tous les commits en JSON
git log --all --pretty=format:'{
  "sha": "%H",
  "author": "%an",
  "email": "%ae",
  "date": "%aI",
  "message": "%s"
}' > commits.jsonl

# Export des diffs par commit (volumineux, ~10-50 Go)
git log --all -p --format="COMMIT:%H" > full_diffs.txt
```

**Durée estimée :** 1-2 heures (clone + export).

### Étape 2 — Extraction GitHub API (jours 2-4)

```python
"""
Script d'extraction des PRs et reviews via l'API GitHub.
Utilise l'API GraphQL pour minimiser le nombre de requêtes.
"""
import requests
import json
import time
from pathlib import Path

GITHUB_TOKEN = "ghp_..."
REPO = "leanprover-community/mathlib4"
OUTPUT_DIR = Path("data/github")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

# Requête GraphQL — récupère 50 PRs avec reviews et comments par appel
QUERY = """
query($cursor: String) {
  repository(owner: "leanprover-community", name: "mathlib4") {
    pullRequests(first: 50, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        number
        title
        body
        author { login }
        state
        createdAt
        mergedAt
        mergeCommit { oid }
        labels(first: 10) { nodes { name } }
        files(first: 100) {
          nodes { path additions deletions }
        }
        reviews(first: 50) {
          nodes {
            author { login }
            state
            body
            submittedAt
            comments(first: 50) {
              nodes {
                body
                path
                line
                diffHunk
                createdAt
                author { login }
              }
            }
          }
        }
        comments(first: 50) {
          nodes {
            author { login }
            body
            createdAt
          }
        }
      }
    }
  }
}
"""

def fetch_all_prs():
    cursor = None
    all_prs = []
    page = 0

    while True:
        variables = {"cursor": cursor}
        response = requests.post(
            GRAPHQL_URL,
            headers=HEADERS,
            json={"query": QUERY, "variables": variables},
        )

        if response.status_code == 403:
            # Rate limited — attendre
            reset = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - time.time(), 10)
            print(f"Rate limited, waiting {wait:.0f}s...")
            time.sleep(wait)
            continue

        data = response.json()
        prs_data = data["data"]["repository"]["pullRequests"]
        all_prs.extend(prs_data["nodes"])

        page += 1
        print(f"Page {page}: {len(all_prs)} PRs récupérées")

        # Sauvegarde incrémentale toutes les 10 pages
        if page % 10 == 0:
            save_checkpoint(all_prs, page)

        if not prs_data["pageInfo"]["hasNextPage"]:
            break

        cursor = prs_data["pageInfo"]["endCursor"]
        time.sleep(1)  # Politesse

    return all_prs

def save_checkpoint(prs, page):
    path = OUTPUT_DIR / f"prs_checkpoint_{page}.json"
    with open(path, "w") as f:
        json.dump(prs, f, indent=2)

if __name__ == "__main__":
    prs = fetch_all_prs()
    with open(OUTPUT_DIR / "all_prs.json", "w") as f:
        json.dump(prs, f, indent=2)
    print(f"Terminé: {len(prs)} PRs extraites")
```

**Durée estimée :** 3-5 heures d'exécution (GraphQL est plus rapide que REST).
**Volume estimé :** ~2-5 Go de JSON.

### Étape 3 — Extraction Zulip (jours 3-4)

```python
"""
Extraction des messages Zulip depuis l'archive publique.
Alternative : API Zulip avec compte enregistré.
"""
import requests
from pathlib import Path

ZULIP_BASE = "https://leanprover.zulipchat.com/api/v1"
ZULIP_EMAIL = "..."  # Créer un compte sur le Zulip
ZULIP_KEY = "..."
OUTPUT_DIR = Path("data/zulip")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Channels prioritaires
CHANNELS = [
    "general",
    "mathlib4",
    "new members",
    "FLT",
    "Machine Learning for Theorem Proving",
    "Is there code for X?",
    "maths",
    "lean4",
]

def fetch_messages(stream, topic=None, anchor="newest", num_before=1000):
    params = {
        "anchor": anchor,
        "num_before": num_before,
        "num_after": 0,
        "narrow": json.dumps([
            {"operator": "stream", "operand": stream},
        ]),
    }
    if topic:
        params["narrow"] = json.dumps([
            {"operator": "stream", "operand": stream},
            {"operator": "topic", "operand": topic},
        ])

    response = requests.get(
        f"{ZULIP_BASE}/messages",
        auth=(ZULIP_EMAIL, ZULIP_KEY),
        params=params,
    )
    return response.json()
```

**Alternative plus simple :** scraper l'archive HTML publique sur `leanprover-community.github.io/archive/`.

**Durée estimée :** 2-4 heures.
**Volume estimé :** ~500 Mo - 1 Go.

### Étape 4 — Extraction des déclarations Lean (jours 5-6)

```bash
# Cloner Mathlib et builder
git clone https://github.com/leanprover-community/mathlib4.git
cd mathlib4
lake exe cache get
lake build

# Extraire toutes les déclarations via un script Lean
lake env lean --run scripts/extract_declarations.lean > declarations.json

# Extraire le graphe d'imports
lake exe graph --to Mathlib mathlib_imports.dot
```

**Script Lean pour l'extraction (à écrire) :**
- Itérer sur `Lean.Environment.constants`
- Pour chaque constante : nom, type, docstring, fichier source, ligne
- Exporter les instances de typeclasses
- Exporter la hiérarchie (parent classes)

**Durée estimée :** 1-2 jours (compilation Mathlib ~2h + script d'extraction).

### Étape 5 — Construction des paires d'entraînement (jours 7-10)

C'est l'étape clé : transformer les données brutes en exemples d'entraînement.

**Type 1 — Paires "PR initiale → PR après review"**

Pour chaque PR avec `changes_requested` puis `approved` :
```json
{
  "input": {
    "pr_description": "...",
    "code_initial": "diff de la première version",
    "context": "fichiers Mathlib environnants"
  },
  "feedback": [
    "commentaire reviewer 1: 'ce lemme devrait être pour CommMonoid'",
    "commentaire reviewer 2: 'nommage: mul_comm pas comm_mul'"
  ],
  "output": {
    "code_final": "diff de la version mergée"
  }
}
```

**Type 2 — Paires "question → emplacement dans Mathlib"**

Depuis le Zulip `#Is there code for X?` :
```json
{
  "question": "Is there a lemma saying that a finite product of noetherian rings is noetherian?",
  "answer": "Mathlib.RingTheory.Noetherian.Pi",
  "declaration": "instance Finset.isNoetherian_pi ..."
}
```

**Type 3 — Paires "définition → API complète"**

Pour chaque structure/classe dans Mathlib, extraire le pattern :
```json
{
  "definition": "structure FooBar where ...",
  "api_lemmas": [
    "FooBar.mk", "FooBar.ext", "FooBar.ext_iff",
    "FooBar_of_bar", "FooBar.toBar", "FooBar.map"
  ],
  "naming_convention": "explication du pattern"
}
```

**Type 4 — Paires "théorème au mauvais niveau → théorème au bon niveau"**

Depuis l'historique des refactorings dans Mathlib :
```json
{
  "before": "theorem foo (R : Field) : ...",
  "reviewer_comment": "This only needs CommRing",
  "after": "theorem foo (R : CommRing) : ..."
}
```

---

## 4. Stockage et format

### Format de sortie

- **Données brutes :** JSON / JSONL, stockées sur GCS ou S3.
- **Dataset structuré :** Parquet (efficace pour les requêtes analytiques).
- **Publication :** Hugging Face Datasets (pour la communauté).

### Structure des fichiers

```
leankeeper-dataset/
├── raw/
│   ├── git/
│   │   ├── commits.jsonl
│   │   └── diffs/           (un fichier par commit)
│   ├── github/
│   │   ├── pull_requests.json
│   │   ├── reviews.json
│   │   └── review_comments.json
│   ├── zulip/
│   │   ├── general.json
│   │   ├── mathlib4.json
│   │   └── ...
│   └── lean/
│       ├── declarations.json
│       ├── import_graph.json
│       └── typeclass_hierarchy.json
├── processed/
│   ├── pr_review_pairs.parquet
│   ├── naming_conventions.parquet
│   ├── api_patterns.parquet
│   ├── generalization_examples.parquet
│   └── zulip_qa_pairs.parquet
├── metadata/
│   ├── extraction_log.json
│   └── schema.md
└── README.md
```

### Volume total estimé

| Source | Brut | Traité |
|--------|------|--------|
| Git (commits + diffs) | ~10-50 Go | ~2 Go (diffs pertinents) |
| GitHub (PRs + reviews) | ~2-5 Go | ~500 Mo |
| Zulip | ~500 Mo - 1 Go | ~200 Mo |
| Lean (déclarations) | ~200 Mo | ~50 Mo |
| **Total** | **~15-55 Go** | **~3 Go** |

---

## 5. Planning

| Jour | Tâche | Livrable |
|------|-------|----------|
| J1 | Clone Git + export commits/diffs | `raw/git/` |
| J2-J3 | Script extraction GitHub API (GraphQL) | `raw/github/` |
| J3-J4 | Script extraction Zulip | `raw/zulip/` |
| J5-J6 | Build Mathlib + extraction déclarations Lean | `raw/lean/` |
| J7-J8 | Construction des paires PR initiale → finale | `processed/pr_review_pairs.parquet` |
| J9 | Construction paires nommage / API / généralisation | `processed/*.parquet` |
| J10 | Validation, documentation, README | Dataset complet |
| J11-J12 | Publication Hugging Face + article de blog | Dataset public |

**Durée totale : ~2 semaines** (une personne à temps plein).

---

## 6. Considérations légales et éthiques

### Licences

- **Mathlib** : Apache 2.0 — libre d'utilisation, y compris commerciale.
- **Discussions Zulip** : contenu public, mais vérifier les conditions d'utilisation de Zulip.
- **Données GitHub** : les métadonnées de PRs/issues sont accessibles via API mais soumises aux ToS GitHub.

### Éthique

- **Anonymisation optionnelle** : les noms des contributeurs sont publics, mais on peut anonymiser si le dataset est utilisé pour de l'analyse comportementale.
- **Respect de la communauté** : publier le dataset et la méthodologie ouvertement, proposer à la communauté Mathlib de review avant publication.
- **Citation** : créditer explicitement tous les contributeurs Mathlib et le projet.

### Alignement avec la communauté

Avant de publier, partager le plan sur le Zulip Lean (`#general`) pour :
- Obtenir du feedback sur le schéma de données.
- Identifier des sources de données manquées.
- S'assurer que la communauté est à l'aise avec l'utilisation prévue.
- Potentiellement recruter des contributeurs.

---

## 7. Prochaines étapes après le dataset

1. **Analyse exploratoire** : statistiques sur les patterns de review (quels types de commentaires reviennent le plus souvent ?), cartographie de la hiérarchie de typeclasses, identification des zones les plus et moins couvertes.
2. **Benchmark de qualité** : créer un benchmark "Mathlib Review Prediction" — étant donné une PR, prédire les commentaires du reviewer.
3. **Fine-tuning** : entraîner un modèle sur les paires d'entraînement.
4. **Évaluation** : soumettre des PRs générées par l'agent et mesurer le taux d'acceptation par les reviewers humains.
