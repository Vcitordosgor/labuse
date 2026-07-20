"""PHASE 0 « Le Juge » — J2 : l'arène (verdict champion / challenger).

Exigence du mandat : l'AVIS bascule bien à **REJETÉ** quand on injecte un faux positif golden
synthétique (le compteur boussole est ÉLIMINATOIRE). `decide_avis` est testé PUR ; le gate boussole
est testé avec un golden + un run challenger synthétiques sur `labuse_test` (transaction rollback).
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.scoring.arene import _golden_boussole, decide_avis


# ───────────────────────── decide_avis (pur) ─────────────────────────

def test_avis_boussole_positive_rejette_eliminatoire():
    # un faux positif servi (boussole > 0) rejette, MÊME avec un RR excellent et un churn nul.
    avis, crit = decide_avis(boussole_compteur=1, rr_chall=99.0, rr_champ=1.0,
                             ece_delta=-0.01, churn_frac=0.0, churn_max=0.25)
    assert avis == "REJETÉ (éliminatoire boussole)"
    assert any("BOUSSOLE" in c for c in crit)


def test_avis_retenu_si_tous_les_criteres_ok():
    avis, crit = decide_avis(0, rr_chall=14.0, rr_champ=13.0, ece_delta=0.0,
                             churn_frac=0.10, churn_max=0.25)
    assert avis == "CHALLENGER RETENU" and crit == []


def test_avis_rejette_si_rr_pas_strictement_superieur():
    avis, crit = decide_avis(0, rr_chall=13.0, rr_champ=13.0, ece_delta=0.0,
                             churn_frac=0.0, churn_max=0.25)
    assert avis == "REJETÉ" and any("RR@" in c for c in crit)


def test_avis_rejette_si_ece_degradee_au_dela_du_seuil():
    avis, crit = decide_avis(0, rr_chall=14.0, rr_champ=13.0, ece_delta=0.02,
                             churn_frac=0.0, churn_max=0.25)
    assert avis == "REJETÉ" and any("ECE" in c for c in crit)


def test_avis_rejette_si_churn_hors_budget():
    avis, crit = decide_avis(0, rr_chall=14.0, rr_champ=13.0, ece_delta=0.0,
                             churn_frac=0.40, churn_max=0.25)
    assert avis == "REJETÉ" and any("churn" in c for c in crit)


def test_avis_baseline_champion_contre_lui_meme():
    avis, _ = decide_avis(0, rr_chall=13.0, rr_champ=13.0, ece_delta=0.0,
                          churn_frac=0.0, churn_max=0.25, is_baseline=True)
    assert avis.startswith("BASELINE")


# ───────────────────────── gate boussole (db, golden synthétique) ─────────────────────────

IDU_FP = "97499000ZZ9001"


def _seed_challenger(session, run_id: str, idu: str, tier: str) -> None:
    session.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:r, :i, 0.9, 30.0, 99.9, 1, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"r": run_id, "i": idu, "t": tier})


def _golden_file(tmp_path) -> str:
    # une parcelle ATTENDUE écartée/exclue (tier ecartee + etage0).
    p = tmp_path / "golden.json"
    p.write_text(json.dumps({"parcelles": {
        IDU_FP: {"db": {"score_v2": {"tier": "ecartee"}, "etage0": True}}}}), encoding="utf-8")
    return str(p)


@pytest.mark.db
def test_boussole_detecte_le_faux_positif_injecte(db_session, tmp_path):
    # INJECTION : le challenger marque BRÛLANTE une parcelle golden attendue écartée → violation.
    _seed_challenger(db_session, "chall-fp", IDU_FP, "brulante")
    res = _golden_boussole(db_session, "chall-fp", _golden_file(tmp_path))
    assert res["compteur"] == 1
    assert res["violations"] == [(IDU_FP, "brulante")]
    # et la décision qui en découle est éliminatoire :
    avis, _ = decide_avis(res["compteur"], 99.0, 1.0, 0.0, 0.0, 0.25)
    assert avis == "REJETÉ (éliminatoire boussole)"


@pytest.mark.db
def test_boussole_zero_si_challenger_respecte_le_verdict(db_session, tmp_path):
    _seed_challenger(db_session, "chall-ok", IDU_FP, "ecartee")   # reste écartée → pas de violation
    res = _golden_boussole(db_session, "chall-ok", _golden_file(tmp_path))
    assert res["compteur"] == 0 and res["violations"] == []
