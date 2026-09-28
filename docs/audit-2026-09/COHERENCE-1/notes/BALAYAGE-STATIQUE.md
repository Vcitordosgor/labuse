# COHERENCE-1 lot D — balayage statique du code (conversions, replis, dénominateurs)

Scan statique (agent, 28/09/2026) de chaque `* 100`, `/ 100`, ha↔m², `round`, `or 0`,
`?? 0`, `coalesce(...,0)` sur le chemin d'une notion affichée. Liste complète par
catégorie ; TOP RISQUES repris ici (le rapport final trie ce qui est confirmé en base).

## TOP RISQUES (lecture statique — à confirmer par les lots B/D/G)

1. `src/labuse/cascade/layers/fiche_couches2.py:28` — `round((coverage or 0.0)*100)` :
   arrondi entier + seuil « < 1 % » → 0 % affiché ≠ « < 1 % » selon l'ordre de grandeur ;
   et `or 0.0` = zéro pour absence sur le % de recouvrement des couches fiche.
2. `src/labuse/registre/moteurs/zonage.py:44-46` — la même structure sert `pct` par
   SURFACE et `n` par PARCELLES : deux dénominateurs pour « part de la commune en zone X »
   selon le lecteur (fiche commune vs filtres).
3. `src/labuse/api/moteurs.py:600` — `float(r["h1121"] or 0)/c1121` : part habitat ZAN
   0 % affiché quand la source est NULL.
4. `src/labuse/flash/data.py:249` — `round(rend*100)` sans décimale : le PDF Flash peut
   dire 79/80 % quand la fiche dit 79,5.
5. `src/labuse/cascade/layers/phase1.py:621` — `part_canne*100 >= seuil` : NULL échoue
   silencieusement (parcelle sans donnée canne jamais exclue).
6. `src/labuse/api/app.py:4469` — `round(float(r["part"] or 0.0)*100,1)` : zéro pour
   absence (comparateur).
7. `src/labuse/exports/financier_bilan.py:109` — `(part_sociale_pct or 0)/100` : absence
   → 0 % silencieux dans le bilan (unité % attendue, garde min/max masque l'erreur d'unité).
8. `src/labuse/api/moteurs.py:679-680` — îlots (count) et ha (surface) côte à côte sans
   dénominateur commun (ZAN).
9. `src/labuse/faisabilite/engine.py:195/212` — aller-retour fraction↔% des hypothèses :
   juste si la saisie respecte l'unité, aucune garde.
10. `src/labuse/zone.py:595` / `zone.py:546` — `v or 0` et `coalesce(sum,0)` : parts et
    surfaces de l'Étude de zone rendent 0 sur source vide.

## Comptes du scan

- Conversions fraction↔% : 26 occurrences (4 à risque).
- Conversions ha↔m² : 14 occurrences (0 risque direct).
- `or 0`/`coalesce 0` sur le chemin d'affichage : 10 cas (3 critiques).
- Dénominateurs mélangés (parcelles vs surface) : 5 cas (2 critiques).

Détail complet par fichier:ligne dans le transcript de l'agent (session 28/09) ; les cas
confirmés passent dans ECARTS.csv / RAPPORT.md avec leur gravité.
