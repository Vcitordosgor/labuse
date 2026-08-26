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
    # M104 : compute rend aussi permis/bodacc/zonage PAR SECTEUR (canal arbitré, distinct du
    # canal retiré « près d'une parcelle suivie ») — l'intention du test est intacte : SANS zone
    # dessinée, rien ne sort de ce module, et jamais par proximité d'une parcelle suivie.
    assert res["dvf_in_zone"] == 0 and res["total"] == 0                      # rien via ce canal
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


# ───────────────────────── M104 — raccordement + 3 déclencheurs ─────────────────────────
# Chaque déclencheur PROUVE qu'il produit un ÉVÉNEMENT RÉEL (event_log, type veille_zone),
# et le rattrapage est borné : un fait antérieur à la création de la zone alimente le
# panneau mais ne notifie JAMAIS (« repartir du présent », arbitrage M104).

def _notifs_secteur(db):
    return db.execute(text(
        "SELECT titre, dedup FROM event_log WHERE kind = 'veille_zone' AND dedup LIKE 'secteur:%'"
    )).all()


def test_permis_dans_secteur_produit_un_evenement_reel(db_session):
    lon, lat = 55.31, -21.06
    alertes.create_watch_zone(db_session, "Quartier permis", COMMUNE, _zone(lon, lat), None)
    alertes.compute_alertes(db_session, COMMUNE, None)              # photo initiale, rien
    db_session.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date_depot, commune, geom) "
        "VALUES ('PC974TEST01', 'PC', now()::date, :c, ST_SetSRID(ST_MakePoint(:lon,:lat),4326))"),
        {"c": COMMUNE, "lon": lon, "lat": lat})
    out = alertes.compute_alertes(db_session, COMMUNE, None)
    assert out["permis_in_zone"] == 1 and out["notifications"] == 1
    assert any("Permis déposé" in t for t, _ in _notifs_secteur(db_session))
    # idempotence : re-évaluer n'ajoute rien
    again = alertes.compute_alertes(db_session, COMMUNE, None)
    assert again["permis_in_zone"] == 0 and again["notifications"] == 0


def test_bodacc_dans_secteur_produit_un_evenement_reel(db_session):
    lon, lat = 55.33, -21.07
    pid = _parcel(db_session, "97499000ZZ0001", lon, lat)
    assert pid
    alertes.create_watch_zone(db_session, "Quartier BODACC", COMMUNE, _zone(lon, lat), None)
    db_session.execute(text(
        "INSERT INTO parcelle_personne_morale (idu, siren, denomination) "
        "VALUES ('97499000ZZ0001', '000000001', 'SCI TEST')"))
    db_session.execute(text(
        "INSERT INTO bodacc_procedures (annonce_id, siren, type_procedure, date_annonce) "
        "VALUES ('A-TEST-1', '000000001', 'Redressement judiciaire', now()::date)"))
    out = alertes.compute_alertes(db_session, COMMUNE, None)
    assert out["bodacc_in_zone"] == 1 and out["notifications"] == 1
    assert any("Procédure BODACC" in t for t, _ in _notifs_secteur(db_session))


def test_zonage_dans_secteur_photo_puis_diff(db_session):
    lon, lat = 55.35, -21.08
    _parcel(db_session, "97499000ZZ0002", lon, lat)
    db_session.execute(text(
        "INSERT INTO parcel_zone_plu (idu, zone_lib) VALUES ('97499000ZZ0002', 'U1')"))
    alertes.create_watch_zone(db_session, "Quartier zonage", COMMUNE, _zone(lon, lat), None)
    # 1re rencontre = PHOTO silencieuse (repartir du présent) — aucune alerte, aucune notif
    out = alertes.compute_alertes(db_session, COMMUNE, None)
    assert out["zonage_in_zone"] == 0
    # le zonage change → alerte + événement réel
    db_session.execute(text("UPDATE parcel_zone_plu SET zone_lib = 'AU2' WHERE idu = '97499000ZZ0002'"))
    out = alertes.compute_alertes(db_session, COMMUNE, None)
    assert out["zonage_in_zone"] == 1 and out["notifications"] == 1
    assert any("Changement de zonage" in t for t, _ in _notifs_secteur(db_session))
    # empreinte mémorisée : re-évaluer n'ajoute rien
    assert alertes.compute_alertes(db_session, COMMUNE, None)["zonage_in_zone"] == 0


def test_repartir_du_present_fait_ancien_ne_notifie_pas(db_session):
    """Un fait daté AVANT la création de la zone alimente le panneau, jamais la cloche."""
    lon, lat = 55.37, -21.09
    alertes.create_watch_zone(db_session, "Zone rattrapage", COMMUNE, _zone(lon, lat), None)
    db_session.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date_depot, commune, geom) "
        "VALUES ('PC974VIEUX', 'PC', '2020-01-15', :c, ST_SetSRID(ST_MakePoint(:lon,:lat),4326))"),
        {"c": COMMUNE, "lon": lon, "lat": lat})
    out = alertes.compute_alertes(db_session, COMMUNE, None)
    assert out["permis_in_zone"] == 1        # le panneau montre l'historique…
    assert out["notifications"] == 0         # …la cloche ne le reçoit jamais


def test_suppression_veille_purge_le_snap_zonage_zero_orphelin(db_session):
    """FIX-C6 (GB-063) — supprimer une veille efface sa photo zonage ; ZÉRO orphelin global.

    Régression : `watch_zone_zonage_snap` n'avait pas de FK vers watch_zones → ses lignes
    fuyaient à chaque DELETE (3 330 orphelins constatés au cycle 6). Garde permanente."""
    lon, lat = 55.41, -21.11
    z = alertes.create_watch_zone(db_session, "Zone snap", COMMUNE, _zone(lon, lat), None)
    # matérialise le schéma du snap (créé paresseusement à la détection) puis y pose une ligne
    alertes.compute_alertes(db_session, COMMUNE, None)
    db_session.execute(text(
        "INSERT INTO watch_zone_zonage_snap (zone_id, idu, zone_lib) VALUES (:z, '974110000AB1', 'U')"
        " ON CONFLICT DO NOTHING"), {"z": z["id"]})
    assert db_session.execute(text(
        "SELECT count(*) FROM watch_zone_zonage_snap WHERE zone_id = :z"), {"z": z["id"]}).scalar() == 1
    # suppression via le chemin applicatif → le snap de CETTE zone disparaît…
    assert alertes.delete_watch_zone(db_session, z["id"], None) is True
    assert db_session.execute(text(
        "SELECT count(*) FROM watch_zone_zonage_snap WHERE zone_id = :z"), {"z": z["id"]}).scalar() == 0
    # …et l'invariant global tient : aucune ligne snap ne pointe une zone disparue
    orphelins = db_session.execute(text(
        "SELECT count(*) FROM watch_zone_zonage_snap s"
        " WHERE NOT EXISTS (SELECT 1 FROM watch_zones w WHERE w.id = s.zone_id)")).scalar()
    assert orphelins == 0
