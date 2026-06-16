Mise a jour de la documentation apres un changement de code.

## Projets a analyser

Lis `.claude/projects.json` pour recuperer la liste des projets enregistres. Si le fichier n'existe pas, indique a l'utilisateur de lancer `/install` d'abord.

Le diff est analyse PROJET PAR PROJET (chaque projet est un repo git imbrique). Pour chacun : `git -C <projet> diff` + `git -C <projet> diff --cached`. Si aucun changement, passe au projet suivant.

Convention de nommage : les fichiers de doc par sujet sont en MAJUSCULES avec `_` comme separateur (ex. `AUTHENTICATION.md`, `BANKING.md`, `ADR_001_TOKEN_AUTH.md`).

## Pour chaque projet ayant un diff

Identifie le type de changement et applique les mises a jour correspondantes :

1. **Nouvelle app creee** dans `<projet>/<app>/` :
   - Creer `<projet>/<app>/CLAUDE.md` (commandes, architecture fichiers, flux, conventions test)
   - Creer `<projet>/<app>/docs/ARCHITECTURE.md`, `<projet>/<app>/docs/API.md`, `<projet>/<app>/docs/AUDIT_SECURITE.md`
   - Ajouter l'app dans la section `Sub-documentation` du `<projet>/CLAUDE.md`
   - Suivre `docs/playbooks/NEW_APP.md` s'il existe

2. **API modifiee** (nouvel endpoint, changement de signature, nouveau champ de reponse) :
   - Mettre a jour `<projet>/<app>/docs/API.md` avec les changements

3. **Structure de fichiers modifiee** (nouveau fichier, fichier renomme/supprime) :
   - Mettre a jour la table "Architecture des fichiers" dans `<projet>/<app>/CLAUDE.md`

4. **Decision d'architecture prise** (nouveau pattern, choix de technologie, compromis) :
   - Creer un ADR dans `docs/architecture/` (racine, partage entre projets) en suivant `docs/architecture/ADR_TEMPLATE.md`
   - Nommer le fichier `ADR_NNN_TITRE_COURT.md` (NNN incremente)
   - Ajouter l'entree dans `docs/architecture/README.md`

5. **Nouveau terme metier introduit** :
   - Ajouter une entree dans `docs/domain/GLOSSAIRE.md` (racine, ordre alphabetique)

Ne modifie que les fichiers qui necessitent reellement une mise a jour. Ne pas toucher aux docs deja a jour.

La documentation doit suffire a donner une vision claire du code. Ne pas tenir de journal de bord (DONE.md, CHANGELOG manuel) : le git log de chaque projet est la source de verite pour l'historique.

## Recapitulatif final

Affiche les fichiers de doc crees ou mis a jour, groupes par projet :

```
## Doc mise a jour

### backend
- backend/invoicing/docs/API.md (endpoint encaissee)
- backend/invoicing/CLAUDE.md (nouvelle table de fichiers)

### frontend
- (aucun changement)

### racine
- docs/domain/GLOSSAIRE.md (terme "F6")
```
