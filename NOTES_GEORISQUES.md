# NOTES GÉORISQUES — Vague B (5 couches)

## État : TEMPS 1 (reco) fait — STOP validation Vic avant persistance

Branche `ingestion/georisques-complet` (jamais mergée). Base `openclaw@…/labuse`.

### API — vérifié live 05/07/2026 (INSEE 97415 Saint-Paul)
- Base : `https://www.georisques.gouv.fr/api/v1`
- **Rate-limit officiel : ~1000 req/min/IP** (source doc/data.gouv). → throttle prudent ~0,15 s
  (leçon INPI : on ne se fait pas brider). Aucun header rate-limit exposé dans les réponses.
- Pagination : `page` + `page_size` ; réponses `{results, page, total_pages, data[], next, previous}`.

### Endpoints par couche (contrats RÉELS)
| # | Couche | Endpoint | Param | DOM 974 | Compte Saint-Paul |
|---|--------|----------|-------|---------|-------------------|
| 1 | Aléas | (WFS DEAL, PAS l'API) — `spatial_layers` kind='georisque_alea' | code_insee | ✓ (6/24 faits) | déjà fait |
| 2 | Sites/sols pollués | `/ssp` | code_insee **ou** latlon+rayon | ✓ | casias **52** + instructions **6** + SIS 0 + SUP |
| 3 | RGA argiles | `/rga` | latlon (code_insee→500) | ✗ **vide** | 0 (voir ci-dessous) |
| 4 | Cavités | `/cavites` | code_insee ou latlon+rayon | ✓ | **20** |
| 5 | ICPE | `/installations_classees` | code_insee ou latlon+rayon | ✓ | **158** |
| + | (bonus) mvt | `/mvt` | code_insee | ✓ | 160 |

### Détail couche 2 `/ssp` (structure imbriquée — 4 sous-collections paginées)
- `casias` : sites CASIAS/ex-BASIAS. Champs : `identifiant_casias`, `nom_etablissement`,
  `adresse`, `statut`, `geom` (Point, parfois null), `fiche_risque` (URL BRGM), `date_maj`.
  Le endpoint `/casias` seul → 404 : CASIAS passe UNIQUEMENT par `/ssp`.
- `instructions` : sites instruits (ex-BASOL). Champs idem + `geom` Point OU MultiPolygon.
- `conclusions_sis` : Secteurs d'Info sur les Sols (0 à Saint-Paul).
- `conclusions_sup` : servitudes (SUP) — nature différente (polygones), à traiter à part ou écarter.

### ⚠️ Couche 3 RGA — endpoint non concluant + N/A géologique 974
- `code_insee` → 500 « paramètres manquants » ; `latlon(+rayon)` → **200 corps VIDE**, y compris
  sur un point métropole à argile forte (Paris) → contrat non confirmé live.
- La Réunion = île volcanique → aléa retrait-gonflement argiles ~inexistant.
- **Reco : documenter + écarter** (ou différer), ne rien inventer. Décision Vic.

### 5 exemples vérifiables (Saint-Paul, live)
1. CASIAS `REU97400011` « Sucrerie Domaine de Clermont » — fiche BRGM (SSP4037996).
2. Instruction (ex-BASOL) « décharge d'ordures ménagères de Cambaie » (SSP001101601, polygone).
3. ICPE « communauté d'agglomération TCO » — régime Autorisation, Non Seveso.
4. ICPE « BANGUI Artifice Cap La Houssaye » — Autorisation.
5. Cavité naturelle `REUAW0021778` « Lotissement des Cactées ».

## Décisions VALIDÉES par Vic (05/07)
1. Stockage = `spatial_layers` (kind sol_pollue/cavite/icpe). ✓
2. RGA écarté + documenté. ✓
3. SSP = casias + instructions. ✓
4. Couche 1 aléas : compléter 6→24 via WFS DEAL, DANS cette session. ✓

## Échantillon Saint-Paul (live 05/07) — ingéré
Volumétrie : sol_pollue **55** (casias+instructions géolocalisés), cavité **20**, ICPE **158**.
Parcelles croisées (≤ 50 m) : sol_pollue **446**, cavité **109**, ICPE **689**. Ingestion 47 s.
Code : connecteur étendu (`sites_pollues`/`cavites`/`installations_classees`, paginé, backoff),
module `ingestion/georisques_layers.py` (parsers + `ingest_commune` idempotent + `sample_report`),
3 lignes `data_sources`, 9 tests verts.

## RESTE — TEMPS 2 (après validation échantillon)
- Passe île 24/24 : couches API (sol_pollue/cavite/icpe) sur les 24 communes + aléas DEAL 6→24.
- Chunké/résumable, throttle 0,15 s. Commande CLI à ajouter (pas de script jetable).

## Décisions initiales (archive) — voir rapport
1. Stockage : réutiliser `spatial_layers` (kind='sol_pollue'/'cavite'/'icpe') vs tables dédiées.
2. RGA : écarter (documenté) ou différer.
3. Couche 1 aléas : compléter 6→24 via WFS DEAL (mécanisme existant) — confirmer périmètre session.
4. SSP : quelles sous-collections (casias + instructions ; SIS ; SUP ?).

## Hors périmètre repéré
- `/mvt` (mouvements de terrain, 160 à Saint-Paul) : non demandé explicitement, complète le risque —
  à mentionner, pas ingéré sans demande.
