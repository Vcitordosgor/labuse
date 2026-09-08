"""PALIERS-1 · Lot A — mesurer la NOUVELLE règle de paliers au banc K0 (test 2025).

La règle (décision Vic 08/09/2026), en probabilité ABSOLUE de vente sous 12 mois,
hors copropriété :
  - Priorité   : p ≥ 0,20
  - À suivre   : 0,10 ≤ p < 0,20
  - Sans signal: p < 0,10
  - Écartée    : cascade étage 0 (inchangée)          → hors palier
  - Copropriété: hors palier (motif « copropriété »)  → hors palier

On mesure sur le banc K0 (année vierge 2025, ventes réelles à 12 mois), avec q_v14
scoré par son artefact GELÉ (aucun fit, aucun rescoring de run) :
  - effectif + précision réelle de Priorité et À suivre, île entière et Saint-Paul,
    AVEC et SANS les anciens déclassements (bâti saturé / zone fermée / AU fermée /
    non constructible / bâti révélé) ;
  - churn annuel simulé 2024→2025 sur les seuils de sortie (0,18 / 0,09) — majorant
    du churn mensuel (le p bouge plus sur un an que sur un mois).

GARDE-FOU du mandat : si la précision de Priorité SANS déclassements tombe sous 20 %
au K0, on S'ARRÊTE et on rend compte AVANT d'implémenter le Lot B.

Doctrine : lecture seule ; n'écrit que dans reports/q-v14/. q_v11_m137 reste servi.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocole  # noqa: E402
from _common import engine, ROOT  # noqa: E402
from labuse.scoring.p_v2 import qv14  # noqa: E402
from labuse.faisabilite.constructibilite import (  # noqa: E402
    DECLASSE_ZONE_FERMEE, DECLASSE_NON_CONSTRUCTIBLE,
    DECLASSE_AU_STATUT_INCONNU, DECLASSE_AU_FERMEE)

QDIR = ROOT / "reports/q-v14"
CACHE = ROOT / "reports/score-v2-arene/cache"
ENRICHI_AB = QDIR / "paliers1_enrichi_2024_2025.pkl"  # pickle (pas de pyarrow)
SAINT_PAUL = "97415"

SEUIL_PRIORITE = 0.20
SEUIL_A_SUIVRE = 0.10
SORTIE_PRIORITE = 0.18   # anti-churn : descend de Priorité seulement si p < 0,18
SORTIE_A_SUIVRE = 0.09   # anti-churn : descend d'À suivre seulement si p < 0,09
GARDE_FOU_MIN = 0.20     # précision Priorité sans déclassements — plancher bloquant


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def _charger_enrichi(eng) -> pd.DataFrame:
    if ENRICHI_AB.exists():
        log(f"cache enrichi {ENRICHI_AB.name}…")
        return pd.read_pickle(ENRICHI_AB)
    log("chargement 2024-2025 (dataset ext) + enrichissement recette q_v14…")
    df = protocole.load_range(eng, (2024, 2025))
    df = qv14.enrichir(eng, df, (2024, 2025), cache_dir=CACHE)
    df.to_pickle(ENRICHI_AB)
    log(f"cache écrit ({len(df)} lignes)")
    return df


def _declasse_mask(t: pd.DataFrame) -> pd.Series:
    """Le masque « anciens déclassements », À L'IDENTIQUE de statuts.assign_tiers
    (zone fermée / non constructible / AU fermée / AU inconnu / bâti révélé / saturé)."""
    dc = t["declasse_cause"] if "declasse_cause" in t else pd.Series(pd.NA, index=t.index)
    au = t["au_statut"] if "au_statut" in t else pd.Series(pd.NA, index=t.index)
    br = t["bati_revele"].fillna(False).astype(bool) if "bati_revele" in t else pd.Series(False, index=t.index)
    bs = t["bati_sature"].fillna(False).astype(bool) if "bati_sature" in t else pd.Series(False, index=t.index)
    return (dc.isin([DECLASSE_ZONE_FERMEE, DECLASSE_NON_CONSTRUCTIBLE])
            | au.isin([DECLASSE_AU_FERMEE, DECLASSE_AU_STATUT_INCONNU, "générique"])
            | br | bs)


def _paliers_absolus(p: np.ndarray, hors_palier: np.ndarray) -> np.ndarray:
    """Priorité / À suivre / Sans signal / hors_palier (str), règle ABSOLUE."""
    lab = np.where(p >= SEUIL_PRIORITE, "Priorité",
          np.where(p >= SEUIL_A_SUIVRE, "À suivre", "Sans signal"))
    lab = np.where(hors_palier, "hors_palier", lab)
    return lab


def _mesure_zone(y, palier, eval_mask, declasse, sub, nom_zone) -> list[dict]:
    """Effectif + précision réelle de Priorité et À suivre sur une zone, AVEC et
    SANS les anciens déclassements (SANS = règle neuve, déclassées gardées)."""
    rows = []
    for cle in ("Priorité", "À suivre"):
        base = sub & (palier == cle)
        for variante, m in (("sans déclassements (règle neuve)", base),
                            ("avec déclassements (règle ancienne)", base & ~declasse)):
            ev = m & eval_mask
            n_eff = int(m.sum())
            n_ev = int(ev.sum())
            prec = float(y[ev].mean()) if n_ev else float("nan")
            rows.append({"zone": nom_zone, "palier": cle, "variante": variante,
                         "effectif": n_eff, "n_evalue": n_ev,
                         "precision_reelle": round(prec, 4) if n_ev else None})
    return rows


def _churn_annuel(df, seg_all, m12, eng) -> dict:
    """Churn annuel 2024→2025 (majorant du mensuel) : part des Priorité/À suivre de
    2024 qui SORT en 2025, SANS puis AVEC l'anti-churn (seuils de sortie 0,18/0,09)."""
    import measure
    out = {}
    scores = {}
    for an in (2024, 2025):
        mask = (df.annee == an).to_numpy()
        sub = df[mask].reset_index(drop=True)
        seg = seg_all[mask].reset_index(drop=True)
        p = m12.predict_proba(sub, seg)
        copro = measure.copro_mask(eng, sub)
        sub = sub.copy(); sub["copro"] = copro
        measure._attach_gates(eng, sub)
        hors = copro | sub["ecartee_etage0"].to_numpy()
        scores[an] = pd.DataFrame({"idu": sub["idu"], "p": p, "hors": hors})
    j = scores[2024].merge(scores[2025], on="idu", suffixes=("_24", "_25"))
    j = j[~j["hors_24"] & ~j["hors_25"]]  # dans le palier les deux années
    for cle, entree, sortie in (("Priorité", SEUIL_PRIORITE, SORTIE_PRIORITE),
                                ("À suivre", SEUIL_A_SUIVRE, SEUIL_PRIORITE)):
        # entrés en 2024 dans ce palier (bande [entree, plafond))
        if cle == "Priorité":
            in24 = j["p_24"] >= SEUIL_PRIORITE
            # sort SANS anti-churn : p_25 < 0,20 ; AVEC : p_25 < 0,18
            sortie_sans = j["p_25"] < SEUIL_PRIORITE
            sortie_avec = j["p_25"] < SORTIE_PRIORITE
        else:
            in24 = (j["p_24"] >= SEUIL_A_SUIVRE) & (j["p_24"] < SEUIL_PRIORITE)
            sortie_sans = j["p_25"] < SEUIL_A_SUIVRE
            sortie_avec = j["p_25"] < SORTIE_A_SUIVRE
        n = int(in24.sum())
        c_sans = float((in24 & sortie_sans).sum() / n) if n else float("nan")
        c_avec = float((in24 & sortie_avec).sum() / n) if n else float("nan")
        out[cle] = {"n_2024": n,
                    "churn_annuel_sans_anti_churn": round(c_sans, 4),
                    "churn_annuel_avec_anti_churn": round(c_avec, 4)}
    return out


def main() -> None:
    eng = engine()
    df = _charger_enrichi(eng)
    m12, _, _ = qv14.verify_artifacts()
    copro_all = qv14.copro_de(eng, df)
    seg_all = qv14.segmenter(df, copro_all)

    # ── test 2025 : contexte K0 (label, gates, hygiène, eval_mask) ────────────
    mask25 = (df.annee == 2025).to_numpy()
    ctx = protocole.Contexte(eng, df[df.annee == 2025], score26=None)
    seg25 = seg_all[mask25].reset_index(drop=True)
    p25 = m12.predict_proba(ctx.test, seg25)

    copro = ctx.copro
    ecartee = ctx.test["ecartee_etage0"].to_numpy()
    hors_palier = copro | ecartee
    declasse = _declasse_mask(ctx.test).to_numpy()
    palier = _paliers_absolus(p25, hors_palier)
    y = ctx.y
    eval_mask = ctx.eval_mask
    insee = ctx.test["idu"].str.slice(0, 5).to_numpy()

    rows = []
    rows += _mesure_zone(y, palier, eval_mask, declasse,
                         np.ones(len(palier), bool), "île")
    rows += _mesure_zone(y, palier, eval_mask, declasse,
                         insee == SAINT_PAUL, "Saint-Paul (97415)")
    tab = pd.DataFrame(rows)
    tab.to_csv(QDIR / "paliers1_lotA_precision.csv", index=False)

    churn = _churn_annuel(df, seg_all, m12, eng)
    (QDIR / "paliers1_lotA_churn.json").write_text(
        json.dumps(churn, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── garde-fou : précision Priorité SANS déclassements, île ────────────────
    gf = tab[(tab.zone == "île") & (tab.palier == "Priorité")
             & (tab.variante.str.startswith("sans"))].iloc[0]
    verdict = {
        "garde_fou_seuil": GARDE_FOU_MIN,
        "precision_priorite_sans_declassements_ile": gf["precision_reelle"],
        "effectif_priorite_sans_declassements_ile": int(gf["effectif"]),
        "n_evalue": int(gf["n_evalue"]),
        "DECLENCHE": bool(gf["precision_reelle"] is not None
                          and gf["precision_reelle"] < GARDE_FOU_MIN),
    }
    (QDIR / "paliers1_lotA_gardefou.json").write_text(
        json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n===== EFFECTIF + PRÉCISION RÉELLE (K0 test 2025) =====")
    print(tab.to_string(index=False))
    print("\n===== CHURN ANNUEL 2024→2025 (majorant du mensuel) =====")
    print(json.dumps(churn, indent=2, ensure_ascii=False))
    print("\n===== GARDE-FOU =====")
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    if verdict["DECLENCHE"]:
        print("\n*** GARDE-FOU DÉCLENCHÉ : précision Priorité sans déclassements "
              f"< {GARDE_FOU_MIN:.0%} — STOP avant Lot B, rendre compte à Vic. ***")
    else:
        print(f"\nGarde-fou OK (précision {gf['precision_reelle']:.1%} ≥ "
              f"{GARDE_FOU_MIN:.0%}) — feu vert pour le Lot B.")


if __name__ == "__main__":
    main()
