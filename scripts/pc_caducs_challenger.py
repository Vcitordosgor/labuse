"""PHASE A cycle 2, volet 2 — CHALLENGER « composante V PC caducs » (dérivé de q_v7_defisc).

Montage STRUCTUREL identique au défisc (volet 3 cycle 1) : le **triplet gelé** (tier v2 · statut cascade ·
matrice Q×A) est copié VERBATIM du champion ; V ne module QUE le rang `p_raw`. Donc gate boussole 3 axes
= 0/64 par construction, et le signal caduc seul ne peut JAMAIS faire franchir un seuil de tier.

Périmètre V : caduc (table pc_caducs) ∩ non-écarté dans q_v7_defisc.

POIDS calibré PRÉ-LABEL (anti-leakage strict). Décision de fenêtre :
  - CLEAN 2016-2018 (cohortes propres) : OR 1,97 → **W = 0,0062** (retenu).
  - FULL 2014-2018 (avec l'inversion 2014-2015) : OR 1,52 → W = 0,0038 (−39 %, sensibilité, cf. rapport).
  Formule : W = W_CAP · ln(OR_cal) / ln(3), W_CAP = 0,010 (plafond, même montage que défisc).
Jamais calibré sur les mutations ~2025 que l'arène jugera.

Verdict = L'ARÈNE, juge de plein droit (signal RÉTROSPECTIF) : ΔRR apparié IC95 excluant zéro vs
q_v7_defisc, gate boussole 0/64, ECE non dégradée, churn commenté. Pas d'exception forward.

Usage: python scripts/pc_caducs_challenger.py   (idempotent)
Puis : labuse arene --challenger q_v7_defisc_Vcaduc --champion q_v7_defisc
"""
from __future__ import annotations
import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from labuse.db import session_scope  # noqa: E402

CHAMPION = "q_v7_defisc"
CHALLENGER = "q_v7_defisc_Vcaduc"
V_CAP = 0.010
OR_CAL = 1.97                    # OR caduc vs réalisés, cohortes PROPRES 2016-2018 (pré-label)
import math
W = round(V_CAP * math.log(OR_CAL) / math.log(3.0), 4)   # = 0.0062


def build(session) -> dict:
    session.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id = :c"), {"c": CHALLENGER})
    session.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE run_label = :c"), {"c": CHALLENGER})
    session.execute(text("DELETE FROM p_score_v2_runs WHERE run_id = :c"), {"c": CHALLENGER})

    v_idus = [r[0] for r in session.execute(text(
        "SELECT s.parcelle_id FROM parcel_p_score_v2 s "
        "JOIN pc_caducs c ON c.idu = s.parcelle_id "
        "WHERE s.run_id = :ch AND s.tier <> 'ecartee'"), {"ch": CHAMPION}).all()]

    # header — computed_at ANTÉRIEUR au champion (challenger temporaire, jamais servi par défaut)
    session.execute(text(
        "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, n_parcelles, "
        " duration_s, snapshot_label, computed_at) "
        "SELECT :c, model_version, model_sha256, "
        "  COALESCE(params,'{}'::jsonb) || jsonb_build_object('challenger','Vcaduc','w',CAST(:w AS double precision),"
        "                                                     'or_cal',CAST(:orc AS double precision)), "
        "  n_parcelles, duration_s, 'challenger_Vcaduc', computed_at - interval '1 minute' "
        "FROM p_score_v2_runs WHERE run_id = :ch"), {"c": CHALLENGER, "ch": CHAMPION, "w": W, "orc": OR_CAL})

    # scores — copie verbatim, SEUL p_raw nudgé (+W) sur le périmètre V ; tier gelé
    n_scores = session.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        " contrib_z, contrib_d, top5_contributions, copro, tier, event_date, model_version, computed_at, "
        " icd, icd_detail) "
        "SELECT :c, parcelle_id, p_raw + CASE WHEN parcelle_id = ANY(:vids) THEN :w ELSE 0 END, "
        "       mult_base, percentile, rang, contrib_z, contrib_d, top5_contributions, copro, "
        "       tier, event_date, model_version, computed_at, icd, icd_detail "
        "FROM parcel_p_score_v2 WHERE run_id = :ch"),
        {"c": CHALLENGER, "ch": CHAMPION, "vids": v_idus, "w": W}).rowcount

    # dryrun (statut + matrice) — copie verbatim → axes boussole statut/matrice identiques
    n_dry = session.execute(text(
        "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, opportunity_score, "
        " opportunity_base, status, rules_version, created_at, q_score, a_score, a_completude, matrice_statut) "
        "SELECT :c, parcel_id, completeness_score, opportunity_score, opportunity_base, status, rules_version, "
        "       created_at, q_score, a_score, a_completude, matrice_statut "
        "FROM dryrun_parcel_evaluations WHERE run_label = :ch"),
        {"c": CHALLENGER, "ch": CHAMPION}).rowcount

    return {"v_parcelles": len(v_idus), "n_scores": n_scores, "n_dryrun": n_dry, "W": W}


def main():
    with session_scope() as s:
        r = build(s)
    print(f"challenger {CHALLENGER} (base {CHAMPION}) :")
    print(f"  W calibré pré-label (clean 2016-2018, OR {OR_CAL}) = {r['W']}")
    print(f"  composante V : {r['v_parcelles']} parcelles caduc ∩ non-écarté (+{r['W']} p_raw), triplet gelé")
    print(f"  scores {r['n_scores']} · dryrun {r['n_dryrun']}")
    print(f"\n  juger : labuse arene --challenger {CHALLENGER} --champion {CHAMPION}")


if __name__ == "__main__":
    main()
