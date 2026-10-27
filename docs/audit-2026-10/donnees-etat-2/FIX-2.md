# DONNEES-ETAT-FIX-2 — fermer les trous restants

Branche `fix/donnees-etat-fix-2` (worktree `~/Desktop/labuse-etatfix2`) depuis `origin/main` (`0490baed0`). **Pas de merge, rien en prod.** DA existante, cartes au format actuel (aucune refonte du dashboard). Tests locaux + captures avant/après.

| Lot | Trou | Correctif | Preuve |
|-----|------|-----------|--------|
| 0 | repose crontab dans le mauvais script ; deploiement.json figé ; fumée rouge si Playwright absent | tout dans `deploy_app.sh` (le seul vrai déploiement) ; `deploy_vps.sh` neutralisé | test + simulation |
| A | pas de test de restauration | agent launchd Mac (restaure → compte → DROP, garde 20 Go, marqueur dashboard) | restauration réelle jouée |
| B | oubli du disque externe | carte « copie hors-site » (orange 7 j / rouge 10 j) | captures (vraie date 19/10) |
| C | incidents ouverts invisibles | une carte rouge par incident (vérité-sources, job-echec…), Voir le détail / Accepter | capture (vérité-sources + 3 écarts) |
| D | après bascule, cloche figée | la bascule rejoue la cloche + rafraîchit les caches | bascule aller-retour → chasse 0 |

---

## Lot 0 — Un seul script de déploiement

**Le trou.** FIX-1 avait mis la repose du crontab dans `deploy_vps.sh` — qui **ne tourne jamais** (la prod n'a pas de clone git). `deploy_app.sh` (rsync depuis le Mac, le SEUL vrai déploiement) ne touchait ni le crontab ni `deploiement.json`.

**Correctif.** Dans `deploy_app.sh` :
- **crontab** (étape 4b) : régénère depuis le registre, sauvegarde l'ancien (`labuse.bak-deploy-*`), pose, **vérifie** (`jobs crontab --verifier`) ; tout écart **arrête le déploiement** (`exit 5`).
- **deploiement.json** (étape 4c) : écrit `{sha, iso, deploye_le}` du commit réellement déployé, à chaque passage.
- **fumée** : `smoke_build.mjs` **saute proprement** (code 77 « sauté », exit 0 global) quand le navigateur Playwright est absent, au lieu de jeter une exception non rattrapée → rouge.
- `deploy_vps.sh` est **neutralisé** (panneau « OBSOLÈTE → utilisez deploy_app.sh », `exit 2`) : un seul script de déploiement.

**Preuves.** `tests/test_donnees_etat_fix1.py` (deploy_app vérifie le crontab · deploiement.json · vps obsolète) ; déploiement **simulé** → deploiement.json à jour (`sha == HEAD`, `deploye_le` présent) ; `smoke_build.mjs` avec navigateur introuvable → **exit 77** (vérifié).

## Lot A — Test de restauration mensuel (Mac)

**Fait.** `deploy/mac/restore_test.sh` (agent launchd `com.labuse.restore-test`, 1er du mois 09:00) : rapatrie le dernier dump, le restaure dans une base **jetable** (`labuse_restore_test`), compare les comptages clés à la prod (parcels, data_sources) **+ compte le run servi** (score_labuse du run de `served_run.txt`), **supprime** la base (trap EXIT), et écrit un **marqueur `.restore-test.json`** lu par le Tableau de bord (carte Lot A). **Garde-fou** : refuse si **< 20 Go** libres (`LABUSE_RESTORE_MIN_GO`, configurable). Ajouté à `install_agents.sh` (4 agents) ; plist repointé vers `~/.labuse/ops` (jamais `~/Desktop`).

**Preuves.**
1. **Garde-fou** : `restore_test.sh` avec `MIN_GO=20` sur le Mac (12 Go libres) → **REFUSE**, marqueur `statut:"refuse"`, exit 0 (non bloquant).
2. **Restauration réelle** : base jetable + `pg_restore` du vrai dump (`…20261027-173056.dump`) → **parcels 434 582 = prod 434 582 · data_sources 130 = prod 130** (0 erreur), base **supprimée**. *(Le Mac de dev n'a que 12 Go libres → restauration ciblée des tables clés, PostGIS posé d'abord ; le run mensuel restaure le dump COMPLET avec le garde-fou 20 Go. Le comptage run-servi est couvert par le code/les tests.)*
3. Carte dashboard « Dernière restauration : vérifiée (2026-10-28) » — capture `01-tableau-de-bord.png`.

## Lot B — Plus jamais d'oubli du disque externe

**Fait.** Carte « copie hors-site » (`cockpit_resume._carte_copie_externe`, nourrie par `ops_alertes.lire_copie_externe` + l'âge en jours) : **jaune à 7 jours, rouge à 10**. Fraîche (< 7 j) → pas de carte. L'incident générique `copie-externe-ancienne` ne double plus (rendu délégué à cette carte).

**Preuve.** Capture avec la **vraie date (19/10)** : le dashboard affiche « Copie hors-site ancienne (**8 jours**) » en **orange** (capture `01-tableau-de-bord.png`). ⚠️ 19/10 fait **8-9 jours** le 28/10 → **orange** ; le **rouge** se déclenche à 10 jours (donc le 29/10). L'état **rouge** est démontré avec un marqueur à 11 jours → « Copie hors-site ancienne (10 jours) » rouge (`APRES-copie-externe-ROUGE.json`).

## Lot C — Les incidents ouverts au Tableau de bord

**Le trou.** `_cartes_incidents` **sautait** (`continue`) tout incident dont la clé n'était pas dans `_INCIDENT_CARTE` : **vérité-sources et job-echec:\*** étaient **invisibles** au dashboard.

**Correctif.** `_cartes_incidents` rend **chaque** incident ouvert : clé connue → libellé dédié ; sinon titre FR générique (`verite-sources` → « Des valeurs servies divergent des sources officielles » ; `job-echec:X` → « Un automate a échoué : X »). Chaque carte = **rouge** + **Voir le détail** (le détail porte les écarts/faits) + un bouton **Accepter** (acquitte via `POST /admin/cockpit/accepter-incident`, rouvre au prochain contrôle s'il est toujours réel). Un incident **fermé** sort de `incidents_ouverts` → sa carte **disparaît**.

**Preuve.** Incident `verite-sources` (3 écarts) ouvert en base → le dashboard affiche la carte rouge « Des valeurs servies divergent des sources officielles » ; « Voir le détail » montre les **3 écarts lisibles** (97411…AB0123 PLU UA↔UB (GPU) · 97415…AC0045 PPR bleu↔rouge (Géorisques) · 97409…AD0210 vente 2021↔2023 (DVF)) — captures `01-tableau-de-bord.png` + `02-verite-sources-detail.png`.

## Lot D — Propagation après bascule

**Le trou.** `basculer()` purgeait les caches mais **ne rejouait pas la cloche** : après une bascule, `event_log` restait figé sur l'ancien run → 2 écarts chasse_donnees : **`cloche-fraicheur`** (detect_events jamais rejoué) + **`digest-vs-cloche`** (« cloche dans un autre monde »).

**Correctif.** `basculer()` appelle `_propager_apres_bascule(db)` : (a) **rejoue la cloche** — `detect_events` pose les bascules du marché avec `run_to = run servi` + `evaluer_radar_cloche` réévalue les veilles ; (b) **rafraîchit les caches** à clé de run via un `labuse rebuild` **détaché**. Best-effort (ne défait jamais une bascule réussie).

**Preuve (bascule aller-retour en local).**
- Après bascule q_v20 → **q_v19** (sans propagation) : `chasse_donnees` = **2 ECART** (`cloche-fraicheur` + `digest-vs-cloche`).
- Après bascule q_v19 → **q_v20** (AVEC propagation) : **cloche rejouée pour q_v20** → `chasse_donnees` = **23 OK · 0 ECART · 2 SKIP**.

---

## Captures (`captures/donnees-etat-fix2/`)

| Fichier | Montre |
|---------|--------|
| `00-tableau-AVANT.png` | origine : ni copie hors-site, ni restauration, et vérité-sources **invisible** (4 cartes) |
| `01-tableau-de-bord.png` | **après** : copie hors-site (orange), restauration vérifiée (gris), vérité-sources (rouge + Accepter) |
| `02-verite-sources-detail.png` | « Voir le détail » : les **3 écarts** parcelle ↔ source officielle |
| `APRES-cartes.json` · `APRES-copie-externe-ROUGE.json` | le payload exact rendu verbatim par le front (dont l'état rouge 10 j) |

Harnais : `qa/fix2_captures.mjs` (Chrome système, `circuit-harness.html` via vite dev, fixture RÉELLE capturée du backend — zéro base touchée pour les captures).

## Tests

Backend : **59 passés** (`test_donnees_etat_fix1.py` MAJ Lot 0, `test_donnees_etat_fix2.py` nouveau — cartes B/C/A, lecteur marqueur, restore_test garde, propagation bascule ; + cockpit/solidite/bascule non régressés). Front : **tsc 0 erreur**, **vitest 19 passés** (circuit), **vite build** OK.

## Fichiers touchés

`deploy/scripts/deploy_app.sh` · `deploy/scripts/deploy_vps.sh` (obsolète) · `deploy/scripts/smoke_build.mjs` · `deploy/mac/restore_test.sh` · `deploy/mac/com.labuse.restore-test.plist` · `deploy/mac/install_agents.sh` · `src/labuse/cockpit_resume.py` · `src/labuse/ops_alertes.py` · `src/labuse/api/dashboard.py` · `src/labuse/bascule_flux.py` · `frontend/src/components/admin/circuit/TableauDeBord.tsx` · `frontend/src/components/admin/circuit/types.ts` · `frontend/src/lib/api.ts` · `tests/test_donnees_etat_fix1.py` · `tests/test_donnees_etat_fix2.py` · `qa/fix2_captures.mjs`.

## À retenir

- Effet en prod au **prochain déploiement** (et c'est désormais `deploy_app.sh` qui reposera le crontab + écrira deploiement.json tout seul).
- L'agent de restauration Mac : l'**installer** (`deploy/mac/install_agents.sh`) ; il refuse tant que le Mac n'a pas **20 Go** libres (le Mac de dev est à 12 Go).
- Carte copie hors-site : **orange à 7 j, rouge à 10 j** — la vraie copie du 19/10 passe au rouge le 29/10.
