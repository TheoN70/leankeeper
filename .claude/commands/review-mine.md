Auto-review du diff git courant avant commit.

## Projets a reviewer

Lis `.claude/projects.json` pour recuperer la liste des projets enregistres. Si le fichier n'existe pas, indique a l'utilisateur de lancer `/install` d'abord.

Le repo racine ne contient que le framework Claude (pas de code applicatif) — il n'est PAS reviewe ici. Chaque projet liste est un repo git imbrique avec son propre diff.

## Pour chaque projet enregistre

Execute la procedure ci-dessous successivement sur chaque projet (`git -C <projet> ...`). Si `git -C <projet> diff` ne retourne rien (staged + unstaged), affiche « Aucun changement dans `<projet>` » et passe au suivant.

1. Lis le diff complet : `git -C <projet> diff` + `git -C <projet> diff --cached`
2. Pour chaque fichier modifie, lis le CLAUDE.md de l'app concernee (`<projet>/<app>/CLAUDE.md`)
3. Verifie chaque point :

**Conventions code (skill python — pour les projets backend Python/Django) :**
- Imports dans l'ordre : stdlib → third-party → Django → DRF → local
- Nommage : snake_case fonctions/variables, PascalCase classes, UPPER_SNAKE_CASE constantes
- Guillemets doubles, f-strings, type hints quand utile
- Pas de bare `except:`, pas de valeurs hardcodees pour les constantes metier

**Conventions code (skill react-nextjs — pour les projets frontend) :**
- Structure features/components/hooks conforme au skill
- Composants typed (TypeScript), pas de `any` non justifie
- Server actions dans `actions/*.action.ts`

**Tests :**
- Toute nouvelle fonctionnalite a des tests correspondants
- Les tests existants ne sont pas casses par le changement
- `@override_settings(SECURE_SSL_REDIRECT=False)` sur les classes de test (Django)

**Qualite :**
- Pas de requetes N+1 (utiliser select_related/prefetch_related cote Django)
- Pas de code mort ou commente
- `@extend_schema` sur chaque nouvel endpoint DRF
- `__str__()` sur chaque nouveau modele Django

**Documentation :**
- Si le comportement public change : `<projet>/<app>/docs/API.md` mis a jour
- Si la structure de fichiers change : `<projet>/<app>/CLAUDE.md` mis a jour
- Si un nouveau terme metier apparait : `docs/domain/GLOSSAIRE.md` (racine) mis a jour
- Si une decision structurante est prise : ADR cree dans `docs/architecture/` (racine)

**Securite :**
- Pas de secrets, credentials, cles API dans le diff
- Pas de `csrf_exempt` sauf sur les webhooks
- Validations presentes sur les entrees externes

4. Produis un verdict par projet :

```
## Review du diff — <projet>

| Critere | Verdict | Detail |
|---------|---------|--------|
| Conventions | OK/KO | ... |
| Tests | OK/KO | ... |
| Qualite | OK/KO | ... |
| Documentation | OK/KO | ... |
| Securite | OK/KO | ... |

**Verdict** : PASS / FAIL
**Issues a corriger** : (liste numerotee si FAIL)
```

## Recapitulatif final

Apres avoir traite tous les projets, affiche un recap :

```
## Recap global

| Projet | Verdict |
|--------|---------|
| backend | PASS/FAIL |
| frontend | PASS/FAIL |

**Verdict global** : PASS (tous PASS) / FAIL (au moins un FAIL)
```
