# PLU-CALIBRAGE-8 (oct.) — Lot D · Dry-run & non-régression

**Aucune écriture en base, aucun run.** Le gabarit (`build_gabarit_input` + `compute_gabarit`) est
rejoué EN LECTURE sur la base `labuse` dans les deux worktrees — `main` (`3f473aa3`) = **avant**,
`feat/plu-calibrage-8` = **après** — sur les **mêmes idus**, même DB. Script :
`scripts/plu8_dryrun.py` (self-sampling : `calibrees` pour D1, `temoins` pour D2). Les deux états ne
diffèrent que par mes commits (B.1 moteur, B.2/B.3 YAML + Lot C).

## D1 — échantillon de chaque zone calibrée (avant / après)

88 parcelles, jusqu'à 4 par zone nouvellement servable (priorité aux parcelles « à potentiel »,
tri déterministe). Résultat du gabarit : **`incomplete` → `ok`**.

| | n |
|---|--:|
| **Débloquées (incomplet → calculé)** | **70** |
| **Régressions (calculé → incomplet)** | **0** |
| Toujours bloquées (cause **géométrie**, hors PLU) | 18 |

Par commune (parcelles `ok` après / échantillon) : Saint-André 21/28 · Saint-Denis 11/12 ·
Saint-Leu 18/20 · Saint-Louis 16/16 · Saint-Paul (U1pru) 2/4 · Saint-Joseph (U5cvd) 1/4 ·
Saint-Pierre (Uep) 1/4.

**Les 18 toujours bloquées le sont par la GÉOMÉTRIE de la parcelle, pas par le PLU** :
- 9 × « Limites de la parcelle non qualifiées (arête sans voie / desservie par voie privée) » ;
- 9 × « parcelle sur ≥ 2 zones constructibles distinctes : découpage multi-CES non servi ».

Ce sont exactement les causes « géométrie » (47 % du LOT5), hors du périmètre de la calibration PLU.
La zone, elle, est désormais calibrée dans les 26 cas.

**Exemples de capacité servie (après)** — zone d'implantation (après reculs/exclusions), hauteur :
- `97409000AC1024` 1AUc → implantation **586 m²**, faîtage **12 m** / égout 9 m (via UC) ;
- `97409000AK1138` 1AUe → implantation **666 m²**, hauteur **16 m** (via UE) ;
- Saint-Denis AUm → faîtage 10 m / égout 7 m, CES 50 % ; Saint-Leu AUA → faîtage 12 m, CES 80 %.

Le **plafond d'emprise** est servi quand le règlement fixe un CES (ex. Saint-Leu 80/60/50/40 %,
Saint-Denis 50/30/60 %) ; il reste « non réglementé » (silence prouvé) pour les zones dont le
règlement ne fixe pas de CES (ex. Saint-André UB/UC/UD, repris par renvoi) — comportement inchangé
de la zone mère.

### Bande / score — hors de ce dry-run (nécessite un run)
Le passage `residuel_legacy → gabarit` et l'éventuel changement de **bande** ne sont chiffrables
que par un **run** (`compute_residuel` recalcule la SDP et réaffecte `assiette_source`, puis le score
réaffecte la bande). Le mandat l'exclut explicitement (« Aucun run dans ce mandat ») : ces 70
parcelles (et leurs ~2 300 sœurs à potentiel dans les 26 zones) **migreront au prochain run**. Le
dry-run prouve seulement que le gabarit, qui renvoyait `incomplete`, renvoie désormais `ok` avec une
enveloppe chiffrée et sourcée.

## D2 — non-régression sur les zones NON touchées

220 parcelles tirées au hasard (déterministe `ORDER BY md5(idu)`) **hors des 26 zones calibrées**,
toutes familles U/AU. Même gabarit rejoué avant / après :

| Parcelles témoins (zones non touchées) | Différences avant / après |
|--:|--:|
| **220** | **0** |

**Byte-identique.** Aucune zone non touchée n'a changé d'état ni de valeur.

En complément (garanties formelles de non-régression, cf. D4) : les **témoins PLU-CALIBRAGE-4**
(`tests/test_plu_calibrage4_zonage.py`) et **CHASSE-CALCULS-1 B1** (`tests/verrous/test_calculs1_recalcul.py`)
restent verts, et les bancs `banc_calcul` / `banc_chasse_calculs` sont rejoués (RAPPORT §D4).

## Reproduire

```
# dans CHAQUE worktree (main = avant, feat/plu-calibrage-8 = après), même base :
LABUSE_DATABASE_URL=postgresql+psycopg://<user>@/labuse DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  PYTHONPATH=<worktree>/src <venv>/python scripts/plu8_dryrun.py calibrees > avant|apres.json  # D1
  …                                                              scripts/plu8_dryrun.py temoins  > …  # D2 (→ 0 diff)
# puis diff des statuts (incomplete→ok pour D1 ; aucun changement pour D2).
```
