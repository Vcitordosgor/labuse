# RECETTE-1 B — Vitesse de la carte (maplibre v4, pas de montée de version)

Mesure GPU réel (Chrome headful, ANGLE Metal, M1, 8 cœurs), front :5895.

## Diagnostic
- Frames FLUIDES déjà (median 16,7 ms ≈ 60 fps ; p99 18,6 ms ; 0 % > 33 ms ; 0 long-task ; 0 repaint au repos).
- Le ressenti « lent » = TEMPS DE POSE après zoom/pan : la carte met plusieurs secondes à se stabiliser.
- CAUSE : maplibre-gl v4.7.1 n'utilise **qu'UN worker** hors Safari (`getWorkerCount()===1`) → tout le
  décodage des tuiles vectorielles (parcelles MVT z9-15, zonage, SUP…) est SÉRIALISÉ sur un thread.

## Correctif (pixel-neutre)
`maplibregl.setWorkerCount(moitié des cœurs, cap 4)` AVANT la création de la 1re carte
(MapView init). Override QA `?wc=N` borné [1,8] pour l'A/B. 0 px changé — seule la file des tuiles se vide plus vite.

## Mesure A/B (temps de pose moyen, 5 vols vers des zones non vues, flyTo 1500 ms)
| workerCount | temps de pose moyen | détail (ms) |
|---|---|---|
| 1 (défaut v4) | 4393 ms | 4399 · 4561 · 5823 · 3785 · 3399 |
| 4 (correctif) | 3716 ms | 3459 · 3925 · 5600 · 2897 · 2700 |

**−15 % de temps de pose**, confirmedWc 1 vs 4 (l'override s'applique bien). Rendu identique.
