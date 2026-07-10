# RAPPORT DATA GAP — audit & complétion des sources (mandat 10/07/2026)

Branche `feature/data-gap-2026-07` (depuis main, tag `score-v1.1` inclus). **Phase 0 : audit
réel du code et de la base** — rien n'est supposé, chaque statut a été vérifié (tables,
`spatial_layers`, modules d'ingestion, `config/cascade_rules.yaml`, cascade étages 0/1/2).
La Phase 1 (colonnes « Décision Phase 1 ») sera complétée lot par lot.

## Socle confirmé PRÉSENT (hors lots)

| Source | Où (code / base) | Notes |
|---|---|---|
| PLU calibrés 23 communes + St-Philippe RNU | `config/communes_gold_standard.yaml`, `plu_*.yaml`, couches `plu_gpu_zone` (6 306) / `plu_gpu_prescription` (17 765), cascade `zonage_plu_gpu`+`prescription_plu` | ✓ |
| Cadastre / parcelles | `parcels` = 431 663, geom_2975, centroïdes | ✓ |
| Propriétaires PM (DGFiP) | `parcelle_personne_morale` = 82 701 liens | ✓ + enrichissements Score V |
| BODACC | `bodacc_procedures`, `bodacc_annonces_owner`, étage 2 + Score V | ✓ |
| INPI RNE | `pm_dirigeants` (27 146), gigogne, étage 2 `age_dirigeant` | ✓ |
| Géorisques PPR + aléas | couches `ppr` (164), `georisque_alea` (993), `icpe`, `cavite`, `mvt`, cascade `risques` | ✓ |
| Cartofriches | couche `friche` (372), étage 1 POSITIVE | ✓ |
| DPE ADEME | `dpe_records` (910 — base 974 intrinsèquement mince), étage 2 flag | ✓ |
| QPV 2024 | couche `qpv` (57), fiscal fiche | ✓ |
| ABF / Mérimée | couche `abf` (200), cascade UNKNOWN covisibilité | ✓ |
| ENS | couche `ens` (73), SOFT_FLAG moyen | ✓ |

## Lots cibles — statut d'audit

| Lot | Source cible | Statut | Où dans le code / la base | Manque exact |
|---|---|---|---|---|
| 1 | DVF Etalab 974 | **PARTIEL** | `dvf_mutations_parcelle` (102 551 lignes, 37 868 parcelles, **millésimes 2021-2025 seuls** — 2014-2020 retirés de la distribution) ; `dvf_mutations` (points, bonus étage 2 existant) | Variables par parcelle (prix / prix·m² dernière mutation) non matérialisées ; **médiane €/m² par secteur × type de bien** absente. Flag « >20 ans » incalculable (consigné). Aucun scoring dormance (Score V le fait déjà). |
| 2 | SIS + CASIAS | **PARTIEL** | Géorisques `/ssp` ingéré : couche `sol_pollue` = 480 (tous `identifiant_ssp`, 424 `identifiant_casias`) ; cascade étage 1 `sol_pollue` ≤ 50 m SOFT_FLAG **faible** (`etage1.py:71`) | Distinction SIS (intersection périmètre) vs CASIAS (< 100 m) absente ; malus actuel = faible/info, mandat = malus Stage 1 + mention fiche coût dépollution |
| 3 | PEB + classement sonore | **ABSENT** | rien (aucune couche, aucun module) | Tout — sources à identifier (GPU/DEAL : PEB Roland-Garros + Pierrefonds, classement sonore ITT 974) |
| 4 | SUP complètes (GPU) | **ABSENT** | rien — API Carto GPU `assiette-sup-s/l/p` vérifiée VIVANTE sur le 974 (acte-sup répond à St-Denis) | Tout (I4, canalisations, T4/T5/T7, autres) |
| 5 | SAR / SMVM | **PARTIEL** | couche `sar` (2 453) = **PROXY** vocation via « potentiel foncier » Région ODS (couverture partielle, îlots seulement) ; vocations dont « Coupure d'urbanisation » (~23) et « Espace d'urbanisation prioritaire » présentes ; cascade : INFO SANS pouvoir d'exclusion (décision Vic 08/07/2026, `phase1.py:129`) | Le SAR **réglementaire** (zonage complet DEAL/Région + SMVM) : à retrouver ; si introuvable → BLOQUÉ (le proxy reste informatif, décision 08/07 respectée) |
| 6 | 50 pas géométriques | **ABSENT** | rien | Tout — source DEAL/ONF à identifier |
| 7 | Périmètres irrigués (ILO/PEIGEO) | **ABSENT** | rien (PEIGEO déjà noté injoignable dans une vague antérieure) | Tout — retenter PEIGEO + data.gouv |
| 8 | Dynamique constructive | **PARTIEL** | `sitadel_permits` = 50 043 (SDES/Dido, jusqu'au mois courant — mandat Sitadel3 mergé) ; bonus étage 2 `sitadel` rayon 200 m / 36 mois (binaire de fait) ; signal `new_permit_nearby` = ÉVÉNEMENT (veille, non scoré), touche 31 499 parcelles sur St-Paul seul | Indicateur **GRADUÉ** (densité PC 300-500 m / 5 ans) par parcelle ; graduation du bonus existant SANS double compte (cf. décision lot 8) |
| 9 | Potentiel résiduel (bâti + MNT) | **PARTIEL** | `parcel_residuel` = 263 626 (SDP résiduelle, `faisabilite/residuel.py`) ; bâti BD TOPO 817 506 dont **85,7 % avec `hauteur`** et `nombre_d_etages` ; grille pente RGE ALTI **~180 m** (147 398 cellules, `slope_pct`) ; cascade pente = max des cellules intersectées | `parcel_terrain(idu, pente_moy_deg, pente_max_deg, flag_terrassement_lourd)` absent ; pente 5 m à dériver (RGE ALTI 5 m, disque OK : 100 Gi libres) ; vérifier que `residuel.py` consomme bien la hauteur réelle (placeholder niveaux repéré) |
| 10 | RNIC copropriétés | **ABSENT** | rien | Tout |
| 11 | Pack marché | **PARTIEL** | `commune_contexte_sru` (24, millésime 2025, statuts dont 2 carencées) ✓ ; `commune_insee_logement` (RP 2023) ✓ ; loyers DHUP 2025 (`data/carte_loyers_reunion_2025.json` + `loyers.py`) ✓ ; Obsimmo ✓ | **RPLS** (parc social par commune) absent ; **Filosofi carreaux 200 m** absent ; (`plh_epci` vide — noté, PLH hors liste cible) |

## Vérifications AJOUTS SESSION

1. **Permis datés dans le futur : 1 seul** (max 2026-08-17, > aujourd'hui) sur 50 043 → < 50 :
   **artefact d'alimentation source consigné**, parsing de dates hors de cause.
2. **`new_permit_nearby`** : signal d'ÉVÉNEMENT (delta de veille, rayon 200 m, non scoré) —
   le lot 8 produira bien un indicateur **gradué** (densité), le booléen ne discrimine plus
   (31 499 parcelles touchées sur Saint-Paul).

## Contraintes actées

- Score V intouchable (tables/moteur/vue) — la dormance/vendabilité n'est re-scorée nulle part.
- Espace disque vérifié : 100 Gi libres → RGE ALTI 5 m 974 possible, dalles brutes nettoyées
  après dérivation du raster de pente (conservé pour le mandat ortho).
- Millésimes et règles de scoring exactes : complétés lot par lot en Phase 1 ci-dessous.

## Phase 1 — journal des lots (complété au fil de l'eau)

*(à venir : un bloc par lot avec statut final, règle de scoring exacte, millésime, volumétrie)*
