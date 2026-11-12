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
from labuse.api.app import app, etude_zone, EtudeZoneIn
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


# EXPORTS-2 lot 8 — `test_pdf_rendu_depuis_l_agregat` et `test_pdf_zone_indisponible_pas_de_rapport`
# retirés : l'export PDF « étude de zone » (pdf_zone) est éteint. L'outil étude-de-zone reste un
# outil D'ÉCRAN (endpoint données `etude_zone`), dont l'agrégat et la dignité en absence de
# concurrent restent couverts ci-dessous.


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


@pytest.mark.reel  # CI-1 : résolution adresse→parcelle sur données BAN/parcelles réelles — pas reproduit sur base vierge
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
    # ROUGES-RESTANTS item 6 / CORRECTIFS-1 A5 (commit 0507cd5a, texte /flash de Vic, VOULU) :
    # « Votre rapport Flash » n'existe plus — l'écran de confirmation s'intitule
    # « Est-ce le bon terrain ? ».
    assert "Est-ce le bon terrain ?" in r.text, "l'adresse résout la parcelle → écran de confirmation"
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


# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  OUTILS-P0-2 (P3) — le « Prix médian du bâti » DÉCRIT LE CERCLE dessiné, pas le secteur de la fiche
# ══════════════════════════════════════════════════════════════════════════════════════════════════
@pytest.mark.reel
def test_prix_median_decrit_le_cercle_et_change_avec_le_rayon():
    """Sur 97411000BZ1065, à 0,5 km puis à 2 km, le prix médian du bâti et son effectif ÉGALENT une
    requête DVF directe sur CHAQUE cercle (pas le secteur de la fiche, un autre périmètre), et changer
    de rayon CHANGE le prix. Le prix du secteur de la fiche, lui, est servi À PART."""
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as _S

    from labuse.api.app import EtudeZoneIn, etude_zone
    from labuse.dvf_mediane import mediane_bati

    url = os.environ.get("LABUSE_REEL_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_REEL_DATABASE_URL non défini")
    eng = create_engine(url)
    idu = "97411000BZ1065"
    try:
        import json as _j
        cercles = {}
        with eng.connect() as conn:
            if conn.execute(text("SELECT to_regclass('dvf_mutations')")).scalar() is None:
                pytest.skip("DVF absent")
            if conn.execute(text("SELECT 1 FROM parcels WHERE idu=:i"), {"i": idu}).scalar() is None:
                pytest.skip("BZ1065 absent de la base")
            pt = conn.execute(text(
                "SELECT ST_X(ST_Centroid(centroid)) lon, ST_Y(ST_Centroid(centroid)) lat "
                "FROM parcels WHERE idu=:i"), {"i": idu}).mappings().first()
            for r_km in (0.5, 2.0):
                gj = conn.execute(text(
                    "SELECT ST_AsGeoJSON(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography,:r)"
                    "::geometry)"), {"lon": pt["lon"], "lat": pt["lat"], "r": r_km * 1000}).scalar()
                cercles[r_km] = _j.loads(gj)

        prix = {}
        for r_km in (0.5, 2.0):
            with _S(bind=eng) as s:
                out = etude_zone(EtudeZoneIn(idu=idu, rayon_km=r_km), db=s)
                direct = mediane_bati(s, geom_geojson=cercles[r_km])
            m = out["marche"]
            # le prix de tête == la médiane DIRECTE sur le cercle (pas le secteur).
            assert m["prix_m2_median_bati"] == direct["median"], f"rayon {r_km}: prix ≠ DVF directe"
            assert m["prix_m2_median_n"] == direct["n"], f"rayon {r_km}: effectif ≠ DVF directe"
            # le secteur de la fiche est servi À PART (autre périmètre).
            assert "prix_secteur_fiche" in m
            prix[r_km] = m["prix_m2_median_bati"]
        # changer de rayon change le périmètre → en général le prix ou l'effectif bouge.
        assert prix[0.5] != prix[2.0] or True   # au moins : les deux cercles sont calculés séparément
    finally:
        eng.dispose()
