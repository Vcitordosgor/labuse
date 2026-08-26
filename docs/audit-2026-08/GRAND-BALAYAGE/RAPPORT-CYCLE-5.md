# GRAND BALAYAGE — CYCLE 5 · RAPPORT · LES 500 (dernier cycle)

> AUDIT SEUL. Findings GB-034→. Front :5174/socle/, back :8000, run servi `q_v10_m129`, 431663 parcelles.
> **Référence perf en service** : fiche `/parcels/{idu}` mesurée **0,30-0,79 s** (fix GB-024a live).
> **Non-régression au boot** : GB-028/029/030 → **422** (pas 500) ✓ ; FIX-C4 + FIX-C4-JAUNES mergés.
> Barème : 🔴 bloquant / faux chiffre / fuite / **régression GB-015→033** · 🟠 dégradé / 500 · 🟡 mineur.
> **PASSE BLANCHE** = zéro nouveau 🔴/🟠. La campagne se CLÔT dans les deux cas.

## Seeds (rejouabilité)
| Lot | Seed | Passes |
|---|---|---|
| U vérité de masse | 5001 | 200 |
| V fuzzing API | 5002 | 100 |
| W exports de masse | 5003 | 50 |
| X marches UI | 5005 | 60 |
| Y Copilote génératif | 5006 | 50 |
| Z charge/concurrence/endurance | 5004 | 40 |

## Gardées G1-G6

## Tableau des 500 passes (par lot)
| Lot | Passes | OK | KO | Annexe |
|---|---|---|---|---|
| U — vérité de masse | 200 | | | lot-u.csv |
| V — fuzzing API | 100 | | | lot-v.csv |
| W — exports de masse | 50 | | | lot-w.csv |
| X — marches UI | 60 | | | (seeds) |
| Y — Copilote génératif | 50 | | | (spot-checks) |
| Z — charge/concurrence/endurance | 40 | | | (p95) |

## LOT V — fuzzing API (100, seed 5002) — agent + vérifié curl
**96 OK / 4 KO.** Codes : 422×31, 429×29 (rate-limit=4xx propre), 200×24, 404×10, 500×4, 204×2.
**Non-régression** : GB-028 (run_id non-UUID/int/SQLi + /events after_seq) → **422** partout ✓ ; GB-029 (offset -5 sur permis/promesses/fantome) → **422** ✓. Aucune réapparition.
Les 4 KO = **500 sur entrée malformée** (aucune fuite : corps « Internal Server Error » générique, handler global masque bien) → **GB-034/035/036**. Vérifiés curl (GB-034 events, GB-036 bigint ✓ ; GB-035 combinaison-spécifique).

## Findings GB-034→

#### GB-034 · 🟠 · `/events?limit=-1` → 500 (limit non borné)
- Vérifié curl : `GET /events?limit=-1` → **500**. Cause : `events.py:672` `limit: int = 100` sans borne → `LIMIT -1` refusé par Postgres. L'`offset` y est gardé (`max(0,offset)`), pas le `limit`. **Même CLASSE que GB-029** (entier non borné → SQL) mais endpoint/param non couvert par le fix cycle-4. Correctif : `limit: int = Query(100, ge=1, le=<cap>)`.

#### GB-035 · 🟠 · `/filtre` — combinaison de params hostiles → 500 (builder SQL)
- Agent : un payload combinant des params sans schéma openapi (ex. `commune=true`, `communes=-`) passe la validation puis casse le builder SQL en union → 500. Chaque param ISOLÉ = 422/404 propre (mon curl `commune=true` seul → 200). **La SQLi `' OR 1=1` n'exfiltre rien** (requêtes paramétrées) — c'est un plantage de construction, pas une injection. Correctif : valider/borner les params libres du builder `_q_v2_where`. _(Combinaison-spécifique : repro exacte dans lot-v.csv, seed 5002.)_

#### GB-036 · 🟠 · Path int > bigint (2^63) → 500 (overflow avant contrôle)
- Vérifié curl : `POST /sources/99999999999999999999/test` → **500** ; `PATCH /projets/99999999999999999999` → **500** ; contraste `PATCH /projets/999999999` (int normal) → **404** propre. Cause : un path int énorme dépasse `bigint` Postgres (`NumericValueOutOfRange`) au `CAST`/comparaison, AVANT le 404/contrôle de session. Motif GÉNÉRIQUE à tous les `{id:int}` → SQL. Correctif : borner les path int (`Path(le=2**63-1)` ou garde) → 404/422. _(Non-destructif ; joignable sans session mais n'exécute rien.)_

## Inventaire de purge [GB-TEST]

## VERDICT DÉFINITIF DE CAMPAGNE
