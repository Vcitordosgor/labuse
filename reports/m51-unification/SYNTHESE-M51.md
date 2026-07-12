# SYNTHÈSE M5.1 — Unification des vues sur le scoring v2 + check couches & fraîcheur

Branche `feat/m51-unification` (depuis main = M5, 576e865). **Aucun merge — validation visuelle Vic puis merge `--no-ff` par Vic.**
Date : 13/07/2026. Run v2 servi : `m36-l2f-2026-2026-07-12` (modèle M3.6 gelé, sha `00a58008…`).

## Le résultat en une phrase

Un seul monde visible : le v2 — compteurs, chips, tri, cartes de résultat, filtres, recherche NL, modules Outils, exports et PDF racontent tous le même verdict (tier v2 effectif, l'étage 0 du run servi prime) ; le legacy reste calculé et accessible (`legacy=1`, secondaire discret), plus jamais pilote.

## Lot 0 — prérequis (vérifiés)

- main contient M5 (merge 576e865), module `p_v2` présent, `verdictMeta` en place.
- Run v2 : `m36-l2f-2026-2026-07-12`, 431 663 parcelles, snapshot `m5-2026-07-12`.
- `mvt_parcels.tier_v2` rempli à 100 % (5 tiers).

## Les chiffres du monde v2 (SQL-exacts, tiers EFFECTIFS — étage 0 du run servi prime)

| Tier | Compte |
|---|---|
| Brûlantes v2 | **117** |
| Chaudes v2 | 960 |
| Réserve foncière | 3 607 |
| À creuser | 74 359 |
| Écartées (étage 0 dur) | 352 620 |
| **Opportunités** (brûlantes + chaudes) | **1 077** |

⚠ **117 et non 119** : le run v2 étiquette 119 brûlantes, mais 2 d'entre elles sont en étage 0 du run SERVI (`q_v3_datagap`) — la doctrine M5 (« l'étage 0 prime ») s'applique aussi aux compteurs, sinon liste et fiche raconteraient deux vérités. Les 99 brûlantes « écartées matrice » (non étage 0) APPARAISSENT désormais en liste par défaut — dont tout le haut du classement (le rang 1 île, `97423000AB1908`, était invisible avant M5.1).

## Lot 1 — panneau carte/résultats

- Chips = tiers v2 : Tout / Brûlantes v2 / Chaudes / Réserve foncière / À creuser / Écartées (opt-in = étage 0 dur, motifs dans l'entonnoir). « À surveiller » a disparu de l'UI.
- « Opportunités détectées » = brûlantes v2 + chaudes v2 (définition documentée dans le tooltip et le popover « pourquoi ? », qui ventile aussi par tier).
- Tri par défaut = **rang P** ; options ×N, surface, commune. Le tri par V et le compteur « 🔥 120 brûlantes » ont disparu (les événements restent en badges datés).
- Carte de résultat : chip tier v2 EN PREMIER (couleur verdictMeta) avec rang ; ×N en grand à droite ; badges secondaires conservés (● ÉVÉNEMENT daté, même proprio ×N — désormais calculé sur les opportunités v2, veille succession, ◠ vue mer, PUBLIC/BAILLEUR/COPRO). Le badge « V nn » a disparu (liste ET pastilles carte, remplacées par « #rang ») ; le dossier propriétaire reste dans la fiche (« Signaux vendeur »).
- Périmètre par défaut = univers v2 HORS étage 0 servi + toggle « masquer les copropriétés ».

## Lot 2 — filtres, entonnoir, stats, recherche

- `/stats` ventile par tiers v2 (source = run servi) ; matrice via `legacy=1` (deprecated, non requêtée par le front). Dossiers propriétaires (CRED-3) recalculés sur les opportunités v2 : 294 parcelles couvertes par 149 propriétaires identifiés + 783 personnes physiques.
- `/stats/entonnoir` : opportunités = v2, ventilation par tier ajoutée, motifs d'écartement inchangés (SQL-exacts).
- Filtres : tiers v2 (multi), commune(s), surface, copro, événement daté, **veille succession** (nouveau), signaux propriétaire (libellés métier). Les bandes V et le filtre 🔥 v1.3 ont disparu.
- NL : « montre-moi les brûlantes de Saint-Paul » → `tiers:["brulante"] + commune` (stub ET prompt du modèle réel) ; « à surveiller » → réserve foncière ; « succession » → veille. Champ `statuts` deprecated, plus jamais émis.
- `/parcels/search` (omnibox) : tier v2 + rang dans chaque résultat, ordre piloté par le tier effectif.
- Liens partageables : `tv=` (tiers) remplace `st=` (statuts). ⚠ Les anciennes veilles/liens `st=` retombent proprement sur le périmètre par défaut — les re-sauvegarder (consigné).

## Lot 3 — modules Outils & lexique

- 9 endpoints modules/moteurs servent tier v2 + rang + étage 0 ; composant partagé `TierBadge` : tier v2 principal, « (matrice : X) » secondaire discret. Les PÉRIMÈTRES candidats des modules restent matrice (fonctionnel, pas d'affichage) — à trancher en M6 (consigné).
- Tableau lexical exhaustif : `TABLEAU-LEXICAL.md` (24 occurrences traitées, 6 conservées justifiées, 3 restes consignés dont le moteur de notifications — matrice fonctionnelle, audit M6 1.6).
- Contributions en français client : `src/labuse/scoring/p_v2/libelles_client.py` (VERSION 2026-07-12.1) — mapping feature/bin → phrase (« canopée [≤ 0.4] » → « parcelle peu boisée » ; « croisement ancienneté… × … » → « mutation et permis récents combinés ») + fallback propre (jamais de crochets vides) ; bin exact conservé au survol et dans le payload (audit). Servie par `/v2/score/{idu}` → fiche.

## Lot 4 — audit couches & fraîcheur (lecture seule)

Livrables : `AUDIT-COUCHES.md` + `audit-couches.csv` (couches + 5 parcelles témoins), `FRAICHEUR.md` + `fraicheur-sources.csv`, `PLU-A-RECALIBRER.md` + `plu-communes.csv`.

**Fraîcheur — l'essentiel** (détail sourcé dans FRAICHEUR.md) :
- À JOUR : DVF (pub. 20/04/2026), Sitadel (Dido 01/06), DPE, RNIC, Filosofi (2021 = dernier carroyé), cadastre (éd. 29/06), Cartofriches, Géorisques.
- À RAFRAÎCHIR : **DGFiP PM millésime 2025 publié** (base : 2024) · **Fichiers fonciers Cerema 2025** (à coupler au prep-recompute) · BODACC (~8 j de retard, cron) · BD TOPO éd. juillet (mineur).
- À VÉRIFIER : **QPV 974 = génération 2025 DOM ?** (la 2024 en base ne vaut que pour la métropole — finding le plus sensible) · millésime OCS GE 974 non tracé.
- SOURCE MIGRÉE : RGE ALTI (MAJ arrêtées 2024) → MNT LiDAR HD ; geoservices → cartes.gouv.fr ; MH data.gouv figé 2017 → POP.
- Anomalie Sitadel résolue : max(date)=17/08/2026 = 1 outlier producteur sur 50 043 (DP locaux, erreur de saisie SDES) ; max réel 30/05/2026. Reco : garde-fou `date <= now()` au chargement (fix non trivial → consigné, pas corrigé).

**PLU (4.3) — liste « à recalibrer » : VIDE.** Les 24 communes sont au millésime GPU opposable. 5 vigilances : Saint-Louis (doc GPU retiré le 10/07/2026, republication à surveiller — le GPU ne sert temporairement AUCUN zonage) ; Saint-Leu (PLU 2007 opposable, révision générale en approbation imminente S2 2026 = candidat n°1 au recalibrage) ; Saint-André (révision en cours non approuvée) ; Le Port (`PARTIALLY_ANNULLED` au GPU, jugement à creuser) ; Saint-Philippe (RNU confirmé ; les zones 97412/97419 sous son emprise = débordements géométriques des voisins).

**Couches carte (4.1) : 9/9 OK** (rendu non vide, requêtes 200, comptes réseau = comptes base au filtre d'affichage près ; captures + script rejouable `frontend/qa/audit_couches_m51.mjs`). Notes : ANRU légitimement vide hors des 6 communes NPNRU (0 feature servie, consigné A3) ; Vue mer = filtre sur la couche parcelles (pas de requête propre, voulu) ; zéro erreur console.

**Témoins (4.4) : 5/5 RACCORD** (fiche ↔ tuiles ↔ base sur statut/tier/rang/étage 0) : AS1425, CD0905, AB1908, AB1341 (écartée étage 0, PPR rouge), EY1509 (réserve foncière).

**4 anomalies CONSIGNÉES (non corrigées — mandat séparé)** :
- **A1 (sérieuse)** : 441 géométries `plu_gpu_zone` dupliquées inter-communes (polygones à cheval ingérés une fois par commune) → la cascade somme les intersections : « Zone N — recouvrement 95 % » sur AB1341 alors que la vraie couverture est N 47,5 % + AUc 52,5 %. Des HARD_EXCLUDE zonage le long des limites communales peuvent être infondés → à corriger en M6 Phase 2b (moteur PLU) avec delta complet.
- A2 : `parc_national` stocké ×24 (une fois par commune) → dessiné 24 fois en mode île (opacité empilée, payload ×24).
- A3 : couche ANRU muette hors des 6 communes couvertes (0 feature sans message UI) — état vide à prévoir (M6 1.6).
- A4 : couche Équipements sert 7 subtypes dont `tcsp` (43 % du volume) et `commerce` absents de la légende (points gris non documentés).

## Lot 5 — tests

- **E2E `frontend/qa/qa_m51.mjs` : tout vert** (compteurs v2 SQL-exacts, tri rang par défaut, rang 1 « écartée matrice » en tête, chip tier en premier, aucun « V nn », « À surveiller » absent, 🔥 absent, toggle copro, légende « VERDICT · SCORING V2 », AS1425 top 3 Saint-Benoît, filtre brûlantes → 117 cartes, fiche raccord, zéro erreur console).
  - Précision AS1425 : rang 16, **2e** de Saint-Benoît derrière CD0905 (rang 8) — « en tête » vérifié comme top 3 ; les 5 premières de Saint-Benoît sont toutes « écartées matrice ».
- **Suite Python : au niveau de main.** 770+ verts ; 3 tests adaptés au v2 (documentés : stub NL → tiers, forme /stats) ; les 9 échecs restants (backup, cascade ×3, courrier, ortho, verdict_effectif ×3) **préexistent sur main à l'identique** (vérifié sur worktree main).
  - Bonus : la dette pyproj (189 erreurs DataDirError) se contourne avec `PROJ_DATA=/Users/openclaw/miniforge3/envs/labusedb/share/proj`.
- `CHECKLIST-DEMO-51.md` : 8 vérifications visuelles pour Vic.

## Performance (contrainte : ≤ aujourd'hui)

- Liste île (500) : **4,1 s (main) → 1,5 s** ; filtrée/commune : 0,3-0,4 s. Deux causes traitées : (1) requête restructurée — tri+filtres d'abord, jointures d'affichage sur la page seulement ; (2) **index partiel** `ix_dryrun_cascade_evenement` (la sous-requête « événement rouge » seq-scannait 14,2 M de lignes pour en retenir 40 — goulot préexistant). Index créé en base ET déclaré dans models.py.
- /stats : ~2,6 s à froid, cache 30 s (inchangé de structure).

## Contraintes respectées

Aucune suppression API/DB (bascule d'affichage : `statuts`/`legacy=1`/`sort=v` restent servis, deprecated). Aucune ingestion (audit en ligne lecture seule). Étage 0 et doctrines inchangés. Modèle M3.6 gelé intouché. Seed 974.

## Écarts & décisions à valider par Vic

1. **« Brûlantes v2 (119) » du mandat → 117 affichées** : doctrine « étage 0 du run servi prime » appliquée aux compteurs (2 brûlantes du run sont en étage 0). Le chiffre 119 reste visible dans le module Scoring v2 (lecture directe du run, onglet Brûlantes v2 = 119 - copros… servi par /v2/brulantes). Si Vic préfère 119 partout : une ligne à changer (compter sur le tier brut).
2. Anciennes veilles/liens `st=` (statuts matrice) : ignorés proprement → re-sauvegarder les veilles.
3. Grand chiffre des cartes de résultat = **×N** (avant : score Q) — cohérence v2 ; Q reste dans la fiche.
4. « Même proprio ×N » compté sur les opportunités v2 (avant : chaudes matrice).
5. Périmètres candidats des modules + moteur de notifications : restés matrice (fonctionnels) — M6.

## Fichiers du livrable

`reports/m51-unification/` : SYNTHESE-M51.md · TABLEAU-LEXICAL.md · CHECKLIST-DEMO-51.md · AUDIT-COUCHES.md + audit-couches.csv · FRAICHEUR.md + fraicheur-sources.csv · PLU-A-RECALIBRER.md + plu-communes.csv · captures/ (avant-*/apres-* île + Saint-Benoît + filtre brûlantes/fiche + couches).
E2E : `frontend/qa/qa_m51.mjs` (rejouable : `BASE=http://127.0.0.1:8010/socle/ node qa/qa_m51.mjs`).
