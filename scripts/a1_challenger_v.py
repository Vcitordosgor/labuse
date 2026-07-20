"""PHASE A-1 étape 2, volet 3 — CHALLENGER « composante V défisc » (dérivé de q_v6_m8).

Matérialise un run challenger dans SON PROPRE run_id, dérivé du run servi `q_v6_m8` + une composante V
(« fenêtre de sortie de défiscalisation »). Le run servi n'est JAMAIS touché.

CONTRAINTE DURE (mandat) : le signal défisc seul ne peut JAMAIS faire franchir un seuil de tier. Design
qui la garantit PAR CONSTRUCTION : le **triplet gelé** (tier v2 · statut cascade · matrice Q×A) est copié
VERBATIM du champion ; la composante V ne module QUE le score de rang `p_raw`. Donc :
  - tier/statut/matrice challenger ≡ champion → gate boussole 3 axes = 0/64 par construction ;
  - V ne fait que réordonner à l'intérieur des bandes déjà servies (jamais de nouveau tier).

Périmètre V : défisc-actif ∩ MONO ∩ **non-écarté** (tier ≠ ecartee). Nudger une parcelle écartée serait
absurde (exclue de la prospection) et polluerait le top-1158 → on ne le fait pas. Reste 131 parcelles.

Bump PLAFONNÉ : `p_raw' = p_raw + V_CAP` (V_CAP = 0.01 ≈ écart p50→p90 de p_raw sur le run). Borné,
additif, sans effet sur le tier (gelé).

Verdict de victoire = le WALK-FORWARD (volet 1, déjà PASSÉ). L'arène = garde-fou (boussole 0/64, ECE non
dégradée, churn commenté) ; son ΔRR n'est PAS le critère (signal forward, doctrine PHASE0_BILAN.md).

Usage: python scripts/a1_challenger_v.py   (écrit le run challenger, idempotent)
Puis : labuse arene --challenger q_v6_m8_Vdefisc --champion q_v6_m8
"""
from __future__ import annotations
import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from labuse.db import session_scope  # noqa: E402

CHAMPION = "q_v6_m8"
CHALLENGER = "q_v6_m8_Vdefisc"
V_CAP = 0.01                    # plafond du bonus V sur p_raw (borné, ne touche jamais le tier)


def build(session) -> dict:
    # idempotence : purge d'un éventuel challenger précédent
    session.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id = :c"), {"c": CHALLENGER})
    session.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE run_label = :c"), {"c": CHALLENGER})
    session.execute(text("DELETE FROM p_score_v2_runs WHERE run_id = :c"), {"c": CHALLENGER})

    # ensemble V : défisc-actif ∩ mono ∩ non-écarté (dans le run champion)
    v_idus = [r[0] for r in session.execute(text(
        "SELECT s.parcelle_id FROM parcel_p_score_v2 s "
        "JOIN defisc_fenetres d ON d.idu = s.parcelle_id AND d.fenetre_active "
        "WHERE s.run_id = :ch AND NOT s.copro AND s.tier <> 'ecartee'"), {"ch": CHAMPION}).all()]

    # 1) run header — computed_at ANTÉRIEUR au champion pour ne jamais devenir le « dernier run » par défaut
    session.execute(text(
        "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, n_parcelles, "
        " duration_s, snapshot_label, computed_at) "
        "SELECT :c, model_version, model_sha256, "
        "       COALESCE(params,'{}'::jsonb) || jsonb_build_object('challenger','Vdefisc','v_cap',:cap), "
        "       n_parcelles, duration_s, 'challenger_Vdefisc', computed_at - interval '1 minute' "
        "FROM p_score_v2_runs WHERE run_id = :ch"), {"c": CHALLENGER, "ch": CHAMPION, "cap": V_CAP})

    # 2) scores — copie VERBATIM du champion ; SEUL p_raw est nudgé (+V_CAP) sur l'ensemble V. tier gelé.
    n_scores = session.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        " contrib_z, contrib_d, top5_contributions, copro, tier, event_date, model_version, computed_at, "
        " icd, icd_detail) "
        "SELECT :c, parcelle_id, "
        "       p_raw + CASE WHEN parcelle_id = ANY(:vids) THEN :cap ELSE 0 END, "
        "       mult_base, percentile, rang, contrib_z, contrib_d, top5_contributions, copro, "
        "       tier, event_date, model_version, computed_at, icd, icd_detail "
        "FROM parcel_p_score_v2 WHERE run_id = :ch"),
        {"c": CHALLENGER, "ch": CHAMPION, "vids": v_idus, "cap": V_CAP}).rowcount

    # 3) dryrun (statut cascade + matrice) — copie VERBATIM → axes boussole statut/matrice identiques
    n_dry = session.execute(text(
        "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, opportunity_score, "
        " opportunity_base, status, rules_version, created_at, q_score, a_score, a_completude, matrice_statut) "
        "SELECT :c, parcel_id, completeness_score, opportunity_score, opportunity_base, status, rules_version, "
        "       created_at, q_score, a_score, a_completude, matrice_statut "
        "FROM dryrun_parcel_evaluations WHERE run_label = :ch"),
        {"c": CHALLENGER, "ch": CHAMPION}).rowcount

    return {"v_parcelles": len(v_idus), "n_scores": n_scores, "n_dryrun": n_dry}


def main():
    with session_scope() as s:
        r = build(s)
    print(f"challenger {CHALLENGER} matérialisé :")
    print(f"  composante V appliquée à {r['v_parcelles']} parcelles (défisc-actif ∩ mono ∩ non-écarté), +{V_CAP} p_raw")
    print(f"  scores copiés : {r['n_scores']} · dryrun copiés : {r['n_dryrun']} (triplet gelé)")
    print(f"\n  juger (garde-fou) : labuse arene --challenger {CHALLENGER} --champion {CHAMPION}")


if __name__ == "__main__":
    main()
