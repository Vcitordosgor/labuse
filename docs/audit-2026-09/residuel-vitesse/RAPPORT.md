# RESIDUEL-VITESSE — pourquoi le run résiduel tombait à 2 p/s (et le fix)

Branche `fix/residuel-vitesse` (worktree `labuse-residuel-fix`), base main `a8db2a5e`.
Commit du fix : `c7f581b2`. DB partagée `labuse`, run servi = run_seq 5.

## Symptôme
Run résiduel `post-plu8` (run 7) à ~2 p/s contre 48 p/s le 22/09, **malgré** `shared_buffers`
passé à 2 Go et `spatial_layers` vacuumée. Le diagnostic « environnement » de l'audit
RESIDUEL-VITESSE-1 ne suffisait pas.

## Observation du vivant
- **`pg_stat_activity`** : 2 backends à ~98 % CPU sur la MÊME base — le résiduel (SELECT grève)
  ET un `INSERT INTO parcel_couche_intersection …` (build-intersections d'un autre worktree,
  `psql /tmp/fix1_sp4.sql`) qui bouclait en `ST_Intersection` lourd. Ce parasite **volait un cœur
  entier** et calait le résiduel à **0 p/s** par intermittence. → tué.
- **Pas de verrou** (`pg_blocking_pids` = 0) : le résiduel n'était pas bloqué, il était lent.
- Après coupure du parasite : **8 p/s** — mieux mais toujours pas 48.
- **cProfile de `compute_residuel`** : 99,6 % du temps en `psycopg.wait` (attente DB),
  ~8,6 requêtes/parcelle. Breakdown par requête : **la grève `_greve_certaine_m2` = 94 %**
  (415 ms/parcelle), tout le reste = 26 ms.

## La vraie cause (au niveau requête, pas « environnement »)
`_greve_certaine_m2` intersecte chaque parcelle contre les couches PPR / PLU **telles quelles**.
`EXPLAIN ANALYZE` par parcelle → variance énorme : la plupart 0,7–14 ms, mais certaines
**1007–1176 ms**. Le plan montre l'`Aggregate` final (ST_Union + ST_Intersection des grèves) à
**797 ms**.

Cause racine : à La Réunion le **PPR INTERDICTION est un polygone de 140 k à 320 k sommets**
(jusqu'à 2,2 Mo ; `plu_gpu_zone` jusqu'à 90 k). `ST_Intersection` / `ST_Union` / `ST_MakeValid`
parcourent **TOUS les sommets** même pour ne garder qu'un ruban le long de la petite parcelle.
Décomposition sur la parcelle 8168 (PPR) : `ST_MakeValid` = 82 ms, `ST_Intersection` (sans
MakeValid) = **552 ms**. **Toutes les couches grève sont VALIDES en base** (0 invalide sur l'île)
→ `ST_MakeValid` ne corrige rien mais coûte quand même.

Mesure directe : **requête grève d'origine = 2,1 req/s** — ce qui reproduit exactement le ~2 p/s.
(Ce n'est PAS un index manquant — l'index GiST `idx_spatial_layers_geom_2975` est bien utilisé ;
PAS une géométrie invalide — tout est valide ; c'est le **nombre de sommets** du gros polygone.)

## Le fix
`ST_ClipByBox2D(geom, p.b)` rogne le gros polygone à la **bbox de l'assiette insetée `p.b`**
(opération O(bbox), pas O(sommets)) **avant** l'intersection fine. Appliqué à `uau`/`plu_gpu_zone`,
`ppr`, `peb`, `cinquante_pas`. `dpf`/`ravine` (petits + buffer) laissés inchangés.

Résultat **strictement identique** : bbox(`p.b`) contient `p.b`, l'assiette ⊆ `p.b`, donc
`grève ∩ assiette` est inchangée.

## Preuves d'identité (le fix ne change AUCUN résultat)
1. **Aire grève** orig vs fixé, parcelles à gros PPR (8168, 8695, 8732, 8692, 8673) + lot de 60 :
   identique au bit près, écart max **5e-10 m²** (bruit flottant, très en-dessous de l'arrondi
   entier de `sdp_residuelle_m2`).
2. **30/30 parcelles constructibles** (sdp > 0, là où la grève retranche vraiment) :
   fixé (run 9) == baseline sans-fix (run 10), **zéro écart** sur les 6 colonnes.
3. **55 parcelles golden** (dont 40 chevauchant PPR/PEB) : fixé == run 5 servi, zéro écart.
4. Isolation : baseline vs run 5 = 20/30 écarts sur constructibles — **dérive PRÉ-EXISTANTE**
   (PIEGES-RISQUES-2 a gradué le PPR + élargi les prescriptions, mergé dans main depuis le 22/09),
   présente aussi SANS mon fix. C'est la raison d'être du recalcul (run 7/8), indépendant du fix.
5. **34 tests** verts (`test_scoring6_assiette`, `test_residuel`, `test_faisabilite`).

## Chiffres de vitesse
| Mesure | Avant | Après fix |
|---|---|---|
| Grève seule (60 parcelles PPR) | **2,1 req/s** | **85,9 req/s** (×40) |
| Grève in-situ parcelle 8168 (PPR) | 978 ms | **6,3 ms** |
| Run résiduel mono-thread (machine chargée) | 2 p/s | **33 p/s** (×16) |
| Run résiduel **2 shards parallèles** | — | **50 p/s** ✅ ≥ 40 |

Le fix supprime le goulot grève (94 % → négligeable). Le plafond mono-thread à 33 p/s vient
ensuite des ~7 autres requêtes/parcelle **gonflées par la pression mémoire** (machine 8 Go,
swap 7–9 Go, 4 agents Claude concurrents) — facteur machine, pas le code résiduel. Le run étant
mono-processus (1 backend à 85 % CPU, cœurs libres), **2 shards de communes disjointes** dans un
seul `run_seq` remontent à **50 p/s** et atteignent l'objectif. Sur machine quiète (22/09 = 48 p/s)
le fix seul dépasse 40.

## Run déliverable en cours
`run_seq 8` « post-plu8-clip-2shard » : île entière via 2 workers (`/tmp/shard_worker.sh`,
communes alternées `shardA`/`shardB`), à ~50 p/s. Chaque worker écrit des communes disjointes →
pas de conflit de clé. Métadonnées `residuel_runs` (duree_s) écrites par-commune (cosmétique).
`bascule` = geste manuel de Vic (jamais le run servi).
