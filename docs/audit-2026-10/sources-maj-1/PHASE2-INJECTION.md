# MANDAT-SOURCES-MAJ-1 — Phase 2 : injections (journal)

Date 2026-10-10. Base locale uniquement. Sauvegardes dans `~/labuse-backups/sources-maj-1/`.
Toolchain : venv `~/Desktop/labuse/.venv` + `PYTHONPATH=…/labuse-sources/src` + `LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@/labuse?host=/tmp`.

## Groupe A / B — sources injectées (commande existante)

| id | source | commande | avant → après | guard ±20 % | millésime | état |
|---|---|---|---|---|---|---|
| 126 | Fibre Arcep | `ingest-arcep` (+ bump `MILLESIME` T1→T2 dans le connecteur) | 330 051 → 330 310 immeubles | +0,08 % | 2026_T2 | ✅ |
| 74 | Transport GTFS + OSM | `transport-reseaux` | 14 041 → 14 039 lignes couches | −0,01 % | màj 2026-10-10 (Car Jaune) | ✅ |
| 16 | SITADEL (SDES) | `ingest-permits --refresh` | 50 545 → 50 809 (max 2026-07-31 → 2026-08-31) | +0,5 % | 2026-08 | ✅ (impact run → q_v18) |
| 100 | RNIC copropriétés | `ingest-rnic --csv <national 432 Mo>` | 2 220 → 2 220 (974 stable) | 0 % | re-sync 2026-10-10 | ✅ |
| 86 | SIRENE établissements géoloc | `ingest-sirene-etab` | 158 515 → 158 515 | — | — | ✗ ÉCHEC |

**SIRENE (86) — échec passé (mandat « si un connecteur est cassé, le dire et passer ») :** la livraison de septembre contient `insee=97454` absent de `communes_referentiel` → `ForeignKeyViolation`, transaction **annulée** (0 ligne touchée, millésime inchangé). Pas de refonte de connecteur. À corriger hors mandat (tolérer/mapper l'INSEE orphelin).

## Sources NON injectées (plus qu'un re-sync — documentées, non faites)

| id | source | pourquoi | reco |
|---|---|---|---|
| 28 | Érosion côtière | URL connecteur figée sur le fichier 2018 **+** ne se rafraîchit que par le chemin par-commune qui **re-score** | avec q_v18 (changement d'URL + ingestion) |
| 46 | Classement sonore | la couche ArcGIS `_V2` figée ≠ arrêtés 26/12/2024 (jeu data.gouv distinct) → **changement de source** | avec q_v18 |
| 10 | RPG agricole | WFS LATEST = 2025, mais refresh seulement via chemin par-commune qui **re-score** | avec q_v18 |
| 102 | Conso NAF | aucune commande CLI + colonne `conso_2021_2025` à ajouter | optionnel (aucun impact run) |
| 41 | INSEE RP Logement 2023 | **réécriture du parseur** (format harmonisé 2023) | optionnel (aucun impact run) |
| 73 | FRR ex-ZRR | arrêté 14/04/2025 existe mais **aucune commune 974 concernée** | sans objet |
| 35 | Cartofriches | API en 503 depuis 02/10 | réessayer |

## Cadastre différentiel (96/1) — appliqué

Détail du diff : `CADASTRE-DIFF.md`. Sauvegarde `parcels-AVANT-CADASTRE-20261010-223358.dump` (201 Mo).
- **2 919 nouvelles** insérées (géométrie brute `ST_MakeValid`, surface/centroïde/bbox dérivés, `geom_2975` par trigger, scores NULL → q_v18).
- **1 501 géométries** réellement modifiées mises à jour (+ contenance depuis staging) ; **7 864 ré-encodages** `ST_Equals` laissés intacts.
- **0 contenance** changée (vérifié, y compris géométrie identique).
- **1 353 disparues** marquées `parcels.cadastre_disparue_le = 2026-09-01` (nouvelle colonne), **aucune suppression** (réversible ; les FK CASCADE auraient détruit des données client).
- **Liens de remplacement** `parcel_cadastre_remplacement` (recouvrement ≥ 50 %) : **1 292 / 1 353** disparues mappées (3 007 liens), 61 vraiment disparues.
- **Adresses** : rattachement ciblé des nouvelles (ST_Contains) → +1 981 liens, 1 063 nouvelles avec adresse.
- Parcels 431 663 → **434 582** (+0,68 %). Millésime data_sources id 1 → 2026-09, id 96 → Etalab 2017-07→2026-09.
- **Intersections** (`parcel_couche_intersection`) : l'outil `build-intersections` n'a PAS de ciblage par IDU (island-wide, version-gated) → **laissé au run q_v18** qui reconstruit tout.

## Code (dans ce commit)

- `ingestion/arcep_fibre.py` : `MILLESIME` 2026_T1 → 2026_T2.
- `api/app.py` : fiche de courtoisie pour une parcelle `cadastre_disparue_le` (HTTP 200 « Parcelle disparue du cadastre (version du …) — remplacée par […] » au lieu d'une erreur) + helper `_fiche_cadastre_disparue`. **Rendu front du bandeau = à faire (Phase suivante).**

## Détection d'une nouvelle version du cadastre (task cron)

**Déjà en place** : SENTINELLE-1 surveille QUOTIDIENNEMENT les deux sources cadastre (id 1 `parcellaire-express-pci`, id 96 dataset `cadastre` — `last_update`), sonne la cloche admin et **n'ingère rien** (« Vic décide »). C'est plus fort que le trimestriel demandé → **pas de job redondant ajouté** (décision à confirmer).

## Reste à faire (Phase suivante / Phase 3)

1. Rendu front du bandeau « parcelle disparue » + exclusion des disparues de carte/recherche/filtres/listes au niveau du **run** (`cadastre_disparue_le IS NULL` dans la sélection des parcelles du run) — se fait proprement avec q_v18.
2. Sources 28/46/10 (impact run) à ingérer **avec** q_v18.
3. Tuiles : overlays transport auto-invalidées (bump IngestionRun 62) ; `mvt_parcels` reconstruit par q_v18/`build-mvt`.
4. **Run q_v18** (résiduel + scoring) = Phase 3, sur décision de Vic.
