"""SCORING-3 · L4.3 — la mesure du potentiel : sur 2025 (année vierge), les
parcelles qui se sont VENDUES **et** avaient un FORT POTENTIEL — la cible réelle
du promoteur. Précision@100 par commune de l'INDICE D'OPPORTUNITÉ
(p × valeur créée, le classement candidat) vs la PROBABILITÉ SEULE.

Définitions (les mêmes que potentiel.backfill_run, as-of 2025) :
  - valeur créée = SDP résiduelle (lecture K3) × médiane €/m² bâti de la
    commune, année Y-1 = 2024 (DVF L2-F) ;
  - fort potentiel = valeur créée > médiane communale des valeurs strictement
    positives (relatif à chaque marché, pas un seuil absolu) ;
  - univers : hors copro, exclusions d'hygiène K0 appliquées.

Caveat consigné : la SDP résiduelle est un état STATIQUE (PLU/bâti courants) —
le résiduel « au 01/01/2025 » n'est pas archivé ; la mesure suppose le PLU
stable sur la fenêtre (vrai sauf révision — même convention que le modèle).

Sortie : reports/q-v12/l4_precision_potentiel.csv (tableau au compte-rendu).
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
from labuse.scoring.p_v2 import qv12  # noqa: E402

CACHE = ROOT / "reports/score-v2-arene/cache"
QDIR = ROOT / "reports/q-v12"
QDIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def prec_at_100(g: pd.DataFrame, score_col: str, y_col: str) -> float:
    k = min(100, len(g))
    return float(g.nlargest(k, score_col)[y_col].mean())


def main() -> None:
    eng = engine()
    log("chargement test 2025 + enrichissement recette…")
    df = protocole.load_range(eng, (protocole.TEST_YEAR,))
    df = qv12.enrichir(eng, df, (protocole.TEST_YEAR,), cache_dir=CACHE)
    ctx = protocole.Contexte(eng, df)
    seg = qv12.segmenter(ctx.test, ctx.copro)
    m12, _, _ = qv12.verify_artifacts()
    p = m12.predict_proba(ctx.test, seg)

    t = ctx.test.copy()
    t["p"] = p
    t["y"] = ctx.y
    # valeur créée as-of 2025 : SDP (lecture K3) × médiane communale 2024
    t["valeur"] = (pd.to_numeric(t["sdp_residuelle_v2_m2"], errors="coerce")
                   * pd.to_numeric(t["med_pm2_commune_a1"], errors="coerce"))
    t["indice"] = t["p"] * t["valeur"]
    m = ctx.eval_mask & ~ctx.copro
    t = t[m].reset_index(drop=True)

    # fort potentiel = valeur > médiane communale des valeurs > 0
    med_pos = (t[t["valeur"] > 0].groupby("commune")["valeur"].median()
               .rename("med_pos"))
    t = t.merge(med_pos, on="commune", how="left")
    t["fort_potentiel"] = (t["valeur"] > t["med_pos"]).fillna(False)
    t["y_fort"] = (t["y"].astype(bool) & t["fort_potentiel"]).astype(int)

    rows = []
    for com, g in t.groupby("commune"):
        rows.append({
            "commune": com, "n": len(g),
            "n_vendues": int(g["y"].sum()),
            "n_vendues_fort_potentiel": int(g["y_fort"].sum()),
            "prec@100_proba_seule": round(prec_at_100(g, "p", "y_fort"), 4),
            "prec@100_indice_opportunite": round(prec_at_100(g, "indice", "y_fort"), 4),
        })
    out = pd.DataFrame(rows).sort_values("commune")
    resume = {
        "cible": "vendue 2025 ET fort potentiel (valeur > médiane communale des > 0)",
        "n_cible_total": int(t["y_fort"].sum()),
        "prec@100_proba_mediane": float(out["prec@100_proba_seule"].median()),
        "prec@100_indice_mediane": float(out["prec@100_indice_opportunite"].median()),
        "communes_indice_gagne": int((out["prec@100_indice_opportunite"]
                                      > out["prec@100_proba_seule"]).sum()),
        "communes_egalite": int((out["prec@100_indice_opportunite"]
                                 == out["prec@100_proba_seule"]).sum()),
        "n_communes": len(out),
    }
    out.to_csv(QDIR / "l4_precision_potentiel.csv", index=False)
    pd.DataFrame([resume]).to_csv(QDIR / "l4_precision_resume.csv", index=False)
    print(out.to_string(index=False))
    print(json.dumps(resume, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
