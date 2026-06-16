Setup le framework "manager d'agents" sur le projet courant.

A executer une fois, a l'initialisation du framework dans un repo. Idempotent : peut etre relance pour ajouter de nouveaux projets ou regenerer les fichiers manquants.

## Etapes

### 1. Recuperer la liste des projets

Demande a l'utilisateur la liste des projets (sous-repos) qui composent le produit. Exemples :
- Un seul : `backend`
- Deux : `backend`, `frontend`
- Trois : `api`, `web`, `mobile`

Format attendu : noms separes par des virgules ou des espaces. Les noms correspondent aux dossiers du repo racine qui contiennent chacun un repo git distinct.

### 2. Verifier la presence des dossiers

Pour chaque nom donne :
- Si `<nom>/` existe : OK, conserve
- Si `<nom>/` n'existe pas : demande a l'utilisateur si le dossier doit etre cree (vide) ou si le nom est une erreur

### 3. Ecrire `.claude/projects.json`

Cree ou met a jour `.claude/projects.json` :

```json
{
  "projects": ["backend", "frontend"]
}
```

Si le fichier existe deja, fusionne sans doublon. Conserve l'ordre fourni par l'utilisateur.

### 4. Ajouter les projets au `.gitignore` racine

Lis le `.gitignore` a la racine (cree-le s'il n'existe pas). Pour chaque projet enregistre, ajoute une ligne `<nom>/` si elle n'est pas deja presente. Conserve les lignes existantes.

Justification : le repo racine ne contient que le framework Claude. Les sous-projets sont des repos git imbriques avec leur propre historique — ils ne doivent pas etre suivis par le repo racine.

Exemple de `.gitignore` resultant :

```
backend/
frontend/
```

### 5. Verifier la structure `.claude/`

Verifie que les dossiers suivants existent, cree-les sinon :
- `.claude/commands/`
- `.claude/skills/`
- `.claude/agents/`

Ne touche PAS aux fichiers existants dans ces dossiers (skills, agents et commandes deja en place).

### 6. Verifier la structure `docs/`

Verifie que les dossiers suivants existent, cree-les sinon (avec un `.gitkeep` si vides) :
- `docs/architecture/`
- `docs/domain/`
- `docs/playbooks/`
- `docs/synthesis/`

### 7. Bootstrap du `CLAUDE.md` racine

Si `CLAUDE.md` racine n'existe pas, cree un squelette minimal :

```markdown
# <Nom du projet>

## Projets

<liste des projets enregistres avec leur role en une ligne>

## Workflow

Tout ticket non-trivial se demarre en plan mode (Shift+Tab).

## Slash commands

| Commande | Role |
|----------|------|
| `/install` | Setup ou mise a jour du framework |
| `/review-mine` | Auto-review du diff avant commit |
| `/update-brain` | Mise a jour de la doc apres un changement |
| `/commit-changes` | Commiter dans les projets enregistres |

## Apres toute modification de code

1. `/review-mine`
2. Tests
3. `/update-brain`
4. `/commit-changes`
```

Demande a l'utilisateur le nom du projet et le role de chaque sous-projet pour completer le squelette. Si `CLAUDE.md` existe deja, ne le modifie pas.

### 8. Generation du brain

Genere la documentation initiale (Phase 1 du README — « Poser le brain »). Idempotent : ne touche jamais a un fichier existant, complete uniquement ce qui manque.

Avant de commencer, previens l'utilisateur :

> « Generation du brain en cours. Pour chaque fichier produit, je m'appuie sur le code lu dans le projet. La validation metier reste a ta charge — relis et corrige les brouillons. »

#### 8.1 Brain partage (racine)

- Si `docs/domain/GLOSSAIRE.md` n'existe pas : cree-le avec l'en-tete et un tableau vide (`| Terme | Definition | Alias/Contexte |`). Si des termes metier ressortent clairement de la lecture du code/README, pre-remplis quelques entrees.
- Si `docs/architecture/ADR_TEMPLATE.md` n'existe pas : cree-le avec le template standard (Contexte, Decision, Consequences, Alternatives, Statut, Date).
- Si `docs/architecture/README.md` n'existe pas : cree-le avec un index vide des ADRs.
- Ne cree PAS d'ADR retroactif automatiquement : demande a l'utilisateur s'il veut en initialiser quelques-uns ; si oui, demande lesquels.

#### 8.2 Brain par projet

Pour chaque projet enregistre dans `.claude/projects.json` :

1. **`<projet>/CLAUDE.md` racine du projet** — si absent, lis le code (structure, README, configs, package.json/pyproject) et genere un squelette : description (1 paragraphe), commandes essentielles (setup/test/run), table des apps/modules, fichiers critiques, pointeur vers `docs/`. Vise ~100 lignes max.

2. **Identification des apps/modules** — detecte les sous-dossiers de premier niveau qui correspondent a des apps autonomes (presence d'un `models.py`, `views.py`, `package.json` local, `index.tsx`, etc.). Liste-les a l'utilisateur pour confirmation avant d'aller plus loin.

3. **Pour chaque app/module confirme**, si manquant :
   - `<projet>/<app>/CLAUDE.md` : commandes de test specifiques, table des fichiers et leurs roles, mecanismes cles, pointeurs vers docs detaillees.
   - `<projet>/<app>/docs/ARCHITECTURE.md` : schema/flux, modeles, dependances.
   - `<projet>/<app>/docs/API.md` (seulement si l'app expose des endpoints) : reference des endpoints.
   - `<projet>/<app>/docs/AUDIT_SECURITE.md` : invariants securite (permissions, validations).

Convention de nommage doc : MAJUSCULES avec `_` comme separateur.

#### 8.3 Mode de generation

- Genere les fichiers un par un, en montrant le contenu produit a l'utilisateur avant de passer au suivant (gros volume — laisse-le valider/interrompre).
- Si un projet est trop gros (> 5 apps), propose a l'utilisateur de cibler un sous-ensemble pour cette execution et de relancer `/install` plus tard pour le reste.
- Ne reecris JAMAIS un fichier existant. Si l'utilisateur veut le regenerer, il doit le supprimer manuellement d'abord.

### 9. Recapitulatif

Affiche :
- Liste des projets enregistres dans `.claude/projects.json`
- Lignes ajoutees au `.gitignore`
- Fichiers/dossiers crees (structure + brain), groupes par projet
- Fichiers laisses intacts (deja presents)
- Elements de brain restant a produire manuellement (ADRs retroactifs, GLOSSAIRE a enrichir)

Termine par : « Framework installe et brain initialise. Relis les fichiers generes — la validation metier reste a ta charge. »
