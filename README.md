# LeanKeeper — Un agent IA natif pour Mathlib

## Vision

Créer un agent IA spécialisé, entraîné spécifiquement sur les conventions, la hiérarchie et la culture de [Mathlib](https://github.com/leanprover-community/mathlib4), capable de produire des contributions de qualité bibliothèque — pas juste des preuves qui compilent, mais du code qui passe la revue humaine.

## Contexte

### Lean et Mathlib

- **Lean** est un proof assistant et langage de programmation développé par Leonardo de Moura (Lean FRO). Si ça compile, la preuve est correcte.
- **Mathlib** est la bibliothèque communautaire de mathématiques formalisées en Lean 4 : ~210 000 théorèmes, ~100 000 définitions, ~2 millions de lignes de code, 500+ contributeurs sur 8 ans.
- Mathlib est organisée comme un **DAG de dépendances** avec une **hiérarchie de typeclasses** (`Monoid → Group → Ring → Field`, `TopologicalSpace → MetricSpace → NormedSpace`…) permettant la réutilisation automatique des preuves.

### L'IA et le theorem proving

| Projet | Organisation | Résultat clé |
|--------|-------------|--------------|
| **AlphaProof** | Google DeepMind | Médaille d'argent IMO 2024, or en 2025 |
| **Aristotle** | xAI | Médaille d'or IMO 2025 (vérification formelle Lean) |
| **Goedel-Prover-V2** | Princeton | Prouveur open-source le plus puissant, 90 % sur miniF2F |
| **Gauss** | Math, Inc. | Formalisation du PNT fort en 3 semaines |
| **HyperTree Proof Search** | Meta | 10 problèmes IMO résolus |

Tous convergent vers la même architecture : **LLM pour l'intuition + Lean pour la vérification formelle**.

## Le problème : l'IA actuelle nuit à Mathlib

### Des dumps massifs, pas des contributions

Les entreprises d'IA produisent du code Lean qui **compile** mais qui **n'est pas de qualité Mathlib** : définitions au mauvais niveau de généralité, conventions de nommage non respectées, pas d'API, code non maintenable, soumis en blocs monolithiques impossibles à reviewer.

### Conséquences concrètes (discussion Zulip, mars 2026)

- **Sébastien Gouëzel** (maintainer) : *« Si Math, Inc. formalise le théorème de Mazur de manière crappy, personne ne voudra le refaire proprement, et on n'aura jamais Mazur dans Mathlib. »*
- **Patrick Massot** (créateur du blueprint system) : *« Les entreprises d'IA vont bombarder cette zone pour la transformer en un désert radioactif. »*
- Des étudiants en master ont perdu leur sujet de mémoire après le scoop de Gauss sur le sphere packing.

### Le problème fondamental : les définitions

**Une preuve qui compile n'est pas forcément « bonne ».** Les définitions peuvent être au mauvais niveau de généralité, mal intégrées à la hiérarchie de typeclasses, sans API standard, ou sémantiquement fausses — et Lean ne prévient pas. C'est ce jugement de design que l'IA actuelle ne sait pas faire.

## La proposition : LeanKeeper

### Pourquoi c'est faisable

- Mathlib fait ~2M de lignes (~50-70M tokens) — un fine-tuning trivial pour les modèles actuels.
- Les conventions sont un **corpus fermé** et bien documenté : nommage, style, hiérarchie, patterns d'API.
- Les linters automatiques encodent déjà une partie des règles.
- Les reviews de PRs sont publiques : ~20 000+ PRs mergées sur GitHub avec commentaires.

### Le dataset d'entraînement

| Source | Contenu | Valeur |
|--------|---------|--------|
| Dépôt Git | Commits, diffs | Le *quoi* (code final) |
| PRs GitHub | Version initiale → commentaires → version finale | Le *pourquoi* (jugement de design) |
| Zulip Lean | Discussions sur les choix de définitions | Le *raisonnement* derrière les décisions |
| Linters / CI | Résultats automatiques | Les *règles* formalisées |
| Import graph | Graphe de dépendances structuré | La *topologie* de la bibliothèque |

Tout est public et extractible via les APIs GitHub et Zulip.

### Ce que LeanKeeper ferait

L'agent fonctionne comme un **bon contributeur Mathlib junior** :

1. **Reçoit** un théorème à formaliser (en langage naturel ou informel).
2. **Explore** la hiérarchie de typeclasses existante pour trouver le bon niveau de généralité.
3. **Propose** une définition intégrée à la hiérarchie, avec l'API standard.
4. **Écrit** la preuve avec les bonnes tactiques et le bon style.
5. **Vérifie** le nommage selon les conventions Mathlib.
6. **Soumet** une PR propre, ciblée (~200 lignes), prête pour la revue.

### Métrique de succès

Pas « est-ce que ça compile » (trivial) mais **« est-ce que ça passe la revue Mathlib »** — les maintainers acceptent de merger sans modifications majeures.

## Le goulot d'étranglement de Mathlib

- **~300 PRs en attente**, délai médian ~2 semaines.
- Les reviewers vérifient le **design**, pas la correction (Lean s'en charge).
- Les reviewers sont majoritairement bénévoles, avec des profils rares (expert du domaine mathématique ET de Lean/Mathlib).
- Financement récent : **10M$ de Alex Gerko** (XTX Markets) — 5M$ au Lean FRO, 5M$ à la Mathlib Initiative.


## Références

- [Mathlib GitHub](https://github.com/leanprover-community/mathlib4)
- [Mathlib Initiative](https://mathlib-initiative.org/)
- [Lean FRO](https://lean-lang.org/fro/)
- [Discussion Zulip : « The role of AI companies in large formalisation projects »](https://leanprover.zulipchat.com/#narrow/channel/113488-general/topic/The.20role.20of.20AI.20companies.20in.20large.20formalisation.20projects)
- [Kevin Buzzard — Xena Project](https://xenaproject.wordpress.com/)
- [AlphaProof (Nature, nov. 2025)](https://www.nature.com/articles/s41586-025-09833-y)
- [Aristotle (xAI)](https://arxiv.org/html/2510.01346v1)
- [Gauss (Math, Inc.)](https://www.math.inc/gauss)
- [Goedel-Prover-V2 (Princeton)](https://ai.princeton.edu/news/2025/princeton-researchers-unveil-improved-mathematical-theorem-prover-powered-ai)
- [Growing Mathlib (arXiv)](https://arxiv.org/html/2508.21593v2)
