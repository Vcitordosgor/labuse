"""OUTIL-PERMIS-FIX-13 — LOT 0 : le FILET, écrit AVANT les correctifs (il doit ÉCHOUER maintenant).

Contre-audit 02-PERMIS-ASTRA-7, liste « C'est faux » (3 points). Chaque fait se prouve par CE QUE
L'UTILISATEUR REÇOIT (fiche parcelle, filtre carte, écran Scan patrimoine).

  1. DURÉE DE VALIDITÉ RÉELLE — 97401000AM0036 (PC 97440122A0070 autorisé le 06/11/2022, état 2) ne doit
     PAS être « caduc probable depuis 2025 » : le décret n° 2025-461 du 26/05/2025 porte à 5 ans la
     validité des autorisations délivrées du 28/05/2022 au 28/05/2024 → échéance 06/11/2027, dans le
     futur → la parcelle SORT du signal. (La règle « année » la retient à tort.)
  2. 8 PARCELLES MANQUANTES — 97415000DP0016 (PC 97441520A0030 autorisé le 26/02/2020, état 2) DOIT être
     dans les caducs. La table intermédiaire `p_model_permits` porte une date de dépôt brute (28/08/2023)
     en « date d'autorisation » → la parcelle manque. La reconstruction doit lire la date d'autorisation
     SOURCE (sitadel_permits.date), pas la colonne brute de la table dérivée (périmée).
  3. SCAN PATRIMOINE — l'opération de 97416000DR0312 (PC 97441625A0405, DÉPOSÉ en 2025 [an_depot], autorisé
     le 25/08/2026) ne doit PAS entrer dans « opérations déposées depuis le 01/01/2026 » : c'est son
     autorisation 2026 qui la fait entrer aujourd'hui (filtre sur la date d'AUTORISATION, pas de dépôt).
"""
from __future__ import annotations

import datetime as dt
import json

import pytest
from sqlalchemy import text

REF = dt.date(2026, 11, 25)   # « au » 25/11/2026 (date de l'audit)


def _seed_parcelle(db, idu, commune):
    wkt = "POLYGON((55.47 -20.88,55.471 -20.88,55.471 -20.881,55.47 -20.881,55.47 -20.88))"
    db.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
        "VALUES (:i,:c,'AM','0036', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), "
        " 500, ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": wkt, "c": commune}).scalar()


def _seed_pc(db, pid, idu, *, date_aut, date_depot, an_depot, etat="2", nb_lgt=None,
            lon=55.47, lat=-20.88, commune="X"):
    db.execute(text("DELETE FROM sitadel_permits WHERE permit_id = :p"), {"p": pid})
    raw = {"etat": etat, "an_depot": an_depot}
    if nb_lgt is not None:
        raw["nb_lgt"] = str(nb_lgt)
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, date_depot, commune, geom, idu_codes, raw) "
        "VALUES (:p,'PC',:a,:d,:com, ST_SetSRID(ST_MakePoint(:lon,:lat),4326), CAST(:i AS jsonb), CAST(:r AS jsonb))"),
        {"p": pid, "a": date_aut, "d": date_depot, "i": json.dumps([idu]), "r": json.dumps(raw),
         "lon": lon, "lat": lat, "com": commune})


def _seed_pmp(db, pid, idu, date_autorisation):
    """Reproduit la table dérivée (potentiellement PÉRIMÉE) lue par le code AVANT correctif."""
    db.execute(text("CREATE TABLE IF NOT EXISTS p_model_permits "
                    "(permit_id varchar, idu text, type varchar, date_autorisation date)"))
    db.execute(text("DELETE FROM p_model_permits WHERE permit_id = :p"), {"p": pid})
    db.execute(text("INSERT INTO p_model_permits (permit_id, idu, type, date_autorisation) "
                    "VALUES (:p,:i,'PC',:d)"), {"p": pid, "i": idu, "d": date_autorisation})


@pytest.mark.db
def test_lot0_caduc_echeance_decret_2022(db_session):
    """Point 1 — 97401000AM0036 (PC autorisé 06/11/2022) SORT du signal (échéance 2027 > 2026-11-25).
    ÉCHOUE maintenant : la règle « année » (Y ≤ 2022) le retient comme caduc depuis 2025."""
    from labuse.ingestion.pc_caducs import build_pc_caducs
    s = db_session
    idu = "97401000AM0036"
    _seed_parcelle(s, idu, "Les Avirons")
    _seed_pc(s, "97440122A0070", idu, date_aut="2022-11-06", date_depot="2022-11-06", an_depot="2022")
    _seed_pmp(s, "97440122A0070", idu, "2022-11-06")   # table dérivée cohérente (règle année → caduc)
    build_pc_caducs(s, ref_date=REF, commit=False)
    present = s.execute(text("SELECT count(*) FROM pc_caducs WHERE idu = :i"), {"i": idu}).scalar()
    assert present == 0, "PC 2022 : validité 5 ans (décret 2025-461), échéance 2027 → PAS caduc en 2026"


@pytest.mark.db
def test_lot0_parcelle_manquante_date_source(db_session):
    """Point 2 — 97415000DP0016 (PC autorisé 26/02/2020, source sitadel_permits.date) DOIT être caduc.
    ÉCHOUE maintenant : la reconstruction lit `p_model_permits.date_autorisation` = 28/08/2023 (date de
    dépôt brute) → année 2023 > 2022 → parcelle écartée."""
    from labuse.ingestion.pc_caducs import build_pc_caducs
    s = db_session
    idu = "97415000DP0016"
    _seed_parcelle(s, idu, "Saint-Paul")
    _seed_pc(s, "97441520A0030", idu, date_aut="2020-02-26", date_depot="2023-08-28", an_depot="2020")
    _seed_pmp(s, "97441520A0030", idu, "2023-08-28")   # table dérivée PÉRIMÉE (brute en date_autorisation)
    build_pc_caducs(s, ref_date=REF, commit=False)
    row = s.execute(text("SELECT libelle_court FROM pc_caducs WHERE idu = :i"), {"i": idu}).mappings().first()
    assert row is not None, "PC autorisé 2020 (source) → échéance 2023 → caduc : doit figurer"
    assert "2020" in row["libelle_court"]


@pytest.mark.db
def test_lot0_scan_patrimoine_depose_pas_autorise(db_session):
    """Point 3 — l'opération de 97416000DR0312 (PC déposé en 2025, autorisé 25/08/2026) ne doit PAS entrer
    dans « déposées depuis 01/01/2026 ». ÉCHOUE maintenant : le filtre lit la date d'AUTORISATION 2026."""
    from labuse.api.veille_promoteurs import _operations
    s = db_session
    idu = "97416000DR0312"
    _seed_parcelle(s, idu, "Saint-Pierre")
    _seed_pc(s, "97441625A0405", idu, date_aut="2026-08-25", date_depot="2026-08-25", an_depot="2025",
             nb_lgt=41, lon=55.48, lat=-20.90, commune="Saint-Pierre")
    s.execute(text("DELETE FROM parcelle_personne_morale WHERE idu = :i"), {"i": idu})
    s.execute(text("INSERT INTO parcelle_personne_morale (idu, groupe, denomination, siren) "
                   "VALUES (:i, 0, 'PROMO SCAN', '900900900')"), {"i": idu})
    ops = _operations(s, [0], "Saint-Pierre", "2026-01-01")
    idus = {i for op in ops for i in op["idus"]}
    assert idu not in idus, "déposé en 2025 (an_depot) → hors « déposées depuis 01/01/2026 »"


# ───────────────────────────── LOT 4 — alertes : permis aujourd'hui annulé ─────────────────────────────

def _seed_compte(db) -> int:
    return db.execute(text(
        "INSERT INTO comptes (nom, plan, statut) VALUES ('FIX13', 'interne', 'actif') RETURNING id")).scalar()


def _watch_zone(db, name, commune, lon, lat, cid):
    from labuse import alertes
    zone = {"type": "Polygon", "coordinates": [[
        [lon - 0.003, lat - 0.003], [lon + 0.003, lat - 0.003], [lon + 0.003, lat + 0.003],
        [lon - 0.003, lat + 0.003], [lon - 0.003, lat - 0.003]]]}
    zid = alertes.create_watch_zone(db, name, commune, zone, cid)["id"]
    alertes.compute_alertes(db, commune, cid)
    return zid


@pytest.mark.db
def test_lot4_alerte_annule_live_dit_son_etat(db_session):
    """Génération live — un permis GÉOLOCALISÉ aujourd'hui ANNULÉ (état 4) dans une zone suivie : le détail
    dit « autorisé le … · annulé depuis ». ÉCHOUE maintenant (pas d'annotation d'état)."""
    from labuse import alertes
    s = db_session
    cid = _seed_compte(s)
    commune, lon, lat, pid = "Zoneannule13", 55.26, -20.92, "97441513A0361"
    s.execute(text("DELETE FROM alertes WHERE source_ref = :p"), {"p": pid})
    _seed_pc(s, pid, "97415000ZZ0001", date_aut="2013-09-09", date_depot="2013-09-09", an_depot="2013",
             etat="4", lon=lon, lat=lat, commune=commune)
    _watch_zone(s, "Annulé FIX-13", commune, lon, lat, cid)
    alertes.compute_alertes(s, commune, cid)
    row = s.execute(text("SELECT label, payload->>'detail' det FROM alertes WHERE source_ref = :p"),
                    {"p": pid}).mappings().first()
    assert row is not None
    assert "autorisé le 2013-09-09" in row["det"] and "· annulé depuis" in row["det"]


@pytest.mark.db
def test_lot4_migration_annote_annules_sans_reemettre(db_session):
    """Migration — une alerte enregistrée « autorisé le … » dont le permis est désormais annulé reçoit
    «  · annulé depuis », sans réémission, et de façon idempotente."""
    from labuse import alertes, alertes_migration
    s = db_session
    cid = _seed_compte(s)
    commune, lon, lat, pid = "Zoneannmig13", 55.25, -20.91, "97441513A0361"
    s.execute(text("DELETE FROM alertes WHERE source_ref = :p"), {"p": pid})
    _seed_pc(s, pid, "97415000ZZ0002", date_aut="2013-09-09", date_depot="2013-09-09", an_depot="2013",
             etat="4", lon=lon, lat=lat, commune=commune)
    zid = alertes.create_watch_zone(s, "AnnMig FIX-13", commune, {
        "type": "Polygon", "coordinates": [[
            [lon - 0.003, lat - 0.003], [lon + 0.003, lat - 0.003], [lon + 0.003, lat + 0.003],
            [lon - 0.003, lat + 0.003], [lon - 0.003, lat - 0.003]]]}, cid)["id"]
    s.execute(text(
        "INSERT INTO alertes (kind, zone_id, compte_id, source_ref, label, payload, detected_at) "
        "VALUES ('permis_in_zone', :z, :c, :p, 'Permis autorisé dans « AnnMig FIX-13 »', CAST(:pl AS jsonb), now())"),
        {"z": zid, "c": cid, "p": pid, "pl": json.dumps(
            {"fait_date": "2013-09-09", "type": "PC", "zone": "AnnMig FIX-13",
             "detail": "PC 97441513A0361 autorisé le 2013-09-09"})})
    ev_avant = s.execute(text("SELECT count(*) FROM event_log")).scalar()
    n1 = alertes_migration.annoter_annules(s)
    n2 = alertes_migration.annoter_annules(s)   # idempotent
    det = s.execute(text("SELECT payload->>'detail' FROM alertes WHERE source_ref = :p"), {"p": pid}).scalar()
    assert n1 == 1 and n2 == 0
    assert det == "PC 97441513A0361 autorisé le 2013-09-09 · annulé depuis"
    assert s.execute(text("SELECT count(*) FROM event_log")).scalar() == ev_avant   # aucune réémission
