# GEOMETRIE-1 — Un seul moteur de géométrie : le résiduel adopte l'assiette du Gabarit

Branche `feat/geometrie-1` (base main `ea6feb72`), worktree `~/Desktop/labuse-geometrie`,
4 commits (un par lot) : `1b189da9` (A) · `a7432852` (B) · `053c037c` (C) · `da6afa8d` (D).
**Non mergée. Aucun run servi.** Exécute la décision Vic du 24/09 (constat GABARIT-AUDIT-1) :
deux moteurs calculaient la surface constructible ; il n'en reste qu'un, celui du gabarit.

---

## Lot A — Le gabarit à la vitesse du run (`1b189da9`)

La requête PPR rouge du builder (`gabarit/builder.py`, `ST_Intersection(ST_Union(ppr), parcelle)`)
reçoit la même optimisation que `_greve_certaine_m2` (RESIDUEL-VITESSE) : `ST_ClipByBox2D`
sur la bbox de la parcelle avant l'intersection fine. Résultat mathématiquement identique
(la parcelle ⊆ sa bbox).

**Preuve d'identité** (`geometrie1_prove_1000.txt`, `geometrie1_prove_55.txt`) :
- 1 000 parcelles du benchmark (seed 0.42), 248 touchant du PPR INTERDICTION :
  écart d'aire max **1,7e-08 m²** ; les WKB qui diffèrent ont une différence symétrique
  ~0 (ordre des sommets, bruit flottant) ;
- 55 golden (10 PPR) : écart max **9,9e-09 m²**. VERDICT : identique au m² près.

**Chrono** (`/tmp/bench_gabarit.py` rejoué tel quel, même seed, mêmes comptages
603 servies / 397 bloquées / 76 PPR rouge / 0 erreur) :

| | avant | après |
|---|---|---|
| débit `build_gabarit_input` | 5,2 p/s | **51,9 p/s** (×10) |
| requête PPR (part du temps DB) | 164,7 ms/parc · 89,3 % | 6,0 ms/parc · 45,0 % |
| extrapolation île mono-thread | 22,9 h | **2,31 h** |

**Postes restants > 10 % du temps DB — consignés, PAS optimisés** (mandat) :
PPR géométrie 45 % (6 ms/parc, 0,24 appel/parc), multizone 25 %, reculs par côté 22 %.
Le temps DB ne pèse plus que 69 % du mur (13,3 ms/parc).

## Lot B — Le résiduel lit l'assiette du gabarit (`a7432852`)

Dans `parcel_faisabilite` (le moteur unique servi par la fiche, l'outil M22, le bilan et
`compute_residuel`), quand `assiette_clippee=True` : **l'assiette = zone d'implantation du
gabarit** (`build_gabarit_input` + `compute_gabarit` — les mêmes fonctions que l'endpoint
`/outils/gabarit`, aucune copie). Reculs par côté (voie ≠ séparatives), PPR rouge découpé,
morceau constructible seul si à cheval.

- **Une contrainte, une fois** : le PPR ne passe plus par `_greve_certaine_m2` sur ce chemin ;
  ER/EBC, PEB A/B, marchepied DPF, ravine et 50 pas sont soustraits de la NOUVELLE assiette
  (`_GREVE_SUR_ASSIETTE`, seuils lus de `cascade_rules.yaml`, ClipByBox2D). La cascade, elle,
  reste un verdict d'exclusion (HARD_EXCLUDE) — pas une soustraction d'aire : pas de double compte.
- **Parcelles non servies par le gabarit** (5 causes) : chemin legacy strictement inchangé,
  et la provenance est écrite — colonne **`assiette_source`** (`gabarit` / `residuel_legacy`)
  dans `parcel_residuel_runs` + vue `parcel_residuel` (ALTER + CREATE OR REPLACE idempotents,
  appliqués par `ensure_residuel_cache`).
- **Aval intact** : bâti mesuré sur la portion U/AU (correctif run 5), plafonds CES /
  pleine terre, SDP, logements, VRD — seule la géométrie amont change.
- `assiette_clippee=False` (run servi) : aucun changement, aucun appel gabarit.

**Golden 55** (`geometrie1_golden_table.md`, avant = même code avec gabarit débranché =
branche legacy byte-identique à main) : 46 servies gabarit · 7 legacy **identiques** ·
2 terrain-exigu inchangées. Chaque écart expliqué par **reculs par côté** et/ou **PPR rouge
découpé** (+ morceau multizone) — aucun d'une autre cause.
- **BZ1065 : étape 1 = 927 = gabarit** (840 avant — l'écart de l'audit).
- **BW0102 : 5 867** = la zone d'implantation de l'audit. L'avant legacy vaut aujourd'hui
  6 495 (pas 6 193 comme dans GABARIT-AUDIT-1) : la graduation du PPR (PIEGES-RISQUES-2,
  mergée depuis l'audit) a réduit la grève certaine legacy à 72 m². L'écart −628 m² reste
  entièrement porté par les deux causes du mandat (reculs par côté + PPR découpé, morceau U6c 72,3 %).

## Lot C — Run de test Saint-Denis 97411 (`053c037c`)

Run 9 « geometrie-1 test Saint-Denis (assiette gabarit) », `--assiette-clippee`,
`caffeinate -i`, base au repos, code `a7432852`. **Jamais servi.**

- **38 138 parcelles en 1 848 s = 20,6 p/s** → île (431 663) = **5,8 h mono-thread**
  (< seuil STOP 6 h) ; 2 shards de communes disjointes (`scripts/residuel_shard.sh`,
  ×1,5 mesuré au RESIDUEL-VITESSE) ≈ **4 h**.
- 26 826 calculées, **0 erreur** : 18 806 assiette **gabarit** (70 %) / 8 020 legacy (30 %) ;
  11 312 avec cause (terrain_exigu 9 523, zones A/N…).
- **vs run 8** : 34 788/38 138 SDP identiques (91 %). Sur les 9 197 comparables (SDP > 0
  aux deux runs) : 66,5 % identiques, **19,3 % bougent de plus de 10 %** ; histogramme
  (`geometrie1_run97411_analyse.txt`) : gains 28,8 % / pertes 4,8 % — les reculs par côté
  préservent les angles que l'inset uniforme érodait, et le recul voie (souvent 3-4 m contre
  2 m de séparatif) s'applique enfin géométriquement. 272 flips `sous_densite`.
- **10 plus gros écarts expliqués un à un** (`geometrie1_run97411_top10.txt`) : tous
  assiette gabarit ; les baisses (BL0524, BL0112, BP0647, AH0030) = recul voie 4 m que
  l'inset uniforme à 2 m sous-estimait, ± PPR découpé ; les hausses (AK0196, BZ0157,
  HZ0285, CE0016, CR0343, HX0075) = angles préservés / parcelle étroite que l'inset vidait
  (HZ0285 : 6 → 722 m²), morceau multizone servi (AK0196 Upr 69 %, CE0016 Um 43 %).
  Aucun écart d'une autre cause.

## Lot D — La fiche et l'outil lisent la même chose (`da6afa8d`)

Étape 1 de la capacité et bloc Gabarit du tiroir §10 : **même fonction** (lot B),
**même chiffre**, **même badge**. L'étape 1 dit sa source : « Emprise au sol — zone
d'implantation réglementaire », formule « reculs par côté (voie/limites séparatives),
PPR zone rouge déduit », badge Sourcé ; le bloc Gabarit porte désormais le même badge
Sourcé sous « Zone d'implantation » (même composant `StepProv`).

Captures BZ1065 (`captures/`) : `D-etape1-capacite` (~927 m² · Sourcé · Moteur gabarit),
`D-bloc-gabarit` (Zone d'implantation 927 m² · Sourcé), `D-fiche-potentiel` (vue d'ensemble).

## Vérification

- pytest : périmètre géométrie **124 verts** (residuel, residuel_runs, scoring6_assiette,
  scoring6_garanties, faisabilite, gabarit) + golden servi/scoring6/calibrage 47 verts ;
  **suite complète : 3 055 verts** (1 619 + 1 436, jouée en 2 moitiés — un segfault machine
  transitoire à 82 % en monolithique), **12 échecs PRÉ-EXISTANTS vérifiés à l'identique sur
  main** (liste dans `geometrie1_pytest.txt`) ; 2 corrections d'environnement/stub pendant la
  vérification (`.env` absent du worktree recréé ; stub `test_prospect` → gabarit débranché,
  le test porte sur le hook prospect) — aucune régression de code.
- tsc `--noEmit` vert · `npm run build` vert · **vitest 187/187**.
- Appel complet de la fiche : `GET /parcels/{idu}` **200** sur BZ1065 / BW0102 / AH0022
  (API du worktree, port 8415) ; fiche ouverte au navigateur pour les captures.

## La commande du run île (pour Vic, après merge)

```bash
cd ~/Desktop/labuse && git merge feat/geometrie-1        # (geste de Vic)
# mono-thread (~5,8 h) :
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
PYTHONPATH=src caffeinate -i .venv/bin/python -m labuse.cli compute-residuel \
  --ile --new-run "q_v15 assiette gabarit" --assiette-clippee
# OU 2 shards (~4 h) : créer le run puis
#   psql "$LABUSE_DATABASE_URL" -tAc "SELECT DISTINCT commune FROM parcels ORDER BY commune" > /tmp/communes.txt
#   awk 'NR%2==1' /tmp/communes.txt > /tmp/shardA.txt ; awk 'NR%2==0' /tmp/communes.txt > /tmp/shardB.txt
#   caffeinate -i scripts/residuel_shard.sh <run_seq> /tmp/shardA.txt &
#   caffeinate -i scripts/residuel_shard.sh <run_seq> /tmp/shardB.txt &
# vitesse à vérifier à 5 min : ~20 p/s mono / ~30+ à 2 shards.
# Ensuite : residuel-serve <run_seq> ; run_qv15.py ; bascule q_v15.
```

NB : le run 9 (Saint-Denis, test) reste en base, non servi — purgeable
(`purge_run`) ou réutilisable comme témoin.

## Hors mandat (rappel)

Servir un run · bascule scoring · ER/EBC/SUP déduits de l'assiette gabarit côté OUTIL
(mandat suivant) · exports · merge.
