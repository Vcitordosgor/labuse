"""3.C — Alertes intelligentes (« nouveautés »), sur PostGIS réel.

Recette du brief : **simuler une nouvelle donnée → elle apparaît dans les nouveautés.**
Couvre aussi le scope (hors zone / permis lointain ignorés), l'idempotence (pas de doublon
au re-rafraîchissement) et l'accusé de lecture.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import alertes

pytestmark = pytest.mark.db

COMMUNE = "Alertaville"


def _parcel(db, idu, lon, lat):
    wkt = (f"POLYGON(({lon} {lat},{lon + 0.0005} {lat},{lon + 0.0005} {lat + 0.0005},"
           f"{lon} {lat + 0.0005},{lon} {lat}))")
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "(:i,:c,'AB','1', ST_GeomFromText(:w,4326), 2000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "c": COMMUNE, "w": wkt}).scalar()


def _zone(lon, lat, half=0.002):
    return {"type": "Polygon", "coordinates": [[
        [lon - half, lat - half], [lon + half, lat - half], [lon + half, lat + half],
        [lon - half, lat + half], [lon - half, lat - half]]]}


def _dvf(db, lon, lat, valeur=300000):
    return db.execute(text(
        "INSERT INTO dvf_mutations (date_mutation, valeur_fonciere, nature_mutation, commune, geom) "
        "VALUES (now(), :v, 'Vente', :c, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)) RETURNING id"),
        {"v": valeur, "c": COMMUNE, "lon": lon, "lat": lat}).scalar()


def _permit(db, lon, lat, typ="PC"):
    return db.execute(text(
        "INSERT INTO sitadel_permits (type, date, commune, geom) "
        "VALUES (:t, now(), :c, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)) RETURNING id"),
        {"t": typ, "c": COMMUNE, "lon": lon, "lat": lat}).scalar()


def _follow(db, pid):
    db.execute(text("INSERT INTO pipeline_entries (parcel_id, status, priority) "
                    "VALUES (:p,'a_qualifier','moyenne')"), {"p": pid})


def test_vente_dvf_dans_zone_apparait_en_nouveaute(db_session):
    """Le cas du brief : une vente DVF SIMULÉE dans une zone de veille → nouveauté."""
    lon, lat = 55.30, -21.05
    alertes.create_watch_zone(db_session, "Centre-bourg", COMMUNE, _zone(lon, lat))
    assert alertes.compute_alertes(db_session, COMMUNE)["dvf_in_zone"] == 0   # rien encore
    _dvf(db_session, lon, lat)                                                # ← donnée nouvelle
    assert alertes.compute_alertes(db_session, COMMUNE)["dvf_in_zone"] == 1
    new = alertes.list_alertes(db_session, COMMUNE, only_new=True)
    assert any(a["kind"] == "dvf_in_zone" and a["zone_name"] == "Centre-bourg" for a in new)


def test_vente_hors_zone_ignoree(db_session):
    lon, lat = 55.31, -21.05
    alertes.create_watch_zone(db_session, "Petite zone", COMMUNE, _zone(lon, lat, half=0.001))
    _dvf(db_session, lon + 0.05, lat + 0.05)                                  # ~5 km plus loin
    assert alertes.compute_alertes(db_session, COMMUNE)["dvf_in_zone"] == 0


def test_permis_pres_parcelle_suivie_apparait(db_session):
    lon, lat = 55.32, -21.06
    _follow(db_session, _parcel(db_session, "ALERT0001", lon, lat))
    _permit(db_session, lon + 0.0005, lat)                                    # ~50 m
    assert alertes.compute_alertes(db_session, COMMUNE)["permit_near_followed"] == 1


def test_permis_loin_de_parcelle_suivie_ignore(db_session):
    lon, lat = 55.34, -21.07
    _follow(db_session, _parcel(db_session, "ALERT0002", lon, lat))
    _permit(db_session, lon + 0.01, lat)                                      # ~1 km > 200 m
    assert alertes.compute_alertes(db_session, COMMUNE)["permit_near_followed"] == 0


def test_idempotent_pas_de_doublon(db_session):
    lon, lat = 55.30, -21.05
    alertes.create_watch_zone(db_session, "Centre-bourg", COMMUNE, _zone(lon, lat))
    _dvf(db_session, lon, lat)
    assert alertes.compute_alertes(db_session, COMMUNE)["dvf_in_zone"] == 1
    assert alertes.compute_alertes(db_session, COMMUNE)["dvf_in_zone"] == 0   # re-run = aucune
    _dvf(db_session, lon + 0.0001, lat + 0.0001, valeur=420000)              # 2e vente
    assert alertes.compute_alertes(db_session, COMMUNE)["dvf_in_zone"] == 1


def test_accuse_de_lecture(db_session):
    lon, lat = 55.30, -21.05
    alertes.create_watch_zone(db_session, "Centre-bourg", COMMUNE, _zone(lon, lat))
    _dvf(db_session, lon, lat)
    alertes.compute_alertes(db_session, COMMUNE)
    assert len(alertes.list_alertes(db_session, COMMUNE, only_new=True)) == 1
    assert alertes.acknowledge(db_session, commune=COMMUNE) == 1
    assert alertes.list_alertes(db_session, COMMUNE, only_new=True) == []


def test_suppression_zone_efface_ses_alertes(db_session):
    lon, lat = 55.30, -21.05
    z = alertes.create_watch_zone(db_session, "Éphémère", COMMUNE, _zone(lon, lat))
    _dvf(db_session, lon, lat)
    alertes.compute_alertes(db_session, COMMUNE)
    assert len(alertes.list_alertes(db_session, COMMUNE)) == 1
    assert alertes.delete_watch_zone(db_session, z["id"]) is True
    assert alertes.list_alertes(db_session, COMMUNE) == []                    # cascade


# ───────────────────────── Bout en bout via l'API (HTTP) ─────────────────────────

@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    from labuse.db import session_scope
    cli = TestClient(app)
    try:
        yield cli, "ApiAlertVille"
    finally:
        with session_scope() as s:   # nettoyage (les alertes partent par cascade avec la zone)
            s.execute(text("DELETE FROM watch_zones WHERE commune = 'ApiAlertVille'"))
            s.execute(text("DELETE FROM dvf_mutations WHERE commune = 'ApiAlertVille'"))


def test_api_alertes_bout_en_bout(api_client):
    """POST zone → (rien) → insérer une vente → refresh → nouveauté → ack → vidée."""
    from labuse.db import session_scope
    client, commune = api_client
    poly = {"type": "Polygon", "coordinates": [[
        [55.40, -21.10], [55.42, -21.10], [55.42, -21.08], [55.40, -21.08], [55.40, -21.10]]]}
    assert client.post("/watch-zones", json={"name": "Zone API", "geometry": poly, "commune": commune}).status_code == 200
    assert client.get("/alertes", params={"commune": commune, "only_new": True}).json() == []
    with session_scope() as s:                       # ← donnée nouvelle simulée dans la zone
        s.execute(text("INSERT INTO dvf_mutations (date_mutation, valeur_fonciere, nature_mutation, commune, geom) "
                       "VALUES (now(), 350000, 'Vente', :c, ST_SetSRID(ST_MakePoint(55.41,-21.09),4326))"), {"c": commune})
    assert client.post("/alertes/refresh", params={"commune": commune}).json()["dvf_in_zone"] == 1
    items = client.get("/alertes", params={"commune": commune, "only_new": True}).json()
    assert len(items) == 1 and items[0]["kind"] == "dvf_in_zone"
    assert client.post("/alertes/ack", json={"id": items[0]["id"], "commune": commune}).json()["acknowledged"] == 1
    assert client.get("/alertes", params={"commune": commune, "only_new": True}).json() == []
