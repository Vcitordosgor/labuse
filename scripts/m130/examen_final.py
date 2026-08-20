"""M130 Phase 2 — L'EXAMEN FINAL sur le VIVIER RÉEL.

La question : sur le vivier servi aujourd'hui (q_v10_m129 : 285 781 parcelles, dont
deux tiers de bâti), quel modèle est le meilleur — l'ACTUEL ou C_bati (M127-bis) ?

Protocole IDENTIQUE à M127/M127-bis (walk-forward, train ≤2023 binning TRAIN seul,
calibration isotonique 2024, test 2025 ; RR@1158 hors copro ; ties seedées). LA SEULE
chose qui change — et c'est le sujet — la POPULATION D'ÉVALUATION est le nouveau vivier,
pas l'ancien. On garde k=1158 (la métrique ne bouge pas), on restreint la population aux
parcelles NON écartées par la cascade servie q_v10_m129.

Deux concurrents, même fit, même fold :
  • ACTUEL   = A_ref (22 features nettoyées, résiduel v1) — la reproduction sous-protocole
               du modèle servi m36-l2f-2026 (M127 : 6,67 ≈ réf gelée 6,73).
  • C_bati   = A_ref + cause M125 + 9 features bâti (M127-bis) — le challenger gardé au chaud.

Mesures : RR global (ancien vivier ET nouveau — pour isoler l'effet d'univers), RR par
segment nu/bâti, ECE, et la COMPOSITION de la tête de liste (top 100 / top 1000 : nu vs bâti).

RIEN de servi ne bouge. Lit p_model_dataset_v2bis + dryrun_parcel_evaluations. Écrit
reports/m130/ uniquement.
Usage : PYTHONPATH=src python scripts/m130/examen_final.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, "scripts/m127")
from examen import KEPT, fit_fold  # protocole M127 réutilisé tel quel  # noqa: E402
sys.path.insert(0, "scripts/m127bis")
from examen_bis import BATI_SPECS, CAUSE_SPEC, frame_for, load_v2bis  # noqa: E402

from labuse.db import engine  # noqa: E402
from labuse.scoring.p_model import evaluate as ev  # noqa: E402

REPORTS = Path("reports/m130")
K = 1158
SERVED_RUN = "q_v10_m129"
CONTROLE_ANCIEN = 6.73    # référence gelée ALGO-1/M36 (RR@1158 hors copro fold 2025)

#: les deux concurrents — même protocole, résiduel propre à chacun (l'actuel n'a jamais lu M125).
LADDERS = {
    "actuel":  {"specs": KEPT, "residuel": "v1"},
    "C_bati":  {"specs": KEPT + [CAUSE_SPEC] + BATI_SPECS, "residuel": "v2"},
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def rr_median(y, p, k, seeds=range(1, 21)):
    """RR@k médian sur 20 tirages d'ex æquo (la coupure tombe dans des paliers de score
    identiques : un seul tirage serait une fausse précision — motif M36 rr_commune)."""
    vals = [ev.rr_at_k(y, p, k, seed=s)["rr"] for s in seeds]
    return float(np.median(vals)), float(min(vals)), float(max(vals))


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)

    # ── le vivier servi : les idus NON écartés par la cascade q_v10_m129 ────────────
    vivier = pd.read_sql(text(
        "SELECT par.idu FROM dryrun_parcel_evaluations d "
        "JOIN parcels par ON par.id = d.parcel_id "
        "WHERE d.run_label = :r AND d.status <> 'exclue'"), engine(),
        params={"r": SERVED_RUN})
    vivier_idus = set(vivier["idu"])
    log(f"vivier servi {SERVED_RUN} : {len(vivier_idus):,} parcelles (non écartées)")

    copro = pd.read_sql("SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro",
                        engine()).set_index("idu")["copro"]
    log("chargement dataset v2bis (2017-2025)…")
    df = load_v2bis()
    log(f"{len(df):,} lignes")

    glob_rows, seg_rows, head_rows = [], [], []
    for name, spec in LADDERS.items():
        fdf = frame_for(df, spec["residuel"])
        log(f"── fit {name} (résiduel {spec['residuel']}, {len(spec['specs'])} features) fold 2025…")
        r = fit_fold(fdf, spec["specs"], 2025, copro)   # train ≤2023, iso 2024, test 2025

        test, p, y, hc = r["test"], r["p"], r["y"].astype(int), r["hc"]
        in_vivier = test["idu"].isin(vivier_idus).to_numpy()
        nu = (test["nu"] == True).to_numpy()            # noqa: E712 (pandas bool)

        # ── RR global : ANCIEN vivier (toute la population 2025 hors copro) ──────────
        m_old = hc
        rr_o, lo_o, hi_o = rr_median(y[m_old], p[m_old], K)
        boot_o = ev.bootstrap_rr(y[m_old], p[m_old], K, n_boot=1000)
        # ── RR global : NOUVEAU vivier (hors copro ∩ vivier servi) ───────────────────
        m_new = hc & in_vivier
        rr_n, lo_n, hi_n = rr_median(y[m_new], p[m_new], K)
        boot_n = ev.bootstrap_rr(y[m_new], p[m_new], K, n_boot=1000)
        ece_n, _ = ev.ece(y[m_new], p[m_new])
        ece_o, _ = ev.ece(y[m_old], p[m_old])

        log(f"   {name} : RR@{K} hc ANCIEN vivier = {rr_o:.2f} [{boot_o['ic95_bas']:.2f},"
            f"{boot_o['ic95_haut']:.2f}] (n={m_old.sum():,}, base {y[m_old].mean()*100:.3f}%)")
        log(f"   {name} : RR@{K} hc NOUVEAU vivier = {rr_n:.2f} [{boot_n['ic95_bas']:.2f},"
            f"{boot_n['ic95_haut']:.2f}] (n={m_new.sum():,}, base {y[m_new].mean()*100:.3f}%) · ECE {ece_n:.4f}")

        glob_rows.append({
            "modele": name,
            "rr_ancien_vivier": round(rr_o, 3), "rr_ancien_min": round(lo_o, 3), "rr_ancien_max": round(hi_o, 3),
            "rr_ancien_ic_bas": round(boot_o["ic95_bas"], 3), "rr_ancien_ic_haut": round(boot_o["ic95_haut"], 3),
            "n_ancien": int(m_old.sum()), "base_ancien_pct": round(float(y[m_old].mean()) * 100, 4),
            "rr_nouveau_vivier": round(rr_n, 3), "rr_nouveau_min": round(lo_n, 3), "rr_nouveau_max": round(hi_n, 3),
            "rr_nouveau_ic_bas": round(boot_n["ic95_bas"], 3), "rr_nouveau_ic_haut": round(boot_n["ic95_haut"], 3),
            "n_nouveau": int(m_new.sum()), "base_nouveau_pct": round(float(y[m_new].mean()) * 100, 4),
            "ece_ancien": round(ece_o, 4), "ece_nouveau": round(ece_n, 4),
        })

        # ── RR par segment nu/bâti (sur le NOUVEAU vivier hors copro) ────────────────
        for seg, smask in [("nu", nu), ("bati", ~nu)]:
            mm = m_new & smask
            if mm.sum() < 5:
                seg_rows.append({"modele": name, "segment": seg, "n": int(mm.sum()),
                                 "k": 0, "rr": None, "positifs_topk": 0, "base_pct": None})
                continue
            k_seg = max(1, int(round(K * mm.sum() / m_new.sum())))
            rr_seg, _, _ = rr_median(y[mm], p[mm], k_seg)
            pt = ev.rr_at_k(y[mm], p[mm], k_seg)
            seg_rows.append({"modele": name, "segment": seg, "n": int(mm.sum()), "k": k_seg,
                             "rr": round(rr_seg, 3), "positifs_topk": pt["positifs_topk"],
                             "base_pct": round(float(y[mm].mean()) * 100, 4)})
            log(f"     segment {seg}: n={mm.sum():,} k={k_seg} RR={rr_seg:.2f} "
                f"(base {y[mm].mean()*100:.3f}%)")

        # ── composition de la tête de liste (top 100 / top 1000 du NOUVEAU vivier hc) ─
        idx_new = np.where(m_new)[0]
        order = idx_new[np.argsort(-p[idx_new], kind="stable")]   # score DESC, ordre stable
        for topn in (100, 1000):
            head = order[:topn]
            n_nu = int(nu[head].sum())
            n_bati = int((~nu[head]).sum())
            pos = int(y[head].sum())
            head_rows.append({"modele": name, "tete": topn, "nu": n_nu, "bati": n_bati,
                              "part_bati_pct": round(100 * n_bati / topn, 1),
                              "mutations_observees": pos})
            log(f"     tête {topn}: nu {n_nu} · bâti {n_bati} ({100*n_bati/topn:.0f}%) · "
                f"mutations {pos}")

    pd.DataFrame(glob_rows).to_csv(REPORTS / "global.csv", index=False)
    pd.DataFrame(seg_rows).to_csv(REPORTS / "segments.csv", index=False)
    pd.DataFrame(head_rows).to_csv(REPORTS / "tete_de_liste.csv", index=False)

    # ── verdict brut (le rapport le motive) ─────────────────────────────────────────
    g = {r["modele"]: r for r in glob_rows}
    act, cb = g["actuel"], g["C_bati"]
    delta = (cb["rr_nouveau_vivier"] - act["rr_nouveau_vivier"]) / act["rr_nouveau_vivier"] * 100
    log("═" * 70)
    log(f"ANCIEN vivier — actuel {act['rr_ancien_vivier']:.2f} (réf gelée {CONTROLE_ANCIEN})")
    log(f"NOUVEAU vivier — actuel {act['rr_nouveau_vivier']:.2f} · C_bati {cb['rr_nouveau_vivier']:.2f} "
        f"→ Δ {delta:+.1f}%")
    log(f"effet d'univers seul (actuel, ancien→nouveau) : "
        f"{act['rr_ancien_vivier']:.2f} → {act['rr_nouveau_vivier']:.2f}")
    log("FIN — sorties dans reports/m130/")


if __name__ == "__main__":
    main()
