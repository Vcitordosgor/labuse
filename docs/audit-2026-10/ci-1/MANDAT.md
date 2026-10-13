# MANDAT-CI-1 — aucun code cassé n'arrive dans main

Rédigé le 13/10/2026. Modèle : Opus. Branche `feat/ci-1` depuis main, worktree `~/Desktop/labuse-ci`. Rien sur le VPS, aucune écriture dans la base locale.

## Pourquoi

Aujourd'hui, un test cassé ou une erreur de typage peut partir dans main sans que personne ne le voie (exemple : ProspectionSolaire, cassé depuis plusieurs commits). Vic merge en local puis pousse directement sur main : la vérification doit l'attraper **avant** l'envoi, et GitHub doit confirmer **après**.

## Règles

- **Étape 0** : `pwd`, branche, arbre propre.
- Aucun secret dans le dépôt ni dans la configuration GitHub : la vérification n'a accès ni à la prod, ni au `.env`, ni à la base réelle.
- Durée cible : moins de 10 minutes sur GitHub, moins de 2 minutes en local avant envoi.
- Ne pas changer la façon dont Vic travaille (merge `--no-ff` en local, push sur main) : on ajoute des filets, pas de procédure.
- Un commit par lot. Ne merge pas.

## Lot 1 — repartir au vert

Faire passer **toute** la suite actuelle avant de l'automatiser : corriger les tests cassés connus (ProspectionSolaire, et tout autre échec pré-existant), ou les marquer explicitement avec la raison s'ils dépendent des données réelles. Liste dans le rapport : test, cause, correction ou marquage.

## Lot 2 — trier les tests

Trois familles, par marqueur pytest : **unitaires** (aucune base), **base de test** (PostGIS vide + petites fixtures), **données réelles** (exigent la base complète : jamais en CI, ils restent dans le banc de nuit en prod). Front : `tsc -b`, `vitest`, `vite build`.

## Lot 3 — la vérification GitHub

Workflow GitHub Actions déclenché à chaque push sur main et sur chaque branche : Python (unitaires + base de test, avec un conteneur PostGIS de la même version majeure que la prod) · front (`npm ci`, `tsc -b`, `vitest`, `vite build`) · recherche de secrets commités (clés, mots de passe, `.env`). Cache des dépendances pour tenir sous 10 minutes. Résultat visible sur le commit (coche verte ou croix rouge).

## Lot 4 — le filet local avant envoi

Un hook `pre-push` (installé par une commande unique, documentée) qui lance en moins de 2 minutes : `tsc -b`, `vitest`, les tests unitaires Python, et la recherche de secrets. S'il échoue, le push est refusé avec un message clair ; `git push --no-verify` reste possible en cas d'urgence, et le rapport dit quand l'utiliser.

## Lot 5 — l'alerte

Une croix rouge sur GitHub déclenche un mail à Vic (notification GitHub ou passage par l'alerte unique de SOLIDITE-1, au plus simple).

## Preuve

Un commit volontairement cassé (erreur de typage dans une branche de test) : refusé par le hook local, croix rouge et mail sur GitHub. Puis le commit corrigé : vert partout. Captures dans le rapport.

## Livrables

`.github/workflows/ci.yml`, le hook et sa commande d'installation, `docs/audit-2026-10/ci-1/RAPPORT.md` (durées mesurées, tests marqués et pourquoi, preuve), une section « Vérification avant envoi » dans `docs/EXPLOITATION.md`.
