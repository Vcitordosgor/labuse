# LOT V — Fuzzing API (100 passes seedées) — CYCLE 5

**Type** : AUDIT SEUL, non destructif. Aucune écriture réelle complétée (corps invalide, sans cookie).
**SEED (RNG python)** : `5002` — noté et appliqué (`random.seed(5002)`).
**Cible** : `http://localhost:8000` — openapi 200 paths (140 GET / 65 POST / 7 PATCH / 7 DELETE).
**Script** : `/tmp/fuzz_lotv.py` — boucle openapi + matrice hostile (types faux, bornes 0/-1/1e18/1e400, négatifs, unicode/emoji, SQLi `' OR 1=1--`, params doublés `?x=1&x=2`, encodages `%00`/`%2e%2e%2f`, chaînes 5000 car., bigint 20 chiffres).
**Livrable CSV** : `lot-v.csv` (100 lignes).

## Score : OK 96 / KO 4 sur 100

Distribution des codes : `422×31, 429×29, 200×24, 404×10, 500×4, 204×2`.
(429 = plafond de débit atteint pendant le run — 4xx propre, conforme à l'invariant.)

**INVARIANT VIOLÉ 4 fois** (500). Aucune stacktrace / chemin serveur / `Traceback` fuité : le corps des 4 est le générique `Internal Server Error` (bon), mais un 500 reste un 500 → chaque cas = 🟠.

## Régressions cycle 4 — TOUTES TENUES (aucune réapparition)

| Cas | Attendu | Observé | Verdict |
|---|---|---|---|
| GB-028 `/api/copilote/runs/{run_id}` non-UUID | 422 | **422** | OK |
| GB-028 run_id int / SQLi / `/events` after_seq | 422 | **422** | OK |
| GB-029 `/modules/permis` `?offset=-5` | 422 | **422** | OK |
| GB-029 `/modules/promesses` `?offset=-5` | 422 | **422** | OK |
| GB-029 `/modules/fantome` `?offset=-5` | 422 | **422** | OK |

GB-028 et GB-029 **ne réapparaissent pas**. Pas de 🔴 régression.

## Les 4 × 500 trouvés (tous 🟠, tous reproductibles et stables)

### 1. 🟠 `/events` GET — LIMIT négatif → SQL error
- **Entrée minimale** : `GET /events?limit=-1`  (stable, 3/3 → 500)
- **Corps** : `Internal Server Error` (pas de fuite).
- **Cause** : `src/labuse/api/events.py:672` — `limit: int = 100` **sans borne** (`ge=`/`le=`). `offset` est protégé par `max(0, offset)` (l.691) mais `limit` va tel quel dans `LIMIT :lim` (l.690) → Postgres refuse `LIMIT -1` → 500. `offset=-5` seul = 200 (garde OK) ; c'est bien `limit<0` le trou.
- **Correctif suggéré** : `limit: int = Query(100, ge=1, le=<cap>)` (ou `max(1,limit)` avant la requête, comme `offset`).

### 2. 🟠 `/filtre` GET — combinaison hostile atteint le constructeur SQL
- **Entrée** : payload complet (`limit=NaN&offset=' OR 1=1&sort=%s%s%s%n&idus=-1&commune=true&surface_max=null&…&communes=-&…`), stable 3/3 → 500.
- **Corps** : `Internal Server Error` (pas de fuite).
- **Cause** : effet d'ordre de validation. Les params `commune`/`communes` n'ont **aucun schéma** (type `None` en openapi) → passent la validation ; combinés aux autres filtres ils atteignent le builder qui bâtit un SQL invalide. Chaque param isolé = 422/404 propre ; c'est l'union qui casse. La SQLi `' OR 1=1` **n'exfiltre rien** (requêtes paramétrées, corps générique) — c'est un plantage de construction, pas une injection réussie.
- **Correctif suggéré** : borner/valider `commune`/`communes` (schéma `str`) et blinder le builder contre les combos vides.

### 3. 🟠 `/sources/{source_id}/test` POST — bigint overflow (path int)
- **Entrée** : `POST /sources/99999999999999999999/test` (bigint 20 chiffres), **sans cookie**, corps `[1,2,3]` → 500 stable.
- **Corps** : `Internal Server Error` (pas de fuite).
- **Cause** : Python n'a pas de borne d'entier → FastAPI accepte `99999999999999999999` comme `int` **valide**, mais la valeur **dépasse `bigint` Postgres** → `NumericValueOutOfRange` avant même le contrôle de session. `source_id=1` = 200, `source_id=abc`/`1e18` = 422 (OK) : seul le très-grand-entier passe.
- **Correctif suggéré** : contraindre le path (`Path(..., le=9223372036854775807)`) OU rattraper l'overflow → 404. **Note** : 500 atteint SANS session → non-destructif mais joignable non authentifié.

### 4. 🟠 `/projets/{pid}` PATCH — même bigint overflow (path int)
- **Entrée** : `PATCH /projets/99999999999999999999` (sans cookie, corps `{}`) → 500 stable.
- **Corps** : `Internal Server Error` (pas de fuite).
- **Cause** : identique au #3 — `pid` int non borné → overflow `bigint`. `pid=1` = 404 (auth OK), `pid=abc`/`1e18` = 422 : seul le bigint casse.
- **Correctif suggéré** : borner le path int (motif générique, s'applique à tous les `{pid}`/`{...id}` int → SQL).

## Familles de cause (2 racines pour 4 KO)

- **A — param entier non borné atteignant SQL** : `LIMIT -1` (#1) et **bigint overflow** sur path int (#3, #4). Racine générique : un `int` accepté par FastAPI (Python illimité) ou un négatif non gardé arrive tel quel dans une requête Postgres.
- **B — combinaison de filtres non validés** (#2) : params sans schéma (`commune`/`communes`) passent la validation et cassent le builder en union.

Aucune fuite de chemin/stacktrace/Traceback dans aucun des 4 corps (le handler d'erreur global masque bien) — le défaut est le **500 lui-même**, pas une divulgation.
