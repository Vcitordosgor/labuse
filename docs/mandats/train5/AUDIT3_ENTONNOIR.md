# AUDIT 3 — ENTONNOIR_MOTIFS (lecture seule, rollback)

Mort depuis DEUX bascules (q_v2/q_v6). `build_entonnoir()` mesuré à blanc sur le run servi
(rollback) : **317 lignes** matérialisées en ~5 s. Décomposition île des écartées (motifs
cumulables) : déjà bâtie 390 418 · PPR rouge/aléa fort 213 596 · zonage A/N 207 444 ·
Q<50 116 016 · surface <100 m² 77 176 · foncier public 72 758 · pente >60 % 29 662 ·
voirie/délaissé 27 602 · forêt/parc 19 394 · ER/prescriptions 10 292 · faux positifs OSM 3 052.
**Reco : rebuild réel = 1 commande de secondes, à raccrocher à `matrice-apply`/au geste de
bascule (il y était censé être : « à reconstruire après chaque matrice »).**
