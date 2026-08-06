# M45 — PHASE 1 · Perf du compteur unifié `/filtre` (mesuré, modèle M42)

Endpoint `/filtre` (le « théâtre » : compte exact + ventilation par tier + page d'aperçu en UN
appel). Compteur = `_q_v2_stats` (SQL exact, mémorisé 30 s). Mesures **run servi `q_v8_calibre`,
île entière** (le pire cas ; en commune c'est plus rapide), combos DISTINCTS (cache miss chacun).

## Barre NIVEAU 1 (cible P3 : compteur < 500 ms) — ✅ TENUE
| Combo | compteur |
|---|---|
| tier(×4) + surface_min=350 + sdp≥100 | **217 ms** |
| tier(×4) + surface_min=550 + sdp≥100 | **195 ms** |
| tier(×4) + surface_min=750 + sdp≥100 | **197 ms** |
| tier + surface_min (×8 valeurs) | 136–200 ms (hors 1er hit à froid ~830 ms, JIT du plan) |

Chemin index `ix_p_v2_run_rang` / `uq_p_v2_run_parcelle` (index-only scan). **< 500 ms tenu** pour
toute la barre niveau 1. Cache 30 s : un ajustement répété = ~4 ms.

## Index ajouté (P1) : `ix_dryrun_cascade_flag_probe`
Filtre `flags`/`flags_exclus` (vigilances par type) : l'EXISTS **seq-scannait 9,7 M lignes** de
`dryrun_cascade_results` (~4–9 s île entière). Index PARTIEL `(run_label, layer_name, parcel_id)
WHERE result IN ('SOFT_FLAG','UNKNOWN')` → EXPLAIN confirme le passage **Seq Scan → Index Scan**
(coût 889 k → 277 k). Déclaré dans `models.py` (+ `ensure_flags_probe_index`, idempotent).

### Filtre vigilance NIVEAU 2 (île entière) — après index
| flag | avant | après | n parcelles flaguées |
|---|---|---|---|
| cinquante_pas | ~4 s | **637 ms** | 16 099 |
| sol_pollue | ~0,8 s | **805 ms** | 10 333 |
| ravine | ~1,2 s | **1 174 ms** | 13 972 |
| pente | 4 141 ms | **4 141 ms** | 60 616 |
| bruit_route | 7 098 ms | **7 098 ms** | 111 228 |

**Constat honnête** : l'index supprime le seq-scan, mais pour les couches à **forte cardinalité**
(bruit_route 111 k, pente 60 k) le coût résiduel est **la jointure île entière** (111 k parcelles
flaguées × trame + scores v2), pas le scan — l'EXPLAIN le montre (Parallel Seq Scan on parcels +
Hash Join). Sub-500 ms pour ces couches exige une **dénormalisation** (colonne bitset de flags sur
`parcel_p_score_v2`, ou table matérialisée `parcel_flags` indexée), pas un simple index.

## Recommandation (avant d'exposer le tiroir « Risques » en P2)
1. **Barre niveau 1 : rien à faire** — < 500 ms tenu.
2. **Vigilances (tiroir Risques), 2 options à l'exposition P2** :
   - dénormaliser les flags servis en `parcel_flags` (matérialisée au build du run) → probe O(1) ;
   - **ou** scoper le filtre vigilance à la commune quand aucune commune n'est choisie (les
     couches à forte cardinalité ne sont pas des filtres « île entière » utiles en pratique).
   Mon appel : la **dénormalisation** (alignée « point de calcul unique » + compteur direct), à
   décider au moment d'exposer le tiroir. Rien n'est exposé tant que ce n'est pas sous la barre.

## Architecture confirmée
Endpoint unifié `/filtre` (dataclass `FiltreCriteres` → `_q_v2_where`) ; compteur = `_q_v2_stats`
(SQL exact + cache 30 s) ; **0 filtrage client GeoJSON** ; `source` REQUISE (404 sinon). Une
nouvelle facette P2 s'ajoute dans `FiltreCriteres` + `_q_v2_where` et coule dans tous les endpoints.
Digest : `qa/m45/compteur_perf_p1.csv`.
