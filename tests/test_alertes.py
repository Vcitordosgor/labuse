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
    alertes.create_watch_zone(db_session, "Centre-bourg", COMMUNE, _zone(lon, lat), None)
    assert alertes.compute_alertes(db_session, COMMUNE, None)["dvf_in_zone"] == 0   # rien encore
    _dvf(db_session, lon, lat)                                                # ← donnée nouvelle
    assert alertes.compute_alertes(db_session, COMMUNE, None)["dvf_in_zone"] == 1
    new = alertes.list_alertes(db_session, COMMUNE, None, only_new=True)
    assert any(a["kind"] == "dvf_in_zone" and a["zone_name"] == "Centre-bourg" for a in new)


def test_vente_hors_zone_ignoree(db_session):
    lon, lat = 55.31, -21.05
    alertes.create_watch_zone(db_session, "Petite zone", COMMUNE, _zone(lon, lat, half=0.001), None)
    _dvf(db_session, lon + 0.05, lat + 0.05)                                  # ~5 km plus loin
    assert alertes.compute_alertes(db_session, COMMUNE, None)["dvf_in_zone"] == 0


def test_permis_ne_passe_plus_par_ce_canal(db_session):
    """M54-EXPO-2 (arbitrage Vic) : le kind `permit_near_followed` est RETIRÉ — la cloche
    (events kind='permis') couvre déjà les permis près d'une parcelle suivie. Test JUMEAU :
    même AVEC une parcelle suivie ET un permis à 50 m, ce canal n'émet AUCUNE alerte permis
    (ni clé `permit_near_followed`, ni ligne d'alerte). Un signal, un canal."""
    lon, lat = 55.32, -21.06
    _follow(db_session, _parcel(db_session, "ALERT0001", lon, lat))
    _permit(db_session, lon + 0.0005, lat)                                    # ~50 m — jadis détecté
    res = alertes.compute_alertes(db_session, COMMUNE, None)
    assert "permit_near_followed" not in res                                  # clé disparue
    assert res == {"dvf_in_zone": 0, "total": 0}                              # rien via ce canal
    assert not any(a["kind"] == "permit_near_followed"
                   for a in alertes.list_alertes(db_session, COMMUNE, None))  # aucune ligne permis


def test_idempotent_pas_de_doublon(db_session):
    lon, lat = 55.30, -21.05
    alertes.create_watch_zone(db_session, "Centre-bourg", COMMUNE, _zone(lon, lat), None)
    _dvf(db_session, lon, lat)
    assert alertes.compute_alertes(db_session, COMMUNE, None)["dvf_in_zone"] == 1
    assert alertes.compute_alertes(db_session, COMMUNE, None)["dvf_in_zone"] == 0   # re-run = aucune
    _dvf(db_session, lon + 0.0001, lat + 0.0001, valeur=420000)              # 2e vente
    assert alertes.compute_alertes(db_session, COMMUNE, None)["dvf_in_zone"] == 1


def test_accuse_de_lecture(db_session):
    lon, lat = 55.30, -21.05
    alertes.create_watch_zone(db_session, "Centre-bourg", COMMUNE, _zone(lon, lat), None)
    _dvf(db_session, lon, lat)
    alertes.compute_alertes(db_session, COMMUNE, None)
    assert len(alertes.list_alertes(db_session, COMMUNE, None, only_new=True)) == 1
    assert alertes.acknowledge(db_session, None, commune=COMMUNE) == 1
    assert alertes.list_alertes(db_session, COMMUNE, None, only_new=True) == []


def test_suppression_zone_efface_ses_alertes(db_session):
    lon, lat = 55.30, -21.05
    z = alertes.create_watch_zone(db_session, "Éphémère", COMMUNE, _zone(lon, lat), None)
    _dvf(db_session, lon, lat)
    alertes.compute_alertes(db_session, COMMUNE, None)
    assert len(alertes.list_alertes(db_session, COMMUNE, None)) == 1
    assert alertes.delete_watch_zone(db_session, z["id"], None) is True
    assert alertes.list_alertes(db_session, COMMUNE, None) == []                    # cascade


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


def test_api_watch_zone_rename(api_client):
    """M54-EXPO-3 : PATCH /watch-zones/{id} renomme ; GET reflète ; id inconnu → 404."""
    client, commune = api_client
    poly = {"type": "Polygon", "coordinates": [[
        [55.40, -21.10], [55.42, -21.10], [55.42, -21.08], [55.40, -21.08], [55.40, -21.10]]]}
    zid = client.post("/watch-zones", json={"name": "Avant", "geometry": poly, "commune": commune}).json()["zone"]["id"]
    assert client.patch(f"/watch-zones/{zid}", json={"name": "Après"}).json()["ok"] is True
    z = [x for x in client.get("/watch-zones", params={"commune": commune}).json() if x["id"] == zid][0]
    assert z["name"] == "Après"
    assert client.patch("/watch-zones/99999999", json={"name": "X"}).status_code == 404
