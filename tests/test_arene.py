"""PHASE 0 « Le Juge » — J2 / J2-bis : l'arène (verdict champion / challenger).

Exigences : (1) l'AVIS bascule à REJETÉ sur un faux positif golden injecté (boussole ÉLIMINATOIRE) ;
(2) le critère RR repose sur un IC95 APPARIÉ de la différence (ΔRR) qui doit exclure zéro ;
(3) CANARI de dégradation — un challenger dégradé (scores partiellement permutés) est bien REJETÉ,
prouvant que la chaîne différentielle détecte une vraie perte de performance, pas que le gate boussole.
"""
from __future__ import annotations

import json

import numpy as np
import pytest
from sqlalchemy import text

from labuse.scoring.arene import _golden_boussole, decide_avis, paired_bootstrap_diff


# ───────────────────────── decide_avis (pur) — critère RR = IC apparié exclut zéro ─────────────────────────

def test_avis_boussole_positive_rejette_eliminatoire():
    # un faux positif servi (boussole > 0) rejette, MÊME avec un ΔRR très significatif.
    avis, crit = decide_avis(boussole_compteur=1, rr_diff_ic_low=5.0,
                             ece_delta=-0.01, churn_frac=0.0, churn_max=0.25)
    assert avis == "REJETÉ (éliminatoire boussole)"
    assert any("BOUSSOLE" in c for c in crit)


def test_avis_retenu_si_diff_significative_et_reste_ok():
    avis, crit = decide_avis(0, rr_diff_ic_low=0.5, ece_delta=0.0, churn_frac=0.10, churn_max=0.25)
    assert avis == "CHALLENGER RETENU" and crit == []


def test_avis_rejette_si_diff_rr_non_significative():
    # IC apparié de ΔRR = borne basse ≤ 0 → pas fiablement meilleur → REJETÉ (les deux cas).
    for ic_low in (0.0, -1.5):
        avis, crit = decide_avis(0, rr_diff_ic_low=ic_low, ece_delta=0.0, churn_frac=0.0, churn_max=0.25)
        assert avis == "REJETÉ" and any("RR@" in c for c in crit)


def test_avis_rejette_si_ece_degradee():
    avis, crit = decide_avis(0, rr_diff_ic_low=1.0, ece_delta=0.02, churn_frac=0.0, churn_max=0.25)
    assert avis == "REJETÉ" and any("ECE" in c for c in crit)


def test_avis_rejette_si_churn_hors_budget():
    avis, crit = decide_avis(0, rr_diff_ic_low=1.0, ece_delta=0.0, churn_frac=0.40, churn_max=0.25)
    assert avis == "REJETÉ" and any("churn" in c for c in crit)


def test_avis_baseline_champion_contre_lui_meme():
    avis, _ = decide_avis(0, rr_diff_ic_low=0.0, ece_delta=0.0, churn_frac=0.0,
                          churn_max=0.25, is_baseline=True)
    assert avis.startswith("BASELINE")


# ───────────────────────── bootstrap apparié + CANARI de dégradation (pur, numpy) ─────────────────────────

def _synthetic(n: int = 4000, seed: int = 0):
    """Champion informatif : label corrélé au score → le champion range bien les mutations."""
    rng = np.random.RandomState(seed)
    champ = rng.random(n)
    y = (rng.random(n) < 0.02 + 0.10 * champ).astype(int)
    return y, champ


def test_paired_diff_runs_identiques_non_significatif():
    y, champ = _synthetic()
    d = paired_bootstrap_diff(y, champ, champ, k=200, n_boot=300)
    assert abs(d["diff_rr"]) < 1e-9        # A == B → ΔRR = 0
    assert d["significatif"] is False      # IC contient zéro → pas d'amélioration


def test_canari_degradation_bascule_a_rejete():
    # challenger = champion DÉGRADÉ (50 % des scores permutés = bruit) → range moins bien.
    y, champ = _synthetic()
    rng = np.random.RandomState(1)
    chall = champ.copy()
    m = rng.random(len(chall)) < 0.5
    chall[m] = rng.permutation(chall[m])
    d = paired_bootstrap_diff(y, chall, champ, k=200, n_boot=300)
    assert d["diff_rr"] < 0                 # dégradation réelle : ΔRR négatif
    assert d["ic95_bas"] <= 0               # non significativement positif
    avis, crit = decide_avis(0, d["ic95_bas"], ece_delta=0.0, churn_frac=0.0, churn_max=0.25)
    assert avis == "REJETÉ" and any("RR@" in c for c in crit)


# ───────────────────────── gate boussole (db, golden synthétique injecté) ─────────────────────────

IDU_FP = "97499000ZZ9001"


def _seed_challenger(session, run_id: str, idu: str, tier: str) -> None:
    session.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:r, :i, 0.9, 30.0, 99.9, 1, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"r": run_id, "i": idu, "t": tier})


def _golden_file(tmp_path) -> str:
    p = tmp_path / "golden.json"
    p.write_text(json.dumps({"parcelles": {
        IDU_FP: {"db": {"score_v2": {"tier": "ecartee"}, "etage0": True}}}}), encoding="utf-8")
    return str(p)


@pytest.mark.db
def test_boussole_detecte_le_faux_positif_injecte(db_session, tmp_path):
    _seed_challenger(db_session, "chall-fp", IDU_FP, "brulante")     # golden écartée → brûlante = violation
    res = _golden_boussole(db_session, "chall-fp", _golden_file(tmp_path))
    assert res["compteur"] == 1 and res["violations"] == [(IDU_FP, "brulante")]
    avis, _ = decide_avis(res["compteur"], 99.0, 0.0, 0.0, 0.25)
    assert avis == "REJETÉ (éliminatoire boussole)"


@pytest.mark.db
def test_boussole_zero_si_challenger_respecte_le_verdict(db_session, tmp_path):
    _seed_challenger(db_session, "chall-ok", IDU_FP, "ecartee")
    res = _golden_boussole(db_session, "chall-ok", _golden_file(tmp_path))
    assert res["compteur"] == 0 and res["violations"] == []
