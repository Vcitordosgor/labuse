"""O10 — SURFACE D (moteur) : construction de surface_d_events depuis les badges datés.

Sources absentes → 0 (guardé, jamais un crash) ; défisc/caducs branchés ; dédup par (idu,type,date).
Le moteur seulement — la notification est post-M7.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import surface_d as sd


_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def test_event_types_declares():
    assert "entree_fenetre_defisc" in sd.EVENT_TYPES and "pc_caduc" in sd.EVENT_TYPES
    assert "dpe_passoire" in sd.EVENT_TYPES and "permis_octroye" in sd.EVENT_TYPES


@pytest.mark.db
def test_build_defisc_et_caduc_branches(db_session):
    s = db_session
    idu = "97499000SD0001"
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','SD','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": _WKT})
    # badges minimaux
    s.execute(text("CREATE TABLE IF NOT EXISTS defisc_fenetres (idu varchar(14), fenetre_debut int, "
                   "fenetre_active boolean, libelle_court text, source_libelle text)"))
    s.execute(text("INSERT INTO defisc_fenetres (idu, fenetre_debut, fenetre_active, libelle_court, source_libelle) "
                   "VALUES (:i, 2028, true, 'Fenêtre défisc', 'defisc')"), {"i": idu})
    s.execute(text("CREATE TABLE IF NOT EXISTS pc_caducs (idu varchar(14), caduc_depuis int, libelle_court text)"))
    s.execute(text("INSERT INTO pc_caducs (idu, caduc_depuis, libelle_court) VALUES (:i, 2020, 'PC caduc')"), {"i": idu})

    r = sd.build_events(s, commit=False, log=lambda *_: None)
    assert r["par_type"]["entree_fenetre_defisc"] == 1 and r["par_type"]["pc_caduc"] == 1
    # sources absentes en base de test → 0, jamais un crash
    assert r["par_type"]["dpe_passoire"] == 0
    ev = {e["type"]: e for e in sd.recent_events(s, limit=10)}
    assert ev["entree_fenetre_defisc"]["idu"] == idu
    assert str(ev["pc_caduc"]["date_evenement"]) == "2020-01-01"


@pytest.mark.db
def test_dedup_meme_idu_type_date(db_session):
    s = db_session
    idu = "97499000SD0002"
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','SD','2', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": _WKT})
    s.execute(text("CREATE TABLE IF NOT EXISTS pc_caducs (idu varchar(14), caduc_depuis int, libelle_court text)"))
    # deux lignes même parcelle/année → une seule entrée (contrainte UNIQUE)
    s.execute(text("INSERT INTO pc_caducs (idu, caduc_depuis, libelle_court) VALUES (:i, 2020, 'a'), (:i, 2020, 'b')"), {"i": idu})
    r = sd.build_events(s, commit=False, log=lambda *_: None)
    assert r["par_type"]["pc_caduc"] == 1
