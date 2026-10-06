# TUILES-TX-1 — fuite de transactions sur la route des tuiles

**Branche** `fix/tuiles-tx-1` · pas de merge · 3 fichiers source touchés (+91 / −60).

## Symptôme
En prod, jusqu'à 45 connexions bloquées `idle in transaction` sur
`WITH b AS (SELECT ST_TileEnvelope($1,$2,$3)…)` → pool saturé, site figé.

## Route et fonction qui servent cette requête
| Couche | Route | Handler | Requête `ST_TileEnvelope` |
|---|---|---|---|
| Parcelles | `GET /map/tiles/{z}/{x}/{y}.pbf` | `api/tiles.py:mvt_tile` | `_parcel_tile_bytes` (`tiles.py:587-596`) |
| Couches/overlays | `GET /map/tiles/{kind}/{z}/{x}/{y}.pbf` | `api/couches_tuyau.py:couche_tuile` | `_construire_tuile` (`couches_tuyau.py:591-610`) |

## Cause
Les deux handlers recevaient leur session via `Depends(get_db)`. La **fermeture**
(commit/rollback/close de `session_scope`) d'une dépendance `yield` est **DÉFÉRÉE par le
framework à APRÈS la réponse**. À la déconnexion / annulation du client, ce report peut être
sauté : la transaction auto-ouverte par le premier `SELECT` (SQLAlchemy *autobegin*) reste
ouverte sur une connexion du pool → `idle in transaction` jusqu'à épuisement du pool.

## Correctif (ne touche NI la requête NI le rendu)
Chaque tuile **possède et ferme sa transaction dans le corps du handler**, plus aucun report :

- `app.py` — nouveau context manager **`api_session()`** = `session_scope` (commit si OK,
  rollback sinon, **close TOUJOURS dans un `finally`**) + le plafond `statement_timeout` par
  requête. `get_db` en devient un simple emballage (routes inchangées par ailleurs).
- `tiles.py:mvt_tile` et `couches_tuyau.py:couche_tuile` — n'utilisent plus `Depends(get_db)` :
  ils ouvrent `with api_session() as db:` **dans le handler**. Le `finally` de close s'exécute
  de façon synchrone à la sortie — **succès, erreur OU client qui annule**. SQL, paliers de
  simplification, propriétés servies, cache LRU/persistant, ETag/304 : **identiques**.
  (Les bornes de zoom hors-plage répondent 204/404 **sans ouvrir de connexion**.)

`mvt_tiles_meta` et `couche_detail` conservent `Depends(get_db)` (hors périmètre : pas la
route des tuiles).

## Preuves locales (base `labuse`, 431 663 parcelles)

**1. Serveur réel — 200 tuiles dont 77 annulées en plein vol** (`reports/run_tuiles_tx_proof.sh`)
```
Requêtes : ok=123, cancelled=77, errors=0
pic PENDANT rafale : idle in transaction = 15   (= pool plein, transitoire)
max idle-in-tx APRÈS drain (2,4 s) : 0
SELECT state, count(*) — snapshot final :  idle  5
idle in transaction (final) = 0  →  OK
```
Les 15 du pic sont transitoires (pool pool_size+overflow) et **retombent à 0** ; aucune
connexion ne reste bloquée.

**2. Mécanisme, déterministe et indépendant de la version du framework**
(`reports/tuiles_tx_direct.py` — appelle les handlers EN DIRECT, sans finalisation FastAPI)
```
(0) session laissée ouverte après un SELECT  → idle in transaction = 1  (état de panne reproduit)
(1) mvt_tile parcelles succès (status 200)    → idle in transaction = 0
(2) couche_tuile « limites_parcelles » succès → idle in transaction = 0
(3) erreur en pleine génération (ST_AsMVT lève = annulation) → idle in transaction = 0
VERDICT : OK — chaque tuile ferme sa transaction (succès ET erreur/annulation)
```

**3. Non-régression** — `pytest` tuiles/carte : **22 passed** (test_carte_tuiles,
retours14/16_carte, algofix1_point4_tuiles, peremption_tuiles) ; `py_compile` OK.

> Note d'honnêteté : sous le stack local (Starlette 1.3.1) le chemin `Depends` d'AVANT retombe
> lui aussi à 0 (la finalisation s'exécute ici même à la déconnexion). La preuve (2) démontre donc
> le mécanisme sans dépendre de ce comportement : le correctif **supprime la dépendance** à la
> finalisation différée — la fermeture est désormais garantie dans le handler, quel que soit le stack.
