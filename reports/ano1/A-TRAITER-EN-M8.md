# ANO-1 — À TRAITER EN M8 (report de la correction au prochain re-run cascade)

Décision Vic (2026-07-14) : le fix ANO-1 est **mergé** (code correct, base servie inchangée,
golden 32/32 + cohérence 3/3 verts = les bons critères). On **NE re-score PAS maintenant** — la
correction atterrit au **prochain re-run cascade, qui sera M8** (ingestions), avec `monitor-forward`
pour tracer le delta.

## 1. Correction des 58 parcelles (effet du fix ANO-1)

Le fix fait que `parcel_p_score_v2` lira l'étage 0 du run SERVI (`Q_A_RUN_LABEL`) au lieu de `q_v2`
gelé. Au prochain `labuse score-v2` :

- **≥58 parcelles** aujourd'hui servies « écartée » à tort (q_v2 les exclut, q_v5_m6b NON) retrouveront
  leur vrai tier (`a_creuser`/`reserve_fonciere`). Exemple : `97406000AL0563` (`etage0=False` mais
  `tier='ecartee'` aujourd'hui).
- Léger effet de **recalibration `n_entree`** (86 parcelles fantômes chaude/brûlante quittent le vivier
  éligible → le seuil chaude/brûlante se recale).
- Churn de base attendu ~100 verdicts/run (hystérésis + intercept), indépendant du fix.

**À faire en M8**, dans l'ordre, après les ingestions :
1. `labuse score-v2` (re-run cascade complet)
2. `labuse build-mvt` (re-matérialiser les tuiles sur le run servi)
3. `labuse monitor-forward` → **tracer et documenter le delta** (les 58 + churn) dans `reports/monitoring/`.

## 2. `matrice-apply` — même défaut `q_v2` en dur (mutant) — À ALIGNER EN M8

`cli.py:449` `matrice-apply` a un défaut `label="q_v2"` **mutant** (applique la convention matrice ×24
+ tuiles + tops). Même classe de dette que `build-mvt` (déjà corrigé l.470 : défaut `None → Q_A_RUN_LABEL`).
Non corrigé dans ANO-1 (hors périmètre strict « étage 0 », changement de comportement CLI).

**À faire en M8** (dans le même re-run) : aligner le défaut sur la source unique, pattern `build-mvt` :

```python
# cli.py — matrice-apply (et matrice-simulate cli.py:368, mêmes)
label: str = typer.Option(None, help="run_label (défaut : run de référence Q_A_RUN_LABEL).")
...
label = label or RUN   # RUN = Q_A_RUN_LABEL
```

Idem défauts de fonction `dryrun.py:236` (`apply_convention`) et `dryrun.py:280` (`build_entonnoir`).
`detect-events` (cli.py:1491, diff 2 runs) : sémantique « deux runs » légitime — à documenter, pas
forcément à changer. Les mentions `q_v2` en commentaire/docstring (projets.py, pdf_premium.py,
partners.py, etage0_ext.py) sont cosmétiques — nettoyage optionnel.

**Critère de sortie M8** : plus aucun run en dur hors config/tests (défauts CLI mutants inclus), et
delta des 58 verdicts tracé par `monitor-forward`.
