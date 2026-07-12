"""Tests API scoring v2 + idempotence du job (M5 lot 6.1)."""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from labuse.api import score_v2 as api_v2

pytestmark = pytest.mark.db

RUN = "test-m5-run"


def _seed(session):
    session.execute(text("""
        INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, n_parcelles)
        VALUES (:r, 'm36-l2f-2026', 'abc', '{"n_entree": 10}', 3)"""), {"r": RUN})
    rows = [
        ("97411000AB0001", 0.5, 21.0, 99.9, 1, "brulante", False),
        ("97411000AB0002", 0.02, 1.2, 60.0, 2, "a_creuser", False),
        ("97411000AB0003", 0.4, 18.0, None, None, "a_creuser", True),   # copro
    ]
    for idu, p, m, pct, rg, tier, copro in rows:
        session.execute(text("""
            INSERT INTO parcel_p_score_v2
                (run_id, parcelle_id, p_raw, mult_base, percentile, rang, contrib_z,
                 contrib_d, top5_contributions, copro, tier, model_version)
            VALUES (:r, :i, :p, :m, :pct, :rg, 0.2, 1.5,
                    '[{"feature": "permis_bin", "bin": "<2a", "signe": "+",
                       "libelle": "ancienneté du dernier permis", "log_hazard": 1.3}]',
                    :c, :t, 'm36-l2f-2026')"""),
            {"r": RUN, "i": idu, "p": p, "m": m, "pct": pct, "rg": rg,
             "t": tier, "c": copro})
    session.flush()


def test_score_endpoint_sans_proba_brute(db_session):
    _seed(db_session)
    out = api_v2.score_parcelle("97411000AB0001", db_session)
    assert out["mult_base"] == 21.0 and out["rang"] == 1
    assert out["tier"] == "brulante"
    assert "p_raw" not in out                      # JAMAIS la probabilité brute
    assert out["pourquoi"][0]["libelle"] == "ancienneté du dernier permis"
    assert "retard" in out["avertissement"]        # avertissement censure


def test_score_endpoint_404_inconnue(db_session):
    _seed(db_session)
    with pytest.raises(HTTPException) as e:
        api_v2.score_parcelle("97499000ZZ9999", db_session)
    assert e.value.status_code == 404


def test_liste_exclut_copro_par_defaut(db_session):
    _seed(db_session)
    out = api_v2.liste(tier=None, commune=None, include_copro=False,
                       limit=100, offset=0, db=db_session)
    idus = {i["parcelle_id"] for i in out["items"]}
    assert "97411000AB0003" not in idus            # copro hors univers par défaut
    out2 = api_v2.liste(tier=None, commune=None, include_copro=True,
                        limit=100, offset=0, db=db_session)
    assert "97411000AB0003" in {i["parcelle_id"] for i in out2["items"]}
    assert [i["rang"] for i in out["items"]] == sorted(
        [i["rang"] for i in out["items"]])          # tri par rang


def test_brulantes_et_badges(db_session):
    _seed(db_session)
    out = api_v2.brulantes(db_session)
    assert out["n"] == 1 and out["items"][0]["parcelle_id"] == "97411000AB0001"
    copro_row = api_v2.score_parcelle("97411000AB0003", db_session)
    assert copro_row["badges"]["copro"] is True


def test_job_refuse_run_existant(db_session):
    """Idempotence (lot 1.2/6.1) : un run_id déjà présent est REFUSÉ avant tout
    calcul — aucun écrasement silencieux."""
    _seed(db_session)
    from labuse.scoring.p_v2.pipeline import run_score_v2
    with pytest.raises(RuntimeError, match="existe déjà"):
        run_score_v2(db_session, run_id=RUN, rebuild=False, snapshot=False)
