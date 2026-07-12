"""M3.6 lot 2 / B0 (avenant) — censure des transcriptions DVF 974.

Millésimes témoins 2018, 2019, 2020, chacun vu par DEUX éditions cquest du
FICHIER BRUT DGFiP (précoce ≈ N+1 avril ; tardive ≈ N+3/N+5, réputée complète) :
  1. courbe de complétude : lignes brutes 974, mutations proxy, L2, L2-F ;
  2. concordance de CLASSEMENT : un modèle fold (train ≤ N-2, calibration N-1,
     pipeline identique au walk-forward) est évalué sur l'année N avec les labels
     PRÉCOCES puis COMPLETS — si RR@1158 concorde, la censure est neutre pour le
     classement (elle enlève du niveau, pas de l'ordre) ;
  3. annotation des taux attendus 2023-2025 (vus à ~6-30 mois d'âge en 2026) et
     amendement du protocole forward 2026.

Usage : LABUSE_DATABASE_URL=… python scripts/m36-foncier/lot2_b0_censure.py
"""
from __future__ import annotations

import csv
import time
from pathlib import Path

import numpy as np
import pandas as pd

from labuse.db import engine
from labuse.scoring.p_model import evaluate as ev
from labuse.scoring.p_model.features import FEATURES
from labuse.scoring.p_model.model import PModel

REPORTS = Path("reports/m36-foncier")
CQ = Path("/tmp/cquest")
TEMOINS = {2018: ("201904", "202304"), 2019: ("202004", "202404"),
           2020: ("202104", "202504")}
L2 = {"Vente", "Vente terrain à bâtir"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_raw(path: Path) -> pd.DataFrame:
    """Fichier brut DGFiP filtré 974 → une ligne par (mutation proxy, parcelle, local).

    IDU 14 = 974 + commune(2, zéro-paddée) + préfixe(3) + section(2, paddée) + plan(4).
    Proxy mutation (le brut n'a pas d'id) : (date, valeur, commune) — identique
    dans les deux éditions donc valide pour des RATIOS et labels par parcelle.
    """
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        rd = csv.DictReader(fh, delimiter="|")
        for r in rd:
            if r.get("Nature mutation") not in L2:
                continue
            com = (r.get("Code commune") or "").strip().zfill(2)
            pre = (r.get("Prefixe de section") or "").strip().zfill(3) or "000"
            sec = (r.get("Section") or "").strip().rjust(2, "0")
            plan = (r.get("No plan") or "").strip().zfill(4)
            if not com or not sec or not plan.strip("0"):
                continue
            rows.append({
                "idu": f"974{com}{pre}{sec}{plan}",
                "mut": (r.get("Date mutation"), r.get("Valeur fonciere"),
                        com),
                "type_local": (r.get("Type local") or "").strip() or None,
            })
    return pd.DataFrame(rows)


def labels_l2f(df: pd.DataFrame) -> tuple[set, set]:
    """(parcelles L2, parcelles L2-F) — même règle L2-F que ext_sql (excl. ssi
    tous locaux ∈ {Appartement, Dépendance}, ≥1 App, <4 App)."""
    g = df.groupby("mut")["type_local"].agg(list)
    excl = set()
    for mut, locs in g.items():
        nn = [t for t in locs if t]
        n_app = sum(t == "Appartement" for t in nn)
        if nn and all(t in ("Appartement", "Dépendance") for t in nn) \
                and n_app >= 1 and n_app < 4:
            excl.add(mut)
    l2 = set(df["idu"])
    l2f = set(df.loc[~df["mut"].isin(excl), "idu"])
    return l2, l2f


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)

    # ---- 1. courbe de complétude ------------------------------------------------
    comp_rows = []
    labels = {}
    for annee, (early, late) in TEMOINS.items():
        de = parse_raw(CQ / f"vf974-{annee}-{early}.txt")
        dl = parse_raw(CQ / f"vf974-{annee}-{late}.txt")
        l2_e, l2f_e = labels_l2f(de)
        l2_l, l2f_l = labels_l2f(dl)
        labels[annee] = {"early": l2f_e, "late": l2f_l,
                         "early_l2": l2_e, "late_l2": l2_l}
        comp_rows.append({
            "millesime": annee, "edition_precoce": early, "edition_complete": late,
            "age_mois_precoce": (int(early[:4]) - annee) * 12 + int(early[4:]) - 12,
            "mut_l2_precoce": len({m for m in de["mut"]}),
            "mut_l2_complete": len({m for m in dl["mut"]}),
            "parcelles_l2f_precoce": len(l2f_e),
            "parcelles_l2f_complete": len(l2f_l),
            "completude_l2f": len(l2f_e) / max(len(l2f_l), 1),
        })
        log(f"{annee} : complétude L2-F précoce/complète = "
            f"{comp_rows[-1]['completude_l2f']:.1%}")
    comp = pd.DataFrame(comp_rows)
    comp.to_csv(REPORTS / "completude-censure.csv", index=False)

    # ---- 2. concordance de classement (témoin 2020, le plus riche) --------------
    from labuse.scoring.p_model.features import derive

    df = pd.read_sql(
        "SELECT * FROM p_model_ext_dataset WHERE annee IN (2017, 2018, 2019, 2020)",
        engine())
    df = derive(df)
    train = df[df.annee.isin((2017, 2018))].reset_index(drop=True)
    cal = df[df.annee == 2019].reset_index(drop=True)
    test = df[df.annee == 2020].reset_index(drop=True)
    m = PModel(feature_names=[f.name for f in FEATURES])
    m.year_dummies = [2017]
    m.fit(train, train["label"].astype(int), C=5.0)
    m.calibrate(cal, cal["label"].astype(int))
    p = m.predict_proba(test)

    conc_rows = []
    for annee in (2019, 2020):
        tst = df[df.annee == annee].reset_index(drop=True)
        pp = m.predict_proba(tst) if annee != 2020 else p
        for vue in ("early", "late"):
            y = tst["idu"].isin(labels[annee][vue]).astype(int).to_numpy()
            r = ev.rr_at_k(y, pp, 1158)
            conc_rows.append({"millesime": annee, "vue": vue, "n_pos": int(y.sum()),
                              "taux": r["taux_global"], "rr@1158": r["rr"]})
            log(f"concordance {annee} vue {vue} : RR@1158 = {r['rr']:.1f} "
                f"({int(y.sum())} positifs)")
    conc = pd.DataFrame(conc_rows)
    conc.to_csv(REPORTS / "concordance-censure.csv", index=False)

    # ---- 3. annotation 2023-2025 -------------------------------------------------
    ages = {2023: 42, 2024: 30, 2025: 18}  # âge (mois) des millésimes prod vus en 07/2026
    note = pd.DataFrame([
        {"millesime": y, "age_mois_en_072026": a,
         "completude_attendue": "≈ complète" if a >= 36 else
         f"~{np.interp(a, [16, 36], [comp['completude_l2f'].mean(), 1.0]):.0%} "
         "(interpolation témoins)"}
        for y, a in ages.items()])
    note.to_csv(REPORTS / "annotation-taux-2023-2025.csv", index=False)
    print(note.to_string(index=False))


if __name__ == "__main__":
    main()
