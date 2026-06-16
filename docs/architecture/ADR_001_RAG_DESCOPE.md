# ADR-001 : Retirer le RAG vectoriel de l'update et des évaluations

## Statut

Accepté

## Date

2026-06-16

## Contexte

Le système RAG (embeddings sentence-transformers + recherche pgvector) était branché sur deux
chemins :
- l'**indexation** automatique à chaque `update` (6 tables, dont ~215K déclarations Lean) ;
- la **récupération d'exemples** dans les évaluations de PR (`rag eval`, `/eval-pr` via
  `eval-context`), injectés dans `pr_<N>_rag.md`.

Deux constats l'ont remis en cause :
1. Les **conventions Mathlib** (le savoir porteur de l'éval) sont déjà injectées en entier via
   `BASE_CONTEXT.md` — la recherche vectorielle dessus est redondante et non-déterministe.
2. Les exemples effectivement récupérés à l'éval étaient du **bruit** (similarité ~0.51 : « bors
   merge », « Thanks! »), n'améliorant pas la review.
3. La recherche de lemmes existants est déléguée aux **outils Mathlib** (Loogle, `exact?`/`apply?`,
   cf. `BASE_CONTEXT` §12), rendant l'index des déclarations inutile.

## Décision

- `update` ne fait plus d'indexation : il est **extract-only**. L'indexation reste possible à la main
  via `rag index` (pour `rag chat`).
- Les évaluations n'utilisent **plus la recherche vectorielle**. La review s'appuie sur
  `BASE_CONTEXT.md` (conventions). `build_reviewer_prompt()` rend la section « Retrieved examples »
  optionnelle ; l'éval l'appelle sans exemples.
- `declarations` est retiré de `SOURCE_MODELS` (plus indexé du tout).

## Conséquences

- **Positives** : `update` nettement plus rapide et léger ; éval déterministe ancrée sur les
  conventions ; moins de poids mort (index déclarations) ; surface RAG réduite à `rag chat`/`context`.
- **Négatives / coûts** : `rag chat` nécessite désormais une indexation manuelle explicite ; les
  embeddings de déclarations déjà en base restent jusqu'à un `rag delete --table declarations`.
- **Contraintes futures** : si on veut de la recherche floue d'exemples à l'éval, il faudra la
  re-justifier par une mesure (le bruit observé ne la justifiait pas).

## Alternatives considérées

- **Garder le RAG partout** — écarté : conventions déjà en contexte, exemples récupérés bruités.
- **Wiki ordonné + index structuré maison des déclarations** — partiellement retenu : `BASE_CONTEXT`
  est le wiki canonique ; mais l'index de recherche est délégué aux outils Mathlib plutôt que
  reconstruit (toujours à jour, maintenu par la communauté). La lecture ciblée d'une déclaration
  existante est fournie par `lean show <name>`, et le fichier entier au commit d'une PR par
  `rag fetch-file <pr> <filepath>` (via `merge_commit_sha` + `git show`, sans embeddings).
