# RAPPORT GABARIT-6 — Micro-arêtes et parcelle affichée

Date : 23/09/2026 · Branche `feat/gabarit-6` (worktree `~/Desktop/labuse-gabarit6`, base main `b88b66d5`).
API 8135 · Vite 5336 (le 5335 mandaté était occupé par un autre worktree, `labuse-dash4b`).
Commits : `ae62f62e` (Lot A) · `3f0f5b28` (Lot B) · Lot C + correctifs (a)/(b) (ce rapport + recette).

> **Correctif de prémisse (23/09).** « 97417 » du mandat est le **code postal** de La Montagne
> (quartier de **Saint-Denis**, INSEE **97411**), PAS l'INSEE 97417 (Saint-Philippe). La vraie parcelle
> « 3 Chemin de la Citerne » est **`97411000BZ1065`** (Saint-Denis, PLU calibré). Le premier jet de
> GABARIT-6 avait résolu 97417 comme INSEE (collision : 97417 est aussi l'INSEE de Saint-Philippe) et
> conclu à tort « RNU, hors mandat ». L'application, elle, ne confond pas (l'autocomplétion d'adresse
> résout « 3 chemin de la citerne » → `97411000BZ1065`) ; l'erreur était dans l'enquête. Détail :
> `docs/GABARIT/GABARIT-6-PREMISSE-97417.md`.

---

## Lot A + correctifs (a)/(b) — une micro-arête ne bloque plus

### Le vrai cas : `97411000BZ1065` (3 Chemin de la Citerne, Saint-Denis)

La parcelle bloquait sur `Limites non qualifiées — arête résiduelle < 1 m`. Diagnostic : l'arête
« non classée » mesure en fait **2,26 m**, composée de **4 micro-chunks** de numérisation
(0,33 + 0,64 + 0,63 + 0,66 m), tous < 1 m, dans une ré-entrance de la façade sur voie. Deux défauts :

- **(a) motif faux à la fusion** : `run_motif = run_motif or m` héritait le motif du PREMIER chunk
  (0,33 m → « < 1 m »). L'arête fusionnée fait 2,26 m — c'est ce libellé « < 1 m » qui a inspiré la
  règle initiale « < 1 m ».
- **(b) garde trop étroite** : le Lot A initial ne rattachait qu'une arête dont la **longueur fusionnée**
  < 1 m → il ratait la ré-entrance de 2,26 m.

### Règles implémentées (`src/labuse/gabarit/limites.py`)

- **(a)** `_nonclass_motif(longueur)` fixe le motif sur la **vraie longueur fusionnée** : une arête ≥ 1 m
  est « limite non qualifiée », jamais « résiduelle < 1 m ». Appliqué à la fusion (`_flush`).
- **(b)** le test d'artefact porte sur le **run entier** : une arête nonclass est rattachée à l'arête
  **adjacente la plus longue** du même anneau (héritage type + source) **si et seulement si** `all_short`
  (TOUS ses chunks < 1 m — une ré-entrance finement numérisée, jamais une face droite) **ET** longueur
  < **2 %** du périmètre (`RESIDUAL_MAX_PERIM_FRAC = 0.02`). `Edge.all_short` est calculé à la fusion.
- **Garde 0 faux** : un artefact est nonclass *parce que rien n'est à portée*. Hériter « voie BD TOPO »
  fabriquerait une **fausse façade sur voie** (recul voie sur un renfoncement à > portée de la chaussée —
  observé sur BZ1065 à 5,68 m et BE0429 à 6,09 m, portée ~5,5–6 m). Donc, quand la donneuse est une voie
  BD TOPO et que l'artefact n'est **pas** lui-même à portée d'une route, il est rattaché en **séparative**
  (`side`). Les voies citées (emprise publique / voie privée) et les donneuses séparatives sont héritées
  telles quelles.

Restent bloquantes : arête < 1 m **mais ≥ 2 %** du périmètre (parcelle minuscule) ; face droite non
qualifiée (chunks ≥ 1 m, `all_short=False`) ; ré-entrance all_short **mais ≥ 2 %**.

Traçage (inchangé) : `Edge.attached`, `LimitesResult.residual_attached`,
`raccordement.classification.aretes_residuelles_rattachees` + `note_residuelles`.

**Résultat sur BZ1065** : `status=ok`, surface 1 625 m², zone d'implantation 927 m², plafond 488 m²,
hauteur 7 m. La ré-entrance de 2,26 m est rattachée en **séparative** (`side` : 2 → 3), **0 fausse voie**.

### Mesure 170 (builder complet, base réelle) — `scripts/gabarit_a0_6_mesure.py`

| | Servies | Faux | Flips per-idu |
|---|---|---|---|
| AVANT (main `b88b66d5`) | **143 / 170 (84 %)** | 0 | — |
| APRÈS (a)+(b)+garde | **143 / 170 (84 %)** | **0** | **0** |

- **0 régression** : 0 flip per-idu vs main ET vs le Lot A intermédiaire.
- La cohorte figée (GABARIT-3) **n'exerce pas** (b) (0 rattachement) — BZ1065 n'en fait pas partie ; le
  mécanisme se prouve donc hors cohorte (ci-dessous).
- **Audit 0 faux ciblé** sur les parcelles où (b) s'active réellement (échantillon 3 000, communes
  calibrées 97411/09/15/05) : **4 rattachées, 3 servies, 0 faux**. La garde route élimine le seul mode
  de faux (fausse voie) : re-vérifié sur `BE0429` (faux AVANT garde → 0 APRÈS), `AO0524`, `BZ1065`.

### Tests (`tests/gabarit/test_limites.py`, 78 verts)

- `test_nonclass_motif_selon_longueur_fusionnee` — (a) : 0,6 → « < 1 m » ; 2,26 et 1,0 → « non qualifiée ».
- `test_microarete_helper_run_multichunk_rattache` — (b) : run 2,26 m all_short < 2 % → rattaché (cas BZ1065).
- `test_microarete_helper_garde_zero_faux_voie_hors_portee` — donneuse voie hors portée → séparative ;
  à portée → voie légitime.
- `test_microarete_helper_run_court_mais_2pct_bloque` · `test_microarete_helper_face_droite_non_qualifiee_bloque`
  — ré-entrance ≥ 2 % et face droite (chunks ≥ 1 m) → bloquantes.
- `test_microarete_bout_en_bout_run_multimarches_ne_bloque_plus` — escalier de 5 marches de 0,6 m →
  rattaché, servie ; `..._pese_bloque` — même escalier sur petite parcelle (≥ 2 %) → bloque, motif
  « non qualifiée ».
- `test_microarete_bout_en_bout_mordu_court` — mordu 0,6 m entre séparatives → rattaché.

---

## Lot B — parcelle visible même bloquée (inchangé)

Sur un calcul incomplet, l'API sert le contour cadastral + surface (réf/commune via
`raccordement.parcelle`) ; le front trace le contour, centre la carte, et affiche
« Parcelle <idu> · <commune> » au-dessus du motif. `tsc -b` + `vite build` verts.

---

## Lot C — portes et recette

| Porte | Résultat |
|---|---|
| `pytest tests/gabarit/` | **78 passés** |
| `pytest tests/ -q` (suite complète) | 6 échecs / 3256 passés / 63 ignorés — **0 nouveau** (6 pré-existants hors gabarit) |
| `tsc -b` · `vite build` | verts |
| `registre.verifier()` | 0 violation |
| `ruff check` (fichiers modifiés) | clean |

### Recette navigateur (`scripts/gabarit6_recette.mjs`, headless, flux OUTIL pur)

Captures `docs/GABARIT/captures/gabarit-6/` (Saint-Denis, la BONNE commune) :

- **3 Chemin de la Citerne, `97411000BZ1065` (Saint-Denis)** — `recette-citerne-bz1065-{avant,apres}.png` :
  AVANT bloquée « arête résiduelle < 1 m » (parcelle visible grâce au Lot B), APRÈS **servie** (zone
  d'implantation + retrait + chiffres). C'est le cas cœur du mandat.
- **3 parcelles à contour irrégulier servies** — `recette-servie-irreguliere-{1,2,3}-apres.png` :
  `97411000CV0740` (52 sommets), `97415000CT2639`, `97409000AV0323`.
- **1 parcelle bloquée pour une AUTRE cause, visible** — `recette-bloquee-autre-cause-apres.png` :
  `97411000EV0332` (Saint-Denis) — 1 arête résiduelle rattachée MAIS bloc sur une **autre** limite non
  qualifiée (> 1 m, ravine) ; contour + référence visibles.

WebGL headless rend la carte 2D ; 3D non capturée (comme les recettes GABARIT antérieures).

> Les anciennes captures portant sur Saint-Philippe (`97417000BH0267`) ont été supprimées (mauvaise
> commune). `bug-parcelle-invisible.png` (démonstration Lot B « écran vide ») est conservé.

---

## Fichiers

- `src/labuse/gabarit/limites.py` — `_nonclass_motif` (a) ; `Edge.all_short` + fusion (b) ;
  `_attach_residual_microedges` (test run + garde route 0 faux).
- `src/labuse/gabarit/builder.py` — note résiduelle mise à jour.
- `tests/gabarit/test_limites.py` — 8 tests micro-arêtes (a)/(b)/garde.
- `scripts/gabarit_a0_6_mesure.py` · `scripts/gabarit6_recette.mjs`.
- `docs/GABARIT/GABARIT-6-PREMISSE-97417.md` (enquête postal/INSEE).

## Hors mandat (conforme)

Zones non calibrées · hauteur prospect · exports · merge · `residuel-serve`.
