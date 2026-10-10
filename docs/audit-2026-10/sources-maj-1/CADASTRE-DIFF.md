# Cadastre différentiel — diff 2026-06 (servi) → 2026-09 (Etalab latest)

**Date** : 2026-10-10 · staging isolé `_cad_sm1_staging` (433 229 parcelles, 24 communes 974) vs `parcels` (431 663).
Sauvegarde parcels : `~/labuse-backups/sources-maj-1/parcels-AVANT-CADASTRE-20261010-223358.dump` (201 Mo). **Rien d'écrit dans `parcels` — STOP accord Vic.**

## Comptes (clé = IDU 14 car.)

| catégorie | nombre | note |
|---|---|---|
| **Nouvelles** (staging ∉ parcels) | **2 919** | subdivisions récentes ; contenance ≈ aire dessin |
| **Disparues** (parcels ∉ staging) | **1 353** | dont **46 référencées par un client**, 1 307 non référencées |
| **Contenance modifiée** (commun) | **0** | la contenance voyage avec les nouveaux IDU ; backfill issu de la même source Etalab |
| **Géométrie réellement modifiée** (`NOT ST_Equals`) | **1 501** | vraies redécoupes |
| géométrie byte-diff mais `ST_Equals` (ré-encodage) | 7 864 | topologiquement identiques → **laissées intactes** |

## Exemples

**Nouvelles** : 97401000AD1643 (359 m²), AD1644 (644), AD1651 (915), AH0371 (5 578), AI1127 (609)…
**Disparues** : 97401000AD0744, AD1204, AH0114, AI0124, AI0557, AI0569…
**Géométrie modifiée** (aire ancienne→nouvelle) : 97418000AC1522 33→3 295 m² (correction d'une géométrie fausse), 97420000AC0262 897→606 (−32 %), 97420000BH1222 389→154 (−60 %), 97411000AW0563 40→95, 97415000BW2037 10 685→10 682 (~0 %)…

## Contrainte FK découverte (détermine la méthode des disparues)

Beaucoup de FK sur `parcels` sont `ON DELETE CASCADE`, **dont des tables client** : `pipeline_entries`, `projet_parcelles`, `alertes`, `module_division`, `watch_snapshots`, `parcel_feedback`. Un `DELETE` d'une parcelle disparue **cascaderait silencieusement sur ces données client**. D'autres FK sont `NO ACTION` (`parcel_solar`, `parcel_anc`, `parcel_vegetation`, `parcel_equipements`, `parcel_bati_revele`, `score_e`, `pc_caducs`…) et **bloqueraient** le DELETE tant que leurs lignes existent.

➡️ Le hard-delete est donc risqué et partiellement impossible. **Méthode recommandée : marquer, ne pas supprimer.**

## Plan d'application proposé (après accord)

1. **Nouvelles (2 919)** : INSERT (idu, commune, geom brute 4326, contenance) ; dérive `geom_2975`/`centroid`/`bbox`/`surface_m2` via `ensure_geom_2975`. Scores NULL jusqu'au run q_v18.
2. **Géométrie modifiée (1 501)** : UPDATE `geom` (+ `contenance_m2` depuis staging) ; re-dérive géométries projetées. Géométrie brute Etalab, **aucune simplification**. (Les 7 864 ré-encodages NON touchés.)
3. **Disparues (1 353)** : **marquées** `cadastre_disparue_le = DATE '2026-09-01'` (nouvelle colonne `parcels.cadastre_disparue_le`), **exclues du service** ; **aucune suppression** (ni client, ni orpheline) — réversible. Le run q_v18 les écarte du servi. Les 46 client-référencées gardent leurs liens intacts.
4. **Recalcul ciblé** (hors run global) : contenance déjà posée ; `build-intersections` **sur les seuls IDU touchés** (2 919 + 1 501) ; rattachement adresses sur ces IDU.
