# ANO-1 — Diagnostic : run étage 0 en dur (pipeline.py:218)

**Branche** `fix/ano-1-etage0-run` · seed 974 · aucun merge · 2026-07-14

## Lot 0 — Prérequis

| Prérequis | État | Note |
|---|---|---|
| main à jour (M-VIA mergé) | ✅ | `c2b8b1d merge M-VIA` présent sur main |
| run servi = q_v5_m6b | ✅ | `Q_A_RUN_LABEL = "q_v5_m6b"` (score_v_constants.py:35) |
| source unique du run | ✅ ⚠ | **`get_served_run()` n'existe pas** ; la source unique EST la constante `Q_A_RUN_LABEL`, importée par ~12 modules (« bascule centralisée / run de référence »). Le mandat la nomme `get_served_run()` par commodité — le mécanisme existe, sous forme de constante. |
| cohérence 3/3 | ✅ | `tests/test_run_serving_coherence.py` 3/3 (avec `LABUSE_DATABASE_URL` réel) |
| golden 32/32 | ✅ | `qa/golden_check.py` 32/32 PASS |

## Lot 1 — Ce que pipeline.py:218 calcule, et pourquoi q_v2 en dur

```python
# p_v2/pipeline.py (run_score_v2), AVANT :
etage0 = pd.read_sql(text("""
    SELECT p.idu FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
    WHERE d.run_label = 'q_v2' AND d.status IN ('exclue', 'faux_positif_probable')
"""), session.connection())
df["ecartee_etage0"] = df["idu"].isin(set(etage0["idu"]))
```

`ecartee_etage0` alimente ensuite l'**éligibilité aux tiers** (ligne ~239) :

```python
eligibles = work[~work["copro"] & ~work["ecartee_etage0"] & plancher_c(work, base_params)]
n_e = calibre_n_entree(eligibles["rang"], cible=1150)   # seuil chaude/brûlante calibré sur l'éligible
```

Donc l'étage 0 lu ici : (a) marque les parcelles en `tier='ecartee'` dans `parcel_p_score_v2` ;
(b) **retire ces parcelles du vivier** sur lequel `n_entree` (cible ~1 150 chaudes) est calibré →
influence le seuil chaude/brûlante de **toutes** les parcelles.

**Pourquoi q_v2 en dur** : legacy M5. Au M5 le run servi ÉTAIT q_v2 ; la bascule centralisée
(`Q_A_RUN_LABEL`) a été introduite ensuite (q_v3_datagap → q_v4_m6a → q_v5_m6b) mais cette lecture
n'a jamais suivi — dette. Le résultat SERVI reste correct **au niveau statut** parce que la fiche lit
`matrice_statut`/`etage0` du run servi q_v5_m6b ; mais le **tier v2** (qui pilote la bannière) est
calculé, lui, sur l'étage 0 gelé de q_v2.

### Écart réel entre les étages 0

| | parcelles étage 0 |
|---|---|
| q_v2 | 342 285 |
| q_v5_m6b | 353 942 |
| seulement q_v2 (q_v5 ne les exclut PAS) | **58** |
| seulement q_v5_m6b (q_v2 ne les excluait pas) | **11 715** |

Parmi les 11 715 « nouvellement étage 0 en q_v5 », **86 sont actuellement chaude/brûlante** (rang
jusqu'à 48) dans le run de prod : le pipeline buggé les considère éligibles alors que le run servi les
exclut. Au service, elles sont déjà masquées (`head.etage0` q_v5 prime), mais leur présence dans le
vivier **fausse la calibration `n_entree`**.

### Autres lectures de run en dur (grep hors tests) — classification

| Emplacement | Occurrence | Nature | Verdict |
|---|---|---|---|
| **p_v2/pipeline.py:218** | `run_label = 'q_v2'` | **calcul interne SILENCIEUX** (tiers) | 🔴 **LA dette — corrigée** |
| cli.py:368 `matrice-simulate` | `label="q_v2"` défaut | simulation à blanc, aucune écriture | 🟡 défaut CLI overridable, humain |
| cli.py:449 `matrice-apply` | `label="q_v2"` défaut | **mute** matrice+tuiles+tops | 🟠 même classe que build-mvt (déjà corrigé l.470) → à aligner |
| cli.py:1491 `detect-events` | `run_from="q_v2"`, `run_to="q_v2_demo"` | outil de diff 2 runs | 🟡 défaut CLI, sémantique « 2 runs » |
| dryrun.py:236,280 | `run_label="q_v2"` défaut de fonction | appelé par matrice-apply | 🟡 défaut de signature |
| projets.py, pdf_premium.py, partners.py, etage0_ext.py | « q_v2 » en **commentaire/docstring/texte** | non-code | ⚪ cosmétique |

Seul **pipeline.py:218** est un calcul interne silencieux branché sur un run gelé. Les défauts CLI
sont des points d'entrée **humains, overridables** (`--label`) ; `matrice-apply` (mutant) mérite le
même alignement que `build-mvt` — recommandé en suivi (hors périmètre strict « étage 0 »).
