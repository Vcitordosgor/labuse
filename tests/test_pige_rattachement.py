"""RADAR V0 · P2 — cascade de rattachement à la parcelle (Sourcé / Estimé / Absent).

Base de test vide → on SEME des parcelles [RADAR-TEST] + un DPE + une emprise bâtie, et on gèle :
GPS contenant = Sourcé · DPE/morpho 1-3 candidates = Estimé · rien / trop ambigu = Absent (jamais un
pin faussement sûr). Aucune requête réseau (le géocodeur BAN est injecté).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige.rattachement import rattacher

pytestmark = pytest.mark.db

COMMUNE = "RadarTestVille"
INSEE = "97499"
# petit carré ~ autour d'un point à La Réunion
WKT = "POLYGON((55.30 -21.00,55.302 -21.00,55.302 -21.002,55.30 -21.002,55.30 -21.00))"
PT = (55.301, -21.001)          # à l'intérieur du carré
PT_DEHORS = (55.90, -20.90)     # loin, dans aucune parcelle


@pytest.fixture
def seed(engine):
    tag = uuid.uuid4().hex[:4].upper()
    idu = f"{INSEE}0{tag}0001"[:14].ljust(14, "0")
    with session_scope() as s:
        s.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox)"
            " VALUES (:i,:c,'ZZ','1',ST_GeomFromText(:w,4326),ST_Transform(ST_GeomFromText(:w,4326),2975),"
            " 500, ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
            {"i": idu, "c": COMMUNE, "w": WKT})
        s.execute(text(
            "INSERT INTO dpe_records (numero_dpe, etiquette_dpe, surface_habitable, code_insee, parcelle_idu)"
            " VALUES (:n,'D',95,:insee,:i)"),
            {"n": f"RT-{tag}", "insee": INSEE, "i": idu})
        s.execute(text("INSERT INTO p_model_bati (idu, emprise_bati_m2) VALUES (:i, 100)"), {"i": idu})
    yield {"idu": idu}
    with session_scope() as s:
        s.execute(text("DELETE FROM dpe_records WHERE parcelle_idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM p_model_bati WHERE idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})


def test_gps_contenant_est_source(seed):
    with session_scope() as db:
        r = rattacher(db, commune=COMMUNE, lon=PT[0], lat=PT[1])
    assert r["niveau"] == "source" and r["idu"] == seed["idu"] and r["etage"] == "gps"


def test_ban_geocode_injecte_est_source(seed):
    fake_geocode = lambda adr: {"lon": PT[0], "lat": PT[1], "score": 0.9}
    with session_scope() as db:
        r = rattacher(db, commune=COMMUNE, adresse="12 rue Test", geocode=fake_geocode)
    assert r["niveau"] == "source" and r["idu"] == seed["idu"] and r["etage"] == "ban"


def test_dpe_morpho_donne_estime(seed):
    # ni GPS ni adresse → cascade retombe sur DPE (classe D, 95 m²) + morpho (emprise 100 m²)
    with session_scope() as db:
        r = rattacher(db, commune=COMMUNE, commune_insee=INSEE,
                      surface_hab=95, dpe_classe="D")
    assert r["niveau"] == "estime"
    assert any(c["idu"] == seed["idu"] for c in r["candidates"])
    assert 1 <= len(r["candidates"]) <= 3
    # confirmé par deux étages (DPE + morpho) → confiance relevée
    assert any(c["etage"] == "dpe+morpho" for c in r["candidates"])


def test_gps_hors_parcelle_et_rien_de_plausible_est_absent(seed):
    with session_scope() as db:
        r = rattacher(db, commune=COMMUNE, commune_insee=INSEE, lon=PT_DEHORS[0], lat=PT_DEHORS[1])
    assert r["niveau"] == "absent" and r["idu"] is None and r["candidates"] == []


def test_jamais_de_pin_pour_une_commune_inconnue(seed):
    with session_scope() as db:
        r = rattacher(db, commune="Nulle-Part", lon=PT[0], lat=PT[1])
    # le point est réel mais aucune parcelle de cette commune → pas de faux pin
    assert r["niveau"] == "absent"
