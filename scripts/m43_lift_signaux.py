"""M43 Phase 1 — MESURE À BLANC du pouvoir prédictif des signaux propriétaire PM (0 poids modifié).

Harnais gelé RR M36 : `p_model_ext_dataset` (fold annee=2025, `label` = mutation). Pour chaque
signal SOCIÉTÉ (cessée / radiée / procédure collective), on mesure :
  1. le lift BRUT de mutation vs la base PM-sans-signal (RR + IC95 Katz-log) ;
  2. le lift RÉSIDUEL une fois la TENURE connue (RR stratifié Mantel-Haenszel par tenure_bin) —
     si le signal ne fait que répéter la tenure, le RR résiduel s'effondre vers 1.
Honnêteté : effectifs, IC, « non concluant » (IC couvrant 1) dit tel quel. Lecture seule.

Usage : PYTHONPATH=src python scripts/m43_lift_signaux.py
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import engine  # noqa: E402

FOLD = 2025
SQL = f"""
WITH pm AS (
  SELECT DISTINCT ON (idu) idu, siren FROM pm_proprietaires_millesimes
  WHERE millesime = 2024 AND siren <> '')
SELECT d.idu, d.label::int AS label, COALESCE(d.tenure_bin,'inconnu') AS tenure_bin,
  (pm.siren IN (SELECT siren FROM owner_enrichment WHERE payload->>'etat_administratif'='C'))::int AS cessee,
  (pm.siren IN (SELECT siren FROM bodacc_annonces_owner WHERE famille='radiation'))::int AS radiee,
  (pm.siren IN (SELECT siren FROM bodacc_annonces_owner WHERE famille='pcl'))::int AS pcl
FROM pm JOIN p_model_ext_dataset d ON d.idu = pm.idu AND d.annee = {FOLD}
"""


def _rr_katz(a: int, n1: int, c: int, n0: int) -> tuple[float, float, float]:
    """RR = (a/n1)/(c/n0) + IC95 log (Katz). a=mutés signal, n1=n signal, c=mutés base, n0=n base."""
    if not a or not c or not n1 or not n0:
        return (float("nan"), float("nan"), float("nan"))
    rr = (a / n1) / (c / n0)
    se = math.sqrt(1.0 / a - 1.0 / n1 + 1.0 / c - 1.0 / n0)
    return (rr, rr * math.exp(-1.96 * se), rr * math.exp(1.96 * se))


def _mh_rr(strata: list[tuple[int, int, int, int]]) -> tuple[float, float, float]:
    """RR de Mantel-Haenszel sur des strates (a, n1, c, n0) — ajuste sur la tenure. IC log (Greenland-Robins)."""
    num = den = 0.0
    for a, n1, c, n0 in strata:
        N = n1 + n0
        if N == 0:
            continue
        num += a * n0 / N
        den += c * n1 / N
    if den == 0 or num == 0:
        return (float("nan"), float("nan"), float("nan"))
    rr = num / den
    # variance de Greenland-Robins pour ln(RR_MH)
    p_sum = r_sum = s_sum = 0.0
    for a, n1, c, n0 in strata:
        N = n1 + n0
        if N == 0:
            continue
        r_sum += a * n0 / N
        s_sum += c * n1 / N
        p_sum += ((n1 * n0 * (a + c) - a * c * N) / (N * N))
    if r_sum == 0 or s_sum == 0:
        return (rr, float("nan"), float("nan"))
    se = math.sqrt(p_sum / (r_sum * s_sum))
    return (rr, rr * math.exp(-1.96 * se), rr * math.exp(1.96 * se))


def main() -> None:
    with engine().connect() as c:
        rows = c.execute(text(SQL)).mappings().all()
    data = [dict(r) for r in rows]
    n_total = len(data)
    base_mask = [r for r in data if not (r["cessee"] or r["radiee"] or r["pcl"])]
    c_base, n0_base = sum(r["label"] for r in base_mask), len(base_mask)
    print(f"— MESURE À BLANC (fold {FOLD}, {n_total} parcelles PM) — base PM-sans-signal : "
          f"{c_base}/{n0_base} = {100*c_base/n0_base:.2f}% de mutation —\n")
    print(f"{'signal':10s} {'n':>6s} {'mutés':>6s} {'taux':>7s} {'RR brut [IC95]':>22s} {'RR|tenure MH [IC95]':>24s} verdict")
    results = []
    tenures = sorted({r["tenure_bin"] for r in data})
    for sig in ("cessee", "radiee", "pcl"):
        grp = [r for r in data if r[sig]]
        a, n1 = sum(r["label"] for r in grp), len(grp)
        rr, lo, hi = _rr_katz(a, n1, c_base, n0_base)
        # résiduel MH par tenure : strates signal vs base-sans-signal
        strata = []
        for t in tenures:
            gt = [r for r in grp if r["tenure_bin"] == t]
            bt = [r for r in base_mask if r["tenure_bin"] == t]
            strata.append((sum(r["label"] for r in gt), len(gt),
                           sum(r["label"] for r in bt), len(bt)))
        mh, mlo, mhi = _mh_rr(strata)
        concluant = (lo > 1.0)
        resid_tient = (not math.isnan(mlo)) and (mlo > 1.0)
        verdict = ("INTÉGRABLE" if concluant and resid_tient else
                   "brut concluant, résiduel faible" if concluant else "NON CONCLUANT (IC couvre 1)")
        print(f"{sig:10s} {n1:>6d} {a:>6d} {100*a/n1:>6.2f}% "
              f"{rr:>6.2f} [{lo:.2f};{hi:.2f}] {mh:>10.2f} [{mlo:.2f};{mhi:.2f}]  {verdict}")
        results.append({"signal": sig, "n": n1, "mutes": a, "taux_pct": round(100 * a / n1, 2),
                        "rr_brut": round(rr, 2), "ic_bas": round(lo, 2), "ic_haut": round(hi, 2),
                        "rr_tenure_mh": round(mh, 2), "mh_ic_bas": round(mlo, 2), "mh_ic_haut": round(mhi, 2),
                        "verdict": verdict})
    # digest
    import csv
    out = os.path.join(os.path.dirname(__file__), "..", "qa", "m43", "lifts_signaux_p1.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader(); w.writerows(results)
    print(f"\n✓ digest : {out}")


if __name__ == "__main__":
    main()
