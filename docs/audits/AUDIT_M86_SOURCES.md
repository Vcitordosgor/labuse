# AUDIT M86 — Les 51 sources (page Sources & fraîcheur, véracité)

> **Restitution.** 51 sources servies (compteur `/accueil/chiffres` **CALCULÉ**, pas en dur —
> `accueil.py:77`). **OK : 41** · **À CORRIGER : 6** (dates de millésime en dur dans le front —
> **corrigées** dans ce mandat, cf. bas de page) · **MORTE : 4** (ingérées mais lues par AUCUN point de
> calcul servi — signalées, jamais retirées : arbitrage Vic). Liens officiels : **48/51 en HTTP 200** ;
> 3 non-200 NON-morts (Légifrance 403 anti-bot, LiDAR-HD 503 transitoire IGN, INPN 000 réseau — page
> valide au navigateur). **Corrections factuelles faites : 6 dates en dur → lecture centralisée**
> (`data_sources.source_millesime` exposé par `/sources`, front `millesimeNote` lit l'API, carte
> `MILLESIME_VERIFIE` supprimée). Mesuré le 2026-08-14. Branchée tracée à la source (module + lecteur).

**Les 4 MORTES (Vic arbitre le retrait) :** INSEE RP2022 (EGOUL) · Office de l'eau (Chroniques) ·
Contours IRIS · Sudocuh (procédures). Les 3 premières forment la chaîne ANC `proba_anc` que la fiche ne
lit pas (elle lit `zone_anc` issu du PLU/GPU — preuve DB : 220 973 lignes `source='proba_insee'` toutes
`zone_anc IS NULL`). Sudocuh : sa table n'est touchée que par le SQL de fraîcheur ; le radar PLU servi
lit le YAML curaté `config/veille_plu.yaml` (« squelette » assumé au docstring).

---

## Tableau (ordre de la page : par catégorie puis nom)

| # | source | branchée (module lecteur servi) | affichage exact | lien ↗ | millésime | verdict |
|---|---|---|---|---|---|---|
| 1 | Base Adresse Nationale | ✔ `api/app.py` (géocodage fiche, `/adresses/autocomplete`) | OK | 200 | ingestion tracée | OK |
| 2 | Zonage SAFER (DAAF) | ✔ couche `safer` · `api/resume.py` (préemption) | OK (badge **proxy** vrai) | 200 | — (proxy, non daté) | OK |
| 3 | INSEE RP2022 — Logements (EGOUL) | ✘ **MORTE** — `anc_maille_taux`→`proba_anc` non lu servi | note vraie | 200 | — | **MORTE** |
| 4 | Office de l'eau — Chroniques | ✘ **MORTE** — `calage_office_eau` (CLI/QA) ; `/signals` retiré | note vraie | 200 | — | **MORTE** |
| 5 | Contours IRIS (IGN/INSEE) | ✘ **MORTE** — support d'agrégation EGOUL, non lu servi | note vraie | 200 | — | **MORTE** |
| 6 | Filosofi INSEE (carreaux 200 m) | ✔ `scoring/p_model/sql.py` (prédicteur filo, run servi) | OK | 200 | **était en dur** → source_millesime | **À CORRIGER→fait** |
| 7 | Cadastre (API Carto PCI) | ✔ `parcels` — socle universel (tout `scoring/`, `api/`) | OK | 200 | ingestion tracée | OK |
| 8 | SITADEL (autorisations) | ✔ `p_model/ext_sql.py` (permits) + fiche + notif | OK | 200 | source_millesime `2026-06` | OK |
| 9 | BODACC (procédures) | ✔ `api/modules.py` (foncier sous pression) + notif | OK | 200 | ingestion tracée | OK |
| 10 | INPI RNE (dirigeants) | ✔ `api/modules.py` (verrou fiche) + `score_v.py` | OK | 200 | ingestion tracée | OK |
| 11 | Recherche d'entreprises (DINUM) | ✔ `scoring/score_v.py` (matching propriétaire) | OK | 200 | ingestion tracée | OK |
| 12 | SIRENE | ✔ `scoring/score_v.py` (résolution SIREN→PM) | OK (co-usage recherche-entreprises, pas de table propre) | 200 | ingestion tracée | OK |
| 13 | DPE ADEME (logements existants) | ✔ `scoring/score_v.py` (famille E, F/G passoire) | note vraie — **famélique : 17 lignes** (M66/M71) | 200 | ingestion tracée | OK |
| 14 | PVGIS (CE) | ✔ `faisabilite/viabilisation_build.py` (solaire, info) | OK (info, hors score) | 200 | — | OK |
| 15 | Parkings OSM (loi APER) | ✔ `faisabilite/viabilisation_build.py` (APER, info) | OK (info, hors score) | 200 | — | OK |
| 16 | ENS (Département) | ✔ `cascade/layers/phase1.py EnsLayer` (score) + patrimoine | OK (badge **proxy** vrai) | **000** (réseau — à revérifier) | — | OK |
| 17 | Forêts publiques (ONF) | ✔ `phase1.py ForetPubliqueLayer` (HARD_EXCLUDE) | OK | 200 | — | OK |
| 18 | Parc National (INPN) | ✔ `phase1.py ParcNationalLayer` (HARD_EXCLUDE) | OK | 200 | **était en dur** → source_millesime | **À CORRIGER→fait** |
| 19 | QPV 2024 (ANCT) | ✔ feature P-model + `api/modules.py` (bailleur) | OK | 200 | **était en dur** → source_millesime | **À CORRIGER→fait** |
| 20 | Cartofriches (Cerema) | ✔ `etage1.py FricheLayer` (bonus) + `score_v.py` | OK | 200 | ingestion tracée | OK |
| 21 | BD ORTHO 20 cm (IGN) | ✔ via dérivés `ortho_detections`/`parcel_vegetation` (score P) | OK | 200 | source_millesime `2025` | OK |
| 22 | BD ORTHO IRC (IGN) | ✔ `parcel_vegetation` (pseudo-NDVI, score P) | OK | 200 | ingestion tracée | OK |
| 23 | INSEE RP Logement 2023 | ✔ `api/app.py commune_contexte` (fiche + PDF) | OK | 200 | ingestion tracée | OK |
| 24 | Inventaire SRU (DHUP) | ✔ `commune_contexte` + `modules.py` (bailleur) + comparateur | OK | 200 | ingestion tracée | OK |
| 25 | NPNRU (DEAL/ANCT) | ✔ `commune_contexte` (table) + couche `anru` (fiche) | OK | 200 | ingestion tracée | OK |
| 26 | PLH des 5 EPCI | ✔ `commune_contexte` (`plh_epci`, rattachement EPCI) | OK (script d'ingestion absent — seed manuel, fragile) | 200 | ingestion tracée | OK |
| 27 | DVF / valeurs foncières | ✔ `cascade phase2 DvfLayer` (€/m² terrain) + accueil | OK | 200 | source_millesime + derniere_donnee (live) | OK |
| 28 | OCS GE (IGN) | ✔ `phase1.py OcsGeLayer` | OK (badge **proxy** BDCARTO vrai) | 200 | — | OK |
| 29 | ABF / Monuments historiques | ✔ `phase1.py AbfLayer` (tampons ~500 m) | OK | 200 | — | OK |
| 30 | Potentiel foncier (Région) | ✔ `phase2 PotentielFoncierLayer` + proxy SarLayer | OK | 200 | — | OK |
| 31 | DGFiP — parcelles des PM | ✔ `api/modules.py` (bloc Propriétaire) — **pas** la couche morte SRC_FF | OK | 200 | ingestion tracée | OK |
| 32 | 50 pas géométriques (DEAL) | ✔ `etage1.py CinquantePasLayer` | OK | 200 | **était en dur** → source_millesime | **À CORRIGER→fait** |
| 33 | Classement sonore ITT (Cerema) | ✔ `etage1.py BruitRouteLayer` | OK | 200 | **était en dur** → source_millesime | **À CORRIGER→fait** |
| 34 | SUP — assiettes GPU | ✔ `etage1.py SupLayer` (malus gradué) | OK | 200 | ingestion tracée | OK |
| 35 | RTAA DOM (textes) | ✔ `api/app.py` + `modules.py` (bloc 5bis, YAML `rtaa_dom`) | OK (servie par YAML versionné, pas de table) | **403** (Légifrance anti-bot — page valide) | config figée | OK |
| 36 | DEAL — PPR / aléas | ✔ `phase1.py RisquesLayer` (rouge = exclusion) | OK | 200 | ingestion tracée | OK |
| 37 | DEAL — trait de côte | ✔ `phase1.py TraitDeCoteLayer` (recul = exclude) | OK | 200 | **était en dur** → source_millesime | **À CORRIGER→fait** |
| 38 | Géorisques | ✔ 4 couches spatiales (etage1) — volet gaspar/catnat **non servi** (ops seul) | note vraie (partie non servie signalée) | 200 | ingestion tracée | OK |
| 39 | Géorisques — ICPE | ✔ `etage1.py IcpeLayer` (malus distance) | OK | 200 | ingestion tracée | OK |
| 40 | Géorisques — cavités | ✔ `etage1.py CaviteLayer` | OK | 200 | ingestion tracée | OK |
| 41 | Géorisques — mouvements de terrain | ✔ `etage1.py MvtLayer` (lu, 0 pt anti-double PPR) | OK | 200 | ingestion tracée | OK |
| 42 | Géorisques — sites et sols pollués | ✔ `etage1.py SolPollueLayer` + `api/servitudes.py` | OK | 200 | ingestion tracée | OK |
| 43 | OpenStreetMap / Overpass | ✔ `AmenitesLayer` (`parcel_amenites`) + `osm_faux_positif` | OK | 200 | — | OK |
| 44 | LiDAR HD — MNH 50 cm (IGN) | ✔ `scoring/p_model/features.py` (canopée, score P) | OK | **503** (IGN transitoire — page valide) | ingestion tracée | OK |
| 45 | BD TOPO IGN | ✔ `bati.py` (fiche) + couche `voirie`/`acces` (faisabilité) | OK | 200 | ingestion tracée | OK |
| 46 | RGE ALTI (altimétrie) | ✔ couche `pente` (phase1) + `p_model` — driver de coût | OK | 200 | ingestion tracée | OK |
| 47 | DEAL Réunion (WMS/WFS) | ✔ fiche `api/app.py` (ANRU) + `pdf_premium.py` | OK (badge **servi par proxys** vrai) | 200 | — | OK |
| 48 | GPU — zonages d'assainissement | ✔ `faisabilite/viabilisation_build.py` (assainissement) | OK (couverture 4/24 communes — note vraie) | 200 | ingestion tracée | OK |
| 49 | SAR Réunion (PEIGEO) | ✔ `phase1.py SarLayer` (indicatif) | OK (badge **proxy** vrai) | 200 | — | OK |
| 50 | Sudocuh (procédures d'urbanisme) | ✘ **MORTE** — `sudocuh_procedures` lue par aucun servi (radar = YAML) | note « squelette » vraie | 200 | source_millesime `31/12/2024` | **MORTE** |
| 51 | Urbanisme PLU/GPU (API Carto) | ✔ couches `plu_gpu_zone`/`prescription` — cœur du verdict de zone | OK | 200 | source_millesime + derniere_donnee (live) | OK |

## Corrections factuelles faites (dates en dur → lecture centralisée)
La carte `MILLESIME_VERIFIE` (front, `SourcesPage.tsx`) codait **6 millésimes en dur** RÉELLEMENT
affichés (Filosofi, Parc National, QPV, Classement sonore, 50 pas, trait de côte — les sources hors
matrice de fraîcheur, donc sans `derniere_donnee` live). Corrigé :
1. Ces 6 millésimes (+ DVF) écrits dans `data_sources.source_millesime` (le magasin centralisé, déjà
   peuplé par `persist_millesime` pour les sources de la matrice).
2. `/sources` (`api/app.py`) expose désormais `source_millesime`.
3. Front `millesimeNote` lit `s.source_millesime` (API) ; la carte `MILLESIME_VERIFIE` est **supprimée**.
Résultat : plus aucune date de millésime en dur dans le front — la valeur vient du magasin centralisé,
conforme à la doctrine (fraîcheur = donnée amont, jamais inventée au front).
