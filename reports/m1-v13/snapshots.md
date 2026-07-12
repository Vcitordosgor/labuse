# M1 — Gel des snapshots (lot 4) · 12/07/2026

## Les deux jeux gelés (table `score_snapshots` + `score_snapshot_parcelles`)

| snapshot_id | label | contenu | seuil brûlante | brûlantes | créé le |
|---|---|---|---|---|---|
| 1 | `v1.2-2026-07-10` | statuts q_v3_datagap + V v1.2 (scores `parcel_v_score` calculés les 10-11/07) + brûlantes | 34 | **79** | 12/07/2026, AVANT recalcul |
| 2 | `v1.3-2026-07-12` | statuts q_v3_datagap + V v1.3 (barème signes corrigés) + brûlantes + veille_succession | 17 | **120** | 12/07/2026, APRÈS recalcul |

`snapshot_scores()` refuse d'écraser un label existant — un gel ne se réécrit pas.

## Intégrité de q_v3_datagap (critère d'acceptation)

Le run matrice de référence n'a PAS été touché par le recalcul V :

```
checksum q_v3_datagap AVANT recalcul : f568e45046c3e85892f0876e8096ca13
checksum q_v3_datagap APRÈS recalcul : f568e45046c3e85892f0876e8096ca13   (identique)
```
(md5 de `parcel_id:statut:q:a` agrégés triés — requête dans `annexe` du script `/tmp/m1_run.py`,
recopiée dans SYNTHESE-M1.md.)

## Protocole d'arbitrage forward (au millésime DVF couvrant 2026)

1. Événements de référence : mutations **L2** (nature ∈ {Vente, Vente terrain à bâtir}) avec
   `date_mutation > 2026-07-12` (strictement postérieures au gel v1.3 ; le gel v1.2 du même
   jour partage la borne — aucune vente n'est observable entre les deux gels).
2. Pour chaque snapshot : RR prospectif = taux d'événement L2 des brûlantes-au-gel
   (resp. chaudes-au-gel) vs taux des parcelles non-écartées-au-gel, IC95 Katz ;
   N attendus faibles (79 vs 120 brûlantes) → reporter aussi les taux Wilson bruts.
3. Verdict : le jeu v1.3 doit faire au moins aussi bien que v1.2 sur les brûlantes ET mieux
   sur la bande V ≥ seuil hors chaudes ; sinon, retour d'expérience au design v2.
4. Les chaudes servent de contrôle : même statut matrice dans les deux snapshots
   (q_v3_datagap partagé) — toute divergence brûlantes est imputable à V seul.
