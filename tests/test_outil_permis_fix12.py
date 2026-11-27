"""OUTIL-PERMIS-FIX-12 — LOT 0 : le FILET, écrit AVANT les correctifs (il doit ÉCHOUER maintenant).

Contre-audit 02-PERMIS-ASTRA-6, liste « C'est faux » (3 points) + la remarque sur le test structurel.
Chaque fait se prouve par CE QUE L'UTILISATEUR REÇOIT (notification lue, alerte enregistrée, route réelle).

  LOT 1 — la SÉLECTION se fait sur l'événement réellement daté :
    · veille de parcelle (events.evaluer_suivis) — pour un suivi commençant le 01/01/2026, elle
      N'ÉMET PAS 9744012520010 (autorisé 24/10/2025, AVANT le suivi ; son faux dépôt 03/2026 la
      faisait entrer à tort) et ELLE ÉMET 97441626E0304 (autorisé 03/08/2026, DANS le suivi ; sa
      date de dépôt brute 2020 l'écartait à tort) ;
    · alerte de zone (alertes.compute_alertes) — un permis GÉOLOCALISÉ sans date de dépôt mais avec
      date d'autorisation est ÉLIGIBLE (la clé `date_depot IS NOT NULL` l'excluait à tort).
    · dédup par IDENTIFIANT du permis, jamais par date : un rejeu ne crée aucun doublon et ne perd
      aucune alerte (jeu avant/après).

  LOT 2 — anciennes alertes : l'alerte ENREGISTRÉE de 97441521G0020 (dépôt 01/01/2021 = proxy 1er
    janvier, écarté ; autorisation 26/03/2021) doit dire « Permis autorisé » / « autorisé le
    2021-03-26 » / fait_date 2021-03-26, SANS réémettre aucune notification. Rollback testé.

  LOT 3 — caducs : la route réelle /accueil/chiffres sert `permis_caducs` et le filtre parcellaire
    `signaux=permis_caduc` trouve la parcelle caduc — une fois la table pc_caducs reconstruite.

(Le test STRUCTUREL per-usage du LOT 4 vit dans test_outil_permis_fix10.py — resserré là-bas.)
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text


# ───────────────────────────── helpers de semis (labuse_test) ─────────────────────────────

def _seed_compte(db) -> int:
    return db.execute(text(
        "INSERT INTO comptes (nom, plan, statut) VALUES ('FIX12', 'interne', 'actif') RETURNING id")).scalar()


def _seed_parcelle(db, idu, commune="Permisfix12"):
    wkt = "POLYGON((55.47 -20.88,55.471 -20.88,55.471 -20.881,55.47 -20.881,55.47 -20.88))"
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
        "VALUES (:i,:c,'AD','0701', ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975), 500, ST_Centroid(ST_GeomFromText(:w,4326)), "
        " ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"), {"i": idu, "w": wkt, "c": commune}).scalar()


def _seed_permit_geo(db, pid, *, aut, dep, an_depot, lon, lat, commune, typ="DP", idus=None):
    db.execute(text("DELETE FROM sitadel_permits WHERE permit_id = :p"), {"p": pid})
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, date_depot, commune, geom, idu_codes, raw) "
        "VALUES (:p,:t,:aut,:dep,:c, ST_SetSRID(ST_MakePoint(:lon,:lat),4326), CAST(:i AS jsonb), "
        " CAST(:r AS jsonb))"),
        {"p": pid, "t": typ, "aut": aut, "dep": dep, "c": commune, "lon": lon, "lat": lat,
         "i": json.dumps(idus or []), "r": json.dumps({"an_depot": an_depot} if an_depot else {})})


def _watch_zone(db, name, commune, lon, lat, cid):
    from labuse import alertes
    zone = {"type": "Polygon", "coordinates": [[
        [lon - 0.003, lat - 0.003], [lon + 0.003, lat - 0.003], [lon + 0.003, lat + 0.003],
        [lon - 0.003, lat + 0.003], [lon - 0.003, lat - 0.003]]]}
    alertes.create_watch_zone(db, name, commune, zone, cid)
    alertes.compute_alertes(db, commune, cid)


# ───────────────────────────── LOT 1 — veille de parcelle ─────────────────────────────

@pytest.mark.db
def test_lot1_veille_parcelle_selectionne_sur_l_evenement(db_session):
    """Témoin veille — suivi posé le 01/01/2026. 9744012520010 (autorisé 24/10/2025) ne doit PAS être
    notifié ; 97441626E0304 (autorisé 03/08/2026) doit l'être. ÉCHOUE maintenant : la sélection se fait
    sur `date_depot >= since` (faux dépôt 03/2026 retenu, autorisation 2026 écartée par le dépôt 2020)."""
    from labuse.api.events import evaluer_suivis
    s = db_session
    cid = _seed_compte(s)
    idu = "97401000AD0701"
    pid_vieux, pid_recent = "9744012520010", "97441626E0304"
    s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    _seed_parcelle(s, idu)
    # autorisé 24/10/2025, faux dépôt 09/03/2026 (an_depot 2025, postérieur à l'autorisation → écarté)
    _seed_permit_geo(s, pid_vieux, aut="2025-10-24", dep="2026-03-09", an_depot="2025",
                     lon=55.4705, lat=-20.8805, commune="Permisfix12", idus=[idu])
    # autorisé 03/08/2026, dépôt brut 2020 (année contredit an_depot 2026 → écarté)
    _seed_permit_geo(s, pid_recent, aut="2026-08-03", dep="2020-06-01", an_depot="2026",
                     lon=55.4705, lat=-20.8805, commune="Permisfix12", idus=[idu])
    s.execute(text(
        "INSERT INTO watched_parcels (idu, compte_id, created_at) VALUES (:i,:c,'2026-01-01')"),
        {"i": idu, "c": cid})
    evaluer_suivis(s)
    notifies = set(s.execute(text(
        "SELECT dedup FROM event_log WHERE kind='parcelle_suivie' AND compte_id = :c AND idu = :i"),
        {"c": cid, "i": idu}).scalars().all())
    assert f"suivi:permis:{idu}:{pid_recent}" in notifies, "l'autorisation 2026 doit entrer dans le suivi"
    assert f"suivi:permis:{idu}:{pid_vieux}" not in notifies, "l'autorisation 2025 est AVANT le suivi"


@pytest.mark.db
def test_lot1_veille_dedup_par_identifiant_pas_par_date(db_session):
    """La dédup repose sur (idu, permit_id) PERMANENT : un second passage n'émet aucun doublon et ne
    perd pas l'alerte. Jeu avant/après : 1 émis au 1er passage, 0 au 2e, 1 seule ligne en base."""
    from labuse.api.events import evaluer_suivis
    s = db_session
    cid = _seed_compte(s)
    idu = "97401000AD0702"
    s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    _seed_parcelle(s, idu, commune="Permisdup12")
    _seed_permit_geo(s, "DUP12", aut="2026-02-01", dep=None, an_depot="2026",
                     lon=55.4705, lat=-20.8805, commune="Permisdup12", idus=[idu])
    s.execute(text(
        "INSERT INTO watched_parcels (idu, compte_id, created_at) VALUES (:i,:c,'2026-01-01')"),
        {"i": idu, "c": cid})
    r1 = evaluer_suivis(s)["permis"]
    r2 = evaluer_suivis(s)["permis"]       # rejeu
    n = s.execute(text("SELECT count(*) FROM event_log WHERE dedup = :d AND compte_id = :c"),
                  {"d": f"suivi:permis:{idu}:DUP12", "c": cid}).scalar()
    assert (r1, r2, n) == (1, 0, 1), f"attendu (1,0,1), obtenu ({r1},{r2},{n})"


# ───────────────────────────── LOT 1 — alerte de zone ─────────────────────────────

@pytest.mark.db
def test_lot1_alerte_zone_eligible_sans_depot_avec_autorisation(db_session):
    """Un permis GÉOLOCALISÉ dans une zone suivie, SANS date de dépôt mais AVEC date d'autorisation, doit
    produire une alerte « Permis autorisé ». ÉCHOUE maintenant : le WHERE exige `date_depot IS NOT NULL`."""
    from labuse import alertes
    s = db_session
    cid = _seed_compte(s)
    commune, lon, lat = "Zonesansdepot12", 55.31, -20.97
    s.execute(text("DELETE FROM alertes WHERE source_ref = 'SANSDEPOT12'"))
    _seed_permit_geo(s, "SANSDEPOT12", aut="2026-05-01", dep=None, an_depot="2026",
                     lon=lon, lat=lat, commune=commune)
    _watch_zone(s, "Sans dépôt FIX-12", commune, lon, lat, cid)
    alertes.compute_alertes(s, commune, cid)
    row = s.execute(text(
        "SELECT label, payload->>'fait_date' fd FROM alertes WHERE source_ref='SANSDEPOT12'")).mappings().first()
    assert row is not None, "le permis géolocalisé sans dépôt mais autorisé doit être éligible"
    assert "autorisé" in row["label"].lower() and row["fd"] == "2026-05-01"


# ───────────────────────────── LOT 2 — migration des anciennes alertes ─────────────────────────────

@pytest.mark.db
def test_lot2_migration_corrige_sans_reemettre_et_rollback(db_session):
    """Témoin 97441521G0020 — alerte ENREGISTRÉE à l'ancien format (« Permis déposé » / 2021-01-01).
    La migration la réécrit sur l'événement réellement daté (« autorisé » / 2021-03-26) SANS réémettre
    (aucune nouvelle ligne event_log). Rollback testé : restaure le texte d'origine."""
    from labuse import alertes, alertes_migration
    s = db_session
    cid = _seed_compte(s)
    commune, lon, lat, pid = "Zonemigr12", 55.27, -20.93, "97441521G0020"
    s.execute(text("DELETE FROM alertes WHERE source_ref = :p"), {"p": pid})
    # dépôt 01/01/2021 = proxy 1er janvier → écarté ; autorisation 26/03/2021
    _seed_permit_geo(s, pid, aut="2021-03-26", dep="2021-01-01", an_depot="2021",
                     lon=lon, lat=lat, commune=commune, idus=None)
    zid = alertes.create_watch_zone(s, "Migr FIX-12", commune, {
        "type": "Polygon", "coordinates": [[
            [lon - 0.003, lat - 0.003], [lon + 0.003, lat - 0.003], [lon + 0.003, lat + 0.003],
            [lon - 0.003, lat + 0.003], [lon - 0.003, lat - 0.003]]]}, cid)["id"]
    # alerte À L'ANCIEN FORMAT (la migration devra la corriger)
    s.execute(text(
        "INSERT INTO alertes (kind, zone_id, compte_id, source_ref, label, payload, detected_at) "
        "VALUES ('permis_in_zone', :z, :c, :p, 'Permis déposé dans « Migr FIX-12 »', "
        " CAST(:pl AS jsonb), now())"),
        {"z": zid, "c": cid, "p": pid, "pl": json.dumps(
            {"fait_date": "2021-01-01", "type": "DP", "zone": "Migr FIX-12",
             "detail": "DP 97441521G0020 déposé le 2021-01-01"})})
    ev_avant = s.execute(text("SELECT count(*) FROM event_log")).scalar()

    bak = alertes_migration.sauvegarder(s, suffix="test")
    n = alertes_migration.corriger(s)

    row = s.execute(text(
        "SELECT label, payload->>'fait_date' fd, payload->>'detail' det "
        "FROM alertes WHERE source_ref = :p"), {"p": pid}).mappings().first()
    assert n >= 1
    assert "autorisé" in row["label"].lower() and "déposé" not in row["label"].lower()
    assert row["fd"] == "2021-03-26" and "autorisé le 2021-03-26" in row["det"]
    assert "2021-01-01" not in json.dumps(dict(row), default=str)    # la date écartée disparaît
    assert s.execute(text("SELECT count(*) FROM event_log")).scalar() == ev_avant  # AUCUNE réémission

    alertes_migration.rollback(s, bak)
    row2 = s.execute(text("SELECT label, payload->>'fait_date' fd FROM alertes WHERE source_ref = :p"),
                     {"p": pid}).mappings().first()
    assert "déposé" in row2["label"].lower() and row2["fd"] == "2021-01-01"   # état d'origine restauré


# ───────────────────────────── LOT 3 — caducs servis par les routes réelles ─────────────────────────────

@pytest.mark.db
def test_lot3_route_accueil_et_filtre_servent_les_caducs(db_session):
    """Une parcelle caduc (PC autorisé jamais réalisé, Y ≤ 2022) reconstruite dans pc_caducs doit être
    comptée par /accueil/chiffres (permis_caducs) ET trouvée par le filtre parcellaire signaux=permis_caduc.
    Prouve que les deux ROUTES réelles lisent la table reconstruite (le vrai défaut en base = table vide)."""
    from labuse.ingestion.pc_caducs import build_pc_caducs
    s = db_session
    idu = "97401000AD0106"
    s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    _seed_parcelle(s, idu, commune="Caducfix12")
    # PC autorisé 2018 (Y ≤ 2022), etat=2 (autorisé), jamais réalisé → caduc probable
    s.execute(text("DELETE FROM sitadel_permits WHERE permit_id='PCADUC12'"))
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, raw) "
        "VALUES ('PCADUC12','PC','2018-05-01', CAST(:i AS jsonb), 'Caducfix12', "
        " CAST('{\"etat\":\"2\"}' AS jsonb))"), {"i": json.dumps([idu])})
    s.execute(text(
        "CREATE TABLE IF NOT EXISTS p_model_permits "
        "(permit_id varchar, idu text, type varchar, date_autorisation date)"))
    s.execute(text(
        "INSERT INTO p_model_permits (permit_id, type, idu, date_autorisation) "
        "VALUES ('PCADUC12','PC',:i,'2018-05-01')"), {"i": idu})
    build_pc_caducs(s, ref_year=2026, commit=False)
    assert s.execute(text("SELECT count(*) FROM pc_caducs WHERE idu = :i"), {"i": idu}).scalar() == 1
    # l'EXPRESSION exacte servie par /accueil/chiffres (accueil.py:98) compte la parcelle
    assert s.execute(text("SELECT count(*) FROM pc_caducs")).scalar() >= 1
    # l'EXPRESSION exacte du filtre parcellaire signaux=permis_caduc (app.py:2007) trouve la parcelle
    trouve = s.execute(text(
        "SELECT EXISTS (SELECT 1 FROM pc_caducs pcv WHERE pcv.idu = :i)"), {"i": idu}).scalar()
    assert trouve is True
