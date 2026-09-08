# DÉPLOIEMENT — matérialisation `geom_simple` des couches SOURCES-1 (COUCHES-1 Lot 6 / COUCHES-2 point 3)

**Pour Vic — à jouer en prod au déploiement.** Rien n'a été exécuté en prod par Claude Code.

## Ce que c'est, pourquoi

COUCHES-1 (Lot 6) a ajouté, à la liste de matérialisation de `models.py`, les couches ajoutées par
SOURCES-1 qui simplifiaient leur géométrie **à la volée** à chaque requête `/map/layers.geojson`
(coût mesuré : RPG/`safer` 38 460 polygones = **536 ms** de `ST_SimplifyPreserveTopology` par appel,
contre **34 ms** en lecture de `geom_simple`). La colonne `geom_simple` doit être **remplie une fois**
pour ces couches.

- Le code (`src/labuse/models.py`, UPDATE de la fonction `ensure_*`) remplit `geom_simple` pour les
  nouveaux `kind` **au prochain passage d'ensure** (toute CLI d'ingestion l'appelle). Si un import
  tourne après le déploiement, la matérialisation se fera **toute seule**.
- Cette procédure est le **filet manuel** : la jouer si aucun import n'est prévu à court terme, pour
  que le gain soit effectif dès la mise en ligne. L'UPDATE est **idempotent** (`WHERE geom_simple IS
  NULL`) : le rejouer ne coûte rien.

## Nature de l'opération

- **Écriture** (UPDATE) mais **non destructive** : remplit une colonne actuellement `NULL`, ne touche
  ni `geom` ni `geom_2975` ni aucune donnée servie. Aucune migration de schéma (la colonne existe déjà).
- Aucune interruption de service requise : l'endpoint lit `COALESCE(geom_simple, simplification à la
  volée)` — tant que `geom_simple` est `NULL`, il sert l'ancien chemin ; dès qu'il est rempli, il
  sert le rapide. La bascule est ligne par ligne, transparente.

## Ordre

1. **Déployer le code d'abord** (la branche qui contient la nouvelle liste `models.py` — COUCHES-1
   mergée). Vérifier que le déploiement est en ligne.
2. **Puis** jouer l'UPDATE ci-dessous (ou laisser le prochain import le faire).

## Commande (sur la base de PROD)

Se connecter à la base de prod (adapter la chaîne de connexion prod — rôle, hôte, base) :

```bash
# Exemple — REMPLACER par la connexion prod réelle :
psql "$LABUSE_PROD_DATABASE_URL"
```

Exécuter, dans une transaction, avec un `lock_timeout` de sécurité (l'UPDATE ne prend qu'un verrou
ligne, mais le garde-fou évite d'attendre un verrou concurrent) :

```sql
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '10min';

UPDATE spatial_layers
   SET geom_simple = ST_SimplifyPreserveTopology(geom, 0.0002)
 WHERE geom_simple IS NULL
   AND geom IS NOT NULL
   AND kind IN (
     'plu_gpu_prescription','dpu','peb','sup','dpf','zone_humide','ens','safer',
     'sol_pollue','bruit_route','bruit_carte','tcsp_zone'
   );

COMMIT;
```

*(Liste identique à `src/labuse/models.py` — les couches SOURCES-1 servies en aplat/ligne. Les semis
de points — `amenite`, `amenite_bpe`, points CASIAS — sont exclus : rien à simplifier.)*

### Variante « par couche » (si on veut des verrous plus courts)

Si l'on préfère éviter un seul UPDATE long, le jouer **couche par couche** (chacun est indépendant,
idempotent). Le seul poste lourd est `safer` (≈ 38 460 polygones) :

```sql
UPDATE spatial_layers SET geom_simple = ST_SimplifyPreserveTopology(geom, 0.0002)
 WHERE geom_simple IS NULL AND geom IS NOT NULL AND kind = 'safer';
-- puis répéter en remplaçant 'safer' par : plu_gpu_prescription, zone_humide, bruit_route,
-- sol_pollue, sup, dpf, dpu, ens, bruit_carte, peb, tcsp_zone
```

## Durée attendue

Volumes prod attendus (ordre de grandeur, mesurés sur la base de recette) et coût de simplification :

| kind | lignes (recette) | poids |
|------|------------------|-------|
| safer (RPG) | 38 460 | le plus lourd (~0,5 s de CPU simplify) |
| plu_gpu_prescription (ER/EBC) | 10 490 | moyen |
| zone_humide | 3 122 | léger |
| bruit_route | 1 004 | léger |
| sol_pollue, sup, dpf, dpu, ens, bruit_carte, peb, tcsp_zone | < 600 chacun | négligeable |

Total recette : **54 583 lignes matérialisées en quelques secondes**. En prod, compter **quelques
secondes à ~2 minutes** selon la charge et la taille réelle. Aucun blocage de lecture pendant l'opération.

## Vérification (après l'UPDATE)

**1. Toutes les couches visées ont un `geom_simple`** (chaque `sans_simple` doit valoir `0`) :

```sql
SELECT kind, count(*) AS total, count(geom_simple) AS avec_simple,
       count(*) - count(geom_simple) AS sans_simple
FROM spatial_layers
WHERE kind IN ('plu_gpu_prescription','dpu','peb','sup','dpf','zone_humide','ens','safer',
               'sol_pollue','bruit_route','bruit_carte','tcsp_zone')
GROUP BY kind
ORDER BY sans_simple DESC;
```

**2. Le gain est effectif** — comparer les deux chemins sur la couche la plus lourde :

```sql
EXPLAIN ANALYZE SELECT ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.0002))
  FROM spatial_layers WHERE kind = 'safer';        -- ancien chemin (à la volée) : ~500 ms
EXPLAIN ANALYZE SELECT ST_AsGeoJSON(geom_simple)
  FROM spatial_layers WHERE kind = 'safer';        -- nouveau chemin : ~30 ms
```

**3. Bout en bout** — l'endpoint sert vite (attendu < 1 s côté SQL ; le temps total inclut la
sérialisation JSON, ~19 Mo pour RPG entier) :

```bash
curl -s -o /dev/null -w "%{time_total}s\n" \
  "https://<prod>/map/layers.geojson?kind=rpg&limit=40000"
```

## Rollback

Aucun rollback nécessaire (opération non destructive, idempotente). En cas de doute, vider la
colonne pour ces couches rétablit exactement l'état antérieur (l'endpoint retombe sur la
simplification à la volée) :

```sql
-- Optionnel, seulement si l'on veut annuler :
UPDATE spatial_layers SET geom_simple = NULL
 WHERE kind IN ('plu_gpu_prescription','dpu','peb','sup','dpf','zone_humide','ens','safer',
                'sol_pollue','bruit_route','bruit_carte','tcsp_zone');
```
