"""SCORING-5-RETOUR §5 — ablations au banc K0 (script JETABLE, jamais destiné au merge).

Trois colonnes :
  A — modèle actuel complet (servi m36-l2f) : chiffres K0 CONNUS, cités, pas re-mesurés
      (COMPTE-RENDU-SCORING-2, colonne base de k0_table.csv, candidat « ligne_de_base »).
  B — simplifié propre = recette q_v14 SANS filo_snv_pp/filo_pct_pauv/filo_pct_prop
      (flaggées ATTENTION par SCORING-5) ni piscine/pv_candidat (mortes B.2 SCORING-1).
  C — signaux dynamiques seuls : DVF + Sitadel + voisinage + propriétaire-marché,
      SANS zone_plu, surface, pente, filo, résiduel, nu/pct_bati, anciennete_plu.

Banc : train ≤2023 · calibration isotonique par segment 2024 · test 2025 (protocole.py).
Rien de servi ne change ; n'écrit QUE sous reports/scoring-5/ (pas k0_table.csv).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocole  # noqa: E402
from _common import engine, ROOT  # noqa: E402
from labuse.scoring.p_v2 import qv12, qv14  # noqa: E402

OUT = ROOT / "reports/scoring-5"
OUT.mkdir(parents=True, exist_ok=True)
ENRICHI = ROOT / "reports/q-v14/enrichi_2017_2026.pkl"

RETRAITS_B = {"filo_snv_pp", "filo_pct_pauv", "filo_pct_prop", "piscine", "pv_candidat"}
DYNAMIQUES_C = [
    "tenure_bin_v2", "permis_bin", "pc_pm_sur_parcelle_pp_36m",
    "rot_nu", "rot_bati", "med_pm2_terrain_36m", "med_pm2_bati_36m",
    "tendance_pm2_bati",
    "ventes_150m_12m", "ventes_150m_24m", "ventes_400m_12m", "ventes_400m_24m",
    "ventes_400m_delta", "permis_100m_24m", "operations_pa_400m_24m",
    "volume_commune_a1", "med_pm2_commune_a1", "tendance_volume_3ans",
    "pm_vendeur_actif", "ventes_pm_secteur_36m",
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _extras(ctx, p: np.ndarray, y_override=None) -> dict:
    """Métriques du §7 absentes de protocole.metriques : Brier, précision@k île,
    paliers aux seuils ABSOLUS PALIERS-1 (p≥0,20 / 0,10-0,20, sans déclassements),
    recall de tête."""
    m = ctx.eval_mask
    y = (ctx.y if y_override is None else y_override)[m]
    pm_ = p[m]
    hors = ~ctx.copro[m]
    yh, ph = y[hors], pm_[hors]
    row = {"brier": float(np.mean((ph - yh) ** 2))}
    order = np.argsort(-ph)
    for k in (500, 1000, 2000):
        row[f"prec@{k}"] = float(yh[order[:k]].mean())
    prio = ph >= 0.20
    suiv = (ph >= 0.10) & (ph < 0.20)
    row["n_priorite_abs"] = int(prio.sum())
    row["prec_priorite_abs"] = float(yh[prio].mean()) if prio.any() else float("nan")
    row["n_a_suivre_abs"] = int(suiv.sum())
    row["prec_a_suivre_abs"] = float(yh[suiv].mean()) if suiv.any() else float("nan")
    tete = prio | suiv
    row["recall_tete_abs"] = float(yh[tete].sum() / yh.sum()) if yh.sum() else float("nan")
    return row


def _mesurer(eng, ctx, df, seg_all, tag, names, specs, inter):
    log(f"[{tag}] fit ({len(names)} features, {len(inter)} interactions)…")
    m12 = qv14.fit_qv14(df, seg_all, names, specs, inter)
    seg_test = seg_all[(df.annee == protocole.TEST_YEAR).to_numpy()].reset_index(drop=True)
    seg_26 = seg_all[(df.annee == protocole.SCORE_YEAR).to_numpy()].reset_index(drop=True)
    p = m12.predict_proba(ctx.test, seg_test)
    d_feats = [s.name for s in specs if s.bloc == "D"]
    cd = m12.contributions(ctx.test)[
        [c for c in d_feats if c in m12.base.coefs]].sum(axis=1).to_numpy()
    p26 = m12.predict_proba(ctx.score26, seg_26)
    row = protocole.metriques(ctx, tag, p, cd, p26)
    row.update(_extras(ctx, p))
    return row


def main() -> None:
    eng = engine()
    log("chargement du cache enrichi…")
    df = pd.read_pickle(ENRICHI)
    copro = qv14.copro_de(eng, df)
    seg_all = qv14.segmenter(df, copro)
    ctx = protocole.Contexte(eng, df[df.annee == protocole.TEST_YEAR],
                             df[df.annee == protocole.SCORE_YEAR])

    names14, specs14, inter14 = qv14.features_qv14(avec_ventes_pm=True)

    # B — simplifié propre
    names_b = [n for n in names14 if n not in RETRAITS_B]
    by = {s.name: s for s in specs14}
    specs_b = [by[n] for n in names_b]
    inter_b = [(a, b) for a, b in inter14 if a in names_b and b in names_b]

    # C — dynamiques seuls
    manquantes = [n for n in DYNAMIQUES_C if n not in names14]
    assert not manquantes, f"features C absentes de la recette : {manquantes}"
    names_c = [n for n in names14 if n in DYNAMIQUES_C]
    specs_c = [by[n] for n in names_c]
    inter_c = [(a, b) for a, b in inter14 if a in names_c and b in names_c]

    jeux = {
        "ref": ("sc5_qv14_ref", names14, specs14, inter14),
        "B": ("sc5_B_simplifie", names_b, specs_b, inter_b),
        "C": ("sc5_C_dynamiques", names_c, specs_c, inter_c),
    }
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    csv = OUT / "ablations_k0.csv"
    deja = pd.read_csv(csv) if csv.exists() else pd.DataFrame()
    rows = []
    for cle, (tag, names, specs, inter) in jeux.items():
        if only and cle != only:
            continue
        if not deja.empty and tag in set(deja.get("tag", [])):
            log(f"[{tag}] déjà mesuré — sauté (reprise)")
            continue
        rows.append(_mesurer(eng, ctx, df, seg_all, tag, names, specs, inter))
        table = pd.concat([deja, pd.DataFrame(rows)], ignore_index=True)
        table.to_csv(csv, index=False)  # append incrémental : reprenable
    table = pd.read_csv(csv)
    log(f"écrit : {csv}")
    print(table.to_string(index=False))
    print("\nretraits B :", sorted(RETRAITS_B),
          "\ninteractions B :", inter_b,
          "\nfeatures C :", names_c,
          "\ninteractions C :", inter_c)


if __name__ == "__main__":
    main()
