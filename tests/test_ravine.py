"""Ravines (Lot C1) — couche cascade de proximité, sur PostGIS réel.

Vérifie : SOFT_FLAG sous le buffer, PASS au-delà, UNKNOWN si non ingéré, et que la ravine
n'exclut JAMAIS seule (proximité = recul à vérifier, pas une inconstructibilité).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.cascade import evaluate_parcels
from labuse.enums import CascadeVerdict, Severity

pytestmark = pytest.mark.db


def _seed_parcel(db, idu, wkt):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "(:i,'Ravinia','S','1', ST_GeomFromText(:w,4326), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": wkt}).scalar()


def _ravine(db, wkt):
    db.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, commune, geom, attrs) VALUES "
        "('ravine','ravine','Ravine Test','Ravinia', ST_GeomFromText(:w,4326), '{\"nature\":\"Ravine\"}'::jsonb)"),
        {"w": wkt})


def _ravine_verdict(out):
    return next((v for v in out.verdicts if v.layer_name == "ravine"), None)


def test_proximite_ravine_soft_flag(db_session):
    """Parcelle traversée par une ravine → SOFT_FLAG moyen, jamais une exclusion."""
    _ravine(db_session, "LINESTRING(55.400 -21.000, 55.401 -21.000)")
    pid = _seed_parcel(db_session, "RAV00001",
                       "POLYGON((55.4000 -21.0005,55.4010 -21.0005,55.4010 -20.9995,55.4000 -20.9995,55.4000 -21.0005))")
    out = evaluate_parcels([pid], db_session, persist=False)[0]
    v = _ravine_verdict(out)
    assert v and v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.MOYEN
    assert "ravine" in v.detail.lower()
    assert not any(x.is_hard_exclude() for x in out.verdicts)   # jamais excluante seule


def test_parcelle_loin_de_ravine_pass(db_session):
    """Ravine à > buffer (10 m) → PASS (hors voisinage immédiat)."""
    _ravine(db_session, "LINESTRING(55.500 -21.100, 55.501 -21.100)")
    # parcelle ~200 m plus loin
    pid = _seed_parcel(db_session, "RAV00002",
                       "POLYGON((55.5000 -21.1030,55.5010 -21.1030,55.5010 -21.1020,55.5000 -21.1020,55.5000 -21.1030))")
    out = evaluate_parcels([pid], db_session, persist=False)[0]
    v = _ravine_verdict(out)
    assert v and v.result == CascadeVerdict.PASS


def test_ravine_non_ingeree_unknown(db_session):
    """Aucune ravine ingérée → UNKNOWN (impacte la complétude, ne pénalise pas)."""
    pid = _seed_parcel(db_session, "RAV00003",
                       "POLYGON((55.600 -21.200,55.601 -21.200,55.601 -21.199,55.600 -21.199,55.600 -21.200))")
    out = evaluate_parcels([pid], db_session, persist=False)[0]
    v = _ravine_verdict(out)
    assert v and v.result == CascadeVerdict.UNKNOWN


def test_berge_mesuree_au_bord_quand_surface(db_session):
    """2.C : ravine large avec surface en eau → distance mesurée AU BORD (berge), plus proche."""
    from labuse.cascade import evaluate_parcels
    from labuse.enums import CascadeVerdict
    # axe de ravine à ~18 m de la parcelle (dans le rayon de garde), MAIS une surface en eau
    # (le lit) au contact (~1 m). 1e-4° lon ≈ 10 m à cette latitude.
    _ravine(db_session, "LINESTRING(55.70000 -21.000, 55.70000 -21.010)")   # axe vertical à l'ouest
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, commune, geom) VALUES "
        "('water','riviere','lit ravine','Ravinia',"
        " ST_GeomFromText('POLYGON((55.70010 -21.005,55.70016 -21.005,55.70016 -21.004,55.70010 -21.004,55.70010 -21.005))',4326))"))
    pid = _seed_parcel(db_session, "RAV00010",
                       "POLYGON((55.70017 -21.0048,55.70019 -21.0048,55.70019 -21.0042,55.70017 -21.0042,55.70017 -21.0048))")
    out = evaluate_parcels([pid], db_session, persist=False)[0]
    v = _ravine_verdict(out)
    assert v and v.result == CascadeVerdict.SOFT_FLAG
    assert "berge" in v.detail.lower() and "au bord" in v.detail.lower()
