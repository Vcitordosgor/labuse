"""M131 Phase 2 — L'EXAMEN sous la MÉTRIQUE v2 (arbitrée 19/08/2026).

Même protocole/fold que M130 (walk-forward, train ≤2023 binning-train-seul, iso 2024,
test 2025 ; population = vivier servi q_v10_m129, 285 781). SEULE la NOTATION change :

  • deux notes, une par segment (nu / bâti), chacune sur SON propre classement ;
  • le top est un POURCENTAGE : top 0,4 % de chaque segment (plus de nombre fixe) ;
  • double barre de promotion, mécanique :
      (a) candidat inférieur hors bruit sur AUCUN segment,
      (b) candidat supérieur hors bruit sur AU MOINS UN segment,
      (c) ECE ne se dégrade pas ;
    « hors bruit » = l'IC95 de l'écart PAIRÉ (candidat − servi, mêmes lignes rééchan-
    tillonnées) ne franchit pas 0.

Concurrents : actuel (A_ref, repro sous-protocole du servi m36-l2f-2026) vs C_bati.
Références v2 = les notes de l'ACTUEL par segment, sur le vivier réel (recalculées, dites).

Mesure seule. Cache les prédictions (reports/m131/preds.npz) pour itérer la métrique sans
refit. Écrit reports/m131/*.csv.
Usage : PYTHONPATH=src python scripts/m131/examen_v2.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, "scripts/m127")
from examen import KEPT, fit_fold  # protocole M127/M130 réutilisé tel quel  # noqa: E402
sys.path.insert(0, "scripts/m127bis")
from examen_bis import BATI_SPECS, CAUSE_SPEC, frame_for, load_v2bis  # noqa: E402

from labuse.db import engine  # noqa: E402
from labuse.scoring.p_model import evaluate as ev  # noqa: E402
from labuse.scoring.p_model.evaluate import _ranked_top_mask  # noqa: E402

REPORTS = Path("reports/m131")
PREDS = REPORTS / "preds.npz"
SERVED_RUN = "q_v10_m129"
TOP_PCT = 0.004          # top 0,4 % de chaque segment (métrique v2)
SEED = 974
N_BOOT = 1000

LADDERS = {
    "actuel":  {"specs": KEPT, "residuel": "v1"},
    "C_bati":  {"specs": KEPT + [CAUSE_SPEC] + BATI_SPECS, "residuel": "v2"},
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def rr_median(y, p, k, seeds=range(1, 21)):
    """RR@k médian sur 20 tirages d'ex æquo (motif M36/M130)."""
    return float(np.median([ev.rr_at_k(y, p, k, seed=s)["rr"] for s in seeds]))


def rr_boot(y, p, k):
    """RR@k point + IC95 bootstrap (rééchantillonnage des lignes, k constant)."""
    r = ev.bootstrap_rr(y, p, k, n_boot=N_BOOT, seed=SEED)
    return r["rr"], r["ic95_bas"], r["ic95_haut"]


def paired_delta_ic(y, pa, pb, k):
    """IC95 de l'écart PAIRÉ RR(candidat) − RR(servi) : mêmes lignes rééchantillonnées,
    top-k de CHAQUE modèle sur ce rééchantillon. C'est le test « hors bruit » de la v2."""
    rng = np.random.RandomState(SEED)
    n = len(y)
    deltas = []
    for _ in range(N_BOOT):
        idx = rng.randint(0, n, n)
        yb, pab, pbb = y[idx], pa[idx], pb[idx]
        base = yb.mean()
        if base <= 0:
            continue
        ta = _ranked_top_mask(pab, k, rng)
        tb = _ranked_top_mask(pbb, k, rng)
        deltas.append(yb[tb].mean() / base - yb[ta].mean() / base)
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return float(np.median(deltas)), float(lo), float(hi)


def fit_or_load():
    """Fit les deux modèles fold 2025 (lignes ALIGNÉES : même df filtré annee==2025) et
    cache y / p_actuel / p_Cbati / masques. Recharge le cache s'il existe."""
    if PREDS.exists():
        z = np.load(PREDS, allow_pickle=True)
        log(f"prédictions rechargées depuis {PREDS}")
        return {k: z[k] for k in z.files}

    vivier = pd.read_sql(text(
        "SELECT par.idu FROM dryrun_parcel_evaluations d JOIN parcels par ON par.id = d.parcel_id "
        "WHERE d.run_label = :r AND d.status <> 'exclue'"), engine(), params={"r": SERVED_RUN})
    vivier_idus = set(vivier["idu"])
    log(f"vivier servi {SERVED_RUN} : {len(vivier_idus):,} parcelles")

    copro = pd.read_sql("SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro",
                        engine()).set_index("idu")["copro"]
    log("chargement dataset v2bis…")
    df = load_v2bis()
    log(f"{len(df):,} lignes")

    preds = {}
    ref_test = None
    for name, spec in LADDERS.items():
        fdf = frame_for(df, spec["residuel"])
        log(f"fit {name} ({spec['residuel']}, {len(spec['specs'])} features) fold 2025…")
        r = fit_fold(fdf, spec["specs"], 2025, copro)
        if ref_test is None:
            ref_test = r["test"]
            preds["y"] = np.asarray(r["y"], dtype=int)   # fit_fold renvoie déjà un ndarray
            preds["hc"] = r["hc"]
            preds["in_vivier"] = r["test"]["idu"].isin(vivier_idus).to_numpy()
            preds["nu"] = (r["test"]["nu"] == True).to_numpy()   # noqa: E712
            preds["idu"] = r["test"]["idu"].to_numpy()
        else:
            # sanité : les lignes sont bien alignées (même ordre d'idu)
            assert np.array_equal(r["test"]["idu"].to_numpy(), preds["idu"]), "lignes désalignées"
        preds[f"p_{name}"] = r["p"]
    REPORTS.mkdir(parents=True, exist_ok=True)
    np.savez(PREDS, **preds)
    log(f"prédictions cachées → {PREDS}")
    return preds


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    d = fit_or_load()
    y, hc, in_vivier, nu = d["y"], d["hc"], d["in_vivier"], d["nu"]
    pa, pb = d["p_actuel"], d["p_C_bati"]
    base_pop = hc & in_vivier          # hors copro ∩ vivier servi

    rows, verdict = [], {}
    for seg, smask in [("nu", nu), ("bati", ~nu)]:
        m = base_pop & smask
        n = int(m.sum())
        k = max(1, int(round(TOP_PCT * n)))
        ys, pas_, pbs = y[m], pa[m], pb[m]

        rr_a = rr_median(ys, pas_, k); a_pt, a_lo, a_hi = rr_boot(ys, pas_, k)
        rr_b = rr_median(ys, pbs, k);  b_pt, b_lo, b_hi = rr_boot(ys, pbs, k)
        dmed, dlo, dhi = paired_delta_ic(ys, pas_, pbs, k)

        sup = dlo > 0            # candidat supérieur HORS BRUIT (IC écart > 0)
        inf = dhi < 0            # candidat inférieur HORS BRUIT (IC écart < 0)
        statut = "supérieur hors bruit" if sup else "inférieur hors bruit" if inf else "dans le bruit"
        verdict[seg] = {"sup": sup, "inf": inf}
        log(f"segment {seg}: n={n:,} k={k} (top {TOP_PCT*100:.1f}%) base {ys.mean()*100:.3f}% · "
            f"actuel {rr_a:.2f} [{a_lo:.2f},{a_hi:.2f}] · C_bati {rr_b:.2f} [{b_lo:.2f},{b_hi:.2f}] · "
            f"Δ {dmed:+.2f} [{dlo:+.2f},{dhi:+.2f}] → {statut}")
        rows.append({
            "segment": seg, "n": n, "k": k, "top_pct": TOP_PCT * 100,
            "base_pct": round(float(ys.mean()) * 100, 4),
            "rr_actuel": round(rr_a, 3), "actuel_ic_bas": round(a_lo, 3), "actuel_ic_haut": round(a_hi, 3),
            "rr_C_bati": round(rr_b, 3), "C_bati_ic_bas": round(b_lo, 3), "C_bati_ic_haut": round(b_hi, 3),
            "delta_median": round(dmed, 3), "delta_ic_bas": round(dlo, 3), "delta_ic_haut": round(dhi, 3),
            "statut": statut,
        })
    pd.DataFrame(rows).to_csv(REPORTS / "segments_v2.csv", index=False)

    # ── ECE : global (vivier) + par segment ─────────────────────────────────────────
    ece_rows = []
    for label, m in [("vivier", base_pop), ("nu", base_pop & nu), ("bati", base_pop & ~nu)]:
        ea, _ = ev.ece(y[m], pa[m])
        eb, _ = ev.ece(y[m], pb[m])
        ece_rows.append({"population": label, "ece_actuel": round(ea, 4),
                         "ece_C_bati": round(eb, 4), "degrade": eb > ea + 1e-4})
        log(f"ECE {label}: actuel {ea:.4f} · C_bati {eb:.4f}")
    pd.DataFrame(ece_rows).to_csv(REPORTS / "ece_v2.csv", index=False)

    # ── LA DOUBLE BARRE — verdict mécanique ─────────────────────────────────────────
    a = not any(v["inf"] for v in verdict.values())        # inférieur sur AUCUN segment
    b = any(v["sup"] for v in verdict.values())            # supérieur sur AU MOINS UN
    ece_ok = not any(r["degrade"] for r in ece_rows if r["population"] == "vivier")
    promu = a and b and ece_ok
    log("═" * 70)
    log(f"DOUBLE BARRE : (a) jamais inférieur hors bruit = {a} · "
        f"(b) supérieur hors bruit ≥1 segment = {b} · (c) ECE non dégradée = {ece_ok}")
    log(f"VERDICT MÉCANIQUE : C_bati {'PROMU' if promu else 'NON PROMU'}")
    log("Références v2 gravées (notes de l'ACTUEL servi, par segment, top 0,4 %) :")
    for r in rows:
        log(f"  {r['segment']}: RR {r['rr_actuel']} [{r['actuel_ic_bas']},{r['actuel_ic_haut']}]")
    pd.DataFrame([{"critere_a_jamais_inferieur": a, "critere_b_superieur_1seg": b,
                   "critere_c_ece_ok": ece_ok, "promu": promu}]
                 ).to_csv(REPORTS / "verdict_v2.csv", index=False)
    log("FIN — sorties dans reports/m131/")


if __name__ == "__main__":
    main()
