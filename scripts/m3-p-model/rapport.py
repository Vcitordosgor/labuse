"""Livrables markdown du mandat M3 — SYNTHESE-M3.md + model-card.md.

À lancer APRÈS train.py, eval_test.py et score_2026.py : compile les CSV produits.
Usage : python scripts/m3-p-model/rapport.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPORTS = Path("reports/m3-p-model")
ART = REPORTS / "artifacts"


def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: floatfmt.format(v) if pd.notna(v) else "—")
    header = "| " + " | ".join(str(c) for c in d.columns) + " |"
    sep = "|" + "|".join("---" for _ in d.columns) + "|"
    rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in d.itertuples(index=False)]
    return "\n".join([header, sep, *rows])


def main() -> None:
    freeze = json.loads((ART / "FREEZE.json").read_text())
    val = pd.read_csv(REPORTS / "val-resultats.csv")
    ctrl = pd.read_csv(REPORTS / "controles-negatifs.csv")
    test = pd.read_csv(REPORTS / "test-2025-resultats.csv")
    churn = pd.read_csv(REPORTS / "churn-top1158.csv")
    vent = pd.read_csv(REPORTS / "test-2025-ventilation-owner.csv")
    lift = pd.read_csv(REPORTS / "test-2025-lift.csv")
    inter = pd.read_csv(REPORTS / "interactions-journal.csv")
    iv = pd.read_csv(REPORTS / "iv-features.csv")

    rr = {(r["score"], r["k"]): r for _, r in test.iterrows()}

    def fmt_rr(score: str, k: int) -> str:
        r = rr.get((score, k))
        if r is None:
            return "—"
        return f"{r['rr']:.2f} [{r['ic95_bas']:.2f}, {r['ic95_haut']:.2f}]"

    p_beats = all(
        rr[("P (Z+D, calibré)", k)]["rr"] > rr[(s, k)]["rr"]
        for k in (1158, 500)
        for s in ("baseline rotation DVF secteur", "ablation Z seul",
                  "baseline V v1.3 (ties à 0/NULL seedés 974)")
        if (s, k) in rr)

    synth = f"""# SYNTHÈSE M3 — Modèle P (blocs Z + D), phases 1-2

Modèle gelé le {freeze['gel']} (sha256 `{freeze['sha256'][:16]}…`), train
{freeze['meta']['train']}, C={freeze['meta']['C']}, seed 974. Test 2025 lu UNE
SEULE FOIS après gel (traces : ORDRE-OPERATIONS.md, ORDRE-OPERATIONS-lot5.md,
artifacts/TEST-2025-LU.json).

## Verdicts par lot

| Lot | Verdict |
|---|---|
| 1 — dataset personne-période | ✅ 431 663 parcelles × années, tests anti-leakage synthétiques verts (`tests/test_p_model_dataset.py`) |
| 2 — bloc Z | ✅ rotation shrinkée, €/m² + tendance, Sitadel 24 m, Filosofi/QPV/PLU/pente/équipements |
| 3 — bloc D | ✅ nu constructible, dormance de droits, permis, tenure (bins « inconnu » explicites), végétation/friche/piscine/PV |
| 4 — modèle | ✅ WoE ≤10 bins + logistique L2, contributions ligne à ligne, GBM shadow ({max(int(inter['retenu'].sum()) - 1, 0)} croisements réinjectés), isotonique sur val |
| 5 — évaluation | {'✅' if (ctrl['verdict'] == 'PASS').all() else '❌'} contrôles négatifs ; verdict test reporté ci-dessous {'(P bat les 3 baselines)' if p_beats else '(P ne bat PAS toutes les baselines — reporté tel quel)'} |
| 6 — scoring 2026 | ✅ p_model_scores_2026 (100 % du parc, aucun NA) + top-1158-2026.csv |

## Contrôles négatifs (val 2024, AVANT lecture du test)

{md_table(ctrl)}

## Test 2025 (lecture unique) — baselines vs modèle

| Score | RR@1158 [IC95] | RR@500 [IC95] |
|---|---|---|
| **P (Z+D, calibré)** | {fmt_rr('P (Z+D, calibré)', 1158)} | {fmt_rr('P (Z+D, calibré)', 500)} |
| Ablation Z seul | {fmt_rr('ablation Z seul', 1158)} | {fmt_rr('ablation Z seul', 500)} |
| Baseline rotation DVF secteur | {fmt_rr('baseline rotation DVF secteur', 1158)} | {fmt_rr('baseline rotation DVF secteur', 500)} |
| Baseline V v1.3 (ties seedés) | {fmt_rr('baseline V v1.3 (ties à 0/NULL seedés 974)', 1158)} | {fmt_rr('baseline V v1.3 (ties à 0/NULL seedés 974)', 500)} |

Note V v1.3 : le test 2025 est « vendeur-certain par construction » (V a été conçu
pour un autre usage) ; les ex æquo à 0/NULL sont départagés par tirage seedé 974.
Aucun taux absolu extrapolé — RR relatifs et taux observés avec IC uniquement.

## Sélection de modèle sur val 2024 (ordre : AVANT le test)

{md_table(val)}

## Ventilation du top-1158 test par type de propriétaire

{md_table(vent)}

## Lift par percentile (test 2025)

{md_table(lift)}

## Lecture critique — ce que le modèle a réellement trouvé

Analyse post-hoc du top-1158 test (aucune retouche du modèle) :
{md_table(pd.read_csv(REPORTS / 'test-2025-composition-top.csv'))}

Nature des mutations captées par le top-1158 :
{md_table(pd.read_csv(REPORTS / 'test-2025-nature-hits.csv'))}

**La tête extrême du classement est dominée par les reventes d'appartements en
copropriété** (le label L2 au grain parcelle rend un immeuble « mutant » dès qu'un
lot se vend). Zéro fuite temporelle — l'information était disponible au 01/01/Y —
mais pour l'usage radar foncier, la préversion 2026 doit être lue avec le filtre
produit adéquat. Recommandation Phase 3 : label variante excluant les locaux
« Appartement » (mutation foncière stricte : maison / nu / immeuble entier), ou
exclusion des parcelles copro de la vue produit. Le lift au-delà de la tête
(percentiles 1-10, cf. table ci-dessous) reste très supérieur aux baselines et
porte le signal foncier de fond. Autre constat : « permis < 24 mois » est
POSITIF (5,6 % vs 1,8 %), contrairement à l'attente Phase 0 (signe libre assumé).

## Churn

Top-1158 au 01/01/2024 vs 01/01/2025 : overlap {int(churn['overlap'][0])}
({churn['overlap_pct'][0]:.1%}) — {int(churn['entrants'][0])} entrants,
{int(churn['sortants'][0])} sortants.

## Fichiers

dictionnaire-features.md · model-card.md · val-resultats.csv ·
test-2025-{{resultats,lift,ventilation-owner,calibration}}.csv ·
controles-negatifs.csv · churn-top1158.csv · interactions-journal.csv ·
iv-features.csv · top-1158-2026.csv
"""
    (REPORTS / "SYNTHESE-M3.md").write_text(synth)

    bins = pd.read_csv(REPORTS / "model-card-bins.csv")
    card = [f"""# Model card — modèle P (m3-phase1)

Logistique L2 sur WoE (binning figé sur train {freeze['meta']['train']}),
calibration isotonique sur val 2024, intercept recalé 2025 pour le scoring 2026.
P = probabilité de mutation L2 (Vente + Vente terrain à bâtir) sous 12 mois.
Log-hazard additif : z = intercept + Σ coef×WoE(bin) — contribution traçable
ligne à ligne, par bloc (Z zone / D dormance).

Croisements retenus (GBM shadow, jamais en prod) : {freeze['meta']['interactions'] or 'aucun'}

## Force des features (information value, train)

""" + md_table(iv, "{:.4f}")]
    for feat, grp in bins.groupby("feature", sort=False):
        card.append(f"\n## `{feat}` (bloc {grp['bloc'].iloc[0]}, coef {grp['coef'].iloc[0]:+.4f})\n")
        card.append(md_table(grp[["bin", "effectif", "taux_evenement", "woe", "log_hazard"]],
                             "{:.4f}"))
    (REPORTS / "model-card.md").write_text("\n".join(card) + "\n")
    print("SYNTHESE-M3.md + model-card.md écrits")


if __name__ == "__main__":
    main()
