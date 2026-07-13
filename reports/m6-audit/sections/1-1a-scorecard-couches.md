# M6 §1.1a — Scorecard par couche de données (audit interne base, lecture seule)

Date : 2026-07-13 · Branche : `audit/grand-check` · Base : `postgresql://openclaw@localhost:5432/labuse`
Requêtes sources : `reports/m6-audit/sql/*.sql` · Sorties brutes : `reports/m6-audit/logs/*.log` · CSV compagnon : `1-1a-scorecard.csv`

**Méthode.** Zéro écriture (SELECT uniquement), `SET statement_timeout` 120–580 s par session. Tous les
contrôles sont **exhaustifs** (aucun TABLESAMPLE n'a été nécessaire), à une exception près, dite :
`dryrun_cascade_results` (34,3 M lignes) n'a été que dénombrée, son contrôle d'orphelins a été porté par
`cascade_results` (9,2 M lignes, exhaustif). Les tables `backup_*` (94) sont ignorées. Référentiel de
jointure : `parcels` (431 663 lignes, pivot idu/id). Les contrôles déjà faits en M5.1
(`reports/m51-unification/AUDIT-COUCHES.md`, `FRAICHEUR.md`) ne sont pas refaits : ils sont approfondis
(l'anomalie A1 est notamment **généralisée** ici, voir M6-01).

Convention verdicts : **COMPLÈTE** (couverture attendue, pas d'anomalie bloquante) ·
**PARTIELLE** (couverture incomplète chiffrée) · **À CORRIGER** (anomalie décrite, renvoi M6-xx).
Les couvertures « par construction » (ex. DVF = seules les parcelles mutées) sont notées `by design`.

---

## 1. Socle cadastre

| Couche | Volumétrie | Couverture | NULL champs clés | Bornes | Orphelins | Géométrie | Verdict |
|---|---|---|---|---|---|---|---|
| `parcels` (cadastre Etalab, éd. 2026-06) | 431 663 | référentiel (24 communes) | idu 0 · commune 0 · surface_m2 0 | surface 0,03 m² → 28 174 868 m² ; 850 < 2 m² ; 242 > 100 ha (domanial/ONF plausible) ; updated_at 28-29/06/2026 | idu unique (431 663 distincts) ; 24 paires (left(idu,5), commune) cohérentes | 0 invalide · 0 doublon md5 · **497 parcelles à cheval sur 2 communes** (810 paires, recouvrement > 1 m², voir M6-08) | **COMPLÈTE** (vigilance M6-08) |

Note : `parcels.commune` porte le **nom** de la commune (« Saint-Paul »), pas le code INSEE — le code est
dans `left(idu,5)`. Cohérence nom↔code vérifiée : exactement 24 paires distinctes.

## 2. Couches spatiales (`spatial_layers`, 1 344 844 lignes — somme exacte par kind, 32 kinds)

Scan exhaustif par kind : volumétrie, communes distinctes, geom NULL, `ST_IsValid`, doublons exacts
(`md5(ST_AsBinary(geom))`), avec ventilation doublons **inter-communes** vs **intra-commune**
(requêtes : bloc B, cf. log de session ; ventilation `sql` en tête de section détail M6-01).
**Aucune géométrie NULL ni invalide sur les 1,34 M lignes.** Les doublons sont le problème.

| Kind (source) | Volumétrie | Communes | Doublons géom (lignes excédentaires) | Verdict |
|---|---|---|---|---|
| `batiment` (BD TOPO bâti) | 817 506 | 24 | **303 576 (37 %), 100 % inter-communes** | **À CORRIGER** (M6-01) |
| `voirie` (BD TOPO) | 235 643 | 24 | **90 551 (38 %), 100 % inter-communes** | **À CORRIGER** (M6-01) |
| `pente` (RGE ALTI dérivé) | 147 398 | 24 | 0 | **COMPLÈTE** (source gelée IGN, cf. FRAICHEUR) |
| `safer` | 38 460 | 24 | 15 740 (41 %), inter-communes | **À CORRIGER** (M6-01) |
| `trait_de_cote` | 24 168 | 24 | **23 161 (96 %)** = 1 007 géométries × 24 communes | **À CORRIGER** (M6-01, cas ×24 comme A2) |
| `plu_gpu_prescription` (GPU) | 17 765 | 24 | 7 284 (41 %), quasi tout inter-communes | **À CORRIGER** (M6-01) |
| `amenite` (équipements) | 14 933 | 24 | 5 305 (36 %), inter-communes | **À CORRIGER** (M6-01 ; + A4 M5.1 subtypes hors légende) |
| `ravine` | 12 716 | 24 | 6 368 (50 %), inter-communes | **À CORRIGER** (M6-01) |
| `osm_faux_positif` (interne OSM) | 6 347 | 24 | 1 894 (30 %), inter-communes | **À CORRIGER** (M6-01) |
| `plu_gpu_zone` (PLU GPU) | 6 306 | 24 | 458 (441 groupes, 100 % inter-communes) | **À CORRIGER** (= A1 M5.1, confirmé à l'identique) |
| `water` (BD TOPO hydro) | 6 120 | 24 | 2 857 (47 %), inter-communes | **À CORRIGER** (M6-01) |
| `ocs_ge` | 3 250 | 24 | 1 607 (49 %), inter-communes | **À CORRIGER** (M6-01 ; millésime non tracé, cf. FRAICHEUR) |
| `mvt` (Géorisques BDMvt) | 3 085 | 24 | 395 (13 %) | **À CORRIGER** (M6-01, léger) |
| `sar` | 2 453 | 24 | 0 | **COMPLÈTE** |
| `potentiel_foncier` | 2 453 | 24 | 0 | **COMPLÈTE** |
| `icpe` (Géorisques) | 1 252 | 23 | 511 (41 %), **119 groupes 100 % INTRA-commune** | **À CORRIGER** (M6-03, mécanisme ≠ M6-01 : ré-ingestion) |
| `bruit_route` (sonore) | 1 004 | **25 libellés, tous hors référentiel** | 0 | **À CORRIGER** (M6-02) |
| `georisque_alea` (aléas : mouvement_terrain 917, inondation 76) | 993 | 24 | 0 | **COMPLÈTE** |
| `sol_pollue` (SIS/SSP) | 486 | 23 | 66 (28 groupes intra, 3 inter) | **À CORRIGER** (M6-03, léger) |
| `sup` (servitudes) | 417 | 24 | **294 (70 %)**, inter-communes | **À CORRIGER** (M6-01) |
| `friche` (Cartofriches) | 372 | 22 | 0 | **COMPLÈTE** (2 communes sans friche recensée, plausible) |
| `iris_insee` | 344 | 24 | 0 | **COMPLÈTE** |
| `zonage_assainissement` | 258 | **4** | 0 | **PARTIELLE 4/24 communes** (connu : 4 communes SIG, source ANC) |
| `foret_publique` | 227 | 24 | **162 (71 %)**, inter-communes | **À CORRIGER** (M6-01) |
| `abf` (MH/Mérimée) | 200 | 21 | 0 | **COMPLÈTE** (3 communes sans MH, plausible) |
| `ppr` | 164 | 24 | 0 | **À CORRIGER (mineur)** (M6-07 subtype `i` ×2) + **PARTIELLE côté littoral** : couche PPL DEAL ingérée 2/14 communes côtières (backlog connu) |
| `cinquante_pas` (50 pas géométriques) | 163 | 0 (commune NULL partout) | 0 | **COMPLÈTE** (non commune-scopée ; note : inerte à tout filtre commune=) |
| `cavite` (Géorisques) | 151 | 14 | 8 | **COMPLÈTE** (présence par commune plausible ; 8 doublons à purger avec M6-03) |
| `ens` | 73 | 21 | 39 (53 %), inter-communes | **À CORRIGER** (M6-01) |
| `parc_national` | 72 | 24 | 69 = 3 géométries × 24 | **À CORRIGER** (= A2 M5.1, confirmé) |
| `qpv` | 57 | 13 (+1 libellé « Le Port, La Possession ») | 0 | **À CORRIGER** (M6-04 : génération 2024 servie, 2025 applicable outre-mer) |
| `anru` (NPNRU) | 8 | 6 | 0 | **COMPLÈTE** (A3 M5.1 = UX, pas données) |

## 3. Couches transactionnelles

| Couche | Volumétrie | Couverture parcelles | NULL champs clés | Bornes | Orphelins / intégrité | Verdict |
|---|---|---|---|---|---|---|
| `dvf_mutations` (DVF terrain+bâti, fenêtre 2021-2025) | 29 565 | — (géolocalisée) | valeur 0 · date 0 · geom 0 · surface_terrain **14 610 (49 %)** = ventes de lots bâtis sans terrain, normal DVF | dates 01/01/2021→31/12/2025 ; VF 1 € → 30 M€ (4 > 20 M€, plausibles) | geom 100 % valides | **COMPLÈTE** |
| `dvf_mutations_parcelle` (lien parcellaire 2021-2025) | 102 551 | 37 314 parcelles (8,6 %, by design) | vf 698 (0,7 %) | dates 2021-2025 ; VF max 64 M€ ; **1 409 ventes < 100 €** (euro symbolique, à filtrer dans les stats) | **554 idus orphelins** (1 154 lignes, 1,1 %) = parcelles divisées/fusionnées depuis le millésime cadastre 2026-06 (M6-09) | **COMPLÈTE** (vigilance M6-09) |
| `dvf_mutations_histo` (2014-2020) | 110 463 | 45 078 idus | vf 133 | dates 2014-2020 ; VF max 49,8 M€ ; **222 lignes VF ≤ 0** (aberration source) | **1 957 idus orphelins** (3 261 lignes, 3,0 %) (M6-09) | **COMPLÈTE** (vigilances) |
| `dvf_secteur_medianes` | 2 357 (850 secteurs) | — | mediane_prix_m2 **439 (18,6 %)** | prix m² 50 → 9 882 € ; **n_ventes min = 1** (médianes sur 1 vente) | maj 10/07/2026 | **PARTIELLE 81,4 %** (M6-06) |
| `sitadel_permits` | 50 043 (permit_id unique) | 38 987 parcelles (9,0 %, by design) | date 0 · commune 0 · **geom 10 749 (21,5 %)** | dates 02/01/2013 → 30/05/2026 hors 1 outlier 17/08/2026 (résolu M5.1 FRAICHEUR) | **13 644 / 58 946 refs idu orphelines (23,1 %, 9 295 idus distincts)** (M6-05) | **À CORRIGER** (M6-05) |
| `bodacc_procedures` | 662 | — (par siren) | siren 0 | annonces 19/03/2008 → 02/07/2026 (retard ~8 j connu FRAICHEUR) | 175/191 sirens raccordés à `parcelle_personne_morale` (16 sans parcelle, plausible : procédures historiques) | **COMPLÈTE** |
| `bodacc_annonces_owner` | 1 418 | — | famille 0 | 03/02/2008 → 09/07/2026 | 569 sirens distincts | **COMPLÈTE** |
| `parcelle_personne_morale` (DGFiP PM, millésime en base « 2025 ») | 82 701 (idu unique) | 82 066 parcelles (19,0 %) | siren 1 · denomination 0 | millésime unique 2025 | **635 idus orphelins** (0,8 %) (M6-09) | **COMPLÈTE** (vigilance M6-09 ; voir note millésime §6) |
| `pm_proprietaires_millesimes` (panel) | 461 570 | 72 709 → 81 161 idus/an | siren **7 868 en 2019 (10,8 %)**, ≤ 30 ensuite | millésimes 2019→2024 (6 points, panel étendu depuis MEMORY 2021-2024) | idus obsolètes/an : 3 754 (2019) → 1 067 (2024), décroissance cohérente avec les remaniements cadastraux (M6-09) | **COMPLÈTE** (qualité siren 2019 dégradée, source) |
| `pm_dirigeants` (INPI/RNE) | 27 146 | 9 337 sirens, **100 % raccordés** aux propriétaires PM | nom 3 185 (11,7 %, dirigeants personnes morales) · date_naissance **7 294 (26,9 %)** | 26 318 actifs | 0 orphelin siren | **COMPLÈTE** |
| `pm_dirigeant_gigogne` | 2 124 | 586 sirens | — | — | — | **COMPLÈTE** |
| `owner_enrichment` | 9 730 | 9 730 sirens (source recherche_entreprises) | denomination 27 | — | — | **COMPLÈTE** |
| `owner_denom_lookup` | 2 650 | — | — | statuts : **not_found 2 412 (91,0 %)**, found 134, ambiguous 104 | — | **PARTIELLE 9 %** de résolution (M6-06) |
| `dpe_records` (ADEME 974) | 914 (numero_dpe unique) | 903 rattachées (0,21 % des parcelles ; gisement local complet, décision Cerema actée) | parcelle_idu 11 (1,2 %) · etiquette 0 | dates 06/07/2021→03/07/2026 ; surfaces 13-930 m² OK ; **annee_construction min 1761, 6 valeurs < 1900 ou > 2026** (source) | 0 idu orphelin | **COMPLÈTE** (périmètre connu) |
| `adresses` (BAN) | 339 941 (id_ban unique) | 24 communes | idu 21 (0,006 %) · geom 0 · voie 0 | refreshed 11/07/2026 | 0 idu orphelin | **COMPLÈTE** |
| `adresse_parcelles` (BAN↔parcelle) | 416 357 | **257 145 parcelles (59,6 %)** — parcelles non bâties sans adresse, by design | — | — | 0 orphelin côté parcels ET côté adresses (clé bidirectionnelle saine) | **COMPLÈTE** |
| `rnic_coproprietes` | 2 220 (immatriculation unique) | 22/24 communes (absentes : 97419, 97424 — plausible, zéro copro immatriculée) | parcelle_idu 0 · nb_lots 0 · geom 0 | lots 2 → 860 | 0 idu orphelin (rattachement 100 %, conforme MEMORY) | **COMPLÈTE** |
| `rpls_commune` | 24 | 24/24 communes | — | millésime 2025-01 ; 62 → 25 185 logements/commune, total 87 553 | — | **COMPLÈTE** |
| `filosofi_carreaux_200m` (INSEE 2021) | 14 773 (idcar unique) | — (carroyage) | geom 0 | ind 1→1 258, men 0,2→520, aucun ind<0, aucun men_pauv>men | 0 géom invalide, 0 doublon | **COMPLÈTE** |
| `catnat_arretes` | 239 | 24 communes, 100 % insee 974 | type_peril 0 | arrêtés 18/05/1993 → 08/07/2025 | — | **COMPLÈTE** |
| `parcel_veille_succession` | 7 092 (idu unique) | 1,6 % (by design : PM à dirigeant âgé) | age 7 | âges 70 → **117** ; 3 > 110 ans (aberration état-civil RNE) | 0 idu orphelin | **COMPLÈTE** (vigilance 3 âges) |

## 4. Couvertures dérivées parcellaires

Jointures exhaustives sur `parcels` (idu ou id). **Aucun orphelin sur AUCUNE des 13 tables dérivées**
(remarquable — les couvertures ont été recalculées après le cadastre 2026-06) ; les seuls idus obsolètes
de la base sont dans les couches transactionnelles historiques (M6-09).

| Couche | Volumétrie | Parcelles couvertes (% de 431 663) | Bornes contrôlées | Verdict |
|---|---|---|---|---|
| `parcel_terrain` (pente RGE) | 423 452 | 423 452 (**98,1 %**) | pente moy 0-69,4°, max 0-88,7°, 0 hors [0;90] ; 86 885 terrassement lourd | **PARTIELLE 98,1 %** (8 211 parcelles sans pente) |
| `parcel_solar` (PVGIS/SARAH3) | 431 663 | 431 663 (**100 %**) | prod 950 → 1 598 kWh/kWc (plausible 974, limite côtière connue MEMORY) ; score 0-100 ; 0 NULL | **COMPLÈTE** |
| `parcel_vegetation` (LiDAR MNH + IRC/NDVI) | 426 107 | 426 107 (**98,7 %**) | NDVI −0,698 → 0,905 (⊂ [−1;1]) ; canopée 0-100 ; 0 aberrant, 0 NULL | **PARTIELLE 98,7 %** (5 556 manquantes) |
| `vegetation_zonal_acc` | 1 156 556 | 426 107 (98,7 %) | — (accumulateur interne) | **COMPLÈTE** (raccord exact parcel_vegetation) |
| `parcel_anc` | 278 685 | 278 685 (**64,6 %**) | proba 5-95 ; zone_anc : vide 220 973 (79 %), collectif 47 803, anc 9 909 — zonage opposable limité aux 4 communes SIG | **PARTIELLE 64,6 %** (périmètre résidentiel ; zonage 4/24 communes) |
| `parcel_residuel_bati` | 292 056 | 292 056 (67,7 %, périmètre bâti by design) | emprise résiduelle 0 → 106 279 m², 0 négative ; hauteur max 4-34 m, 0 aberrante | **COMPLÈTE** (périmètre) |
| `parcel_residuel` | 263 626 | 263 626 (61,1 %, périmètre calcul by design) | — | **COMPLÈTE** (périmètre) |
| `parcel_vue_mer` | 150 642 | 150 642 (**34,9 %**, périmètre littoral by design) | oui 92 420 · partielle 17 144 · non 41 078 ; distances 0-8 143 m, 0 négative ; obstruction cohérente par classe (oui 0-10, partielle 10-35, non 35-100) | **COMPLÈTE** (périmètre ; +1 ligne vs M5.1 : 150 642/92 420) |
| `parcel_amenites` | 431 663 | 431 663 (**100 %**) | distances 0 → 8,7-14,6 km, 0 négative, 0 NULL | **COMPLÈTE** |
| `parcel_equipements` (piscines/PV) | 11 558 | 11 558 (2,7 %, table de détections by design) | 8 299 piscines (raccord MEMORY wave-ortho), surfaces 10-144,8 m², 0 hors bornes ; **pv_detecte = 0 partout** alors que `ortho_detections` porte 23 529 détections `pv` → propagation PV volontairement non faite (stub Option B, consigné) | **COMPLÈTE** (PV en attente, connu) |
| `module_division` | 4 433 | 4 433 (1,0 %, périmètre module) | lots 200-1 675 m², score 69-99 | **COMPLÈTE** (périmètre) |
| `parcel_signals` | 69 357 | 67 969 (15,7 %, événementiel) | — | **COMPLÈTE** |
| `mvt_parcels` (tuiles) | 431 663 | 431 663 (**100 %**, 0 NULL status/tier/geom) | vue_mer oui = 92 419 (raccord M5.1) | **COMPLÈTE** |
| `mvt_overlays` (tuiles) | 6 470 = 6 306 plu + 164 ppr | — | raccord exact `spatial_layers` (idem M5.1) — **hérite des doublons M6-01/A1** | **COMPLÈTE** (raccord) |

## 5. Solaire, ortho, réseaux, commune

| Couche | Volumétrie | Couverture | NULL / bornes | Orphelins / géom | Verdict |
|---|---|---|---|---|---|
| `ortho_detections` | 43 448 (pv 23 529 · piscine 19 899 · vegetation 20) | — | idu NULL 70 (pv) ; confiance 0,295-1 ⊂ [0;1] ; surfaces piscine 10-149,9, pv 4-383 m² ; validation : NULL 41 815 (96 %, jugées machine), ok 819, faux_positif 814 | 0 idu orphelin | **COMPLÈTE** |
| `ortho_tiles` | 5 041 | millésime 2025 unique ; 0 non traitée (ortho, pv, veg) | geom 0 NULL | — | **COMPLÈTE** |
| `parkings_aper` | 901 | 1 696 refs idu, **0 orpheline** | surfaces 800-27 406 m² (0 < 500) ; échéances 01/07/2026-01/07/2028, 24 dépassées (raccord MEMORY) ; 31 sans idu | geom 0 NULL | **COMPLÈTE** |
| `pv_registry` (registre EDF/ODRÉ) | 686 | 24 communes | puissance 37-10 452 kW, 0 ≤ 0 ; dates 2003-2025, 0 future | **geom NULL 686/686 (100 %)** — registre à la commune, non géolocalisé | **PARTIELLE** (pas de géolocalisation, M6-06) |
| `solar_grid` | 15 680 | île (grille) | prod 759,9-1 603,5 (1 seul point < 800, marge) ; GHI 989-2 095 | geom 0 NULL | **COMPLÈTE** |
| `grid_capacity` | 24 | — | **capa_dispo_mw = 0 sur 24/24 lignes ET geom NULL 24/24** | — | **À CORRIGER** (M6-10 : table placeholder sans donnée) |
| `anru_quartiers` | 8 | 6 communes (raccord couche anru) | code_qpv 0 NULL | — | **COMPLÈTE** |
| `rgealti_pente_5m` (raster) | 2 793 tuiles | île | — | — | **COMPLÈTE** (source RGE ALTI gelée → bascule MNT LiDAR HD, cf. FRAICHEUR) |
| `anc_maille_taux` (EGOUL RP2022) | 350 | 24 communes | taux 0-100 (échelle **%**, pas [0;1]) ; millésime RP2022 | — | **COMPLÈTE** |
| `commune_insee_logement` | 24 | 24/24 | RP 2023 ; logements 2 515-76 819 | — | **COMPLÈTE** |
| `commune_contexte_sru` | 24 | 24/24 | inventaire LLS 2024 ; taux 2,8-60,7 % | — | **COMPLÈTE** |
| `plh_epci` | 5 | 5/5 EPCI | obj 800-1 800 logts/an (raccord MEMORY plh) | — | **COMPLÈTE** |
| `conso_baseline_commune` | 24 | 24/24 (2024) | 2 388-3 826 kWh/an/logement, plausible 974 | — | **COMPLÈTE** |

## 6. Dérivées scoring (pour mémoire — volumétrie + intégrité seulement)

| Table | Volumétrie | Parcelles distinctes | Intégrité |
|---|---|---|---|
| `cascade_results` | 9 206 258 | 431 663 (100 %) | 0 parcel_id orphelin (exhaustif) |
| `dryrun_cascade_results` | 34 310 660 (reltuples) | — | non contrôlée orphelins (volume) — couvert via cascade_results |
| `parcel_evaluations` | 1 001 622 | 431 663 | — |
| `dryrun_parcel_evaluations` | 1 118 979 | 431 663 | — |
| `parcel_p_score_v2` | 431 663 | 431 663 | 0 doublon, 0 idu orphelin |
| `parcel_v_score` | 431 663 | 431 663 | — |
| `score_snapshot_parcelles` | 1 294 989 | — | snapshots gelés v1.2/v1.3 |

**Note millésime DGFiP PM** : `parcelle_personne_morale.millesime = '2025'` (unique) alors que
FRAICHEUR (12/07) indiquait « max millésime 2024 » pour le panel et « 2025 publié » à ingérer. Lecture :
la table courante est étiquetée 2025 tandis que le panel `pm_proprietaires_millesimes` s'arrête à 2024
— l'ajout du point 2025 au panel (priorité n°1 FRAICHEUR) reste dû, et le panel couvre désormais
2019-2024 (6 points, étendu depuis la note mémoire 2021-2024).

---

## Détail des anomalies (M6-xx)

### M6-01 — **P1 · Doublons géométriques inter-communes généralisés dans `spatial_layers` : ~460 000 lignes excédentaires (34 % de la table)**
L'anomalie A1 de M5.1 (441 doublons `plu_gpu_zone`) n'est **pas un cas isolé** : le même mécanisme
d'ingestion par commune (objets chevauchant une limite communale ingérés une fois PAR commune) touche
**17 kinds**. Ventilation exhaustive (requête ci-dessous) : batiment 303 576 · voirie 90 551 ·
trait_de_cote 23 161 · safer 15 740 · plu_gpu_prescription 7 284 · ravine 6 368 · amenite 5 305 ·
water 2 857 · osm_faux_positif 1 894 · ocs_ge 1 607 · plu_gpu_zone 458 (A1) · mvt 395 ·
sup 294 · foret_publique 162 · parc_national 69 (A2) · ens 39 · cavite 8 → **≈ 459 800 lignes**,
auxquelles s'ajoutent 577 doublons intra-commune (icpe 511, sol_pollue 66, M6-03).
Cas extrêmes « ×24 » : `trait_de_cote` (1 007 géométries × 24) et `parc_national` (3 × 24, = A2).
**Impact** : toute cascade/statistique qui somme des intersections par kind est exposée au même
gonflement que le témoin AB1341 de M5.1 (recouvrement compté deux fois) — en particulier bâtiment
(emprise bâtie), voirie (accès/largeur) et prescriptions PLU. Réparation : dédoublonnage à l'ingestion
+ re-run cascade (déjà qualifiée NON TRIVIALE en M5.1, à mettre au périmètre du prep-recompute).
```sql
WITH d AS (
  SELECT kind, md5(ST_AsBinary(geom)) h, count(*) n, count(DISTINCT commune) nc
  FROM spatial_layers GROUP BY 1,2 HAVING count(*)>1)
SELECT kind, count(*) grp, sum(n)-count(*) lignes_excedentaires,
       count(*) FILTER (WHERE nc>1) inter_communes, count(*) FILTER (WHERE nc=1) intra
FROM d GROUP BY kind ORDER BY 3 DESC;
```

### M6-02 — **P1 · `bruit_route` : libellés commune hors référentiel (couche invisible en mode commune)**
Les 1 004 lignes portent des libellés en MAJUSCULES non conformes au référentiel (`parcels.commune`,
format « Saint-Joseph ») : 25 libellés distincts dont **deux graphies concurrentes** pour Saint-Joseph
(« SAINT JOSEPH »/« SAINT-JOSEPH ») et Saint-Louis. Conséquence : tout filtre `commune=` (dont
`/map/layers.geojson?kind=...&commune=X`) ne matche **aucune** ligne de cette couche → la couche
sonore est de fait morte en mode commune. Requête :
`SELECT kind, count(*) FROM spatial_layers WHERE commune NOT IN (SELECT DISTINCT commune FROM parcels) GROUP BY kind;`
→ bruit_route 1 004 (100 %) ; qpv 2 (libellé composite « Le Port, La Possession »).

### M6-03 — **P2 · `icpe` : 511 doublons intra-commune (41 % de la couche)**
119 groupes de géométries strictement identiques **au sein de la même commune** (contrairement à
M6-01) : signature d'une double/multiple ingestion du même flux Géorisques (created_at unique
10/07/2026). Idem `sol_pollue` (28 groupes intra, 66 lignes) et `cavite` (8). Purge simple par
`DISTINCT ON (md5(geom))` à la ré-ingestion.

### M6-04 — **P1 · QPV : génération 2024 en base, génération 2025 applicable aux outre-mer**
`SELECT attrs->>'generation', count(*) FROM spatial_layers WHERE kind='qpv' GROUP BY 1;` → **2024 : 57**
(aucun périmètre 2025). Confirme au niveau des attributs la vigilance FRAICHEUR (les QPV 2025
outre-mer sont en vigueur depuis le 01/01/2025) : la couche est datée pour tout usage fiscal/scoring.

### M6-05 — **P1 · Sitadel : rattachement parcellaire dégradé (23,1 % de refs orphelines) + 21,5 % sans géométrie**
Sur 58 946 références IDU portées par `idu_codes`, **13 644 (23,1 %)** ne correspondent à aucune
parcelle du cadastre 2026-06 (9 295 idus distincts) — permis anciens (dès 2013) dont les parcelles ont
été divisées/fusionnées, ou idus source erronés. S'y ajoutent **10 749 permis sans géométrie (21,5 %)**.
L'historique de permis par parcelle (signal scoring) est donc structurellement sous-estimé sur les
parcelles remaniées. Piste : re-résolution des idus orphelins via filiation cadastrale ou géocodage
(cf. aussi mémoire Sainte-Suzanne 64,6 % géocodés).

### M6-06 — **P2 · Trois couches à taux de remplissage faible**
(a) `dvf_secteur_medianes` : 439/2 357 lignes (18,6 %) sans `mediane_prix_m2` et `n_ventes` min = 1 —
des médianes assises sur une seule vente sont servies au même rang que les autres (pas de flag de
fiabilité). (b) `owner_denom_lookup` : 91,0 % `not_found` (2 412/2 650) — la résolution
dénomination→siren ne débouche presque jamais. (c) `pv_registry` : 686/686 lignes sans géométrie
(registre à la commune) — inutilisable pour du rapprochement parcellaire direct.

### M6-07 — **P3 · `ppr` : 2 lignes au subtype non normalisé `i`**
`SELECT commune,name,subtype FROM spatial_layers WHERE kind='ppr' AND subtype='i';` → 2 lignes
« PPR inondation » à Saint-Philippe, hors taxonomie (`PRESCRIPTION` 88 / `INTERDICTION` 74). Tout
code qui filtre sur les deux subtypes canoniques ignore ces 2 zones.

### M6-08 — **P2 · Cadastre : 497 parcelles à cheval sur deux communes**
810 paires de parcelles de communes différentes se recouvrent de plus de 1 m²
(`ST_Area(ST_Intersection(a.geom_2975,b.geom_2975))>1`, exhaustif). Imperfections d'assemblage Etalab
le long des limites communales ; combinées à M6-01, elles font des bordures communales la zone la
moins fiable de la base (double comptage possible de surfaces/recouvrements).

### M6-09 — **P2 · Idus obsolètes dans les couches transactionnelles (parcelles divisées/fusionnées)**
Mesure directe de la dérive cadastre : `dvf_mutations_parcelle` 554 idus orphelins ·
`dvf_mutations_histo` 1 957 · `parcelle_personne_morale` (2025) 635 ·
`pm_proprietaires_millesimes` : 3 754 (2019) → 3 279 → 2 590 → 2 161 → 1 525 → 1 067 (2024) ·
`sitadel_permits` 9 295 (cf. M6-05). La décroissance monotone du panel PM confirme qu'il s'agit bien
de remaniements cadastraux (≈ 500-700 parcelles/an disparaissent du référentiel). Aucune couche
**dérivée** (parcel_*) n'a d'idu obsolète : les recomputes post-cadastre 2026-06 sont sains.

### M6-10 — **P2 · `grid_capacity` : table vide de contenu**
24 lignes, `capa_dispo_mw = 0` partout et `geom` NULL partout : placeholder jamais alimenté (capacités
d'accueil réseau — la source Data Fair EDF SEI est identifiée en mémoire). À alimenter ou à retirer des
dépendances produit.

---

## Synthèse des verdicts

- **COMPLÈTE : 48 couches** (dont tout le socle scoring, BAN, DVF, PM/INPI, DPE, RNIC, RPLS, Filosofi, catnat, dérivées parcellaires à 100 %).
- **PARTIELLE : 7** — zonage_assainissement (4/24 communes), ppr volet littoral (2/14 côtières),
  parcel_terrain (98,1 %), parcel_vegetation (98,7 %), parcel_anc (64,6 %), dvf_secteur_medianes (81,4 %),
  owner_denom_lookup (9 % résolus), pv_registry (0 % géolocalisé).
- **À CORRIGER : 20** — 17 kinds `spatial_layers` au titre des doublons M6-01/M6-03 (dont batiment,
  voirie, plu_gpu_zone=A1, parc_national=A2), bruit_route (M6-02), qpv (M6-04), sitadel_permits (M6-05),
  grid_capacity (M6-10), ppr subtype (M6-07, mineur).

Priorités : **M6-01 (doublons inter-communes, impact scoring — englobe et généralise A1)**,
**M6-02 (bruit_route inerte)**, **M6-04 (QPV 2025)**, **M6-05 (Sitadel rattachement)** ; M6-03/08/09/10 à
coupler au prep-recompute déjà au backlog.
