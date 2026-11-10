"""FRAICHEUR-FIX-1 (point 3) — INPI RNE : une tâche de chargement PLANIFIÉE + une SENTINELLE ;
la date servie à l'écran Successions vient de la DONNÉE (max ingested_at), pas du catalogue."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import text


def test_inpi_job_et_sentinelle():
    from labuse import jobs, jobs_impl, sentinelle
    # (1) tâche de chargement PLANIFIÉE au registre
    j = jobs.JOBS["ingest-inpi-rne"]
    assert j.touche == "eau" and j.planifie and j.gel is None
    assert j.famille == 2 and callable(getattr(jobs_impl, "ingest_inpi_rne", None))
    # (2) une SENTINELLE (rappel de cadence sur la fraîcheur réelle)
    noms_rappel = {r["name"] for r in sentinelle.RAPPELS_MANUELS}
    assert "INPI RNE (dirigeants)" in noms_rappel


@pytest.mark.db
def test_ecran_successions_date_vient_de_la_donnee(db_session):
    from labuse.api import modules
    s = db_session
    s.execute(text("DELETE FROM pm_dirigeants"))
    # données réellement ingérées : max ingested_at = 05/07/2026
    for d in (datetime(2026, 7, 5, tzinfo=timezone.utc), datetime(2026, 6, 1, tzinfo=timezone.utc)):
        s.execute(text("INSERT INTO pm_dirigeants (siren, ingested_at) VALUES ('111222333', :t)"),
                  {"t": d})
    # catalogue DÉLIBÉRÉMENT divergent (ancienne faille : l'écran montrait cette date)
    sid = s.execute(text("SELECT id FROM data_sources WHERE name='INPI RNE (dirigeants)'")).scalar()
    if sid is None:
        s.execute(text("INSERT INTO data_sources (name, status, last_sync_at) "
                       "VALUES ('INPI RNE (dirigeants)','connecte','2026-10-06')"))
    else:
        s.execute(text("UPDATE data_sources SET last_sync_at='2026-10-06' WHERE id=:i"), {"i": sid})

    out = modules._calcul_successions(s, None, 0, 200, 0)
    # la date servie suit la DONNÉE (05/07/2026), jamais le catalogue (06/10/2026)
    assert out["rne_sync"] == "05/07/2026"
