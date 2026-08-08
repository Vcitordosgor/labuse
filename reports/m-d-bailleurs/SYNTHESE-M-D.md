# M-D — Typage des bailleurs (CDC, SICA) — synthèse

Branche `feat/m-d-bailleurs` (worktree `~/Desktop/labuse-md`). CC ne merge pas : Vic valide et merge.

## Le constat du mandat était INVERSÉ (mesure préalable)

Le mandat annonçait CDC HABITAT et SICA « classés en SIREN, à typer en bailleurs / agricole ».
La mesure sur `parcel_v_score` (run servi courant) dit l'inverse :

| dénomination | occ. | type AVANT | réalité |
|---|---|---|---|
| CDC HABITAT | 24 | **bailleur** (déjà correct) | vrai bailleur social national |
| SICA HABITAT REUNION | 22 | **bailleur** (FAUX POSITIF) | SICA agricole — pas un bailleur |

Cause unique : `BAILLEUR_DENOM_PATTERN = r"\b(HABITAT|HLM)\b"`. Le token nu **HABITAT** classait
bailleur *toute* raison sociale contenant le mot. CDC HABITAT tombait juste par accident ; SICA
HABITAT REUNION tombait à tort.

## Les voisines existaient bien (comme le mandat le pressentait)

Un correctif sur les 2 seuls noms cités aurait laissé passer 11 autres faux positifs, tous captés
par le même token nu — promoteurs, constructeurs, conseils immobiliers, et 2 syndicats publics.

## Fix (périmètre strict : classification propriétaire + test)

`src/labuse/scoring/score_v_constants.py` :
- `BAILLEUR_DENOM_PATTERN` resserré → `r"\bHLM\b|HABITATIONS? A LOYER MODERE"` (marqueurs NON
  ambigus du logement social uniquement).
- `470801168` (CDC Habitat) ajouté à `BAILLEURS_SOCIAUX_SIREN` : seul bailleur légitime que le
  token nu retenait, désormais épinglé par son SIREN (robuste au resserrement).

`classify_owner` (score_v.py) : **aucun changement de logique** (consomme les constantes).

`tests/test_score_v.py` : `test_classify_owner` ne s'appuie plus sur `HABITAT` nu (remplacé par
`OFFICE HLM` / `HABITATIONS A LOYER MODERE`) ; nouveau `test_classify_owner_bailleur_resserre_m_d`
couvrant les 2 cas nommés **et** 4 voisines.

## Validation chiffrée (diff avant/après persisté, `score-v-compute` rejoué — 431 663 parcelles)

Distribution owner_type (rejeu du build V) :

| type | avant | après | Δ |
|---|---|---|---|
| pp | 349 597 | 349 597 | 0 |
| public | 36 463 | 36 463 | **0** |
| copro | 411 | 411 | **0** |
| bailleur | 11 479 | 11 413 | **−66** |
| pm | 33 713 | 33 779 | **+66** |

- **Une seule transition** : `bailleur → pm`, 66 rows, 13 dénominations. Aucune autre catégorie ne
  bouge (public/copro/pp intacts).
- CDC HABITAT (24) **reste bailleur** (SIREN épinglé). SICA HABITAT REUNION (22) → pm.
- 11 voisines redescendues : SUD HABITAT CONSEIL (20), ELMOJO HABITAT (7), CONSTRUCTION HABITAT
  OCEAN INDIEN (4), ARCHIPEL BOIS HABITAT (3), RAFION/ALLYANCE HABITAT (2 ch.), ENTRE DEUX/YP/GKER/
  ARTHUR HABITAT (1 ch.), + 2 SYND INTERCOMMUNAL D'HABITAT ST ANDRE.
- Écart au mandat : il attendait « 46 changent, rien d'autre ». Réalité mesurée : 22 changent
  (SICA), 24 restent (CDC déjà correct), + 44 voisines corrigées = 66. C'est exactement ce que la
  « mesure préalable » du mandat demandait de débusquer.

Reproduction : `PYTHONPATH=src python reports/m-d-bailleurs/diff_measure.py`.

## Résidu connu (hors périmètre)

Les 2 « SYND INTERCOMMUNAL D'HABITAT … ST ANDRE » (sans SIREN, groupe DGFiP 0) sont des organismes
publics de logement, désormais en `pm` faute de règle propre. Doctrine « le doute ne classe
jamais » : `pm` est le seau honnête. Une règle « public » dédiée dépasserait le périmètre strict.

Tests : `test_score_v.py` + `test_proprietaire_type.py` = 27 passés.
