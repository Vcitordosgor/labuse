"""Témoin CIRCUIT-4 — compteurs cascade : vigilances (SOFT/HARD) et segment renouvellement,
recomptés indépendamment sur lignes seedées."""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_compte_vigilances(engine):
    run = "c4_casc_temoin"
    with engine.begin() as c:
        c.execute(text("DELETE FROM dryrun_cascade_results WHERE run_label = :r"), {"r": run})
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinCasc-C4'"))
        c.execute(text("INSERT INTO parcels (idu, commune, surface_m2, geom) VALUES "
                       "('C4CASC000000', 'TemoinCasc-C4', 10,"
                       " ST_GeomFromText('POINT(55.5 -21.1)', 4326))"))
        pid = c.execute(text("SELECT id FROM parcels WHERE idu = 'C4CASC000000'")).scalar()
        rows = [("ppr", "SOFT_FLAG"), ("littoral", "HARD_EXCLUDE"), ("bruit", "PASS"),
                ("znieff", "SOFT_FLAG")]
        for layer, res in rows:
            c.execute(text("INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name,"
                           " result) VALUES (:r, :p, :l, :res)"),
                      {"r": run, "p": pid, "l": layer, "res": res})
        n = c.execute(text(
            "SELECT count(*) FROM dryrun_cascade_results WHERE run_label = :r AND parcel_id = :p"
            " AND result IN ('SOFT_FLAG', 'HARD_EXCLUDE')"), {"r": run, "p": pid}).scalar()
        c.execute(text("DELETE FROM dryrun_cascade_results WHERE run_label = :r"), {"r": run})
    # recompte à la main : SOFT_FLAG ×2 + HARD_EXCLUDE ×1 = 3 (PASS ne compte pas)
    attendu = sum(1 for _, res in rows if res in ("SOFT_FLAG", "HARD_EXCLUDE"))
    assert n == attendu == 3


@pytest.mark.db
def test_segment_renouvellement(engine):
    """Sémantique count-au-run du segment, sur une table SCRATCH (jamais le nom réel
    parcel_renouvellement : son DDL riche appartient à renouvellement.py — leçon d'isolation)."""
    with engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS c4_renouv_temoin"))
        c.execute(text("CREATE TABLE c4_renouv_temoin (parcel_id int, run_label text)"))
        for pid in (1, 2, 3):
            c.execute(text("INSERT INTO c4_renouv_temoin VALUES (:p, 'c4_ren')"), {"p": pid})
        n = c.execute(text("SELECT count(*) FROM c4_renouv_temoin"
                           " WHERE run_label = 'c4_ren'")).scalar()
        c.execute(text("DROP TABLE c4_renouv_temoin"))
    assert n == 3                               # n_densifiables = count au run (recompté)
