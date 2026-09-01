"""CONNEXIONS-2 Lot 1 (KO-1) — la cascade SERVIE aux documents lit le run ÉPINGLÉ, jamais un
run périmé codé en dur.

Régression du bug : `served_cascade.py` figeait `_DEFAULT_RUN = "q_v8_calibre"` (3 runs en arrière)
et ses appelants (Dossier, Lettre zonage, Pré-dossier PC, Finance, Argumentaire) appelaient
`served_cascade_lines(db, idu)` SANS run → repli silencieux sur le vieux run, en contradiction avec
l'écran (q_v11_m137). Ce test échoue sur l'ancien code : il seed la cascade sous le run SERVI et un
LEURRE sous q_v8_calibre, puis vérifie que l'appel SANS run rend la ligne du run servi, pas le leurre.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api.served_cascade import served_cascade_lines
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL

pytestmark = pytest.mark.db


_WKT = "POLYGON((55.46 -20.92,55.461 -20.92,55.461 -20.921,55.46 -20.921,55.46 -20.92))"


def _seed_parcel(s, idu):
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()


def _seed_cascade(s, pid, run, layer, result, detail):
    s.execute(text(
        "INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name, result, detail) "
        "VALUES (:run,:p,:l,:r,:d)"),
        {"run": run, "p": pid, "l": layer, "r": result, "d": detail})


def test_default_run_est_le_run_servi_pas_q_v8(db_session):
    s = db_session
    idu = "97499000SC0001"
    pid = _seed_parcel(s, idu)
    _seed_cascade(s, pid, Q_A_RUN_LABEL, "zonage_plu_gpu", "PASS", "Zone U — servi")
    _seed_cascade(s, pid, "q_v8_calibre", "zonage_plu_gpu", "HARD_EXCLUDE", "LEURRE run périmé")

    lignes = served_cascade_lines(s, idu)   # SANS run explicite → doit prendre Q_A_RUN_LABEL
    details = [l["detail"] for l in lignes]
    assert any("servi" in (d or "") for d in details)
    assert not any("LEURRE" in (d or "") for d in details), \
        "served_cascade a servi le run périmé q_v8_calibre au lieu du run épinglé"


def test_run_explicite_respecte(db_session):
    s = db_session
    idu = "97499000SC0002"
    pid = _seed_parcel(s, idu)
    _seed_cascade(s, pid, Q_A_RUN_LABEL, "zonage_plu_gpu", "PASS", "Zone U — servi")
    assert served_cascade_lines(s, idu, Q_A_RUN_LABEL)
    assert served_cascade_lines(s, idu, "run_inexistant") == []
