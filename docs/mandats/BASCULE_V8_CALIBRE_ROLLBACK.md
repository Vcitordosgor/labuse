# Bascule `q_v7_defisc` → `q_v8_calibre` — procédure, contrôles & ROLLBACK

Le calibrage de 21 communes atteint le scoring servi. Jusqu'ici, **la fiche était juste et les
tiers périmés** (le run servi datait du 15/07, la calibration des 27-28/07). Cette bascule aligne
les tiers sur les règles calibrées.

> **Statut au 29/07 : PRÉPARÉE ET VÉRIFIÉE, NON EXÉCUTÉE.** L'exécution (écriture production +
> nouveau run servi) est déclenchée PAR VIC. Scripts : `scripts/bascule_v8_calibre.py` /
> `scripts/rollback_v8_calibre.py`.

## Convention
`q_v8_calibre` — 8ᵉ version servie, tag `calibre` = SDP recalculée sur 21 YAML + déclassement
tête-de-liste. **Modèle P INCHANGÉ** (M3.6/m8, `sha256 = 00a58008…9b64`) — seules les features
changent (arène : RR maintenu sur 5 folds, 0 dégradation).

## Contrôles (arbitrage Vic, un seul qui cloche = arrêt)
| # | Contrôle | État |
|---|---|---|
| 1 | Chemin de retour écrit + testé, `q_v7_defisc` intact | scripts écrits ; **test = après 1ère bascule** (rollback → vérif → re-bascule) |
| 3a | O12 : 35 candidats capturés AVANT | ✓ `/tmp/o12_avant.txt` |
| 4 | score_e : écart mesuré | ✓ 31 129/77 718 SDP changées + 2 385 non-constructibles → **recompute = SUITE** (`labuse build-score-e` après bascule), pas préalable |
| 2 | Nouveaux tiers + invariant mis à jour partout | **après bascule** |
| 3b | O12 : 35 candidats vérifiés APRÈS | **après bascule** |
| 5 | Golden 116/116 contre le nouveau servi | **après bascule** |

## Exécution (Vic)
```
python scripts/bascule_v8_calibre.py          # migration parcel_residuel + rebuild static + run q_v8_calibre
LABUSE_GOLDEN_RUN_LABEL=q_v8_calibre python qa/golden_check.py   # doit rendre 116/116
# surfaces :
export LABUSE_SERVED_RUN=q_v8_calibre
(cd frontend && VITE_RUN_LABEL=q_v8_calibre npm run build)       # bundle
labuse build-mvt --label q_v8_calibre                           # tuiles
```
`q_v7_defisc` n'est JAMAIS touché en base (hystérésis). Sauvegardes features préalables créées :
`parcel_residuel_pre_v8` (263 169), `p_model_static_pre_v8` (431 663).

## ROLLBACK (retour intégral à `q_v7_defisc`)
```
python scripts/rollback_v8_calibre.py         # supprime q_v8_calibre + restaure parcel_residuel & p_model_static
export LABUSE_SERVED_RUN=q_v7_defisc
(cd frontend && VITE_RUN_LABEL=q_v7_defisc npm run build)
labuse build-mvt --label q_v7_defisc
```
Le rollback (1) retire le run cible de toutes les tables clés-run → `q_v7_defisc` redevient le
« dernier run » lu par la fiche, et (2) restaure les deux tables de features depuis les sauvegardes.
Aucune re-matérialisation (q_v7_defisc intact). Idempotent. **À TESTER dès la 1ère bascule** :
bascule → `rollback` → vérifier tiers `q_v7_defisc` = 120/1031/3587/72980/353945 + parcel_residuel
263 169 → re-bascule.

## Invariant des tiers (à mettre à jour PARTOUT après bascule)
**Avant (q_v7_defisc, périmé)** : brûlante 120 · chaude 1 031 · réserve 3 587 · à-creuser 72 980 ·
écartée 353 945. **Après (q_v8_calibre, projeté en mémoire)** : + déclassées A 3 221 · déclassées B
6 178 ; brûlante 120 · chaude ~1 038 · réserve 3 336 · à-creuser ~63 832 · écartée 353 945. Valeurs
exactes à relever sur le run réel, puis graver (docs/TESTS.md, mandat-cadre PLU, mandats repli /
multi-modes / dossier communal, mémoire permanente) AVEC date 29/07 et motif « bascule calibrage
21 communes » — sinon un mandat futur conclura à une régression et s'arrêtera à tort.
