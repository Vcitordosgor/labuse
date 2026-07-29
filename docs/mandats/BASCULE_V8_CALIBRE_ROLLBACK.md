# Bascule `q_v7_defisc` → `q_v8_calibre` — procédure, contrôles & ROLLBACK

Le calibrage de 21 communes atteint le scoring servi. Jusqu'ici, **la fiche était juste et les
tiers périmés** (le run servi datait du 15/07, la calibration des 27-28/07). Cette bascule aligne
les tiers sur les règles calibrées.

> **Statut au 30/07 : SCRIPT REFONDU, TESTÉ DE BOUT EN BOUT SUR RUN JETABLE (SUCCÈS), NON EXÉCUTÉ
> EN PROD.** L'exécution (écriture production + nouveau run servi) est déclenchée PAR VIC. Scripts :
> `scripts/bascule_v8_calibre.py` / `scripts/rollback_v8_calibre.py`.

## Refonte 30/07 — le script embarque nativement la cascade et prouve sa complétude
La 1ʳᵉ version produisait un run INCOMPLET (scores P sans cascade `dryrun_*`) et se déclarait
terminée → golden en échec (7e principe : un run incomplet est plus dangereux qu'un run qui
échoue). Le script refondu fait la séquence COMPLÈTE, chaque étape idempotente + transactionnelle :
1. **migration** `parcel_residuel` ← `parcel_residuel_rerun` (TRUNCATE+INSERT, une transaction) ;
2. **rebuild** `p_model_static` ;
3. **RE-PASSE cascade île entière** (24 communes) dans `dryrun_*` sous `run_label=q_v8_calibre` —
   `evaluate_parcels` + `compute_matrice`, chunké/**résumable** (`--resume`). JAMAIS une copie de
   q_v7 (prémisse « copie » prouvée FAUSSE : 50/50 parcelles divergeaient — 6e principe) ;
4. **re-score** `run_score_v2` avec `LABUSE_ETAGE0_RUN=q_v8_calibre` (le scoring lit SA cascade),
   champion sha gelé, snapshot inclus ;
5. **AUTO-VÉRIFICATION** (`verify_completude`) : chaque table comptée vs île entière ; au premier
   manque → `RunIncompletError` (échec BRUYANT), le run n'est PAS déclaré servable.

**Test jetable (Saint-Philippe, 30/07)** : les 5 étapes exécutées sur le code de prod ; cascade
re-passée (4 162 parcelles → 151 503 `dryrun_cascade_results`, matrice renseignée) ; barrière de
complétude testée sur SES DEUX chemins (passe sur périmètre réduit, LÈVE sur attente île) ;
rollback → **prod restaurée à l'identique** (résidu 0, q_v7 intact 431 663/120, parcel_residuel
263 169). SUCCÈS.

## Convention
`q_v8_calibre` — 8ᵉ version servie, tag `calibre` = SDP recalculée sur 21 YAML + déclassement
tête-de-liste. **Modèle P INCHANGÉ** (M3.6/m8, `sha256 = 00a58008…9b64`) — seules les features
changent (arène : RR maintenu sur 5 folds, 0 dégradation). Coût prod : re-passe cascade île
entière = plusieurs heures (Saint-Philippe 4 162 parcelles = ~10 min → île ~431 663). `--resume`
reprend sans dupliquer si interrompu.

## Contrôles (arbitrage Vic, un seul qui cloche = arrêt)
| # | Contrôle | État |
|---|---|---|
| 1 | Chemin de retour écrit + testé, `q_v7_defisc` intact | ✓ rollback TESTÉ au run jetable : prod restaurée à l'identique, résidu 0 |
| 3a | O12 : 35 candidats capturés AVANT | ✓ `/tmp/o12_avant.txt` |
| 4 | score_e : écart mesuré | ✓ 31 129/77 718 SDP changées + 2 385 non-constructibles → **recompute = SUITE** (`labuse build-score-e` après bascule), pas préalable |
| 2 | Nouveaux tiers + invariant mis à jour partout | **après bascule** |
| 3b | O12 : 35 candidats vérifiés APRÈS | **après bascule** |
| 5 | Golden 116/116 contre le nouveau servi | **après bascule** |

## Exécution (Vic)
```
PYTHONPATH=src python scripts/bascule_v8_calibre.py    # migration + rebuild + RE-PASSE cascade île + score + auto-vérif
                                                       # (--resume si interrompu). Échoue BRUYAMMENT si incomplet.
# API en dev mode pour le golden (sinon rate-limit 60/min fausse le résultat, cf. docs/TESTS.md) :
LABUSE_DEV_MODE=1 LABUSE_GOLDEN_RUN_LABEL=q_v8_calibre python qa/golden_check.py   # doit rendre 116/116
# surfaces :
export LABUSE_SERVED_RUN=q_v8_calibre
(cd frontend && VITE_RUN_LABEL=q_v8_calibre npm run build)       # bundle
labuse build-mvt --label q_v8_calibre                           # tuiles
```
`q_v7_defisc` n'est JAMAIS touché en base (hystérésis). Sauvegardes features préalables créées :
`parcel_residuel_pre_v8` (263 169), `p_model_static_pre_v8` (431 663).

## ROLLBACK (retour intégral à `q_v7_defisc`)
```
PYTHONPATH=src python scripts/rollback_v8_calibre.py   # supprime q_v8 (scores+cascade+snapshot) + restaure features
export LABUSE_SERVED_RUN=q_v7_defisc
(cd frontend && VITE_RUN_LABEL=q_v7_defisc npm run build)
labuse build-mvt --label q_v7_defisc
```
Le rollback (1) retire le run cible de toutes les tables clés-run (`parcel_p_score_v2`, `dryrun_*`,
snapshot par `snapshot_id`, `p_score_v2_runs`) → `q_v7_defisc` redevient le « dernier run » lu par
la fiche, et (2) restaure `parcel_residuel` + `p_model_static` depuis les sauvegardes. Aucune
re-matérialisation (q_v7_defisc intact). Idempotent. **TESTÉ au run jetable** : prod restaurée à
l'identique, résidu 0. Note : `p_model_ext_dataset` (dérivé) n'est PAS restauré — il n'est jamais
lu au service (seulement au scoring, reconstruit au prochain run) ; sans effet sur le produit servi.

## Invariant des tiers (à mettre à jour PARTOUT après bascule)
**Avant (q_v7_defisc, périmé)** : brûlante 120 · chaude 1 031 · réserve 3 587 · à-creuser 72 980 ·
écartée 353 945. **Après (q_v8_calibre, projeté en mémoire)** : + déclassées A 3 221 · déclassées B
6 178 ; brûlante 120 · chaude ~1 038 · réserve 3 336 · à-creuser ~63 832 · écartée 353 945. Valeurs
exactes à relever sur le run réel, puis graver (docs/TESTS.md, mandat-cadre PLU, mandats repli /
multi-modes / dossier communal, mémoire permanente) AVEC date 29/07 et motif « bascule calibrage
21 communes » — sinon un mandat futur conclura à une régression et s'arrêtera à tort.
