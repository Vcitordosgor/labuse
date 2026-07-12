"""M5 lot 3.2 — brulantes-v2.csv + delta ligne à ligne vs les brûlantes v1.3.

Les 120 brûlantes v1.3 viennent du snapshot M1 (label v1.3-*, brulante=true).
Pour chaque sortie/entrée, un MOTIF explicite est donné (copro, étage 0, rang,
plancher C, contribution D, événement) — sensibilité ± sur le seuil D incluse.

Usage : LABUSE_DATABASE_URL=… python scripts/m5-produit/brulantes_delta.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from labuse.db import engine

REPORTS = Path("reports/m5-produit")


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    run = pd.read_sql("SELECT run_id, params FROM p_score_v2_runs "
                      "ORDER BY computed_at DESC LIMIT 1", engine()).iloc[0]
    params = run["params"] if isinstance(run["params"], dict) else json.loads(run["params"])
    v2 = pd.read_sql(text("""
        SELECT s.parcelle_id, s.rang, s.mult_base, s.percentile, s.tier, s.copro,
               s.contrib_d, s.event_date, s.top5_contributions, p.commune
        FROM parcel_p_score_v2 s JOIN parcels p ON p.idu = s.parcelle_id
        WHERE s.run_id = :r"""), engine(), params={"r": run["run_id"]})

    # ---- brulantes-v2.csv ------------------------------------------------------
    b2 = v2[v2["tier"] == "brulante"].sort_values("rang")
    exp = b2[["parcelle_id", "commune", "rang", "mult_base", "event_date",
              "contrib_d"]].copy()
    t5 = b2["top5_contributions"].map(
        lambda t: t if isinstance(t, list) else json.loads(t or "[]"))
    for j in range(5):
        exp[f"contribution_{j+1}"] = t5.map(
            lambda e, j=j: f"{e[j]['libelle']}{' [' + e[j]['bin'] + ']' if e[j]['bin'] else ''}"
                           f" {e[j]['signe']}{abs(e[j]['log_hazard']):.2f}"
            if len(e) > j else "")
    exp.to_csv(REPORTS / "brulantes-v2.csv", index=False)
    print(f"brûlantes v2 : {len(b2)} (seuil D = {params['brulante_seuil_d']:.3f}, "
          f"garde-fou 30-120)")

    # ---- delta vs v1.3 ---------------------------------------------------------
    v13 = pd.read_sql(text("""
        SELECT sp.parcelle_id FROM score_snapshot_parcelles sp
        JOIN score_snapshots s ON s.id = sp.snapshot_id
        WHERE s.label LIKE 'v1.3%' AND sp.brulante"""), engine())
    set13, set2 = set(v13["parcelle_id"]), set(b2["parcelle_id"])
    idx = v2.set_index("parcelle_id")

    def motif_sortie(idu: str) -> str:
        if idu not in idx.index:
            return "hors du parc scoré (parcelle disparue du frame)"
        r = idx.loc[idu]
        if r["copro"]:
            return "copro (hors univers produit v2)"
        if r["tier"] == "ecartee":
            return "écartée étage 0"
        if pd.isna(r["rang"]) or r["rang"] > params["n_sortie"]:
            return f"rang P {int(r['rang']) if pd.notna(r['rang']) else '—'} > N_sortie {params['n_sortie']}"
        if r["tier"] == "chaude":
            if r["contrib_d"] < params["brulante_seuil_d"]:
                return (f"chaude mais contribution D {r['contrib_d']:.2f} < seuil "
                        f"{params['brulante_seuil_d']:.2f}")
            return (f"chaude, D {r['contrib_d']:.2f} ≥ seuil mais ni événement "
                    f"< 12 mois ni top décile D ({params['brulante_top_decile_d']:.2f})")
        if r["tier"] in ("a_creuser", "reserve_fonciere"):
            return f"tier v2 = {r['tier']} (plancher C ou rang)"
        return f"tier v2 = {r['tier']}"

    def motif_entree(idu: str) -> str:
        r = idx.loc[idu]
        ev = f"événement daté {r['event_date']}" if pd.notna(r["event_date"]) \
            else "top décile de contribution D"
        return f"rang P {int(r['rang'])}, D {r['contrib_d']:.2f} ≥ seuil, {ev}"

    delta = pd.concat([
        pd.DataFrame({"parcelle_id": sorted(set13 & set2), "mouvement": "gardée",
                      "motif": "brûlante v1.3 ET v2"}),
        pd.DataFrame({"parcelle_id": sorted(set13 - set2), "mouvement": "sortie",
                      "motif": [motif_sortie(i) for i in sorted(set13 - set2)]}),
        pd.DataFrame({"parcelle_id": sorted(set2 - set13), "mouvement": "entrée",
                      "motif": [motif_entree(i) for i in sorted(set2 - set13)]}),
    ])
    delta.to_csv(REPORTS / "delta-brulantes-v2.csv", index=False)
    print(f"delta vs v1.3 ({len(set13)} brûlantes) : "
          f"{len(set13 & set2)} gardées, {len(set13 - set2)} sorties, "
          f"{len(set2 - set13)} entrées")

    # ---- sensibilité ± sur le seuil D (comme M1) --------------------------------
    seuil = float(params["brulante_seuil_d"])
    chaude_pool = v2[v2["tier"].isin(["chaude", "brulante"])]
    rows = []
    for delta_s in (-0.1, -0.05, 0.0, 0.05, 0.1):
        s = seuil + delta_s
        ev_ok = pd.to_datetime(chaude_pool["event_date"], errors="coerce").notna()
        n = int(((chaude_pool["contrib_d"] >= s)
                 & (ev_ok | (chaude_pool["contrib_d"]
                             >= params["brulante_top_decile_d"]))).sum())
        rows.append({"seuil_d": round(s, 3), "delta": delta_s, "effectif": n})
    pd.DataFrame(rows).to_csv(REPORTS / "brulantes-v2-sensibilite.csv", index=False)
    print("sensibilité ± écrite")


if __name__ == "__main__":
    main()
