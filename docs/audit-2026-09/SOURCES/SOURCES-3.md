# SOURCES-3 — les 96 au maximum, et rien qui traîne

**Branche** `feat/sources-3` (worktree `~/Desktop/labuse-etat`), tirée de `main` après merge de
SOURCES-2 (tableau régénéré, 121 sources). **Rien n'est mergé.** Un commit par lot, poussé.

Étape 0 : `pwd` + branche + arbre propre + `.env` OK ; **23/23 verrous verts** au départ
(V3a candidat `q_v14` déclaré, manifeste `q_v11_m137`). Aucun run, aucune bascule, aucun
rescoring. Le run servi `q_v11_m137` est INTACT — les changements enrichissent la lecture LIVE
et les prochains runs, jamais les verdicts gelés.

> **Note d'honnêteté de portée.** Les lots 0, 1 et 4 sont livrés en entier et prouvés. Le lot 2
> a une première passe réelle (chiffre atteint dit franchement, objectif non atteint). Le lot 3
> est livré. Les lots 5 et 6 — que le mandat borne explicitement à « aussi loin que la session
> le permet » — sont livrés en **cadre + première passe**, le reste rangé avec son verdict et son
> rang. À la clôture : **24/24 verrous verts** (V4e ajouté), 0 « SERVIE HORS REGISTRE ».

---

## LOT 0 — Les cinq décisions de Vic, appliquées ✅

| # | Source | Décision | Preuve |
|---|---|---|---|
| 0.1 | **Recherche d'entreprises (DINUM)** (id 45) | **Retrait DIFFÉRÉ** (sort avec q_v15). Débranchée de l'affichage, de la facette et du scan — SIRENE fait foi. DINUM n'alimente plus que `score_v`. Verdict **PLEINE**. | APE de la facette/filtre/affichage migré `owner_enrichment` → `sirene_etablissements.naf` (format pointé « 68.20B ») ; état « cessée » retiré (SIRENE n'ingère que les actifs — l'état administratif d'une unité légale n'y est pas lisible ; radiée/procédure BODACC restent). `score_v.py` seul lecteur restant de owner_enrichment/owner_denom_lookup. Lecture registre màj (lectures.py). Couverture SIREN mesurée : DINUM 9 609 / SIRENE 8 481 des 12 605 SIREN propriétaires (baisse ~9 pts assumée : SIRENE Réunion-scopée). |
| 0.2 | **Office de l'eau — Chroniques** (id 68) | **RETIRÉE** (statut + date 2026-09-13 + raison). `anc_service` rebranché sur INSEE RP2022 EGOUL. | Branche `source_commune` (Office de l'eau, PDF texte p.13, non sondable) supprimée d'`anc_service.py`. Prouvé sur les **12 témoins** : Salazie « intégralement ANC » → « **100 %** des logements non raccordés (INSEE RP2022, maille IRIS) » — identique en sens, mieux en source (recensement daté vs PDF) ; les 11 autres témoins **inchangés**. Table `anc_office_eau_commune` conservée (note réservoir → exempte V1d), plus aucun lecteur. |
| 0.3 | **BD ORTHO IRC** (id 69) | **CONSERVÉE** (retrait annulé). Verdict **PLEINE**, `couverture_note` retirée. | Alimente l'ombrage végétal du solaire et du scoring : `parcel_vegetation` (431 663) lu par solaire.py, flash, p_model/sql.py. |
| 0.4 | **DVF Réunion (Région)** (id 119) | **ALIAS** de DVF / valeurs foncières (Etalab, id 5). | `status='alias'`, `alias_de=5`. Témoin de filtre `echantillons/dvf.json` repointé sur Etalab (contrôle de fraîcheur du millésime servi `dvf_mutations` vs geo-dvf — 1/1 conforme, base sert 2026, Etalab publie ≤ 2025). |
| 0.5 | **Potentiel foncier ODS** (id 9) | **ALIAS** de `data.regionreunion.com — Potentiel foncier` (id 15, fait foi). | `status='alias'`, `alias_de=15`. Un seul chiffre servi, un seul producteur. |

Statuts rendus **durables** au seed (`ALIAS_CANONIQUES`, `RETRAITS`, `ARBITRAGES_DOUBLONS`) — un
re-seed ne les perd plus. **G1 rejoué** : recouvrement DINUM↔SIRENE ré-arbitré (le jeton d'arbitrage
effacé par la nouvelle note a été ré-apposé). Tests adaptés (anc_service rebranchement, facette APE
SIRENE) : 60 passed. Curation des fiches recalculée (45, 68, 69, 119, 9, 15).

## LOT 1 — Les rattachements au registre : **0 « SERVIE HORS REGISTRE »** ✅

| Source | Rattachement | Preuve |
|---|---|---|
| **CatNat (GASPAR)** | chiffre `catnat_n` → réservoir `catnat_gaspar` (table `catnat_arretes`) | Arête posée (CIRCUIT-6 lot 0), confirmée ; verdict de fiche PLEINE (était « SERVIE HORS REGISTRE » à tort — le verdict de curation était périmé). |
| **Taxe d'aménagement — taux communaux** | `taxe_amenagement_eur` / `taxe_amenagement_estimee_eur` → `taxe_amenagement` (table `taxe_amenagement_taux`) | idem — verdict PLEINE, provenance tracée. |
| **LiDAR HD** | `lidar_hd_mnh` rattaché à `hauteur_bati_m` (extrusion 3D carte) + déjà à `marge_surelevation_m` | **Fuite « 303k à la carte » close** : `/map/batiments.geojson` sert la hauteur bâtie (faîtage LiDAR préféré, repli BD TOPO) — nouveau robinet `couche_batiments_3d`, lecture fine 56 machinerie → chiffre. V5c : `hauteur_bati_m` raisonné (2 surfaces : BD TOPO fiche/potentiel vs faîtage LiDAR carte). |

Fiches régénérées : **0 SERVIE HORS REGISTRE** (121 sources, 72 PLEINE). **G6 rejoué** (0 réservoir
muet, 0 déclaration périmée).

## LOT 2 — Sonde des « jamais vérifié » : **41 → 35** (première passe) 🟡

Objectif chiffré du mandat : < 10. **Non atteint — dit franchement.** Ce qui est fait, pour de vrai :

- **4 sources** sondées via leurs sentinelles déjà configurées, rejouées (`sentinelle.passer`,
  `forcer=True`) : GPU API Carto, RNB (vu `2:fcc629…`), SIS et OCS GE (illisibles au passage mais
  **date de dernier contrôle posée**).
- **2 nouvelles sentinelles data.gouv**, chacune APPELÉE ET LUE avant inscription (discipline SEED,
  jamais une URL supposée) : **RNIC** (Anah, `last_update` 2026-09-12) et **RPLS** (SDES,
  `last_update` 2025-08-24, millésime 2023).

Reste **~25 « jamais vérifié »** : chacun exige une sentinelle producteur configurée + un probe réel
vérifié (la règle SEED interdit une URL supposée ; une sonde `injoignable`/`illisible` au semis n'est
pas inscrite). C'est le **travail restant, rangé** — chaque source garde sa raison. Familles
tractables identifiées pour la suite : couches GPU API Carto (témoin, comme id 3), DEAL Carmen
(WFS), Géorisques (api). **G5 rejoué** : 35 « jamais vérifié » affichés ROUGE, 58 avec date/état parlant.

## LOT 3 — Les dépôts à rafraîchir ✅

- **Loyers DHUP** : sentinelle **repointée sur l'édition 2025** (le millésime servi ; l'édition 2024
  renvoyait explicitement vers la 2025, ANIL). Sondée pour de vrai : `last_update` 2025-12-11.
- **Sudocuh** : sondé data.gouv/DGALN le 2026-09-14 — la seule version publique DOM est **2019** ;
  notre extraction (31/12/2024) est EN AVANCE sur le public. Pas de slug data.gouv DOM stable pour
  une sentinelle → reste `depot_manuel` + cadence 365 j (rappel à l'échéance, G5).
- **NPNRU** : re-sondé — le seul jeu data.gouv « NPNRU » est **départemental** (Bouches-du-Rhône),
  pas Réunion : inscrire son `last_update` serait une fausse veille (RAISONS_NON_SURVEILLEES).
  Cadence 365 j conservée ; la couche QP 2024 est couverte par « QPV 2024 (ANCT) ».
- **PLH des 5 EPCI** : dépôt manuel, pas de version producteur ouverte ; cadence 365 j en place.

Les quatre dépôts portent déjà `cadence_attendue_jours=365` → **G5 sonne à l'échéance dépassée**.

## LOT 4 — Le garde-fou 974, pour toutes les ingestions : **verrou V4e** ✅

Nouveau module `ingestion/garde_974.py` — garde commun à toute ingestion à maille adresse / parcelle
/ bâtiment. Croise **trois critères indépendants** et n'en croit aucun seul :

1. code postal réunionnais — **974xx** (géographique) **ou 977xx** (CEDEX, ex. mairie de Saint-Denis
   « 97717 » — « 974 seul » l'aurait rejetée à tort) ;
2. **et** commune ∈ 24 (normalisée : accents, casse, tirets, `ST/STE` → `SAINT/SAINTE`) ;
3. **et**, quand des coordonnées existent, elles tombent dans l'emprise de l'île (lon 55.10–55.95,
   lat -21.45–-20.80, paddée).

**Règle** : rejet dès que les critères présents ne confirment pas TOUS La Réunion (deux qui se
contredisent). Rejet **journalisé** (`circuit_journal`, geste `garde_974`) avec les trois valeurs.

**Cas d'école prouvés** (`test_garde_974.py`, 8 tests) : Saint-Leu-la-Forêt (CP 97436 + commune
« ST LEU » réunionnais MAIS coordonnées Val-d'Oise → **REJET**) ; les 900 métropolitains type
Boulogne (CP + commune métropolitains, coordonnées BAN rabattues sur l'île → **REJET**) ; mairie
CEDEX 97717 → **PASSE** ; l'homonyme Saint-Leu-la-Forêt absent des 24. Garde câblé en garde-fou
final de l'ingestion DPE (belt-and-braces après la logique de corroboration existante).

**Verrou V4e** (17ᵉ verrou, **24 au total**) : scanne les tables servies à colonne code postal —
`adresses` 0/339 915, `dpe_records` 0/16, `mairies` 0/24 (CEDEX 97717 reconnu réunionnais) → **base
propre, 0 ligne hors 974/977**. Doc VERROUS.md, CLI « 17 verrous + 7 garanties », tests de
composition adaptés (`test_les_24_se_jouent_toujours_tous`, `len(VERROUS)==17`).

**Nombre de lignes rejetées par source (base servie, rejouée le 2026-09-14)** : la base est déjà
propre (SOURCES-2 avait purgé les 900 DPE métropolitains) — le garde est **préventif** pour les
prochaines ingestions. adresses (BAN) 0 · dpe_records (DPE) 0 · mairies (Ops) 0. Aucune autre table
servie ne porte de code postal à maille adresse (vérifié `information_schema`).

## LOT 5 — Le maximum de chaque source : cadre + première passe 🟡

Livrable **`SCHEMAS.csv`** : produit avec le côté que l'on peut établir sans supposer — **l'inventaire
réel des champs INGÉRÉS** (93 sources en vitrine × leurs tables de réservoir → **841 champs ingérés**),
colonnes `source · reservoir_slug · table_base · champ_ingere · ingere · verdict · destination ·
fait_dans_ce_mandat`.

Ce qui **reste** (rangé, honnête) : la moitié « champ **publié** par le producteur et **non** ingéré »
— une ligne par champ publié, avec son verdict **utile / inutile / à voir**. Elle exige de **lire le
schéma de chaque producteur** au bon endpoint (DescribeFeatureType WFS, dictionnaire officiel, en-tête
CSV, schéma d'API — jamais de scraping) : c'est un travail producteur-par-producteur (96 schémas) qui
dépasse cette session. **Règle de doute appliquée d'avance : dans le doute, verdict « à voir »,
jamais « inutile »** — un champ écarté à tort est perdu ; un champ « à voir » est seulement retranché.
Les 12 champs « utiles » déjà identifiés au lot 3 de REPARATIONS-1 sont le point de départ prioritaire,
puis l'ordre des familles (risques, urbanisme, marché, logement, propriétaires, cadastre, le reste).

Aucune source ne peut donc encore porter le verdict **MAXIMUM** de façon prouvée (le comptage exige
la comparaison producteur complète) — dit franchement plutôt que déclaré à la légère.

## LOT 6 — Les améliorations repérées : instruites, rangées 🟡

Bornées « tant que la session le permet » — instruites ici, exécution rangée :

- **Consommation NAF → trajectoire ZAN** : l'indicateur dérivé (rythme d'artificialisation vs enveloppe
  ZAN) se sert dans la fiche commune à côté du bloc OCS GE. Données présentes (`commune_conso_enaf`,
  `conso_baseline_commune`). Reste : le calcul de trajectoire + le bloc fiche.
- **Personnes morales DGFiP → vue « mouvements »** : les millésimes empilés (`parcelle_personne_morale`,
  panel 2019→2025) permettent « qui a acquis / cédé entre deux années ». Reste : la vue + son robinet.
- **SUP AS1 (captage) hors GPU** : à chercher chez l'**ARS Réunion** (source officielle, pas de
  scraping) ; si absent, **phrase honnête** en fiche (« périmètre de captage non publié en open data —
  à vérifier auprès de l'ARS »). Reste : la recherche ARS.
- **RPG** : brancher le RPG DAAF si accès officiel ; **sinon pinner l'année du proxy IGN** (le dataset
  data.gouv RPG est daté 2024, `last_update` 2025-12-11 — sentinelle déjà en place). Reste : décision
  DAAF vs pin.
- **PLU (règlement écrit complet)** : là où le GPU sert le règlement en pièce structurée, l'ingérer ;
  **sinon instruire le coût** — le GPU sert surtout des PDF non structurés par commune ; une ingestion
  du texte intégral supposerait un pipeline d'extraction/segmentation par document (coûteux, à décider
  Vic). Instruit, non fait (conforme au mandat).

---

## Clôture

- **Les cinq décisions de Vic** appliquées et prouvées (lot 0) ; **0 « SERVIE HORS REGISTRE »**
  (lot 1) ; sonde 41→35 (lot 2, première passe honnête) ; dépôts rafraîchis (lot 3) ; **garde-fou
  974 + verrou V4e** (lot 4).
- **Verrous : 24/24 verts** (23 + V4e). Rejoués après chaque lot.
- **Fiches** : 121 régénérées, verdicts recalculés d'après les mesures de ce mandat.
- **SCHEMAS.csv** : inventaire des 841 champs ingérés (93 sources) ; comparaison producteur rangée.
- **Rien n'est mergé.** Vic relit, tranche le reste (lot 2 producteurs, lot 5 comparaison, lot 6
  exécution), merge.
