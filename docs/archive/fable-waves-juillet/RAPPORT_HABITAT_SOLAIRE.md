# Rapport de fin — mandat Habitat Solaire (pack data installateurs PV)

**Branche** : `feat/habitat-solaire` (12 commits atomiques, jamais mergée — merge Vic `--no-ff`).
**Ordre exécuté** : socle → 1 → 5 → 2 → 6 → 3 → 4 → 7 → 9 → 8(stub) → QA.
**QA** : 16/16 pytest (dont résilience base sans `parcel_solar`) + E2E Playwright **10/10**
(`qa/e2e_habitat_solaire.mjs` : 3 vues, exports non vides, 2 viewports, mesure fine = 501).

---

## Volumétries par table

| Table | Lignes | Notes |
|---|---|---|
| `solar_grid` | 15 680 | grille 400 m, 100 % des points renseignés (0 échec réseau) |
| `parcel_solar` | 431 663 | **100 %** des parcelles avec `prod_spec_kwh_kwc` (critère ≥ 95 %) |
| `parkings_aper` | 901 | dont **736 assujettis** (> 1 000 m²) |
| `pv_registry` | 686 | filière solaire 974 (661 individualisées ≥ 36 kVA) |
| `grid_capacity` | 24 | postes sources, capacités S3REnR (geom NULL — voir Lot 7) |
| `solar_api_cache` | 0 | stub Lot 8 (TTL 30 j + purge cron prêts) |
| `conso_baseline_commune` | 24 | baseline résidentielle EDF SEI, millésime 2024 |
| `mv_toitures_tertiaires` | 9 635 | matview Lot 6 |

Colonnes remplies de `parcel_solar` : score_solaire 431 663 (percentile 0-100) ·
conso/facture 266 056 (bâties résidentielles) · azimut 271 157 (confiance haute 118 043) ·
proba_proprio_occupant 431 663 (médiane 62) · flag_abf 60 618 vrais · flag_amiante 195
(DPE pilote : 910 lignes, attendu) · flag_topo_ombrage 264 vrais · pv_existant
'commune_forte_densite' 73 427 · repowering 0 (voir Lot 4).

## Sanity check Ouest/Est (Lot 1) — ÉCHEC de l'hypothèse, ingestion VÉRIFIÉE fidèle

Médianes (kWh/kWc/an, aspect nord, horizon topo inclus) : Saint-Leu 1 324 · Saint-Paul 1 308
· **Sainte-Rose 1 482** · Salazie 1 255 → Ouest ≤ Est, le critère du mandat n'est pas vérifié.

**Investigation menée avant de continuer** (exigence du mandat) :
1. *Fidélité de l'ingestion* : sondes directes sur l'API — Sainte-Rose bourg **1 481,99** brut
   vs **1 481,8** interpolé commune ; Saint-Gilles 1 291,5. Le pipeline reproduit la source
   au point près → l'ingestion n'est PAS fausse.
2. *La source elle-même* : PVGIS **SARAH3** (v5_3) donne la côte Est ≥ la côte Ouest à La
   Réunion ; **SARAH2** (1 419 vs 1 447) et **ERA5** (1 690 vs 1 679, maille ~30 km) non plus
   ne reproduisent pas le gradient côtier attendu (climatologie locale : l'Ouest sous le vent
   est réputé le plus ensoleillé). Limite connue des produits satellite/réanalyse sur une
   petite île montagneuse — aucune base PVGIS n'y échappe, et PVGIS est LA source du mandat.
3. *Ce qui est bien capté* (décisif pour le score) : le gradient d'ALTITUDE/relief —
   Plaine-des-Palmistes 1 227, Salazie 1 255, Cilaos 1 293 vs côtes 1 300-1 540 — et
   l'horizon topographique (usehorizon=1, flag ombrage intra-communal : 264 parcelles,
   ex. ravines de Saint-Denis 53).

**Conséquence produit** : le score est fiable pour discriminer hauts/bas et poches d'ombrage ;
la nuance côte Ouest/côte Est est NON DISCRIMINANTE dans cette baseline (à dire tel quel en
démo ; la mesure fine Lot 8 l'affinera par toit). Le CLI affiche l'avertissement documenté.
Paramètre notable : **aspect = 180 (plein nord)** — hémisphère sud, +15 % vérifié vs sud ;
rappel « versant nord optimal » affiché dans l'UI.

## Dataset EDF SEI retenu (Lot 2) — maille COMMUNE

`Consommation annuelle par commune - La Réunion` (portail Data Fair EDF SEI —
l'ancienne API Opendatasoft est morte, 410), secteur Résidentiel, **millésime 2024**,
baseline = MWh / points de soutirage (ex. Bras-Panon 3 214 kWh/an/logement). **La maille
IRIS n'existe pas pour le 974** : le jeu IRIS national de conso est Enedis (métropole
seulement) — documenté dans seed_sources. Modèle additif (config) : baseline × ratio de
surface (DPE sinon emprise × 0,9, borné 30-300 m², ratio 0,5-2,5) ; bonus **ECS/clim câblés
mais inertes** (champs absents de la vague DPE pilote — s'activeront à la réingestion
complète) ; bonus piscine en attente du mandat Détection Ortho. Résultat : 266 056
parcelles, facture min/méd/max = **20 / 140 / 200 €/mois** (garde-fou mandat 80-180 : OK).
Libellé UI : « estimation statistique », jamais une donnée réelle.

## Parkings APER (Lot 3) — seuil Réunion VÉRIFIÉ = 1 000 m²

Textes vérifiés : loi 2023-175 art. 40 (≥ 50 % ombrières, mixte PV/végétal depuis la loi
Huwart) ; décret 2024-1023 (surface = places + voies ; exemptions arbres/technique/coût) ;
**décret 2025-802 du 11/08/2025 : seuil outre-mer adapté — La Réunion 1 000 m²** (et non
1 500). Échéances : 01/07/2026 (≥ 10 000 m², **DÉPASSÉE** — sanction jusqu'à 40 k€/an) ;
01/07/2028 (1 000-10 000 m², 20 k€/an). Tout en config.

| Tranche | Parkings | Avec SIREN (PM) |
|---|---|---|
| ≥ 10 000 m² (échéance dépassée) | 24 | 22 |
| 1 000-10 000 m² | 712 | 632 |
| **Total assujettis** | **736** | **654 (89 %)** |
| sous seuil (détection 800-1 000 m²) | 165 | 152 |

870/901 rattachés à ≥ 1 parcelle ; signal `aper_deadline` sur 1 466 parcelles (statut
depassee/a_venir + sanction au payload). Source OSM (couche déjà en base, 24 communes,
dédup osm_id) : volumétrie = PLANCHER déclaratif, pas un recensement (« dizaines à petites
centaines » attendu par le mandat : on est à 736, mesure du polygone OSM entier). `equipe`
NULL (pas de détection ombrière sans ML ortho) ; `exempt_probable` NULL (pas de couche
végétation en base — non sur-ingéniéré).

## Parc PV & repowering (Lot 4)

Extrait Réunion du registre national (EDF SEI Data Fair = donnée ODRÉ, MAJ 30/06/2026) :
686 lignes solaires (661 individualisées, agrégats communaux < 36 kVA). `pv_existant =
'commune_forte_densite'` : top quartile de densité (petites installations / 1 000 rés.
principales) = 6 communes (97401, 97403, 97404, 97405, 97408, 97413) → 73 427 parcelles.
**Repowering : 309 installations** mises en service 2006-2013 (contrats 20 ans → 2026-2033)
mais **0 parcelle flaggée** : le millésime anonymise les noms (« Confidentiel ») sans adresse
ni géométrie → rattachement parcellaire impossible ; le code pose le flag dès qu'une géoloc
existera ; le vivier reste exploitable par commune/IRIS. Stub `detect_rooftop_pv`
(NotImplementedError + approche documentée, mandat Détection Ortho).

## Capacités réseau (Lot 7) — PRÉSENTES, sans géométrie

Jeu « Capacités d'accueil du réseau - Corse & Outre-Mer » (EDF SEI) : 24 postes sources,
**capacité restante S3REnR = 0 MW sur TOUTE l'île** (avril 2026) — réseau saturé côté
injection, argument commercial autoconsommation. La cartographie des postes a été
**dépubliée** (« sécurité publique ») → geom NULL, la distance au poste de la vue tertiaire
reste NULL (colonne prête).

## Statut Lot 8 — STUB (two-tier = PVGIS pur)

Vic n'a pas confirmé le quickcheck de couverture 974 → conformément au mandat : endpoint
`POST /solaire/mesure/{idu}` = **501 honnête**, AUCUN bouton côté front (leçon TANIA),
table `solar_api_cache` + TTL 30 j STRICT + purge cron (`solaire-cache-purge`) + quotas en
config (100/j/client, breaker global 350/j) prêts. Reste à faire à l'activation : client
buildingInsights, attribution Google UI, **hard cap console GCP (action Vic)**.

## Vues livrées (Lot 9) — convergence : vues = PRESETS du moteur

- **Prospection PV résidentiel** = preset `pv-residentiel` du moteur de segments (score ≥ 60,
  Maison, facture/proprio-occupant/ombrage en optionnels modifiables) : **2 523 parcelles**,
  export « à l'occupant » avec colonnes solaires. `chauffe-eau-solaire` : 6 (étroit par la
  donnée DPE pilote, pas par le moteur). 6 nouveaux filtres + 5 colonnes + 2 tris au registry.
- **Parkings APER** (outil M23) : carte + table triée par échéance, badge « échéance
  dépassée » distinct, filtres tranche, export CSV.
- **Toitures tertiaires** (outil M24) : 9 635 toitures > 500 m² (6 027 avec PM, 1 133 avec
  bilan INPI), tri potentiel = emprise × score, export CSV.
- **Onglet Solaire de la fiche** : score, prod spécifique, facture (« estimation
  statistique »), azimut (+ « versant nord optimal »), badges ABF/amiante/ombrage/PV/
  repowering, alertes APER — chaque bloc SOURCÉ.

## Paramètres config à valider par Vic (défauts posés)

| Paramètre | Défaut | Où |
|---|---|---|
| `LABUSE_TARIF_ELEC_EUR_KWH` | 0,25 €/kWh TTC | settings (tarif bleu — à ajuster) |
| Modèle conso (ratio surface 0,5-2,5, réf. 90 m², ECS +1 500, clim +20 %, piscine +2 000) | — | `config/habitat_solaire.yaml` |
| Seuils APER (1 000 m² Réunion, tranches, échéances, sanctions 20/40 k€) | textes 2026 | idem |
| Repowering 2006-2013, quartile densité 0,75 | mandat | idem |
| Seuil tertiaire (emprise > 500 m²), seuil ombrage (80 % médiane), élongation azimut (1,4) | mandat | idem |
| Quotas Lot 8 (100/j/client, 350/j global, TTL 30 j) | mandat | settings |
| PVGIS : aspect 180 (nord), angle 15°, loss 14 %, pas 400 m, 10 req/s | mandat + hémisphère sud | settings/YAML |

## Actions Vic (hors mandat)

1. **Merge `--no-ff`** de la branche (12 commits) ; puis installer le cron VPS :
   `deploy/cron.d/solaire` (refresh mensuel registre/capacités/parkings/flags/conso/tertiaire
   + purge cache — le PVGIS, climatologique, est one-shot).
2. **Quickcheck Google Solar 974** (buildingInsights, requiredQuality=BASE) : si positif, dire
   GO pour l'implémentation Lot 8 + poser `LABUSE_SOLAR_API_KEY` + **hard cap console GCP**.
3. **Valider le tarif élec** (0,25 €/kWh) et les coefficients du modèle de facture.
4. **Décision commerciale** sur le message score : « gisement fiable altitude/relief,
   nuance côtière non discriminante (limite satellite) » — éviter la sur-promesse en démo.
5. À la **réingestion DPE complète** (vague post-pilote) : les bonus ECS/clim et le flag
   amiante montent en volume sans code (champs déjà câblés).

## Divers

- Bug de plan corrigé en QA : CTE d'agrégat inlinée dans un UPDATE (recalcul en boucle,
  > 10 min) → `MATERIALIZED` (secondes).
- Repli de tri : `score_solaire_desc` sans `parcel_solar` → `surface_desc` (résilience 16/16).
- Les portails EDF SEI et Agence ORE ont migré d'Opendatasoft vers **Data Fair**
  (`/data-fair/api/v1/datasets/{id}/lines`) — les anciennes URLs répondent 410.
- Dette pyproj préexistante inchangée (session dédiée déjà prévue).
