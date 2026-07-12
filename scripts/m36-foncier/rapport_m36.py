"""SYNTHESE-M36.md — compile les CSV des lots 0-3. À lancer en dernier.
Usage : python scripts/m36-foncier/rapport_m36.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REPORTS = Path("reports/m36-foncier")


def md(df: pd.DataFrame, fmt: str = "{:.2f}") -> str:
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: fmt.format(v) if pd.notna(v) else "—")
    return "\n".join(
        ["| " + " | ".join(map(str, d.columns)) + " |",
         "|" + "---|" * len(d.columns)]
        + ["| " + " | ".join(map(str, r)) + " |" for r in d.itertuples(index=False)])


def main() -> None:
    eff = pd.read_csv(REPORTS / "effectifs-copro.csv")
    strate = pd.read_csv(REPORTS / "verdict-strate.csv")
    vol = pd.read_csv(REPORTS / "volumetrie-l2f.csv")
    comp = pd.read_csv(REPORTS / "completude-censure.csv")
    conc = pd.read_csv(REPORTS / "concordance-censure.csv")
    annot = pd.read_csv(REPORTS / "annotation-taux-2023-2025.csv")
    wf = pd.read_csv(REPORTS / "walk-forward.csv")
    stab = pd.read_csv(REPORTS / "stabilite-signes.csv")
    suivi = pd.read_csv(REPORTS / "suivi-permis-piscine.csv")
    cmp_ = pd.read_csv(REPORTS / "comparatif.csv")
    dec = pd.read_csv(REPORTS / "decision-promotion.csv")

    hc = strate[(strate.strate == "hors_copro") & (strate.k == 1158)][
        ["score", "rr", "ic95_bas", "ic95_haut", "taux_topk", "positifs_topk"]]
    wf_l2f = wf[wf.label == "label"][
        ["fold", "rr@1158", "ic_bas", "ic_haut", "rr@1158_hors_copro", "ece"]]
    wf_l2 = wf[wf.label == "label_l2"][["fold", "rr@1158", "rr@1158_hors_copro"]]
    promo = bool(dec["PROMOTION_M36"].iloc[0])

    out = f"""# SYNTHÈSE M3.6 — Verdict foncier (L2-F) + walk-forward long

## ⚑ LOT 0 — LE VERDICT PRODUIT (test 2025, univers HORS COPRO, modèle M3 gelé)

Effectifs : {int(eff['copro_total'][0])} parcelles copro sur {int(eff['parcelles'][0])}
(RNIC {int(eff['copro_rnic'][0])}, détection DVF {int(eff['copro_dvf'][0])}) ;
taux de mutation de base : 29,0 % en copro vs 1,52 % hors copro.

{md(hc, "{:.3f}")}

**Le modèle M3 complet retombe à RR@1158 = 2,85 hors copro, SOUS sa propre
ablation Z-seul (5,07)** : le bloc D de M3 (tenure et ses croisements) ne tirait
sa force que des copropriétés. La rotation de secteur seule ne vaut plus que 1,08
(les « secteurs chauds » L2 étaient les copros). **V v1.3 re-jugé hors copro :
0,51 — le verdict M3 est confirmé, il ne tenait pas aux copros.**

Décomposition du signe « permis <2 ans » (2023-24) : hors copro 5,4 % vs 1,5 %
(jamais) — **le signe positif est un vrai signal foncier**, pas un artefact copro
(en copro tout est à 21-31 %). Détail : permis-signe-copro.csv.

## Lot 1 — Label L2-F

L2-F = L2 moins les mutations « unité de copro » : tous locaux non nuls ∈
{{Appartement, Dépendance}}, ≥1 Appartement et ≤3 appartements (une vente en bloc
de ≥4 appartements = immeuble entier, CONSERVÉE ; maison, terrain nu, local
mixte, dépendance seule : conservés). Part exclue : 23 % (2014) → ~30 % (2022+).

{md(vol, "{:.3f}")}

## Lot 2 — B0 censure (avenant) : forte, mais neutre pour le classement

{md(comp[['millesime', 'age_mois_precoce', 'parcelles_l2f_precoce',
          'parcelles_l2f_complete', 'completude_l2f']], "{:.3f}")}

Concordance de classement (même score, labels précoces vs complets) :

{md(conc, "{:.3f}")}

Un millésime 974 vu à ~16 mois ne contient que 27-45 % des parcelles L2-F
finales, mais le RR@1158 concorde (3,2→3,9 ; 3,3→3,4) : **la censure enlève du
niveau, pas de l'ordre**. Annotation prod au 07/2026 : {annot.to_dict('records')}.
Amendement forward 2026 : verdicts de NIVEAU sur édition N+2 minimum (ou
correction par facteur de complétude) ; le suivi de CLASSEMENT peut être continu.

## Lot 2 — Walk-forward L2-F, 6 folds (train ≤N-2, calibration N-1, test N)

{md(wf_l2f, "{:.4f}")}

Contrôle L2 (mêmes folds) — RR élevé en univers complet (~20, porté par les
copros) mais 4,2-6,5 seulement hors copro, TOUJOURS sous le modèle L2-F :

{md(wf_l2, "{:.2f}")}

Croisements minés une fois sur le fold ancien (2017-18→2019) :
tenure×permis, tenure×surface, ndvi×zone_plu, tenure×rot_nu, surface×permis.

Stabilité des signes : **{int(stab['stable_5_sur_6'].sum())}/{len(stab)} features
stables ≥5/6 folds** ; aucune monotonie contrainte violée ; les instables
(permis_24m_norm, filo_dens_pop, qpv, window_coverage, dormance_droits) sont des
coefficients quasi nuls. Suivis explicites, stables 6/6 et positifs :

{md(suivi, "{:.3f}")}

## Lot 3 — Verdict final

{md(cmp_[['modele', 'cible_eval', 'rr', 'ic95_bas', 'ic95_haut', 'ece']], "{:.3f}")}

Overlap top-1158 M3 vs M3.6 sur 2025 : {cmp_['overlap_top1158_m3_m36'].iloc[0]:.1%}.

Critères de promotion : RR@1158 L2-F 2025 hors copro = {dec['rr_2025_vs_lot0'].iloc[0]:.2f}
vs barre lot 0.2 = 2,85 (mandat) et 5,07 (Z-seul, barre effective retenue — sinon
on promouvrait un modèle sous sa propre ablation) ; RR ≥ 2× sur tous les folds :
{bool(dec['tous_folds_rr_ge_2'].iloc[0])} ; signes : {dec['signes_stables'].iloc[0]}.

### → {"PROMOTION : M3.6 (L2-F) devient le modèle de référence." if promo else "PAS de promotion — documenté ci-dessus."}

Préversion produit : top-1158-2026-foncier.csv (univers hors copro, modèle
train 2017-2024 + calibration 2025, jamais évalué contre un test, 5 contributions
lisibles par parcelle).

## Fichiers

effectifs-copro.csv · verdict-strate.csv · permis-signe-copro.csv ·
volumetrie-l2f.csv · completude-censure.csv · concordance-censure.csv ·
annotation-taux-2023-2025.csv · walk-forward.csv · stabilite-signes.csv ·
suivi-permis-piscine.csv · interactions-fold-ancien.csv · comparatif.csv ·
decision-promotion.csv · top-1158-2026-foncier.csv
"""
    (REPORTS / "SYNTHESE-M36.md").write_text(out)
    print("SYNTHESE-M36.md écrit")


if __name__ == "__main__":
    main()
