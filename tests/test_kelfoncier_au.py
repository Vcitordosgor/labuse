"""KELFONCIER-FIX-1 (Lot A) — statut d'ouverture des zones AU exposé en clair.

Le moteur `parcel_au_statut` était peuplé mais jamais servi en clair. On l'expose : fiche §4
(`_au_ouverture_block`), cause §10 (bloquant), et le crible Pièges & risques (`contraintes_parcelle`
partagé parcelle/lot/fiche). La classe `declasse_au_fermee` est BLOQUANTE (modification du PLU requise).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.5 -21.3,55.5003 -21.3,55.5003 -21.2997,55.5 -21.2997,55.5 -21.3))"


def _seed(db, idu, classe, zone_lib, motif):
    pid = db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'AUVille','S','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 1200,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()
    db.execute(text(
        "INSERT INTO parcel_au_statut (parcel_id, idu, classe, zone_lib, motif) VALUES (:p,:i,:c,:z,:m)"),
        {"p": pid, "i": idu, "c": classe, "z": zone_lib, "m": motif})
    return pid


def test_au_ouverture_block_conditionnelle(db_session):
    from labuse.api.app import _au_ouverture_block
    idu = "97499000AU0001"
    _seed(db_session, idu, "conditionnelle_operation", "AU1est", "Zone à urbaniser — ouverture conditionnée…")
    b = _au_ouverture_block(db_session, idu)
    assert b is not None
    assert b["classe"] == "conditionnelle_operation"
    assert "opération d'aménagement d'ensemble" in b["statut"]
    assert b["bloquant"] is False and b["zone_lib"] == "AU1est"
    assert "conditionnée" in (b["motif"] or "")


def test_au_ouverture_block_fermee_est_bloquant(db_session):
    from labuse.api.app import _au_ouverture_block
    idu = "97499000AU0002"
    _seed(db_session, idu, "declasse_au_fermee", "2AUst", "réserve foncière (2AU)")
    b = _au_ouverture_block(db_session, idu)
    assert b["bloquant"] is True
    assert "fermée" in b["statut"] and "modification du PLU" in b["statut"]


def test_au_absente_hors_zone_au(db_session):
    from labuse.api.app import _au_ouverture_block
    # parcelle non AU (aucune ligne parcel_au_statut) → None (jamais un statut inventé)
    db_session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "('97499000NN0003','AUVille','S','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 900,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"w": _WKT})
    assert _au_ouverture_block(db_session, "97499000NN0003") is None


def test_pieges_crible_inclut_au_fermee(db_session):
    """La contrainte « AU fermée » entre dans le crible PARTAGÉ (parcelle · lot · fiche §Pièges)."""
    from labuse.api.servitudes import contraintes_parcelle
    idu = "97499000AU0004"
    _seed(db_session, idu, "declasse_au_fermee", "AUp1", "réserve foncière")
    items = contraintes_parcelle(db_session, idu)
    au = [x for x in items if x["categorie"] == "Zone à urbaniser (AU)"]
    assert au and "FERMÉE" in au[0]["effet"]
