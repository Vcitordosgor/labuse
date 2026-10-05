"""LIENS-1 (lot 1) — endpoint /parcels/{idu}.kmz : le contour servi en KML zippé (Google Earth).

Vérifie que le KMZ est un vrai zip contenant `doc.kml` (convention Google Earth), que le KML porte
l'IDU et le contour (produit par PostGIS `ST_AsKML`, donc la MÊME géométrie que la carte), et que la
description reprend commune + surface servie. IDU inconnu -> 404.
"""
from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


def test_parcel_kmz_contour_valide(client, engine):
    idu = "97411000ZT0001"  # 14 caracteres (INSEE+section+numero)
    wkt = ("POLYGON((55.400 -20.900,55.401 -20.900,"
           "55.401 -20.901,55.400 -20.901,55.400 -20.900))")
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
        c.execute(text("""
            INSERT INTO parcels (idu, commune, geom, surface_m2)
            VALUES (:i, :com, ST_GeomFromText(:wkt, 4326), :s)"""),
            {"i": idu, "com": "Saint-Paul", "wkt": wkt, "s": 1234.0})
    try:
        r = client.get(f"/parcels/{idu}.kmz")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/vnd.google-earth.kmz")
        assert f'filename="{idu}.kmz"' in r.headers["content-disposition"]

        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert zf.namelist() == ["doc.kml"]        # convention Google Earth
        kml = zf.read("doc.kml").decode("utf-8")
        assert idu in kml
        assert "<Polygon>" in kml                   # ST_AsKML a produit le contour
        assert "Saint-Paul" in kml                  # commune dans la description
        assert "1234 m" in kml                      # surface servie dans la description

        assert client.get("/parcels/INEXISTANT0000.kmz").status_code == 404
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
