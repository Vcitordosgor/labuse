# ANO-1 — Correction & preuve de non-régression

## Lot 2 — Correction

`p_v2/pipeline.py` — la lecture de l'étage 0 lit désormais le run SERVI (source unique
`Q_A_RUN_LABEL`), en paramètre lié, plus aucun run gelé en dur :

```python
from ..score_v_constants import Q_A_RUN_LABEL  # source unique du run SERVI (bascule centralisée)
...
etage0 = pd.read_sql(text("""
    SELECT p.idu FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
    WHERE d.run_label = :run AND d.status IN ('exclue', 'faux_positif_probable')
"""), session.connection(), params={"run": Q_A_RUN_LABEL})
```

Aucun fige légitime : l'étage 0 doit suivre le run servi (c'est justement l'incohérence). Diff = 6 l.

## Lot 3 — Preuve de non-régression

### Sur la base SERVIE (production `m36-l2f-2026-2026-07-14`, INCHANGÉE) — les critères du mandat

Le correctif est **code-only** : il ne touche pas la base. La base servie reste identique, donc :

| Preuve | Résultat |
|---|---|
| **golden 32/32** (`qa/golden_check.py`) | ✅ **32/32 PASS**, 0 FAIL |
| **cohérence 3/3** (`test_run_serving_coherence.py`) | ✅ **3 passed** (front SOURCE, bundle dist, tuiles mvt = q_v5_m6b) |
| suite scoring/serving | ✅ 23 passed, 0 failed (skips = base de test `labuse_test` absente, pré-existant) |

### ⚠ MAIS le correctif n'est PAS neutre au PROCHAIN run — la prémisse « diff = zéro » est fausse

Le mandat postule « Diff avant/après des verdicts = zéro ». **Vérifié empiriquement : c'est faux.**
Protocole : re-run `score-v2` avec le fix (`ano1-verify`, q_v5) et sans le fix (`ano1-control`, q_v2),
mêmes features (`rebuild=False`), verdict servi = `écartée` si étage 0 q_v5 sinon tier v2. *(Runs
d'expérimentation supprimés des tables de prod après mesure ; serving rétabli sur m36-l2f-07-14.)*

| Comparaison | Δ verdicts servis | Lecture |
|---|---|---|
| **effet isolé du fix** (control q_v2 → verify q_v5, mêmes features) | **81** | 58 `ecartee→a_creuser/reserve` (déterministe, cœur) + 23 `chaude↔brûlante` (recalibration) |
| prod → re-run **identique** (q_v2, contrôle de déterminisme) | **111** | ⚠ **le re-run n'est PAS déterministe** : l'hystérésis référence le dernier run + recalage d'intercept → churn de base ~100 verdicts, fix ou pas |
| prod → verify (fix) | 147 | = churn de base ∪ effet du fix, entremêlés |

**Cœur déterministe, robuste = 58 parcelles** que q_v2 exclut à tort et que q_v5_m6b n'exclut PAS.
Exemple vérifié en live (`97406000AL0563`) : servie aujourd'hui `tier='ecartee'` alors que
`etage0=False` — écartée UNIQUEMENT à cause du q_v2 gelé. Le fix rétablit son vrai tier (`a_creuser`).
**C'est une CORRECTION**, pas une régression — mais c'est bien un changement de verdict.

**3 des 32 parcelles golden** (97411000AO0748, 97413000CD0729, 97416000CR1351) sont dans l'écart
d'étage 0 (nouvellement exclues par q_v5) — déjà servies « écartée » via la couche de service, donc
leur verdict servi ne bouge pas ; et la base n'étant pas re-scorée, golden reste 32/32.

### Conclusion honnête

- Le correctif est **juste** (l'étage 0 doit suivre le run servi) et passe les critères concrets du
  mandat **sur la base servie inchangée** (golden 32/32, cohérence 3/3, suite verte).
- Il n'est **pas** « pure plomberie invisible » : au prochain run de prod, il **corrigera ≥58 verdicts**
  (parcelles à tort écartées) + un léger effet de recalibration. De plus, `score-v2` re-churne ~100
  verdicts par run **indépendamment** (hystérésis + intercept) — donc « diff = zéro sur re-run »
  n'était de toute façon pas atteignable ni un test pertinent.
- **Recommandation** : garder le fix (il élimine la dette réelle), le faire atterrir comme une
  **correction assumée** au prochain run planifié — `labuse score-v2` puis `labuse build-mvt` puis
  `labuse monitor-forward` pour tracer le delta — et **NE PAS** re-scorer la prod dans cette PR (ce
  serait changer les verdicts servis maintenant). Le run gelé en dur `matrice-apply` (mutant) mérite le
  même alignement en suivi.
