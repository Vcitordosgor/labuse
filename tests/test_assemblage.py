"""Assemblage foncier v1 (Lot C5) — paires contiguës franchissant le seuil, sur PostGIS réel."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import assemblage

pytestmark = pytest.mark.db


def _p(db, idu, wkt, surf):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox, geom_2975) VALUES "
        "(:i,'Asmville','S','1', ST_GeomFromText(:w,4326), :s, ST_Centroid(ST_GeomFromText(:w,4326)), "
        " ST_Envelope(ST_GeomFromText(:w,4326)), ST_Transform(ST_GeomFromText(:w,4326),2975)) RETURNING id"),
        {"i": idu, "w": wkt, "s": surf}).scalar()


def test_paire_contigue_franchit_le_seuil(db_session, monkeypatch):
    monkeypatch.setattr(assemblage, "_params", lambda: {"min_surface_m2": 1000.0, "individuel_max_m2": 1000.0})
    # deux carrés ADJACENTS de ~600 m² chacun (côte à côte) → cumul ~1200 ≥ 1000, chacun < 1000
    a = _p(db_session, "ASM00001", "POLYGON((55.40 -21.00,55.4003 -21.00,55.4003 -20.9997,55.40 -20.9997,55.40 -21.00))", 600)
    _p(db_session, "ASM00002", "POLYGON((55.4003 -21.00,55.4006 -21.00,55.4006 -20.9997,55.4003 -20.9997,55.4003 -21.00))", 600)
    groups = assemblage.find_assemblages(db_session, "Asmville")
    assert any(set(g["parcelles"]) == {"ASM00001", "ASM00002"} and g["surface_cumulee_m2"] >= 1000
               for g in groups)
    u = assemblage.parcel_assemblage(db_session, a)
    assert u["possible"] and u["meilleur_cumul_m2"] >= 1000


def test_parcelle_seule_au_dessus_du_seuil_pas_d_assemblage(db_session, monkeypatch):
    monkeypatch.setattr(assemblage, "_params", lambda: {"min_surface_m2": 1000.0, "individuel_max_m2": 1000.0})
    big = _p(db_session, "ASM00010", "POLYGON((55.50 -21.10,55.5005 -21.10,55.5005 -21.0995,55.50 -21.0995,55.50 -21.10))", 1500)
    u = assemblage.parcel_assemblage(db_session, big)
    assert u["possible"] is False   # déjà au-dessus du seuil seule → pas besoin d'assemblage


def test_parcelles_non_contigues_pas_de_paire(db_session, monkeypatch):
    monkeypatch.setattr(assemblage, "_params", lambda: {"min_surface_m2": 1000.0, "individuel_max_m2": 1000.0})
    _p(db_session, "ASM00020", "POLYGON((55.60 -21.20,55.6003 -21.20,55.6003 -21.1997,55.60 -21.1997,55.60 -21.20))", 600)
    _p(db_session, "ASM00021", "POLYGON((55.70 -21.30,55.7003 -21.30,55.7003 -21.2997,55.70 -21.2997,55.70 -21.30))", 600)
    groups = assemblage.find_assemblages(db_session, "Asmville")
    assert not any(set(g["parcelles"]) == {"ASM00020", "ASM00021"} for g in groups)
