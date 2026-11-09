"""ALGO-FIX-1 (suite) — la persistance : l'endpoint LIT ce que le run a ÉCRIT.

Vérifie, sur la base réelle (q_v20) où la table `parcel_scenario_v2_runs` a été peuplée par
`scripts/algofix1_persist_run.py` :
  · les lignes persistées correspondent au calcul live du moteur (écrit = calculé) ;
  · l'endpoint-lecture (`analyse_payload_persiste`) renvoie le contrat de sortie + effectifs + le
    Signal relayé, sans RIEN recalculer ;
  · le Signal lu = le Signal servi.

LECTURE SEULE (marqueur `reel`). SKIP si la table n'est pas peuplée."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as _Session

from labuse.scoring import scenarios_v2 as v2
from labuse.scoring import scenarios_v2_build as build
from labuse.scoring import scenarios_v2_persist as persist

pytestmark = [pytest.mark.reel]


@pytest.fixture(scope="module")
def db_session():
    url = os.environ.get("LABUSE_REEL_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_REEL_DATABASE_URL non défini")
    eng = create_engine(url)
    conn = eng.connect()
    trans = conn.begin()
    sess = _Session(bind=conn)
    try:
        exists = sess.execute(text(
            "SELECT to_regclass('parcel_scenario_v2_runs')")).scalar()
        if not exists or sess.execute(text(
                "SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label='q_v20'")).scalar() == 0:
            pytest.skip("table parcel_scenario_v2_runs non peuplée (lancer algofix1_persist_run.py)")
        yield sess
    finally:
        sess.close()
        trans.rollback()
        conn.close()
        eng.dispose()


def test_conservation_persistee_sur_toute_l_ile(db_session):
    # La conservation (keep) est écrite pour TOUT le run servi (≈ 433 k).
    n = db_session.execute(text(
        "SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label='q_v20' AND scenario='keep'")
    ).scalar()
    assert n > 400_000


def test_ecrit_egale_calcule(db_session):
    # Pour un échantillon enrichi (Entre-Deux), la ligne persistée = le calcul live.
    idus = [r[0] for r in db_session.execute(text(
        "SELECT idu FROM parcel_scenario_v2_runs WHERE run_label='q_v20' AND scenario='rebuild' "
        "AND enriched AND commune='Entre-Deux' ORDER BY idu LIMIT 30"))]
    assert idus, "aucune reconstruction enrichie à Entre-Deux"
    lus = {r["idu"]: r for r in persist.read_scenarios(
        db_session, run_label="q_v20", scenario="rebuild", idus=idus)}
    ids = [r[0] for r in db_session.execute(
        text("SELECT id FROM parcels WHERE idu = ANY(:i)"), {"i": idus})]
    for rec, _ in build.records_for_parcels(db_session, ids, run_label="q_v20", enrich=True):
        live = v2.evaluate(rec, {"mode": "potential", "scenario": "rebuild"})
        lu = lus.get(rec.id)
        assert lu is not None
        assert lu["statut"] == live.status
        assert lu["bande"] == live.band
        assert lu["quantites"]["net_signed"] == (None if live.quantities["net_signed"] is None
                                                 else round(live.quantities["net_signed"]))


def test_endpoint_lecture_contrat_et_effectifs(db_session):
    pl = persist.analyse_payload_persiste(
        db_session, run_label="q_v20", mode="potential", scenario="keep",
        sort="capacity", commune="Entre-Deux", limit=50, offset=0, as_of="2026-11-09T00:00:00Z")
    assert pl["source_donnees"] == "run_persiste"
    assert pl["n_selection"] > 6000
    assert sum(pl["effectifs"]["par_statut"].values()) == pl["n_selection"]
    # Tri D10 : groupe de statut croissant, puis quantité décroissante dans ESTIMATED.
    est = [p for p in pl["parcelles"] if p["statut"] == "ESTIMATED" and p["quantites"]["additional"]]
    vals = [p["quantites"]["additional"] for p in est]
    assert vals == sorted(vals, reverse=True) or len(vals) < 2
    # contrat par parcelle présent
    p0 = pl["parcelles"][0]
    for k in ("idu", "statut", "cause", "bande", "quantites", "vigilance", "signal"):
        assert k in p0


def test_signal_lu_egale_signal_servi(db_session):
    sample = persist.read_scenarios(db_session, run_label="q_v20", scenario="keep",
                                    commune="Entre-Deux")[:100]
    for row in sample:
        servi = db_session.execute(text(
            "SELECT signal_p, signal_niveau FROM score_labuse WHERE run_label='q_v20' AND idu=:i"),
            {"i": row["idu"]}).fetchone()
        if servi and servi[0] is not None:
            assert row["signal"]["p"] == servi[0]
            assert row["signal"]["niveau"] == servi[1]
            assert row["signal"]["status"] == "AVAILABLE"
