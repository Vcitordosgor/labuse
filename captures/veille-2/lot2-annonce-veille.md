# VEILLE-2 · Lot 2 — Matrice annonce × veille (3 veilles aux critères différents)

Critères des trois veilles :

- **V1** — SD · maison · ≤ 600 000 €
- **V2** — Possession ou Sainte-Marie · terrain
- **V3** — terrain · ≥ 1000 m² · ≤ 900 000 €

| annonce | commune | type | prix | surface pertinente | rattachement | V1 | V2 | V3 |
|---|---|---|--:|--:|---|---|---|---|
| 3143092379 | Saint-Denis | maison | 655 000 € | 202 m² | non_rattachee | · | · | · |
| 3253364472 | Saint-Denis | maison | 350 000 € | 170 m² | non_rattachee | ✅ | · | · |
| 3184708502 | La Possession | maison | 384 000 € | 102 m² | non_rattachee | · | · | · |
| 3055991753 | Saint-Denis | terrain | 367 500 € | 1108 m² | non_rattachee | · | · | ✅ |
| 3241879744 | La Possession | terrain | 195 000 € | 419 m² | non_rattachee | · | ✅ | · |
| 3200222934 | Sainte-Marie | terrain | 825 000 € | 1600 m² | non_rattachee | · | ✅ | ✅ |

Lecture : chaque annonce ne « part » qu'aux veilles dont elle satisfait TOUS les critères — et à elles seules. Aucune parcelle inventée : rattachement = état réel (`non_rattachee` ici, faute de cadastre en base de test ; la convergence ≥2 critères est prouvée par `tests/test_veille2_lot2.py::test_rattachement_convergence_et_jamais_invente`).
