# LeanKeeper — Vue d'ensemble (état actuel)

Synthèse des fonctionnalités, mécanismes et commandes réels de LeanKeeper. Source de vérité pour
le détail : `CLAUDE.md`, `BASE_CONTEXT.md`, `DB_ARCHITECTURE.md` et le code `leankeeper/`. Commandes
vérifiées dans `leankeeper/__main__.py`.

## 1. Vision & métrique

Agent IA spécialisé **Mathlib** (lib math de Lean 4 : ~2M lignes, ~210K théorèmes). Il prend des
preuves qui **compilent** mais sont **non-idiomatiques** (générées par IA : mauvais nommage,
généralité, API) et vise à les rendre conformes aux standards Mathlib.

**Métrique centrale :** « est-ce que ça passe la review humaine ? » — *pas* « est-ce que ça
compile ? » (Lean garantit déjà la correction).

**État réel :** le projet **évalue** une PR (review aveugle + classification + comparaison à la
vérité terrain). La **correction** existe au niveau texte (`/fix-pr`) mais sans application auto ni
compilation. La réécriture automatique de preuves reste l'objectif final non atteint.

## 2. Architecture en deux couches

### Couche données (Phase 1 — terminée)

Quatre extractors alimentent PostgreSQL (SQLAlchemy ORM, `BigInteger` pour les IDs externes, upserts
idempotents par batch de 500) :

| Extractor | Source | Mécanisme |
|-----------|--------|-----------|
| `github.py` | PRs, reviews, commentaires | GraphQL en masse + REST pour les commentaires inline (`diff_hunk`) ; retry 3× backoff ; détecte les merges Bors via `[Merged by Bors]` |
| `git.py` | commits, stats, patches | Clone **bare** de mathlib4 (`data/mathlib4.git`), parsing `git log`/`--numstat`, subprocess |
| `zulip.py` | discussions de design | API REST Zulip, pagination arrière |
| `lean.py` | ~215K déclarations | `git show HEAD:<file>` sur le bare repo (pas de working tree), regex, ~4 min |

Tables : `pull_requests`, `pr_files`, `reviews`, `review_comments`, `issue_comments`, `commits`,
`commit_files`, `zulip_channels`, `zulip_messages`, `embeddings`, + tables Lean.

### Couche RAG (Phase 2 — en cours)

- `embedder.py` — embeddings locaux **sentence-transformers** (`all-MiniLM-L6-v2`)
- `store.py` — **pgvector** : index/search/status, filtrage temporel (`before_date`) et exclusion de
  source IDs (anti-fuite pour l'éval)
- `llm.py` — backends enfichables : **Claude (défaut)**, OpenAI, Ollama
- `retriever.py` — pipeline retrieve → prompt → generate ; `build_context_md` injecte
  **`BASE_CONTEXT.md` en entier** + exemples récupérés
- `prompt.py` — prompts modes *contributor* / *reviewer*
- `eval.py` — `RAGEvaluator` : génère les fichiers de contexte d'éval, run batch, compare au réel

## 3. Commandes CLI

Toutes via `python -m leankeeper`.

**Extraction**
```bash
extract {github|github-reviews|github-files|git|git-patches|zulip|lean|all} [--update] [--since DATE]
update                              # extract des nouvelles données seulement (PLUS d'indexation RAG)
```

**Inspection**
```bash
stats                               # statistiques DB
export <table> <output_path>        # dump JSONL d'une table
lean show <name>                    # source (énoncé + preuve) d'une déclaration, via git show HEAD
```

**RAG**
```bash
rag init                            # active pgvector + crée la table embeddings
rag index [--table T] [--update]    # indexe (tout, ou une table ; --update = nouvelles lignes)
rag search "<query>" [--type T] [--limit N]
rag context "<query>" [--mode contributor|reviewer] [--limit N] [--no-project] [-o FILE]
rag chat [--mode contributor|reviewer] [--backend claude|openai|ollama]
rag eval [--limit N] [--pr N] [--backend B] [--export FILE]    # éval pilotée LLM
rag eval-context [--limit N] [--pr N] [--output DIR]           # génère les contextes, SANS LLM
rag delete [--table T] [--id ID]
rag status                          # compteurs d'embeddings
rag backfill-dates                  # remplit created_at sur embeddings existants
```

## 4. Skills (slash commands)

**Workflow évaluation / correction (cœur métier) :**

| Skill | Rôle |
|-------|------|
| `/eval-pr <N>` | Review **aveugle** → classe en 5 catégories (Naming, Generality, Style, API, Attributes) → `results/pr_N_result.md` |
| `/eval-batch` | Éval de plusieurs PRs |
| `/review-pr <N>` | Review depuis contextes pré-générés (sans comparaison ni Excel) |
| `/compare-pr <N>` | Confronte la review aveugle au réel → remplit l'Excel |
| `/fix-pr <N>` | Lit `result.md` + diffs → correction avant/après par problème, citée `BASE_CONTEXT` → `results/pr_N_fix.md`. Diff-scopé, non compilé |

**Framework « manager d'agents » :** `/install`, `/update-brain`, `/commit-changes`, `/review-mine`.

**Mécanisme d'éval.** `eval-context` génère 3 fichiers par PR :
- `_context.md` — diffs (ce que voit le reviewer)
- `_rag.md` — `BASE_CONTEXT` (conventions) + instructions reviewer. **Plus de recherche vectorielle :**
  l'éval ne s'appuie que sur les conventions, pas sur des exemples récupérés
- `_actual.md` — vérité terrain, *non lue* pendant la review aveugle

## 5. Savoir conventionnel

- **`BASE_CONTEXT.md`** — wiki canonique injecté dans l'agent. 12 sections : §0 workflow, §2 nommage,
  §3 généralité, §4 API, §5 style, §6 doc, §7 PR, §8 critères review, §9 erreurs fréquentes,
  §11 sévérité, §12 recherche de lemmes.
- **`contribute/`** — 3334 lignes de guidelines Mathlib brutes (référence).
- **`CLAUDE.md`**, **`DB_ARCHITECTURE.md`**, wiki GitHub publié.

## 6. Bibliothèques Lean locales (`lean/`, gitignoré, ~13 Go)

Projets compilables pour tester / miner : `aristotle/`, `mathematics_in_lean/`, `tutorial/` (sandbox
le moins cher). `lake` dispo (Lean 4.31). Sert à lancer `exact?`/`apply?` plutôt que deviner les noms
de lemmes (cf. `BASE_CONTEXT` §12). **Ne pas parcourir l'arbre entier.**

## 7. Limites actuelles

- **Pas de correction appliquée ni compilée** — `/fix-pr` ne voit que les **hunks tronqués**
  (2000 car/fichier), pas les fichiers complets → réécritures de preuve impossibles. Mitigation
  partielle : `lean show <name>` récupère l'énoncé + la preuve d'une déclaration existante depuis
  le bare repo (version HEAD, pas la branche de la PR).
- **mathlib4 = bare repo**, pas de working tree → pas de `lake build` direct sur mathlib4.
- Le **RAG vectoriel** a été retiré de l'`update` (plus d'indexation auto) et des **évaluations**
  (l'éval s'appuie sur `BASE_CONTEXT`, pas sur la recherche vectorielle). Il ne subsiste que pour
  `rag chat`/`rag context`, qui nécessitent une indexation manuelle (`rag index`). `declarations` et
  l'index ne sont donc plus dans le chemin critique.
