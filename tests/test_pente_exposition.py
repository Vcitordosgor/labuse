"""2.A — pente (SOFT_FLAG > seuil) + exposition (aspect RGE ALTI) + majoration VRD du bilan."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db


def _parcel(db, idu, wkt):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "(:i,'Pentia','S','1', ST_GeomFromText(:w,4326), 1000, ST_Centroid(ST_GeomFromText(:w,4326)),"
        " ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"), {"i": idu, "w": wkt}).scalar()


def _pente(db, wkt, slope):
    db.execute(text(
        "INSERT INTO spatial_layers (kind, name, commune, geom, attrs) VALUES "
        "('pente','grille','Pentia', ST_GeomFromText(:w,4326), CAST(:a AS jsonb))"),
        {"w": wkt, "a": f'{{"slope_pct": {slope}}}'})


def test_pente_forte_soft_flag_pas_exclusion(db_session):
    from labuse.cascade import evaluate_parcels
    from labuse.enums import CascadeVerdict, Severity
    cell = "POLYGON((55.40 -21.00,55.41 -21.00,55.41 -20.99,55.40 -20.99,55.40 -21.00))"
    _pente(db_session, cell, 45)
    pid = _parcel(db_session, "PEN00001",
                  "POLYGON((55.4010 -20.9990,55.4020 -20.9990,55.4020 -20.9980,55.4010 -20.9980,55.4010 -20.9990))")
    out = evaluate_parcels([pid], db_session, persist=False)[0]
    v = next((x for x in out.verdicts if x.layer_name == "pente"), None)
    assert v and v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.MOYEN
    assert "pente forte" in v.detail.lower()
    assert not any(x.is_hard_exclude() for x in out.verdicts)   # jamais une exclusion


def test_pente_faible_pass(db_session):
    from labuse.cascade import evaluate_parcels
    from labuse.enums import CascadeVerdict
    cell = "POLYGON((55.50 -21.10,55.51 -21.10,55.51 -21.09,55.50 -21.09,55.50 -21.10))"
    _pente(db_session, cell, 8)
    pid = _parcel(db_session, "PEN00002",
                  "POLYGON((55.5010 -21.0990,55.5020 -21.0990,55.5020 -21.0980,55.5010 -21.0980,55.5010 -21.0990))")
    out = evaluate_parcels([pid], db_session, persist=False)[0]
    v = next((x for x in out.verdicts if x.layer_name == "pente"), None)
    assert v and v.result == CascadeVerdict.PASS


def test_exposition_cardinal(db_session, monkeypatch):
    from labuse.api import enrichment as E
    pid = _parcel(db_session, "PEN00003",
                  "POLYGON((55.60 -21.20,55.601 -21.20,55.601 -21.199,55.60 -21.199,55.60 -21.20))")
    monkeypatch.setattr(E, "_live_enabled", lambda: True)
    # ordre des points : N, S, E, W. Ouest plus bas → la pente FAIT FACE à l'Ouest.
    monkeypatch.setattr(E, "_alti_query", lambda pts, t: [110.0, 110.0, 130.0, 100.0])  # hN,hS,hE,hW
    r = E.exposition(db_session, pid)
    assert r["available"] and r["exposition"] == "Ouest" and 255 <= r["azimut_deg"] <= 285


def test_bilan_majoration_pente_conditionnee():
    from labuse.faisabilite.bilan import compute_bilan
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses()
    prix = {"fiable": True, "fiabilite": "fiable", "fiabilite_raisons": [], "type_prix": "appartement",
            "n": 40, "n_exclus": 0, "n_doublons": 0, "radius_m": 1500.0, "commune_fallback": False,
            "pct_appartement": 100, "periode": [2022, 2025], "q1": 2200, "median": 3000, "q3": 4300,
            "min": 2000, "max": 4700}
    bp = {"cout_vrd_base": 60, "majoration_vrd_pente_pct": 25}
    plat = compute_bilan(4600, 4500, prix, h, contexte_eco={"pente_pct": 5}, bilan_params=bp)
    pentu = compute_bilan(4600, 4500, prix, h, contexte_eco={"pente_pct": 35}, bilan_params=bp)
    assert plat.calc["cout_vrd"] == round(60 * 4500)                 # pente < 15 → pas de majoration
    assert pentu.calc["cout_vrd"] == round(60 * 1.25 * 4500)         # pente ≥ 15 → +25 %
