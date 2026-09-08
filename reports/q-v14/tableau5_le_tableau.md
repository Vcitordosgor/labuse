# LE tableau — SCORING-4 (format SCORING-2)

Ce qui vient du **modèle** (q_v12) vs ce qui vient des **données** (q_v13_sources1), et les deux réunis (q_v14). K0 = banc 2025 (année vierge) ; run = distribution 2026.

| métrique | q_v11_m137 (servi) | q_v12 (modèle seul) | q_v13_sources1 (données seules) | q_v14 (les deux) |
|---|---|---|---|---|
| AUC K0 (2025) | 0.613 | 0.62 | 0.613 | 0.626 |
| préc@100 méd K0 | 0.06 | 0.08 | 0.06 | 0.08 |
| lift décile K0 | 2.06 | 2.27 | 2.06 | 2.27 |
| Priorité préc K0 | 0.137 | 0.076 | 0.137 | 0.305 |
| ECE global K0 | 0.0013 | 0.0022 | 0.0013 | 0.002 |
| ECE PM K0 | 0.0063 | 0.0049 | 0.0063 | 0.0045 |
| — run 2026 — |  |  |  |  |
| brûlante (Priorité) | 111 | 92 | 96 | 92 |
| chaude (À suivre) | 1367 | 1133 | 1173 | 1114 |
| réserve foncière | 8789 | 6471 | 9150 | 5997 |
| à creuser | 136841 | 139412 | 136689 | 136618 |
| cascade disponible (exclusions) | 145882 | 145882 | 150260 | 150260 |
| écartées servies par le run | 145882 | 145882 | 145882 | 150260 |
| modèle K0 =  | ligne_de_base | q_v12 | ligne_de_base | q_v14 |

**Lecture.** Le MODÈLE se lit sur les lignes K0 (AUC, préc@100, lift, Priorité préc, ECE) : q_v12 gagne sur le servi, q_v14 gagne encore. Les DONNÉES se lisent sur la *cascade disponible* : q_v13_sources1 porte les +4 378 exclusions neuves de SOURCES-1 (150 260 vs 145 882), que q_v14 réutilise. q_v14 combine les deux : meilleures métriques K0 ET la cascade élargie (écartées servies = 150 260).

> Nuance de fidélité : le run `q_v13_sources1` a été scoré par SOURCES-1 sur l'étage 0 **servi** (145 882 écartées servies), sans l'override — sa cascade neuve (150 260) ne vivait que dans `dryrun_parcel_evaluations`. q_v14 l'a explicitement réutilisée (`LABUSE_ETAGE0_RUN=q_v13_sources1`) : ses écartées servies sont bien 150 260.
