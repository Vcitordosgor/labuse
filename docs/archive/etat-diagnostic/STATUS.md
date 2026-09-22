# État d'avancement — LA BUSE

Mis à jour au fil des commits. **Dernière mise à jour : 2026-07-06 (post-campagne d'ingestion).**

## Où on en est (résumé)
Le moteur ne tourne plus sur des fixtures/synthétique : il tourne sur **données RÉELLES**.
- **Cadastre réel ingéré** : **431 663 parcelles sur les 24 communes** de La Réunion (API Carto /
  Cadastre Etalab). La démo synthétique de Saint-Paul est remplacée par le cadastre réel.
- **Réseau NON bloqué** : la campagne d'ingestion 05-06/07/2026 a récupéré en **live** BODACC,
  INPI RNE, Géorisques, DPE ADEME, Cartofriches, ABF (Mérimée), QPV (ANCT), aménités (Overpass),
  BAN. (L'ancienne note « allowlist / connecteurs en fixtures » est PÉRIMÉE.)
- **Dernière évaluation cascade de Saint-Paul : 2026-07-04** — soit AVANT la campagne. Les scores
  actuels ne reflètent donc encore **aucune** couche ingérée en 05-06/07. Une ré-évaluation est
  nécessaire pour matérialiser ne serait-ce que les couches déjà branchées.

## Couches ingérées — branchées au scoring vs # TODO
La cascade lit déjà 18 couches phase 1 + 4 phase 2 (eau, parc, forêt, SAR, PLU/GPU, SAFER,
risques PPR/aléas, ravine, trait de côte, pente, ABF, ENS, OCS GE, OSM faux-positifs, bâti, accès,
surface ; puis DVF, SITADEL, potentiel foncier, propriétaire). Parmi les couches de la campagne
récente :

| Couche (récente) | Stockage | Branchée cascade ? | Cible |
|---|---|---|---|
| **ABF (Mérimée, 200 abords → ~60,6k parcelles)** | `spatial_layers kind='abf'` | ✅ **OUI** (phase 1, severity `faible`) | déjà lu — ⚠ voir note |
| Géorisques **aléas** (PPR / georisque_alea) | `spatial_layers` | ✅ OUI (couche `risques`) | déjà lu |
| BODACC (procédures collectives) | `v_foncier_sous_pression` | ❌ non | # TODO **étage 2** |
| INPI dirigeants + gigogne (âge) | `v_pm_propension_vendre` | ❌ non | # TODO **étage 2** |
| DPE passoires F/G | `v_passoire_thermique` | ❌ non | # TODO **étage 2** |
| Cartofriches (friches) | `kind='friche'` (372) | ❌ non | # TODO **étage 1** |
| Géorisques **nouveaux** : sol pollué (480), cavités (151), ICPE (1248), mvt (3085) | `spatial_layers` | ❌ non | # TODO **étage 1** |
| Aménités OSM (distances école/santé/commerce/tcsp) | `parcel_amenites` (9059 POI) | ❌ non (poids à calibrer) | # TODO **étage 1** |
| QPV 2024 (57, 13 communes → 43,8k parcelles) | `kind='qpv'` | ❌ non | # TODO **bilan** (pas cascade) |
| Vue mer (RGE ALTI) | `parcel_vue_mer` | ❌ non | # TODO **bilan** (choix d'archi) |
| Droits résiduels | `parcel_residuel` | ❌ non | # TODO **bilan** (choix d'archi) |

> ⚠ **ABF — piège de ré-évaluation** : la couche `abf` est câblée et son entrée est passée de
> **6 → 60 618 parcelles** intersectées (tampons 500 m qui SUR-COUVRENT, « covisibilité à
> instruire »). Une simple ré-évaluation flaggerait donc ~10 000× plus de parcelles (severity
> `faible`) sans qu'aucune règle n'ait été retouchée. À vérifier explicitement au dry-run étages 1/2.

## Bilan tests / outillage
CLI `labuse` étendue par la campagne : `ingest-inpi-rne` / `ingest-inpi-gigogne`, `ingest-georisques`,
`ingest-mvt`, `ingest-dpe`, `ingest-cartofriches`, `ingest-abf`, `ingest-qpv`, `ingest-amenites`,
`ingest-permits` / `warm-vue-mer` (jointures transverses). Toutes chunkées/résumables, fraîcheur
`data_sources` posée. Tests d'ingestion verts (BODACC, INPI, Géorisques, DPE, Cartofriches, ABF,
QPV, aménités). Dette d'hygiène connue : **189 erreurs pyproj** (env PROJ, pré-existant, hors code
— à traiter en session dédiée).

## Ordre de construction (§12) — état
| # | Étape | État |
|---|-------|------|
| 1 | PostGIS + modèle + EPSG (4326/2975) + test de surface | ✅ testé sur PostGIS réel |
| 2 | Ingestion cadastre → `parcels` | ✅ **RÉEL** — 431 663 parcelles / 24 communes (la démo synthétique est remplacée) |
| 3 | Moteur de cascade (couches, verdicts, motifs, config) | ✅ fait |
| 4 | Couches géométriques cœur (eau, Parc, forêts, SAR, GPU, SAFER, Géorisques/PPR ; pente) | ✅ fait sur `spatial_layers` réels |
| 5 | Page Sources + statut connecteurs + test | ✅ catalogue `data_sources` à jour (fraîcheur réelle) |
| 6 | Fiche parcelle + double score (opportunité + complétude) | ✅ fait |
| 7 | Enrichissement (DVF rayon, SITADEL, Overpass, BAN) + cache | ✅ DVF/SITADEL/aménités ingérés ; cascade phase 2 |
| 8 | Analyse IA (anti-hallucination, JSON borné) | ✅ prompt + schéma + validateur + provider `stub` ; Anthropic prêt à brancher |
| 9 | Vue Découverte (survivantes classées, offre B) | ✅ CLI `discover` + API `/discover` |
| 10 | Export fiche premium | ✅ Markdown/HTML via `/parcels/{idu}/export` |

## Prochaine étape
**Dry-run étages 1 + 2** : brancher au scoring les couches # TODO (étage 1 : Géorisques nouveaux,
friches, aménités ; étage 2 : BODACC, propension INPI, passoires DPE), et statuer sur le piège ABF.
Le `BRIEF_CC_ETAGES_1_2_DRYRUN.md` est en cours de rédaction côté Vic (à recevoir validé).
QPV / vue mer / droits résiduels alimentent le **bilan promoteur**, pas la cascade.
