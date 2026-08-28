"""ÉTUDE DE ZONE · Z5 — recette (rapport PDF + parcours /flash par adresse + cas limites).

Cas limites du mandat gelés ici : PDF rendu depuis l'agrégat · zone indisponible = pas de rapport
(422, jamais un PDF vide) · /flash trouve la parcelle depuis une ADRESSE · adresse introuvable dite
honnêtement · NAF sans concurrent = digne. Données de test préfixées [ZONE-TEST], purgées.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import zone as Z
from labuse.api.app import app, etude_zone, etude_zone_pdf, EtudeZoneIn
from labuse.db import session_scope

pytestmark = pytest.mark.db

_LON, _LAT = 55.6500, -20.9600


def _carre(demi: float) -> dict:
    x0, x1, y0, y1 = _LON - demi, _LON + demi, _LAT - demi, _LAT + demi
    return {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}


def _seed_parcel_polygone(s, idu, demi=0.001):
    x0, x1, y0, y1 = _LON - demi, _LON + demi, _LAT - demi, _LAT + demi
    wkt = f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "(:i,'Saint-André','S','1', ST_GeomFromText(:w,4326), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
        {"i": idu, "w": wkt})


def test_pdf_rendu_depuis_l_agregat(monkeypatch):
    monkeypatch.setattr(Z, "fetch_isochrone", lambda lon, lat, minutes, mode, *, client: _carre(0.03))
    idu = "ZONETEST000010"
    with session_scope() as s:
        _seed_parcel_polygone(s, idu)
        resp = etude_zone_pdf(EtudeZoneIn(idu=idu, minutes=10, mode="voiture", titre="12 rue de la Gare"), db=s)
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM zone_isochrone_cache WHERE cache_key LIKE 'voiture|%'"))
    assert resp.media_type == "application/pdf"
    assert bytes(resp.body).startswith(b"%PDF"), "un vrai PDF est rendu"


def test_pdf_zone_indisponible_pas_de_rapport(monkeypatch):
    def _boom(lon, lat, minutes, mode, *, client):
        raise RuntimeError("IGN down")
    monkeypatch.setattr(Z, "fetch_isochrone", _boom)
    idu = "ZONETEST000011"
    with session_scope() as s:
        _seed_parcel_polygone(s, idu)
        with pytest.raises(Exception) as exc:   # HTTPException 422 — pas de PDF sur une zone non tracée
            etude_zone_pdf(EtudeZoneIn(idu=idu, minutes=10, mode="voiture"), db=s)
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    assert "422" in str(exc.value) or "indisponible" in str(exc.value).lower()


def test_naf_sans_concurrent_reste_digne(monkeypatch):
    monkeypatch.setattr(Z, "fetch_isochrone", lambda lon, lat, minutes, mode, *, client: _carre(0.03))
    idu = "ZONETEST000012"
    with session_scope() as s:
        Z.ensure_tables(s)
        from labuse.ingestion.sirene_etablissements import ensure_tables as se_ens
        se_ens(s)
        _seed_parcel_polygone(s, idu)
        out = etude_zone(EtudeZoneIn(idu=idu, naf="9602A", minutes=10, mode="voiture"), db=s)  # coiffure, aucun semé
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM zone_isochrone_cache WHERE cache_key LIKE 'voiture|%'"))
    assert out["zone_disponible"] is True
    assert out["concurrents"]["n"] == 0, "aucun concurrent : compté à zéro, pas d'invention"
    assert out["habitants_par_concurrent"] is None, "pas de ratio quand il n'y a personne à diviser"


def test_flash_par_adresse_trouve_la_parcelle(monkeypatch):
    idu = "ZONETEST000013"
    with session_scope() as s:
        _seed_parcel_polygone(s, idu)
    import labuse.api.scoreur as sc
    monkeypatch.setattr(sc, "_geocode", lambda q: {"lon": _LON, "lat": _LAT, "label": q})
    client = TestClient(app)
    r = client.get("/flash", params={"q": "12 rue de la Gare, Saint-André"})
    with session_scope() as s:
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    assert r.status_code == 200
    assert "Votre rapport Flash" in r.text, "l'adresse résout la parcelle → écran de confirmation"
    assert "Saint-André" in r.text


def test_flash_adresse_introuvable_dit_honnete(monkeypatch):
    import labuse.api.scoreur as sc
    from fastapi import HTTPException

    def _introuvable(q):
        raise HTTPException(404, "Adresse « xyz » non trouvée.")
    monkeypatch.setattr(sc, "_geocode", _introuvable)
    client = TestClient(app)
    r = client.get("/flash", params={"q": "adresse qui n'existe pas 99999"})
    assert r.status_code == 200
    assert "non trouvée" in r.text, "échec d'adresse dit honnêtement, jamais un 500"
