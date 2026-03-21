# LeanKeeper — Roadmap complète

> Un agent IA natif pour Mathlib, entraîné pour produire des contributions de qualité bibliothèque.

---

## Vue d'ensemble

| Phase | Nom | Livrable |
|-------|-----|-------|---------------|----------|
| 1 | Dataset | Dataset public sur Hugging Face |
| 2 | Analyse et benchmark | Benchmark "Mathlib Review Prediction" |
| 3 | Prototype agent | Agent capable de générer des PRs basiques |
| 4 | Boucle de feedback | Agent intégré au workflow Mathlib |
| 5 | Agent reviewer | Assistant de review pour les maintainers |
| 6 | Passage à l'échelle | Agent autonome, évalué par taux de merge |
| 7 | Pérennisation | Gouvernance, financement durable |

---


## Phase 1 — Dataset

### Objectif

Constituer un jeu de données structuré à partir de l'intégralité des données publiques du projet Mathlib, exploitable pour l'entraînement d'un agent IA.

### Sous-phases

**1.1 — Extraction des données brutes**

| Source | Méthode | Volume |
|--------|---------|--------|
| Git (commits, diffs) | `git clone --mirror` + export | 10-50 Go brut |
| GitHub PRs + reviews | API GraphQL | 2-5 Go |
| Zulip (messages, topics) | API Zulip + archive HTML | 500 Mo - 1 Go |
| Déclarations Lean | Build Mathlib + extraction API | 200 Mo |
| Graphe d'imports + typeclasses | `lake exe graph` + parsing | 50 Mo |

**1.2 — Nettoyage et structuration**

- Parsing des diffs en structures exploitables.
- Résolution des liens PR ↔ commit ↔ review comment.
- Extraction des threads Zulip liés à des PRs spécifiques.
- Déduplication et normalisation.

**1.3 — Construction des paires d'entraînement**

| Type | Description | Volume estimé |
|------|-------------|---------------|
| PR initiale → feedback → PR finale | La paire la plus précieuse | ~5 000 paires |
| Question "Is there code for X?" → réponse | Navigation dans Mathlib | ~2 000 paires |
| Définition → API complète | Patterns d'API standard | ~3 000 paires |
| Code trop spécifique → code généralisé | Refactorings de généralité | ~1 000 paires |
| Code non-idiomatique → code idiomatique | Style et conventions | ~2 000 paires |

**1.4 — Publication**

- Publication sur Hugging Face Datasets avec documentation complète.
- Article de blog expliquant la méthodologie.
- Annonce sur le Zulip Lean.

### Livrables

- Dataset brut (~15-55 Go) sur GCS/S3.
- Dataset traité (~3 Go) sur Hugging Face.
- Documentation du schéma de données.
- Scripts d'extraction reproductibles (repo GitHub public).

### Infrastructure requise

- Machine avec ~100 Go de disque et ~16 Go RAM.
- Token GitHub avec permissions de lecture.
- Compte Zulip Lean.
- Lean 4 + Mathlib installés (pour l'extraction des déclarations).

---

## Phase 2 — Analyse et benchmark

### Objectif

Comprendre les données, identifier les patterns, et créer un benchmark objectif pour évaluer la qualité "Mathlib-style".

### Actions

**2.1 — Analyse exploratoire**

- Distribution des types de commentaires de review (nommage, généralité, style, API manquante, performance...).
- Cartographie de la hiérarchie de typeclasses comme graphe interactif.
- Identification des zones de Mathlib les plus et moins couvertes.
- Analyse des temps de review par domaine mathématique.
- Profils de reviewers : qui review quoi, quels patterns de feedback.

**2.2 — Taxonomie des commentaires de review**

Classifier les commentaires en catégories actionnables :

| Catégorie | Exemple | Automatisable ? |
|-----------|---------|-----------------|
| Nommage | "Should be `mul_comm` not `comm_mul`" | Oui |
| Généralité | "This only needs `CommMonoid`" | Partiellement |
| API manquante | "Missing `_iff` lemma" | Oui |
| Style de preuve | "Use `simp` instead of `rw` chain" | Oui |
| Design de définition | "This should be a typeclass, not a def" | Difficile |
| Mathématique | "The proof strategy should use X instead" | Non (pour l'instant) |

**2.3 — Benchmark "Mathlib Review Prediction"**

Créer un benchmark standardisé :

- **Tâche 1 — Prédiction de nommage :** étant donné un type signature, prédire le nom Mathlib correct.
- **Tâche 2 — Détection de sur-spécialisation :** étant donné un théorème, identifier si les hypothèses peuvent être affaiblies.
- **Tâche 3 — Complétion d'API :** étant donné une nouvelle définition, générer les lemmes d'API attendus.
- **Tâche 4 — Prédiction de review :** étant donné une PR, prédire les commentaires du reviewer.
- **Tâche 5 — Placement dans la hiérarchie :** étant donné un nouveau concept, identifier où il s'insère dans le graphe de typeclasses.

### Livrables

- Rapport d'analyse (publié en tant qu'article ou blog post).
- Benchmark publié avec baselines (GPT-4, Claude, modèles code open source).
- Taxonomie des commentaires de review.

---

## Phase 3 — Prototype agent 

### Objectif

Construire un premier agent capable de générer des PRs Mathlib basiques qui ne soient pas immédiatement rejetées.

### Architecture

```
                    ┌─────────────────────┐
                    │   Entrée utilisateur │
                    │  (théorème informel) │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Module Recherche   │
                    │  (RAG sur Mathlib)   │
                    │  - Lemmes proches    │
                    │  - Typeclasses       │
                    │  - Conventions       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Module Génération   │
                    │  (LLM fine-tuné)     │
                    │  - Définition        │
                    │  - Preuve            │
                    │  - API lemmes        │
                    │  - Nommage           │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Module Vérification │
                    │  - Lean compiler     │
                    │  - Linters Mathlib   │
                    │  - Auto-review       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Module Formatage   │
                    │  - Style Mathlib     │
                    │  - Docstrings        │
                    │  - Import minimal    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │       Sortie         │
                    │   PR prête à review  │
                    └─────────────────────┘
```

### Sous-phases

**3.1 — RAG sur Mathlib**

- Indexer toutes les déclarations Mathlib avec embeddings.
- Permettre la recherche par type signature (pas juste par nom).
- Indexer la hiérarchie de typeclasses comme graphe navigable.
- Intégrer les conventions de nommage comme contraintes.

**3.2 — Fine-tuning du modèle de génération**

- Base : modèle code open source (CodeLlama, DeepSeek-Coder, ou Qwen-Coder).
- Fine-tuning sur les paires d'entraînement de la Phase 1.
- Entraînement en plusieurs étapes :
  1. Pré-entraînement sur tout le code Mathlib (compréhension du style).
  2. Fine-tuning sur les paires PR→review→PR finale (apprentissage du jugement).
  3. RLHF/DPO avec les commentaires de review comme signal de récompense.

**3.3 — Pipeline de vérification**

- Compilation Lean automatique de chaque sortie.
- Exécution des linters Mathlib.
- Vérification du nommage par rapport aux conventions.
- Vérification que les imports sont minimaux (`#min_imports`).
- Auto-review : le modèle critique sa propre sortie avant soumission.

**3.4 — Évaluation sur le benchmark**

- Mesurer les performances sur le benchmark de la Phase 2.
- Comparer avec les baselines.
- Identifier les points faibles.

### Livrables

- Agent prototype fonctionnel (CLI ou API).
- Résultats sur le benchmark.
- Repo GitHub public avec le code de l'agent.

### Infrastructure requise

- GPU pour fine-tuning : 4-8x A100 80Go pendant 1-2 semaines (~10-30K€ en cloud).
- Serveur Lean pour la vérification continue.
- CI/CD pour le pipeline de test.

---

## Phase 4 — Boucle de feedback avec la communauté (mois 8-10)

### Objectif

Intégrer l'agent dans le workflow réel de Mathlib, avec des humains dans la boucle, et itérer.

### Actions

**4.1 — Test sur des PRs réelles**

- Sélectionner 20-30 lemmes manquants identifiés dans les issues Mathlib (label `easy`, `good first issue`).
- Générer les PRs avec l'agent.
- Les soumettre à la review des maintainers **en toute transparence** (marquées comme générées par LeanKeeper).
- Collecter le feedback structuré.

**4.2 — Itération sur le modèle**

- Intégrer le feedback des reviewers comme nouvelles données d'entraînement.
- Affiner le modèle sur les erreurs récurrentes.
- Améliorer le module de recherche RAG si le modèle rate des lemmes existants.
- Ajuster les heuristiques de généralité.

**4.3 — Mode assistant**

Plutôt que de soumettre des PRs autonomes, proposer l'agent comme **assistant** pour les contributeurs humains :

- Un contributeur humain travaille sur une formalisation.
- Il demande à LeanKeeper : "quel est le bon niveau de généralité pour ce lemme ?"
- LeanKeeper analyse la hiérarchie et propose des options.
- Le contributeur choisit et LeanKeeper génère le code.

C'est exactement ce que Chris Birkbeck décrivait dans la discussion Zulip comme le workflow idéal.

### Livrables

- 20-30 PRs soumises à Mathlib avec résultats documentés.
- Taux d'acceptation mesuré (objectif : >30% sans modifications majeures).
- Mode assistant déployé (VS Code extension ou bot Zulip).
- Rapport de feedback de la communauté.

### Métrique clé

**Taux de merge sans réécriture majeure.** Si un reviewer doit réécrire >50% du code, c'est un échec. Si les modifications sont mineures (nommage, un import en trop), c'est un succès.

---

## Phase 5 — Agent reviewer

### Objectif

Inverser la direction : au lieu de générer du code, aider les reviewers à traiter la file d'attente plus vite.

### Pourquoi

C'est peut-être le plus grand impact possible à court terme. Le goulot principal de Mathlib n'est pas le manque de contributions, c'est le manque de reviewers. Un agent qui fait un premier tri et prépare un rapport structuré pour le reviewer humain pourrait doubler le débit de review.

### Actions

**5.1 — Auto-review automatique**

Pour chaque nouvelle PR soumise à Mathlib, LeanKeeper produit un rapport :

```
## LeanKeeper Auto-Review

### Nommage
✅ 12/14 noms suivent les conventions
⚠️ `comm_prod_sum` → devrait être `prod_sum_comm` (convention: l'opération en dernier)
⚠️ `IsFinite_of_foo` → devrait être `Foo.isFinite` (convention: namespace dot notation)

### Généralité
⚠️ `theorem bar (R : Field)` → les hypothèses n'utilisent que CommRing.
   Suggestion: généraliser à CommRing.

### API
⚠️ Nouvelle structure `FooBar` sans lemme `ext_iff`. Suggestion d'ajout.

### Imports
⚠️ 2 imports non utilisés détectés.
✅ Pas de régression dans le graphe d'imports transitifs.

### Style
✅ Docstrings présentes sur toutes les déclarations publiques.
⚠️ Preuve de `baz` : chaîne de 8 `rw` → envisager `simp` avec lemmes listés.

### Résumé
Score estimé : 7/10 — modifications mineures probables.
Domaines à vérifier par un humain : choix de généralité pour `bar`.
```

**5.2 — Triage automatique**

- Classer les PRs par complexité de review estimée.
- Router vers le bon reviewer selon le domaine mathématique.
- Identifier les PRs triviales qui pourraient être auto-mergées (pure API gap filling, nommage correct, linters passent).

**5.3 — Intégration CI**

- GitHub Action qui exécute LeanKeeper sur chaque PR.
- Rapport posté comme commentaire sur la PR.
- Les maintainers peuvent invoquer des vérifications supplémentaires.

### Livrables

- Bot GitHub fonctionnel posté sur les PRs Mathlib.
- Réduction mesurable du temps de review.
- Feedback des maintainers sur l'utilité.

---

## Phase 6 — Passage à l'échelle

### Objectif

Faire de LeanKeeper un contributeur fiable et autonome, capable de combler les trous de Mathlib de manière systématique.

### Actions

**6.1 — Identification automatique des lacunes**

- Scanner la littérature mathématique (manuels, articles) et identifier les théorèmes qui devraient être dans Mathlib mais n'y sont pas.
- Prioriser par : nombre de dépendants potentiels, difficulté estimée, présence des prérequis dans Mathlib.
- Croiser avec la liste "missing undergraduate mathematics" maintenue par la communauté.

**6.2 — Génération à grande échelle**

- Viser 50-100 PRs par mois, chacune de ~200 lignes.
- Chaque PR est auto-reviewée, vérifiée par les linters, et soumise avec une description claire.
- Workflow : l'agent annonce ses intentions sur Zulip → attend 1 semaine pour d'éventuels conflits → génère → soumet.

**6.3 — Apprentissage continu**

- Chaque review humaine (acceptée ou rejetée) devient une donnée d'entraînement.
- Ré-entraînement périodique du modèle.
- Le modèle s'adapte à l'évolution des conventions Mathlib (Mathlib évolue vite).

**6.4 — Extension aux prérequis manquants**

- Quand l'agent identifie qu'un théorème nécessite un prérequis absent de Mathlib, il le formalise d'abord.
- Construction bottom-up : combler les fondations avant de monter.

### Livrables

- 500+ PRs mergées dans Mathlib sur 6 mois.
- Taux de merge >60% sans modifications majeures.
- Rapport d'impact sur la croissance de Mathlib.

### Infrastructure requise

- Cluster GPU dédié pour l'inférence continue.
- Serveur Lean pour la compilation continue (~50 vérifications/jour).
- Monitoring et alerting.

---
