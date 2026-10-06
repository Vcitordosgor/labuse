# VITESSE-PROD-1 — la carte et la fiche rapides EN PRODUCTION

Branche `fix/vitesse-prod-1` (depuis origin/main `0506b5cd`) · worktree `~/Desktop/labuse-vitesseprod` · 06/10/2026.
Mesures prod : VPS `labuse-vps` en **lecture seule** (aucun réglage changé, aucun redémarrage) ; corrections **locales uniquement**, données et géométries **intactes** (preuves §5). Antériorité citée, pas refaite : VITESSE-CARTE-1 (goulots G1-G5), VITESSE-CARTE-FIX-1 (G2 : cache persistant overlays z9-z11, mergé), RECETTE-1 lot B (`setWorkerCount`, mergé), CHASSE-3 (p95 sous charge : fiche 13,7 s, tuile 0,22 s).

## 0. Résumé

La prod ne souffrait pas d'un excès de données mais de **travail inutile et d'un défaut de concurrence** :

1. **Interblocage jetons↔connexions dans `get_db`** (le `SET statement_timeout` exécuté au *setup* de la dépendance) : toute rafale de tuiles > ~48 requêtes gelait le worker par cohortes de 30 s. **Observé en prod le 06/10 en direct** : 75 connexions `idle in transaction` (= 5 workers × pool 15 saturé), 224 `QueuePool TimeoutError`/6 h, SVG statique servi en 229 s, fiche en 464 s. Reproduit localement (piles faulthandler : 40/40 fils du threadpool bloqués dans `pool.connect()` depuis `get_db`), corrigé (écouteur `after_begin`), re-mesuré : **120 tuiles concurrentes : 61 s + 41 erreurs → 2,7 s + 0 erreur**.
2. **Le middleware d'auth interrogeait la BDD sur l'event loop** à chaque requête authentifiée → sous saturation du pool, TOUT le worker gelait (même le statique). Déplacé dans le threadpool.
3. **Chaque tuile d'overlay seq-scannait sa table source** : le prédicat `ST_SetSRID(col, …) && env` empêche l'index GiST de servir (30 022 buffers ≈ 245 Mo lus PAR tuile sur `mvt_parcels`). Prédicat réécrit sur la colonne nue (sonde de SRID) : **z13-z15 ÷8 à ÷10**, contenu prouvé identique (480/480 tuiles, multiset de lignes).
4. **Les octets de tuiles n'étaient PAS déterministes** sur 12 couches (égalités du tri `ORDER BY geom` départagées par l'ordre de scan ; mesuré : 3 calculs = 3 md5) → le cache persistant servait des octets ≠ à-la-volée → ETag qui flappe. Départage total `mvt::text` : octets reproductibles, mêmes entités/propriétés/pixels.
5. **Cache persistant étendu à z12-z13** (lus/alimentés par la route, warm parcels + repères défaut) : l'ensemble reste borné (~320 tuiles/couche), z14-z15 restent à la volée (1-30 ms après le correctif 3).
6. **La fiche recalculait 2 × 1,75 s d'intersections PPR contre des méga-polygones** (2 appels identiques par fiche + `spatial_layers` brut au lieu de la partition `tuyau_subdivise` déjà construite pour les tuiles) + 238 requêtes à chaque clic. Mémo par requête + bascule sur la partition (×44, égalité prouvée 120/120 parcelles) + **cache de fiche versionné** (run + fraîcheur `data_sources`) : **fiche 5,5 s → 1,35 s à froid, 5 ms en cache, octets identiques** (md5).

Objectifs du mandat à cache chaud : **fiche < 1,5 s** → 0,005 s ✓ (froid 1,35 s) · **tuile < 300 ms** → 4-7 ms cache, 1-390 ms à la volée ✓ · **couche < 1 s** → z9-13 depuis cache ✓.

Côté serveur (gestes Vic, §6) : `shared_buffers` est resté au **défaut Debian 128 Mo pour une base de 43 Go** (taux de cache 80,7 % — sain ≥ 99 %), `random_page_cost=4` (défaut disque rotatif sur un SSD), pas de `pg_stat_statements`, Caddy en gzip seul, et **`gdaldem` absent du VPS** = la vraie cause d'« Exposition — relief non disponible » (les tables relief sont identiques local/prod ; le service IGN répond).

## 1. Étape 0 — l'AVANT mesuré en production

### 1.1 Trafic réel (journal Caddy complet 27/08 → 06/10, `mesures/prod_caddy_avant.csv`)

| classe | n | p50 | p95 | max | % 5xx |
|---|---|---|---|---|---|
| tuile parcelles | 1 247 | 0,16 s | 3,61 s | 501 s | 0,6 |
| tuile overlay `limites_parcelles` | 976 | 0,19 s | 5,64 s | 502 s | 1,0 |
| tuile overlay `limites_communes` | 887 | 0,12 s | 4,27 s | 502 s | 0,8 |
| tuile overlay (autres) | 214 | 0,20 s | 2,39 s | 64 s | 0,0 |
| fiche `/parcels/{idu}` | 15 | 3,51 s | 464 s | 464 s | **20,0** |
| outils `/modules/*` | 89 | 0,39 s | 497 s | 598 s | 9,0 |
| `/parcels/at` (clic) | 5 | 0,03 s | 0,12 s | 0,12 s | 0,0 |
| assets statiques (Caddy) | 195 | 0,01 s | 0,04 s | 0,05 s | 0,0 |

Lecture : le régime NOMINAL est correct (p50), mais les p95/max sont catastrophiques — ce sont les **épisodes d'effondrement** (§1.2). Les assets servis par Caddy directement (sans toucher l'API) restent à 10 ms **sauf** pendant l'incident (SVG `/socle/marque` passé par l'API : 229 s).

### 1.2 Incident observé en direct (06/10, 22h16-22h50 Réunion) — la « fuite » du mandat

- **75 connexions `idle in transaction`** = exactement 5 workers × (pool 5 + overflow 10), dernière requête = SQL de tuile ; `wait_event = ClientRead` (l'app ne renvoie plus rien). Tuées par `idle_in_transaction_session_timeout = 10 min` (posé par `db.py make_engine` — c'est le SEUL dé-coinceur de la prod, qui re-fuite aussitôt).
- `journalctl -u labuse` : **224 × `QueuePool limit of size 5 overflow 10 reached, timeout 30.00`** en 6 h.
- Ce n'est **pas** une fuite de session (le `session_scope` ferme en `finally`) : c'est l'**interblocage** diagnostiqué et corrigé au §2.1 — les connexions sont tenues par des requêtes qui attendent un jeton de threadpool, les jetons par des requêtes qui attendent une connexion.

### 1.3 VPS (lecture seule — détail `mesures/vps_etat_2026-10-06.txt`)

6 vCPU · 11,7 Go RAM · disque 90 % plein · uvicorn 5 workers · Caddy `encode gzip` seul, HTTP/2 actif (h3 annoncé) · Postgres 18 : `shared_buffers` **128 Mo** (défaut Debian, base 43 Go), `effective_cache_size` 4 Go (page cache réel 8,5 Go), `random_page_cost` **4**, `work_mem` 4 Mo, `pg_stat_statements` **absent**, `log_min_duration_statement` off. Taux de cache 80,66 %. `mvt_tile_cache` : 51 couches, **z9-z11 seulement**, 1 335 tuiles, 138 Mo.

### 1.4 La capture de Vic — contours qui se dessinent « par carrés » en vue île

Instruit, deux causes qui se multiplient :
1. **Poids** : en vue île (~z9,4-10), la couche `limites_parcelles` (cochée par défaut, famille Repères) tire 4-6 tuiles z9-z10 de **2,2 à 5,8 Mo BRUTES chacune** (mesuré dans `mvt_tile_cache` prod : z10 669/573 = 5,8 Mo ; ~1,7-3 Mo sur le fil en gzip). Elles ARRIVENT l'une après l'autre et MapLibre peint chaque tuile dès réception → les « carrés ». Ces tuiles sont bien **servies du cache persistant** (z9-z11, G2) — c'est le transfert + le décodage qui se voient, pas le calcul.
2. **Saturation** : pendant un épisode §1.2, chaque tuile attend derrière le pool (p95 5,6 s, max 502 s) → les carrés restent vides longtemps et « Chargement de la carte… » s'éternise.

Le correctif structurel du POIDS (dessiner les limites depuis la source `parcels-ile` déjà chargée, −81 % d'octets à l'ouverture) est **prouvé par G1-MESURE** mais **reporté par Vic** (06/10 : « reporter G1 ») — il reste au §7 (propositions, rien d'appliqué). Les correctifs du présent mandat suppriment la cause 2.

### 1.5 « Exposition — relief non disponible » en prod

Ce n'est **pas** une table non migrée : `rgealti_mnt_5m` (2 lignes) et `mnt_tiles` (66) sont **identiques** local/VPS. La cause est `gdaldem` (GDAL) **absent du VPS** : `faisabilite/exposition.py` l'exécute en sous-processus (`_gdaldem`), l'exception est avalée proprement → « relief indisponible ». Le service IGN (data.geopf.fr) répond depuis le VPS en 1,25 s. **Geste G7** (§6) : `apt install gdal-bin`.

### 1.6 Parcours Playwright en prod

Les tuiles et la fiche **ne sont pas publiques** (auth applicative, `auth.py _PUBLIC`) et le mandat m'interdit de lire les secrets du VPS : le parcours complet authentifié est donc livré **rejouable** (`harnais/prod_parcours.mjs`, Chrome réel non headless, froid/chaud × 3 passages, top-10 requêtes par geste) et **validé sans cookie** (il mesure la page /login puis s'arrête : 302 en 51 ms, login 21 ms — colonne « prod réelle » du §4 à rejouer par Vic) :

```
LABUSE_COOKIE='<valeur du cookie labuse_session d'une session ouverte>' \
  BASE=https://app.labuse.immo node docs/audit-2026-10/VITESSE-PROD-1/harnais/prod_parcours.mjs
```

L'AVANT prod chiffré du §1.1 vient du trafic réel (journal Caddy), plus fidèle qu'un passage synthétique pendant un incident.

## 2. Corrections appliquées (locales, données intactes) — chacune AVANT/APRÈS

### 2.1 Interblocage jetons threadpool ↔ pool de connexions (`app.py get_db`) — LA cause de l'effondrement

**Mécanique prouvée** (piles faulthandler sous rafale, 40/40 fils) : `get_db` exécutait `SELECT set_config('statement_timeout', …)` **au setup de la dépendance** → la connexion était prise pendant la phase « dépendances » (jeton threadpool rendu ensuite), puis le handler devait **ré-acquérir** un jeton derrière les setups des autres requêtes, qui eux bloquaient dans `pool.connect()` (30 s) car toutes les connexions étaient tenues par des requêtes… en attente de jeton. Falaise mesurée entre 48 et 72 requêtes simultanées (jetons anyio = 40).

**Correctif** : le plafond est posé par un écouteur SQLAlchemy `after_begin` (il s'exécute au premier execute du handler, sous le MÊME jeton ; `session.info` posé par `get_db` — les batchs CLI ne sont jamais concernés). Gain de justesse au passage : `SET LOCAL` mourait au premier `commit()` intermédiaire (ex. `_tile_cache_put`) — l'écouteur le repose à chaque transaction.

**Même rafale locale (1 worker, 6 couches × 20 tuiles z13 froides, moitié avortées à 300 ms comme MapLibre pendant un zoom)** — `harnais/rafale_tuiles.py`, `mesures/rafale_{AVANT,APRES}.txt` :

| | AVANT | APRÈS |
|---|---|---|
| vague 1 (120 req) | 61,3 s · p50 **61 s** · **41 erreurs 500** | **2,7 s** · p50 1,2 s · **0 erreur** |
| vague 2 (re-pan, 24 req) | 0,5 s · p50 252 ms | 0,1 s · p50 104 ms |
| pool Postgres | 15/15 saturé, idle-in-tx 15 | pic idle-in-tx 7, redescend seul |
| falaise de concurrence | n=72 : 30,6 s, 40 err · n=120 : 60,6 s, 79 err | n=72 : **0,9 s**, 0 err · n=120 : **1,8 s**, 0 err |

### 2.2 Middleware d'auth : lookup de session BDD sorti de l'event loop (`app.py _auth_guard`)

`auth.session_info` (session BDD synchrone) était appelé **sur l'event loop** à chaque requête portant un cookie `u.…` : pendant une saturation du pool, le worker ENTIER gelait (plus aucune réponse, même statique/publique — le SVG à 229 s du §1.2). Désormais `await run_in_threadpool(...)` (idem `token_ok`). Mêmes règles, même cookie, seul le fil change. (La garde `protection.py` utilisait déjà le threadpool.)

### 2.3 Prédicat d'emprise des tuiles overlay : l'index GiST servait enfin (`couches_tuyau._construire_tuile`)

`ST_SetSRID(m.geom, srid) && env` = fonction autour de la colonne → l'index GiST (posé sur la colonne nue) ne matche JAMAIS → **Parallel Seq Scan de toute la table À CHAQUE tuile** (mesuré sur `mvt_parcels` : 30 022 buffers/85 ms le count seul ; 4,05 s la tuile `limites_parcelles` z13 bout en bout à froid). Les 57 couches étaient touchées ; la route parcelles (`tiles.py`, colonne nue) prouvait l'innocuité. Correctif : colonne nue dans le WHERE quand le SRID réel de la table == déclaré (sondé une fois par table, cache process, repli historique sinon) ; la PROJECTION (`ST_AsMVTGeom(ST_Transform(ST_SetSRID(…)))`) est inchangée.

**Banc 60 couches × 8 tuiles témoins (z9→z15), médiane de 3** — `harnais/tuile_srid_bench.py`, `mesures/tuile_srid_bench.csv` :

| zoom | AVANT (total) | APRÈS (total) | commentaire |
|---|---|---|---|
| z13 (×120) | 3 052 ms | 1 741 ms | ÷1,8 (et ÷10+ sur les couches à grosse table : batiment 407→17 ms, safer, zonage_parcelle…) |
| z14 (×60) | 1 185 ms | **142 ms** | ÷8 |
| z15 (×60) | 1 143 ms | **109 ms** | ÷10 |
| z9-z11 (×180) | 37,0 s | 61,1 s | surcoût du TRI déterministe (§2.4) — zooms PRÉ-CHAUFFÉS au build, jamais recalculés en régime servi : le coût bascule sur le warm (+~24 s par rebuild) |

**Neutralité prouvée** : pour chaque (couche, tuile), md5 du **multiset des lignes** (géométrie MVT + toutes propriétés) entrant dans `ST_AsMVT`, ancien vs nouveau WHERE : **480/480 identiques** → mêmes entités, mêmes propriétés, mêmes pixels.

### 2.4 Octets de tuiles enfin déterministes (`ORDER BY mvt.geom, mvt::text` — les 2 routes)

En vérifiant 2.3, découverte d'un défaut PRÉ-EXISTANT : le tri `ORDER BY mvt.geom` de G2 compare des **boîtes** (btree géométrie) — les égalités (points superposés, petits objets) se départageaient par l'ordre de scan. Mesuré : **3 calculs de la même tuile = 3 md5 différents** sur `amenite_bpe`, `batiment`, `trait_de_cote` (12 couches touchées) → en prod, le cache persistant sert des octets ≠ à-la-volée → **l'ETag flappe** et le navigateur re-télécharge des tuiles « inchangées ». Départage total ajouté (`mvt::text`, ligne entière) sur les deux routes : **480/480 tuiles désormais identiques entre 2 calculs**. Même contenu, même rendu ; les octets changent une fois au déploiement (purge du cache au geste G2-vps, §6).

### 2.5 Cache persistant étendu à z12-z13 (`_PERSIST_ZOOMS`, les 2 routes)

En prod le LRU est PAR worker (×5) et z≥12 n'était jamais persisté : chaque worker recalculait chaque tuile z12-z13 à son premier passage — un pan à z13 = des dizaines de `ST_AsMVT` concurrents (la rafale du §2.1). Désormais : z12-z13 lus/alimentés dans `mvt_tile_cache` (ensemble borné ~320 tuiles/couche/run, purgé par version), **warm au build** étendu z12-z13 pour `parcels` + les 2 repères cochés par défaut (`limites_parcelles`, `limites_communes` — frappés par 100 % des sessions). z14-z15 : à la volée (1-30 ms après 2.3, ensemble non borné, disque VPS à 90 %). Warm total estimé : +~40 s par rebuild (mesuré : 320 tuiles parcels ≈ 13 s + repères ≈ 25 s).

### 2.6 Fiche parcelle (G5) : §risques ×44, double appel supprimé, cache versionné

Profil AVANT (AT1066, 2e appel du process) : **5,51 s, 238 requêtes SQL (96 % du temps)** dont **2 × 1 753 ms** la MÊME paire de requêtes PPR/aléas — `ST_Intersection` exacte contre les méga-polygones DEAL de `spatial_layers` (le « défaut de prod » déjà documenté pour les tuiles), appelée par `_aleas_block` (§risques) PUIS `contraintes_parcelle` (§pièges).

Trois correctifs (`servitudes.py`, `couches_tuyau.py`, `app.py`) :
1. **Mémo par session** (`db.info`) : le 2e appel de `aleas_parcelle` dans la MÊME requête ne recalcule plus (portée = la requête, jamais partagé).
2. **Bascule sur `tuyau_subdivise`** (la partition ≤ 256 sommets construite pour les tuiles, union = géométrie d'origine) : `data_source_id` ajouté au build (les millésimes de la fiche en ont besoin), sonde de colonne + repli `spatial_layers` tant que la table n'est pas rebâtie. **Égalité prouvée** : 120 parcelles touchant PPR/aléa, liste COMPLÈTE (nature, niveau, **%**, libellé, rédhibitoire, source, millésime) : **120/120 identiques**, cumul 47,2 s → 1,1 s (**×44**) — `harnais/aleas_egalite.py`, `mesures/aleas_egalite.txt`.
3. **Cache de fiche par parcelle, versionné** (mandat, piste 2) : la fiche est run-scopée et déterministe (vérifié : 2 calculs → md5 identiques) ; clé = (idu, run, run du score, **version de fraîcheur** = `data_sources.max(last_sync/updated)` + sel `tuyau_rev`, relue ≤ 60 s en single-flight — le mécanisme de fraîcheur existant). LRU 128 fiches/worker (~10 Mo). Une bascule change la clé immédiatement ; une ingestion change la version en ≤ 60 s. Inactif sous pytest (précédent `protection._actif_sous_pytest`).

| fiche (API locale) | AVANT | APRÈS froid | APRÈS en cache |
|---|---|---|---|
| AT1066 (PPR lourd) | 9,2 s / 5,1 s chaud | 1,35 s (process échauffé) | **5 ms** |
| BZ1065 | 1,4 s | 2,0 s* | **6 ms** |
| CR0561 | — | 1,9 s* | **8 ms** |

\* premier appel du worker (échauffements process compris). **Payloads octet-IDENTIQUES avant/après correctifs** (md5 `f98d0eb2…` et `99e983ce…` constants, cache ou calcul).

Sous charge : CHASSE-3 mesurait **p95 fiche 13,7 s** (10 clients) — le cache versionné rend les clics répétés indépendants de la charge SQL.

## 3. Ce qui N'a PAS été fait (données/affichage intouchés — propositions §7)

Aucune simplification, aucun retrait de donnée, aucun changement de zoom d'affichage, aucune purge. Les tuiles servent les mêmes entités avec les mêmes propriétés (preuve multiset §2.3) ; la fiche sert les mêmes octets (md5 §2.6) ; le PDF n'est pas touché ; aucun réglage VPS n'a été modifié.

## 4. Tableau AVANT / APRÈS (synthèse)

| geste | AVANT (prod réel §1.1 / local mesuré) | APRÈS (local mesuré) | APRÈS (prod, estimation*) |
|---|---|---|---|
| rafale zoom 120 tuiles (dont avortées) | 61,3 s, 41 × 500 (local) ; en prod : effondrement §1.2 | **2,7 s, 0 erreur** | plus d'effondrement (mécanisme supprimé) |
| tuile overlay z13 froide | 4,05 s (local) ; prod p95 5,6 s | 17-390 ms calcul, 4-7 ms cache | < 300 ms ✓ (cache : ~10-20 ms) |
| tuile z14/z15 froide | ~1,2 s/5 tuiles témoin | **109-142 ms** les 5 | < 300 ms ✓ |
| fiche complète | 5,5 s local · p50 3,5 s / p95 464 s prod · p95 13,7 s charge (CHASSE-3) | 1,35 s froid · **5 ms** cache | < 1,5 s ✓ |
| statique/API pendant une rafale | SVG 229 s, /moi 319 s (prod 06/10) | event loop jamais bloqué (§2.2) | ~10 ms |
| ETag tuiles | flappe sur 12 couches (octets instables) | déterministes 480/480 | 304 fiables |

\* la prod a 5 workers (pool total 75 conn.) et `shared_buffers` 128 Mo : les gains locaux se transposent à iso-mécanisme ; les gestes G3-G5 (§6) donnent en plus au Postgres du VPS de quoi tenir ses index en mémoire. **L'« APRÈS prod réel » se mesure avec `prod_parcours.mjs` (§1.6) après déploiement.**

## 5. Preuves de neutralité (« mêmes pixels, mêmes chiffres »)

- **Tuiles** : multiset de lignes identique ancien/nouveau WHERE, 480/480 (60 couches × 8 tuiles z9-z15) ; octets déterministes 480/480 (2 calculs) — `mesures/tuile_srid_bench.csv`.
- **Fiche** : payloads md5-identiques avant/après (2 parcelles témoins) ; aléas/PPR 120/120 parcelles identiques à la ligne près — `mesures/aleas_egalite.txt`.
- **pytest** surfaces touchées : tuiles 27/27 (`test_carte_tuiles`, `test_algofix1_point4_tuiles`, `test_peremption_tuiles`, `test_coherencefix1_lot_a_fraicheur`), servitudes/fiche 26 passed + 1 skip pré-existant (`test_servitudes`, `test_fiche1_aleas`, `test_copilote2_outil`, `test_kelfoncier_au`).
- **Banc V6b** (`scripts.coherence.banc --echantillon`, 120 parcelles + 24 communes, lecteurs fiche/SQL/tuile décodée/outils, API locale corrigée) : **3 306 comparaisons · 41 écarts, TOUS des familles PRÉ-EXISTANTES documentées** (tiers_hauts_n 22, cinquante_pas 5, prix_neuf 3, copro 3, arrondi surface 6, taxe 2 — baseline ≈ 44 écarts, ORACLE-FIX-1/CHASSE-FIX-1) ; **0 écart impliquant les surfaces touchées** (aucune erreur lecteur tuile, aucun écart fiche-vs-tuile nouveau) — `mesures/v6b_echantillon.txt`.
- **make chasse** (`make -C scripts/chasse chasse`) : **exit 0** — invariants 8/8 OK (mêmes 19 728 violations pré-existantes d'`emprise_lte_surface`, seuls les exemples échantillonnés bougent), filtres 33 tests · 0 écart, face-à-face 15 228 comparaisons · 230 écarts et chasse2 168 écarts = **baselines commitées à l'identique**, à l'exception de la famille FLAPPANTE connue `prix_neuf_eur_m2` (échantillon VEFA, déjà documentée) ; **0 écart nouveau sur tuiles/fiche/servitudes**.
- Front **non touché** (aucun fichier `frontend/` modifié) → tsc/vitest sans objet pour ce mandat.

## 6. GESTES VPS pour Vic (dans l'ordre ; chaque geste avec retour arrière)

> Rappel : rien de tout ceci n'a été appliqué — le VPS est resté en lecture seule.

**G1 — Déployer la branche** (après merge) : déploiement habituel (`deploy.sh`). Retour arrière : redéployer le commit précédent.

**G2-vps — Après déploiement, rebâtir la partition et purger/réchauffer le cache de tuiles** (le tri déterministe change les octets ; la fiche a besoin de `tuyau_subdivise.data_source_id`) :
```bash
sudo -u labuse bash -c 'cd /opt/labuse/app && /opt/labuse/venv/bin/python -c "
from labuse.db import session_scope
from labuse.api.couches_tuyau import build_tuyau_subdivise, warm_overlay_tiles
from labuse.api.tiles import warm_parcel_tiles
with session_scope() as db:
    print(\"subdivise:\", build_tuyau_subdivise(db))   # ~2-4 min, purge le cache overlays
    print(warm_parcel_tiles(db, log=print))
    print(warm_overlay_tiles(db, log=print))
"'
sudo systemctl restart labuse
```
(~5-8 min ; pendant le warm, les tuiles manquantes se génèrent à la volée — pas de coupure.) Retour arrière : aucun nécessaire (tables dérivées, régénérées au prochain build ; l'ancien code ignore la colonne ajoutée).

**G3 — Postgres : réglages adaptés (12 Go RAM, base 43 Go, SSD)** :
```bash
sudo -u postgres psql -c "ALTER SYSTEM SET shared_buffers = '3GB';" \
  -c "ALTER SYSTEM SET effective_cache_size = '8GB';" \
  -c "ALTER SYSTEM SET random_page_cost = 1.1;" \
  -c "ALTER SYSTEM SET work_mem = '16MB';" \
  -c "ALTER SYSTEM SET maintenance_work_mem = '256MB';"
sudo systemctl restart postgresql@18-main   # requis pour shared_buffers
```
Pourquoi : 128 Mo de `shared_buffers` pour 43 Go = taux de cache 80,7 % (sain ≥ 99 %) ; `random_page_cost=4` fait fuir le planeur des index sur un SSD ; `work_mem` 4 Mo fait déborder les tris de la fiche. 3 Go + (5 workers × 15 conn × 16 Mo max) reste ≤ RAM. Retour arrière : `ALTER SYSTEM RESET <param>;` + restart.

**G4 — pg_stat_statements (observabilité, le mandat n'a pas pu lire le « top 20 requêtes »)** :
```bash
sudo -u postgres psql -c "ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';"
sudo systemctl restart postgresql@18-main
sudo -u postgres psql -d labuse -c "CREATE EXTENSION pg_stat_statements;"
```
Retour arrière : `DROP EXTENSION pg_stat_statements;` + `ALTER SYSTEM RESET shared_preload_libraries;` + restart. (Optionnel, même famille : `ALTER SYSTEM SET log_min_duration_statement = '500ms';` + `SELECT pg_reload_conf();` — sans restart.)

**G5 — Caddy : compression zstd en plus de gzip** (`/etc/caddy/Caddyfile`, une ligne) :
```
encode zstd gzip
```
puis `sudo systemctl reload caddy`. −15 à −25 % d'octets sur JSON/tuiles pour les navigateurs qui l'acceptent. Retour arrière : remettre `encode gzip` + reload.

**G6 — garde-fou pool** (optionnel, dans `/etc/labuse/labuse.env`) : `LABUSE_DB_POOL_TIMEOUT_S=10` si disponible dans config — sinon sans objet, l'interblocage est corrigé à la racine. Ne PAS augmenter pool_size (75 connexions ≤ max_connections 100, c'est sain).

**G7 — Exposition/relief** : `sudo apt install gdal-bin && sudo systemctl restart labuse` → la tuile « Exposition » de la fiche cessera de dire « relief non disponible » (cause prouvée §1.5). Retour arrière : `apt remove gdal-bin`.

**G8 — RAM : ce que ça apporterait** (chiffré, pas un geste) : le jeu CHAUD actuel (mvt_parcels 245 Mo + mvt_tile_cache ~150 Mo + index spatiaux chauds + tuyau_subdivise ~2 Go) tient dans ~4-5 Go → **12 Go suffisent une fois G3 appliqué** (le page cache absorbe le reste). Passer à 24 Go ne paierait que si la fiche devait servir des intersections exactes NON partitionnées (ce mandat les a justement supprimées) ou si la base dépasse ~60 Go : à ce stade, `shared_buffers 6 Go` et ~15-20 % de gain sur les requêtes froides, pas plus. Le disque (90 %) est un problème plus urgent que la RAM.

**Mesure APRÈS en prod** : rejouer `prod_parcours.mjs` (§1.6) et re-agréger le journal Caddy (`mesures/prod_caddy_avant.csv` donne la commande dans l'en-tête du harnais) après 48 h de trafic.

## 7. Propositions NON appliquées (changeraient l'affichage ou attendent un arbitrage)

- **G1 (reporté par Vic 06/10)** : dessiner `limites_parcelles` depuis la source `parcels-ile` → **−81 % d'octets à l'ouverture** (G1-MESURE : 3,81 → 0,72 Mo gz) ; supprime la cause 1 des « carrés » (§1.4). Dépend du fix parcels-ile (G1, commits non mergés).
- **Outils GeoJSON (G4 de VITESSE-CARTE-1)** : Piscines 6,1 Mo / 90 % sérialisation Python → re-tuiler via le tuyau. Inchangé ici (hors cible fiche/tuiles du mandat, aucun chiffre ne doit bouger sans banc dédié).
- **Warm z14-z15 zones habitées** : inutile après §2.3 (1-30 ms) et dangereux pour le disque VPS (90 %).
- **Cache proxy Caddy (plugin Souin)** : rendu surtout utile aux ETags stables (§2.4 les fournit) ; à réévaluer après mesure prod.
- **Préfiltre `commune` sur les requêtes servitudes ×12 de la fiche** (197 ms cumulés) : gain faible, surface de risque inutile.
- **URLs de tuiles versionnées** (`?v=<version>` posé par le front depuis `/map/tiles/meta`) + `Cache-Control: immutable` : supprimerait même la revalidation 304. Touche le front (hors périmètre ici) ; les ETags désormais stables (§2.4) en sont le prérequis.
- **Attributs de tuiles jamais lus** : déjà traité par l'antériorité (FIX-CARTE T2 : `flags` retirés, `zone_lib` différé z≥14) — rien de neuf trouvé.

## 8. Livrables

- Code : `src/labuse/api/{app.py, tiles.py, couches_tuyau.py, servitudes.py}` (6 correctifs, §2).
- Harnais rejouables : `docs/audit-2026-10/VITESSE-PROD-1/harnais/{prod_parcours.mjs, rafale_tuiles.py, tuile_srid_bench.py, aleas_egalite.py}`.
- Mesures brutes : `docs/audit-2026-10/VITESSE-PROD-1/mesures/` (Caddy prod, VPS, rafales AVANT/APRÈS, banc SRID 480 tuiles, égalité aléas, V6b).
- Branche poussée `fix/vitesse-prod-1` — **pas de merge** (geste Vic).
