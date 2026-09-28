# fix/sup-source — correctif SUP + optimisation de la requête SUP

**Branche `fix/sup-source` (pas de merge, pas de run).** Suite de RUN11-VS-RUN10 §8. Deux commits :
1. **Correctif** — `sources.append(sup_src)` (la source SUP au catalogue) → fin du repli legacy sous SUP ;
2. **Vitesse** — `sl.commune = p.commune` sur la requête SUP → ×2,9, résultat identique au m².

Base `postgresql+psycopg://openclaw@localhost:5432/labuse`, **lecture seule** (rejeu du moteur en session read-only + `SELECT`), aucune écriture.

---

## 1. Correctif (rappel) et preuve de couverture

`build_gabarit_input` attachait `sup_src` à l'exclusion sans l'ajouter au catalogue → `validate_input` rejetait `exclusion[sup] : source absente du catalogue` → `compute_gabarit=incomplete` → `_assiette_gabarit=None` → `residuel_legacy`. Correctif = 1 ligne, **en miroir du PPR** (`builder.py:342`).

**Test D.15 réparé** (`tests/gabarit/test_builder.py::test_sup_intersectante_deduite_du_gabarit`) : il exerce désormais la **validation** (source au catalogue + absence de l'erreur `exclusion[sup] … catalogue`). L'ancien ne vérifiait que la présence de l'exclusion — d'où le bug passé inaperçu (la `FakeSession` renvoyait « SUP absente », donc aucune exclusion SUP n'était créée).

| État | `test_sup_intersectante_deduite_du_gabarit` |
|---|---|
| **sans** le correctif (`sources.append(sup_src)` retiré) | 🔴 **FAILED** — `AssertionError: source SUP absente du catalogue (sources.append(sup_src) manquant)` |
| **avec** le correctif | 🟢 **PASSED** (suite gabarit complète : **82/82**) |

**Preuve de couverture** — rejeu du moteur corrigé (read-only) sur **501 parcelles** `gabarit@run10 / legacy@run11` des 3 communes vidées (167 chacune) :

| Commune | run 10 | run 11 (bug) | **corrigé** |
|---|---:|---:|---:|
| La Plaine-des-Palmistes | 167 gabarit | 0 | **166 gabarit / 1 legacy** |
| Les Trois-Bassins | 167 gabarit | 0 | **166 gabarit / 1 legacy** |
| Saint-André | 167 gabarit | 0 | **165 gabarit / 2 legacy** |
| **Total** | **501 / 501** | **0 / 501** | **497 / 501 (99,2 %)** |

La couverture gabarit **revient au niveau du run 10**. Les 4 restants = cas **distinct** `exclusion[sup] : géométrie d'exclusion invalide` (sliver d'intersection SUP∩parcelle non valide après `ST_MakeValid` du morceau clippé) — pré-existant, **hors périmètre** de ce correctif (< 1 %).

---

## 2. Optimisation de la requête SUP (×7,5 → …)

### Diagnostic

La requête SUP par parcelle **portait déjà** l'optimisation `ST_ClipByBox2D` (identique au PPR et à `_greve_certaine_m2`). Le ×7,5 du run 11 (32 689 s vs 4 370 s) ne vient donc **pas** d'un `ClipByBox2D` manquant, mais de deux faits :

1. **Elle s'exécute pour CHAQUE parcelle** (le PPR, lui, n'est requêté que pour les rares parcelles `HARD_EXCLUDE`) ;
2. **Absence de scope commune.** La SUP dominante est le sous-type **`el10`** (~1 055 km², **24 copies — une par commune**), à bbox insulaire. Toutes les copies passaient le pré-filtre GiST et subissaient le `ST_Intersects` fin. Mesuré sur une parcelle de La Plaine : **48 lignes SUP** exact-testées, contre **5** avec le scope commune.

`_greve_certaine_m2` — cité comme modèle — ne doit pas sa vitesse au seul `ClipByBox2D` mais **aussi** à `z.commune = p.commune`. On applique donc **ce même scope commune** à la requête SUP. Les 417 SUP portent **toutes** une commune (0 NULL, 24 communes) : le filtre n'en écarte aucune à tort.

### Le changement (1 ligne)

```sql
FROM spatial_layers sl, parcels p
WHERE p.id = :pid AND sl.kind = 'sup'
  AND sl.commune = p.commune          -- ← ajout (miroir _greve_certaine_m2)
  AND ST_Intersects(sl.geom_2975, p.geom_2975)
```

### Preuve d'identité au m² (les deux jeux)

Comparaison de l'aire de `SUP ∩ parcelle` (EPSG:2975), V0 (actuel) vs V1 (+commune) :

| Jeu | Parcelles | dont SUP réelle | Écart max \|V0−V1\| | Parcelles avec écart > 0,01 m² |
|---|---:|---:|---:|---:|
| **55 golden** (GEOMETRIE-1) | 55 | 22 | — | 0 |
| **500 parcelles sous SUP** | 500 | 500 | — | 0 |
| **ensemble** | **555** | 522 | **1,18 × 10⁻¹⁰ m²** | **0** |

Écart max = bruit flottant (même ordre que la preuve `ClipByBox2D` de GEOMETRIE-1 : 9,9 × 10⁻⁹ m²). **Identique au m².**

### Chronos (500 parcelles sous SUP, base chaude, 2 passes)

| Requête | temps (500 p.) | débit | île (borne haute*) |
|---|---:|---:|---:|
| **V0** actuelle | 26,6 s | **18,8 p/s** | **6,38 h** |
| **V1** + commune | 9,2 s | **54,4 p/s** | **2,20 h** |
| | | **×2,9** | **−4,2 h** |

*Borne haute = toutes les parcelles au coût SUP. Elle est réaliste ici : la bbox insulaire d'`el10` fait que **chaque** parcelle teste au moins la copie `el10` de sa commune, qu'elle intersecte ou non. Le ×7,5 observé du run 11 (≈ +7,9 h vs run 10) est cohérent avec la requête SUP V0 ≈ 6,4 h ; V1 en retire ≈ 4,2 h.

### Poste qui dépasse 10 % APRÈS l'optimisation (signalé, non optimisé — mandat)

Profil de `build_gabarit_input` sur parcelles sous SUP, requête SUP en V1 (69 ms/parcelle) :

| Poste | part |
|---|---:|
| requête SUP (V1) | ~23 % de (build+compute) |
| **`classify_parcel_limits`** (qualification voie/séparative par côté) | **21 %** |
| **`zone_dominante`** | **10 %** |
| reste (cascade PPR + résolution PLU + BD TOPO voirie + emprises publiques/privées) | ~46 % |

⚠️ **Signalement (sans action)** : une fois la requête SUP scoppée, elle n'est plus l'aberration ×7,5 (≈ 23 %). Les postes suivants dépassent 10 % : **`classify_parcel_limits` (~21 %)** et **`zone_dominante` (~10 %)**. Un gain structurel supplémentaire sur le SUP lui-même (hors périmètre) serait de **subdiviser** la géométrie `el10` (`ST_Subdivide`) à l'ingestion, pour que le `ST_ClipByBox2D`/`ST_Intersects` par parcelle n'opère plus sur un polygone insulaire. **Non appliqué** conformément au mandat.

---

## 3. Commande exacte du run 12 (pour Vic — À LANCER PAR TOI, pas de run ici)

Le venv est l'install éditable du checkout **principal** (`~/Desktop/labuse`) ; pour exécuter le **code corrigé** de ce worktree, `PYTHONPATH=src` prime sur l'éditable.

```bash
cd ~/Desktop/labuse-run11
git checkout fix/sup-source            # code corrigé (SUP au catalogue + scope commune)
PYTHONPATH=src ~/Desktop/labuse/.venv/bin/labuse compute-residuel \
    --ile --assiette-clippee \
    --new-run "q_v15 lidar + SUP (fix sup-source)"
```

- `--new-run` crée un **run_seq 12 neuf, NON servi** (le `code_commit` = HEAD de `fix/sup-source` est gravé automatiquement).
- Durée attendue : **~2–4 h** (contre 9,1 h pour le run 11), la requête SUP passant de ~6,4 h à ~2,2 h.
- **Ne sert rien.** Après audit du run 12 (ré-appliquer RUN11-VS-RUN10 : couverture gabarit ≈ run 10, deltas de cause, dry-run bandes), bascule manuelle par toi :

```bash
PYTHONPATH=src ~/Desktop/labuse/.venv/bin/labuse residuel-serve 12   # (après vérification seulement)
```

---

*Sources : `spatial_layers` (kind='sup'), `parcels`, `parcel_residuel_runs` (run_seq 10 & 11), golden `docs/audit-2026-09/geometrie-1/geometrie1_golden_table.md` (55 parcelles). Rejeu moteur read-only (`build_gabarit_input`+`compute_gabarit`) et chronos sur base chaude. Aucune écriture en base.*
