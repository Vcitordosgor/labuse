# AUDIT DE FRAÎCHEUR — données branchées à la fiche (M125-C)

> Pour **chaque** champ servi par `_q_v2_fiche` (`src/labuse/api/app.py:2375`) : sa table source,
> sa source amont, son millésime réel en base, sa date de dernier rafraîchissement, son statut.
> **Aucune correction — rapport seul.**

## Méthode

- Lecture **seule** sur la base locale `labuse` (seedée : 431 663 parcelles ; parcelle témoin
  `97402000AH1966` = Bras-Panon). **Date de référence : 2026-08-21.**
- Trois mécanismes de fraîcheur coexistent : **(a)** registre `data_sources`
  (`source_millesime`, `last_sync_at`, `source_cadence`, `prochain_millesime_at`) ; **(b)** horodatage
  par ligne des tables dérivées (`computed_at`/`created_at`/`updated_at`/`ingested_at`) ; **(c)** millésime
  **en config YAML** (PLU, RNU, ZFANG/FRR, qualité commune) — non tracé en base.
- **Dernier refresh** ci-dessous = `max()` réel de l'horodatage de la table dérivée quand il existe,
  sinon `last_sync_at` du registre `data_sources`.

**Statut** — `À JOUR` : rafraîchi dans sa cadence, ou dernier millésime autoritatif diffusé, ou
`prochain_millesime_at` dans le futur · `PÉRIMÉ` : un millésime/refresh plus récent est **échu** ·
`INCONNU` : **aucun** millésime **ni** horodatage tracé (ni registre, ni colonne).

## Tableau principal

| Champ | Table source | Source amont | Millésime | Dernier refresh | Statut |
|---|---|---|---|---|---|
| `idu` `commune` `surface_m2` `coords` | `parcels` | Cadastre Etalab (DGFiP) | non tracé | non tracé | **INCONNU** |
| `adresse` | `adresse_parcelles`+`adresses` | BAN (DINUM/IGN) | — | 2026-08-19 (registre, mensuel) | **À JOUR** |
| `proprietaire_moral` (+`etat_societe`) | `parcelle_personne_morale` (+INPI/SIRENE) | DGFiP PM · INPI RNE | non tracé (PM) | 2026-07-05 (`date_import`) · INPI 2026-07-06 | **À JOUR** |
| `score_v2` `etage0` `icd` *(analyse)* | `parcel_p_score_v2`, `dryrun_parcel_evaluations` | LABUSE scoring (run) | run label | 2026-08-21 (`computed_at`) | **À JOUR** |
| `lines` `flags` | `dryrun_cascade_results` ⋈ `data_sources` | par couche (millésime amont/ligne) | variable/ligne | 2026-08-19 (`created_at` cascade) | **À JOUR** ⚠ (millésime amont variable, cf. §Sources non tracées) |
| `evenement` `evenement_detail` | `dryrun_cascade_results` | BODACC | — | 2026-08-19 | **À JOUR** |
| `reglement_plu` | `spatial_layers` (zonage PLU) + config | GPU/API Carto | GPU par commune | 2026-08-20 (`created_at`) | **À JOUR** ⚠ (millésime PLU par commune → cf. `plu_fraicheur`) |
| `plu_fraicheur` | config `plu_millesimes.yaml` | GPU vs mairie | par commune (config) | maj manuelle YAML | **À JOUR** ⚠ (témoin lui-même ; dépend de la maj config) |
| `radar_procedure` | Sudocuh | Sudocuh (procédures urba) | état 31/12/2024 | 31/12/2024 | **À JOUR** † |
| `historique_site` | `sitadel_permits` + `pc_caducs` | SITADEL | 2026-06 | 2026-06-30 (dépôt) · sync 2026-08-14 | **À JOUR** † |
| `voisinage_proche` | `dvf_mutations` + `sitadel_permits` | DVF · SITADEL | DVF 2021–2025 | 2026-08-10 (mutation) | **À JOUR** † |
| `potentiel_transformation` *(SDP=donnée, niveaux=analyse)* | `parcel_residuel`, `parcel_residuel_bati` | Bloc D SDP · BD TOPO · règles PLU | — | 2026-08-19 (résiduel) · 2026-07-11 (bâti) | **À JOUR** † |
| `dvf_parcelle` | `v_parcel_dvf_last`, `dvf_secteur_medianes` | DVF DGFiP/Etalab | 2021–2025 + archives 2014–2020 | 2026-08-10 ; prochain **2026-10-01** | **À JOUR** |
| `terrain` | `parcel_terrain` | RGE ALTI (IGN) | non tracé (amont) | 2026-08-13 (`computed_at`) | **À JOUR** ⚠ (calcul récent, millésime RGE ALTI non tracé) |
| `coproprietes` *(mort)* | `rnic_coproprietes` | RNIC | snapshot | 2026-07-10 (`ingested_at`) | **À JOUR** |
| `marche_secteur` *(mort)* | `filosofi_carreaux_200m`, `rpls_commune` | INSEE Filosofi · RPLS | Filosofi **2021** · RPLS **01/01/2025** | 2026-07-10 (`computed_at` RPLS) | **À JOUR** (derniers millésimes diffusés) |
| `viabilisation` | `parcel_viabilisation` | faisceau réseaux (BD TOPO…) | — | 2026-07-14 (`computed_at`) | **À JOUR** |
| `anc` | `parcel_anc`, `anc_maille_taux` | GPU assainissement · INSEE RP2022 · Office eau 2023 | RP2022 / commune | 2026-07-11 (`updated_at`) | **À JOUR** |
| `gestionnaires` | config (EPCI/concessionnaires) | contacts admin | — | non tracé | **INCONNU** † |
| `aper` | `viabilisation_build` (parkings OSM) | Parkings OSM (loi APER) | — | 2026-07-11 (registre) | **À JOUR** |
| `renouvellement` *(segment=donnée, rang=analyse)* | `parcel_renouvellement` | LABUSE renouvellement | — | 2026-08-20 (`computed_at`) | **À JOUR** |
| `rnu` | `parcel_pau` + config `rnu_communes.yaml` | RNU registre · DEAL | `verifie_le` (config) | config | **À JOUR** ⚠ (dépend de la maj YAML) |
| `territoire_fiscal` | `territoire_fiscal_commune` + config | ANCT · Légifrance | ZFANG **décret 2026-421 (05/2026)** · FRR 01/07/2024 | config | **À JOUR** |
| `proximites` | `spatial_layers` (transport/pôle/HT) | BD TOPO · OSM · GTFS | GTFS màj 2026-08-17 ; OSM vivant | 2026-08-20 (`created_at`) | **À JOUR** † |
| `data_sources` (liste par-fiche) | `data_sources` ⋈ `dryrun_cascade_results` | catalogue sources | par source | registre | **À JOUR** |
| `qualite_commune` | config `qualite_commune.yaml` | audit RR 2025 | — | non tracé | **INCONNU** |
| `parc_analysees` *(mort)* | `p_score_v2_runs` | LABUSE run | run | 2026-08-21 | **À JOUR** |
| `completeness_score` *(mort)* | `dryrun_parcel_evaluations` | LABUSE matrice (éteinte) | — | 2026-08-19 | **À JOUR** *(mais déprécié)* |
| `score_v` *(mort)* | `parcel_v_score` | vendabilité V (dépréciée) | — | 2026-08-09 (`computed_at`) | **À JOUR** *(mais déprécié)* |
| `anru` *(mort)* | `spatial_layers` (kind='anru') | DEAL/ANCT NPNRU | génération courante | 2026-07-08 (registre) | **À JOUR** |
| `mode_b` | session (non persisté) | Bilan Mode B (à la volée) | — | calcul session | **À JOUR** † |

† = **builder « exception-safe »** : capte toute exception et renvoie `None` **silencieusement**
(`radar_procedure`, `historique_site`, `voisinage_proche`, `potentiel_transformation`,
`gestionnaires`, `proximites`, `mode_b`). Un échec amont devient donc **invisible** — un champ vide
peut cacher une panne, pas une absence de donnée.

## Synthèse

- **Aucun champ `PÉRIMÉ`** au sens strict (aucun `prochain_millesime_at` échu ; DVF prochain
  2026-10-01, SITADEL/BAN/DPE dans leur cadence).
- **3 champs `INCONNU`** (aucune fraîcheur traçable en base) : **`parcels`** (idu/commune/
  surface/coords — cadastre non versionné), **`gestionnaires`** (contacts config), **`qualite_commune`**
  (audit config). + fraîcheur AMONT non tracée pour `terrain` (RGE ALTI) et `proprietaire_moral` (DGFiP PM).

### ⚠ Sources connectées SANS métadonnée de fraîcheur (registre `data_sources` : millésime **et** sync vides)

Ces sources alimentent surtout `lines` (cascade) et les couches spatiales — leur **millésime amont
par ligne est vide**, donc la fiche affiche des constats (risques, zonage, occupation du sol) à
**fraîcheur non traçable** :

`BD TOPO IGN` · `RGE ALTI` (×2) · `OCS GE (IGN)` · `Cadastre (API Carto PCI)` · `Cadastre Etalab` ·
`Zonage SAFER (DAAF)` · `Forêts publiques (ONF)` · `ENS (Département)` · `DEAL — PPR / aléas` ·
`DEAL (WMS/WFS)` · `GPU — zonages d'assainissement` (×2) · `DGFiP — parcelles des PM` ·
`SAR Réunion` · `SIRENE` · `LiDAR HD — MNH` · `Recherche d'entreprises (DINUM)` ·
`data.regionreunion.com — Potentiel foncier`.

> **Alerte** : `DEAL — PPR / aléas` (données de **risque**, à fort enjeu) n'a **ni millésime ni
> `last_sync_at`** dans le registre. Idem `SAR` et `OCS GE` (constructibilité). La fiche les sert
> sans pouvoir en dater la fraîcheur.

### Millésimes anciens mais autoritatifs (dernier diffusé — pas « périmé »)

`trait de côte` 2018 (DEAL) · `Parc National` 2021 · `Filosofi` 2021 (INSEE) · `Contours IRIS` 2024 ·
`50 pas` cadastre 1877 · `Sudocuh` 31/12/2024. À suivre si une version plus récente sort.

## Remontées (pour arbitrage)

1. **Fraîcheur cadastre non tracée** — `parcels` (idu/commune/surface/coords) : ajouter un
   `source_millesime`/`ingested_at` au lot cadastre (fondation de toute la fiche).
2. **Sources de risque sans fraîcheur** — renseigner `source_millesime`+`last_sync_at` pour
   `DEAL — PPR/aléas`, `SAR`, `OCS GE`, `Géorisques (base)` : ce sont les couches les plus sensibles.
3. **Builders « exception-safe » muets** — 7 champs (†) masquent une panne amont en un `None`
   silencieux ; logguer un avertissement préserverait la piste d'audit de fraîcheur.
4. **Millésimes en config YAML** (`plu_fraicheur`, `rnu`, `territoire_fiscal`, `qualite_commune`) :
   fraîcheur dépendante d'une maj **manuelle** hors base — non détectable automatiquement.

---

*Rapport M125-C. Lecture seule, aucune modification. Base d'arbitrage avant M125-A (PDF exhaustif) :
un champ `INCONNU` ou « source sans fraîcheur » ne devrait pas partir au PDF sans décision explicite.*
