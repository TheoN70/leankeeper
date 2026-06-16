Commite les changements en cours dans chaque projet enregistre.

## Projets a commiter

Lis `.claude/projects.json` pour recuperer la liste des projets enregistres. Si le fichier n'existe pas, indique a l'utilisateur de lancer `/install` d'abord.

IMPORTANT :
- Le repo racine contient UNIQUEMENT le framework Claude (`.claude/`, `docs/`, `README.md`). Les projets enregistres sont des repos git imbriques avec leur propre historique.
- Cette commande s'applique UNIQUEMENT aux projets enregistres. Ne JAMAIS commiter dans le repo racine.
- Toutes les commandes git doivent etre executees via `git -C <projet> ...`.

## Pour chaque projet enregistre

Execute la procedure ci-dessous successivement sur chaque projet :

1. Lance `git -C <projet> status` pour voir les fichiers modifies et non-suivis
2. Si aucun changement : passe au projet suivant (affiche "Aucun changement dans `<projet>`")
3. Lance `git -C <projet> diff` (staged + unstaged) pour voir le contenu des changements
4. Lance `git -C <projet> log --oneline -10` pour voir le style des messages de commit recents du projet
5. Analyse les changements et redige un message de commit :
   - Resume la nature du changement (feature, fix, refactor, docs, test)
   - Concentre-toi sur le "pourquoi" plutot que le "quoi"
   - 1 a 2 phrases, concis
   - Suit le style des commits recents du projet (chaque projet peut avoir son propre style)
6. Stage les fichiers pertinents avec `git -C <projet> add <fichier>` (pas de `git add -A` — ajoute les fichiers par nom)
7. Ne jamais commiter : `.env`, credentials, fichiers temporaires, rapports generes
8. Cree le commit avec `git -C <projet> commit -m "..."`
9. Affiche le resultat : projet, hash du commit, message, fichiers inclus

## Recapitulatif final

Recapitule les commits crees par projet :

```
## Commits crees

| Projet | Hash | Message |
|--------|------|---------|
| backend | abc1234 | [FIX] correction du flux d'encaissement |
| frontend | (aucun) | - |
```

Si le repo racine contient des changements (par exemple des modifications dans `docs/` ou `.claude/`), mentionne-le dans le recap mais ne commite PAS — informe l'utilisateur qu'il doit les gerer manuellement.
