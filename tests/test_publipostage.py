"""Tests Lot 2A (wave-adresses) : export publipostage (CSV normalisé + étiquettes)."""
from __future__ import annotations

import csv
import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db

_POLY = ("POLYGON((55.4495 -21.3005, 55.4505 -21.3005, 55.4505 -21.2995,"
         " 55.4495 -21.2995, 55.4495 -21.3005))")


@pytest.fixture
def client_adresse(engine):
    """Parcelle + adresse BAN rattachée + index inverse, tables protection prêtes."""
    from labuse.api import protection
    from labuse.ingestion.ban_adresses import DDL_ADRESSES
    from labuse.segments.registry import reset_availability_cache

    protection.ensure_tables(engine)
    with engine.begin() as c:
        for stmt in DDL_ADRESSES.strip().split(";"):
            if stmt.strip():
                c.execute(text(stmt))
        c.execute(text("DELETE FROM adresse_parcelles"))
        c.execute(text("DELETE FROM adresses"))
        c.execute(text("DELETE FROM parcels WHERE idu = '97416000PB0001'"))
        c.execute(text(
            f"""INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, geom_2975)
                VALUES ('97416000PB0001', 'Saint-Pierre', 'PB', '0001', 900,
                        ST_GeomFromText('{_POLY}', 4326),
                        ST_Transform(ST_GeomFromText('{_POLY}', 4326), 2975))"""))
        c.execute(text(
            """INSERT INTO adresses (id_ban, numero, rep, voie, code_postal, commune, insee,
                                     idu, rattachement)
               VALUES ('97416_pb_1', '12', NULL, 'Rue des Publipostages', '97410',
                       'Saint-Pierre', '97416', '97416000PB0001', 'parcelle')"""))
        c.execute(text(
            "INSERT INTO adresse_parcelles (id_ban, idu, source) "
            "VALUES ('97416_pb_1', '97416000PB0001', 'principal')"))
    reset_availability_cache()
    from labuse.api.app import app
    yield TestClient(app, base_url="https://testserver")
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcels WHERE idu = '97416000PB0001'"))
    reset_availability_cache()


def test_publipostage_zip(client_adresse, engine):
    r = client_adresse.post("/segments/publipostage", json={"filtres": [], "tri": None})
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    noms = set(z.namelist())
    assert {"publipostage.csv", "etiquettes.pdf"} <= noms
    rows = list(csv.reader(io.TextIOWrapper(z.open("publipostage.csv"),
                                            encoding="utf-8-sig"), delimiter=";"))
    entetes, lignes = rows[0], rows[1:]
    assert entetes[:5] == ["Destinataire", "Adresse ligne 1", "Adresse ligne 2",
                           "Code postal", "Ville"]
    assert entetes[-1] == "ref"                     # watermark Lot 3
    assert lignes, "au moins la parcelle seedée"
    occupant = [l for l in lignes if l[5] == "97416000PB0001"]
    assert occupant and occupant[0][0] == "À l'occupant"
    assert "12" in occupant[0][1] and occupant[0][3] == "97410"
    # jamais de nom de personne physique : le destinataire est CONSTANT
    assert {l[0] for l in lignes} == {"À l'occupant"}
    assert z.open("etiquettes.pdf").read(5) == b"%PDF-"
    # fingerprint enregistré (critère d'acceptation Lot 3 : > 0 après 1 export)
    with engine.connect() as c:
        n = c.execute(text(
            "SELECT count(*) FROM export_fingerprints WHERE format = 'publipostage'")).scalar()
    assert n >= 1


def test_gabarits(client_adresse):
    r = client_adresse.get("/segments/gabarits")
    assert r.status_code == 200
    g = r.json()["gabarits"]
    assert {"exterieur", "renovation", "energie", "securite", "foncier_bati"} <= set(g)
    assert all("corps" in v and "titre" in v for v in g.values())


def test_etiquettes_pdf_vide():
    from labuse.segments.publipostage import etiquettes_pdf

    pdf = etiquettes_pdf([], fmt="63.5x38.1", ref="testref")
    assert pdf[:5] == b"%PDF-"
