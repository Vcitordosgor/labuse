"""Témoin CIRCUIT-4 — point mort : recompte indépendant sur lignes seedées (permis PC ancien sans
DAACT, parcelle non bâtie au run servi)."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_point_mort_temoin(engine):
    from labuse.registre.moteurs.commune import permis_point_mort
    run = "c4_run_temoin"
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcels WHERE commune = 'TemoinPM-C4'"))
        c.execute(text("DELETE FROM sitadel_permits WHERE commune = 'TemoinPM-C4'"))
        c.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE run_label = :r"), {"r": run})
        c.execute(text("DELETE FROM dryrun_cascade_results WHERE run_label = :r"), {"r": run})
        # 2 parcelles : P0 nue, P1 bâtie (HARD_EXCLUDE bati au run)
        for i in range(2):
            c.execute(text(
                "INSERT INTO parcels (idu, commune, surface_m2, geom) VALUES "
                "(:i, 'TemoinPM-C4', 100, ST_GeomFromText('POINT(55.5 -21.1)', 4326))"),
                {"i": f"C4PM000000{i}"})
        ids = {r[0]: r[1] for r in c.execute(text(
            "SELECT idu, id FROM parcels WHERE commune = 'TemoinPM-C4'")).all()}
        for idu, pid in ids.items():
            c.execute(text("INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, opportunity_score)"
                           " VALUES (:r, :p, 1.0, 0.5)"), {"r": run, "p": pid})
        c.execute(text(
            "INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name, result)"
            " VALUES (:r, :p, 'bati', 'HARD_EXCLUDE')"), {"r": run, "p": ids["C4PM0000001"]})
        # 3 permis PC vieux de 3 ans : sur P0 (compte), sur P1 (bâtie → non), un avec DAACT (→ non)
        for idu, raw in (("C4PM0000000", {}), ("C4PM0000001", {}),
                         ("C4PM0000000", {"daact": "2024-01-01"})):
            c.execute(text(
                "INSERT INTO sitadel_permits (commune, type, date, idu_codes, raw) VALUES"
                " ('TemoinPM-C4', 'PC', now() - interval '36 months', :idus, :raw)"),
                {"idus": json.dumps([idu]), "raw": json.dumps(raw)})
        n = permis_point_mort(c, "TemoinPM-C4", months=24, run=run)
    # recompte indépendant : seul le permis sans DAACT sur la parcelle NON bâtie compte → 1
    assert n == 1
