# M128 — Échantillon de référence unique **M128-ECH-1**

> Fin des trois bases lues comme une série (374, puis 423, puis 150). **Toute mesure du chantier
> M128 se réfère désormais à cet échantillon.** Reproductible : `qa/m128/echantillon_reference.py`.

## Définition

| Champ | Valeur |
|---|---|
| Identifiant | **M128-ECH-1** |
| Critère de tirage | toutes les parcelles de la base ; sous-ensemble **constructible** mesuré |
| Méthode de tirage | PostgreSQL `setseed(0.128)` puis `ORDER BY random() LIMIT 400` |
| Taille tirée | 400 |
| Seed | **0.128** (fixe) |
| Constructibles mesurés | **241** |

Reproduction : `LABUSE_DATABASE_URL=… .venv311/bin/python qa/m128/echantillon_reference.py`
(le `setseed` fixe rend le tirage déterministe pour une base donnée).

## Deux compteurs de référence — rejoués le 2026-08-21 (état post-M128-6)

| Compteur | Résultat |
|---|---|
| **A — part de parcelles à marge POSITIVE** (méthode documents : `compute_bilan` − prix probable) | **0 / 241 = 0,0 %** |
| **B — part de `vendable > gabarit × 0,8`** | **8 / 241 = 3,3 %** |

**Lecture, dite en clair :**

- **A = 0,0 %.** Sur cet échantillon, **aucune** parcelle n'a de marge documents positive. Le coûtage
  honnête (SDP = vendable ÷ 0,8, construction sur la fourchette réelle) rend la promotion neuve non
  rentable à charge nulle sur la quasi-totalité du vivier tiré. La seule positive connue du chantier
  (DA0319, +2 k€) n'est pas dans le tirage seed 0.128.
- **B = 3,3 %** (contre 62,6 % avant M128-5). L'overshoot systématique de l'aller-retour
  arithmético-harmonique est **éliminé** ; le résidu (≤ 0,6 m² absolu) est l'arrondi de
  `surface_plancher_m2` sur les petites parcelles — pas un défaut de méthode.
