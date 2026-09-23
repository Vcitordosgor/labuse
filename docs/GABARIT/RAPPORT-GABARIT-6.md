# RAPPORT GABARIT-6 — Micro-arêtes et parcelle affichée

Date : 23/09/2026 · Branche `feat/gabarit-6` (worktree `~/Desktop/labuse-gabarit6`, base main `b88b66d5`).
API 8135 · Vite 5336 (le 5335 mandaté était occupé par un autre worktree, `labuse-dash4b`).
Commits : `ae62f62e` (Lot A) · `3f0f5b28` (Lot B) · Lot C (ce rapport + recette).

---

## Lot A — une micro-arête ne bloque plus

### Règle implémentée (`src/labuse/gabarit/limites.py`)

Une arête classée « non classée » (artefact de numérisation) est **rattachée à l'arête adjacente la
plus longue du même anneau** (adjacence cyclique) dont elle **hérite le type ET la source**, et cesse
de bloquer — **si et seulement si** elle fait **< 1 m ET < 2 % du périmètre** de la parcelle
(`RESIDUAL_MAX_PERIM_FRAC = 0.02`). Sinon elle bloque comme avant :

- arête < 1 m **mais ≥ 2 %** du périmètre (parcelle minuscule, l'arête pèse) → **bloquante** ;
- arête **longue** non qualifiable (> 1 m) → **bloquante**.

Le rattachement est **tracé, pas silencieux** : `Edge.attached`, `LimitesResult.residual_attached`,
et côté builder `raccordement.classification.aretes_residuelles_rattachees` +
`note_residuelles` = « N arête(s) résiduelle(s) rattachée(s) ».

Cette règle **remplace** l'absorption grossière pré-existante (`nonclass < 1 m → side`
inconditionnel, silencieux, sans garde de périmètre).

### Mesure 170 (builder complet, base réelle) — `scripts/gabarit_a0_6_mesure.py`

| | Servies | Faux | Flips per-idu | Arêtes rattachées |
|---|---|---|---|---|
| AVANT (main `b88b66d5`) | **143 / 170 (84 %)** | **0** | — | 0 |
| APRÈS (Lot A) | **143 / 170 (84 %)** | **0** | **0** | 0 (sur la cohorte) |

- **0 régression** : comparaison per-idu servie(avant) vs servie(après) = **0 flip** sur les 170.
- **0 faux** : audit des arêtes « road » servies (route BD TOPO à portée / parcelle-voirie /
  voie privée détectée) = 0, avant comme après.
- **Nombre de parcelles débloquées : 0** sur cette cohorte. Le mécanisme y est **inerte** : aucune
  micro-arête < 1 m n'y bloquait déjà (l'absorption pré-existante les gérait). Un **scan complet de
  Saint-Philippe (97417, 4 162 parcelles)** confirme **0 micro-arête < 1 m bloquante** — les blocages
  « limite non qualifiée » y sont de **grandes** arêtes rurales (ravines, centaines de mètres),
  légitimement bloquantes.
- La prémisse « une arête < 1 m bloque aujourd'hui, constaté sur 3 Chemin de la Citerne » **ne se
  reproduit pas** sur la base actuelle (voir *Recette*). Le mécanisme principiel est néanmoins livré,
  plus correct (héritage de la vraie voisine vs `side` forcé), plus honnête (garde 2 % : une arête de
  1 m sur une parcelle minuscule bloque bien) et **tracé**.
- **Preuve que le mécanisme fonctionne sur le réel** : 4 parcelles de Saint-Denis (97411) où le
  rattachement **s'active** — `EV0332`, `HN0401`, `BP0947`, `HE0078` : chacune
  `aretes_residuelles_rattachees = 1` + note ; elles restent bloquées sur une **autre** limite non
  qualifiée (> 1 m), ce qui est correct.

### Tests (`tests/gabarit/test_limites.py`)

- `test_microarete_helper_rattachee_si_courte_et_sous_2pct` — < 1 m et < 2 % → rattachée, hérite du
  type + source de la voisine la plus longue.
- `test_microarete_helper_bloquante_si_sous_1m_mais_2pct_ou_plus` — < 1 m mais ≥ 2 % → bloquante.
- `test_microarete_helper_longue_non_qualifiable_toujours_bloquante` — arête longue → bloquante.
- `test_microarete_bout_en_bout_ne_bloque_plus` — bout-en-bout (`classify_edges`) : un « mordu » de
  0,6 m entre deux séparatives ne bloque pas et est tracé (`attached`).

---

## Lot B — parcelle visible même bloquée

Avant : sur un calcul incomplet ouvert depuis l'**outil** (saisie IDU, sans fiche), l'écran restait
vide — carte sur l'île entière, parcelle **invisible**, ni référence ni commune
(`bug-parcelle-invisible.png`).

Après :

- **API** (`src/labuse/api/gabarit.py`) : le résultat `incomplete` porte désormais le **contour
  cadastral** (`contourGeoJSON`) + la surface ; la référence et la commune viennent de
  `raccordement.parcelle` (déjà présent).
- **Front** (`frontend/src/components/outils/Gabarit.tsx`) : (1) `useMapLayers` trace le **contour** et
  **centre** la carte sur la parcelle même en incomplet — les couches réglementaires (zone/retrait/3D)
  restant réservées au calcul complet ; (2) le panneau affiche **« Parcelle <idu> · <commune> »
  au-dessus du motif** de blocage.

`tsc -b` vert · `vite build` vert.

---

## Lot C — tests et portes

| Porte | Résultat |
|---|---|
| `pytest tests/gabarit/` | **73 passés** |
| `pytest tests/ -q` (suite complète) | **6 échecs / 3256 passés / 63 ignorés** (1260 s) — **0 nouveau**, tous pré-existants et hors gabarit (voir ci-dessous) |
| `tsc -b` | vert |
| `vite build` | vert |
| `registre.verifier()` | **0 violation** |

Les **6 échecs sont pré-existants et sans lien avec GABARIT-6** (aucun n'importe `gabarit/`,
`api/gabarit.py` ni le front Gabarit) :
`test_deps_declared` (dépendance `matplotlib` non déclarée dans pyproject) ·
`test_front_reliquats::test_m135_echelle_action` · `test_plu_destinations::test_module_unique` ·
`test_reparations1_lot2::test_graphe_exact` · `test_scoring6::test_vocabulaire_client_gravé` ·
`verrous/test_lot1_tables` (base réelle absente de labuse_test). Les **73 tests gabarit passent**.

### Recette navigateur (`scripts/gabarit6_recette.mjs`, headless, flux OUTIL pur)

Captures dans `docs/GABARIT/captures/gabarit-6/` :

- **3 Chemin de la (2e) Citerne, 97417** (`BH0267`, Saint-Philippe) — `recette-bloquee-autre-cause-{avant,apres}.png`.
  Saint-Philippe est en **RNU** (sans PLU) : la parcelle bloque sur « zone PLU indéterminée »
  (**hors mandat**, pas une limite). Elle n'est donc **pas servable** ; mais **Lot B** la rend
  visible (contour + « Parcelle BH0267 · Saint-Philippe » au-dessus du motif). Sert aussi de
  « parcelle bloquée pour une autre cause, contour et référence visibles ».
- **3 parcelles à contour irrégulier servies** — `recette-servie-irreguliere-{1,2,3}-apres.png` :
  `97411000CV0740` (52 sommets), `97415000CT2639`, `97409000AV0323` (status `ok`, zone + retrait tracés).
- **Micro-arête rattachée** — `recette-microarete-rattachee-{avant,apres}.png` : `97411000EV0332`
  (Saint-Denis), `aretes_residuelles_rattachees = 1` + note ; bloc sur une autre limite (ravine).
- **`bug-parcelle-invisible.png`** (= avant du bloc RNU) : carte sur l'île entière, parcelle invisible.

Limite de la recette : **WebGL headless** rend correctement la carte 2D ; la 3D n'est pas capturée
(cohérent avec les recettes GABARIT antérieures).

---

## Fichiers

- `src/labuse/gabarit/limites.py` — `RESIDUAL_MAX_PERIM_FRAC`, `Edge.ring/attached`,
  `_attach_residual_microedges`, `LimitesResult.residual_attached`, `summarize_edges`.
- `src/labuse/gabarit/builder.py` — trace `aretes_residuelles_rattachees` + `note_residuelles`.
- `src/labuse/api/gabarit.py` — contour + surface sur le résultat `incomplete`.
- `frontend/src/components/outils/Gabarit.tsx` — contour + centrage en incomplet, réf + commune.
- `tests/gabarit/test_limites.py` — 4 tests micro-arêtes.
- `scripts/gabarit_a0_6_mesure.py` — mesure 170 avant/après (0 faux, per-idu).
- `scripts/gabarit6_recette.mjs` — recette navigateur.
- `docs/GABARIT/captures/gabarit-6/` — CSV mesure + 8 captures.

## Commandes clés

```
# mesure 170 (avant : sur main ; après : sur Lot A)
PYTHONPATH=src DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python \
  scripts/gabarit_a0_6_mesure.py <sortie.csv>

# tests
PYTHONPATH=src LABUSE_TEST_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse_test \
  .venv/bin/python -m pytest tests/gabarit/ -q

# recette (API 8135 + vite 5336 lancés)
node scripts/gabarit6_recette.mjs apres
```

## Hors mandat (non traité, conforme)

Zones non calibrées · hauteur prospect · exports · merge · `residuel-serve`.
