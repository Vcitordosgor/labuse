"""DPE ADEME — parsing + rattachement parcelle 100 % LOCAL (mandat 11/07) + signal passoire.

Champs figés sur un enregistrement RÉEL vérifié live 05/07/2026 (jeu dpe03existant, INSEE 97415),
enrichi des champs BAN natifs (identifiant_ban, coordonnées EPSG:2975) vérifiés live 11/07/2026.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text

from labuse.connectors.dpe import in_reunion
from labuse.ingestion.dpe import (
    _norm,
    _parse_brut,
    ingest_commune,
    parse_record,
    sample_report,
)

REC = {"numero_dpe": "2397E0123456X", "etiquette_dpe": "G", "etiquette_ges": "E",
       "type_batiment": "maison", "surface_habitable_logement": "112.5",
       "annee_construction": "1985", "adresse_ban": "12 Rue des Bougainvilliers 97460 Saint-Paul",
       "adresse_brut": "12 rue des Bougainvilliers 97460 Saint-Paul",
       "code_insee_ban": "97415", "code_postal_ban": "97460", "date_etablissement_dpe": "2025-03-01",
       "identifiant_ban": "97415_9999_00012", "score_ban": 0.92,
       "coordonnee_cartographique_x_ban": 320828.97, "coordonnee_cartographique_y_ban": 7676122.5}


# ───────────────────────── pur ─────────────────────────

def test_in_reunion():
    assert in_reunion(55.27, -21.01)          # Saint-Paul
    assert not in_reunion(-3.0, 56.0)         # le faux _geopoint ADEME (Écosse)


def test_parse_record():
    p = parse_record(REC)
    assert p["numero_dpe"] == "2397E0123456X"
    assert p["etiquette_dpe"] == "G" and p["type_batiment"] == "maison"
    assert p["surface_habitable"] == 112.5
    assert p["annee_construction"] == 1985
    assert p["date_etablissement"] == date(2025, 3, 1)
    assert p["adresse"].startswith("12 Rue")
    assert p["id_ban"] == "97415_9999_00012"
    assert p["x_ban"] == 320828.97 and p["y_ban"] == 7676122.5


def test_parse_record_sans_numero():
    assert parse_record({"etiquette_dpe": "G"}) is None


def test_norm_et_parse_brut():
    assert _norm("Rue de l'Église") == "rue de l eglise"
    assert _parse_brut("12 bis rue des Lilas 97440 Saint-André") == ("12", "rue des lilas")
    assert _parse_brut("Chemin des Anglais 97419 La Possession") == (None, "chemin des anglais")
    assert _parse_brut("") is None


# ───────────────────────── DB : ingestion + signal ─────────────────────────

class _StubDpe:
    """Connecteur DPE factice : rejoue des enregistrements (aucun géocodage réseau)."""

    def __init__(self, records):
        self._records = records

    def fetch_commune(self, insee):
        yield from self._records


def _parcel(db, idu, commune, wkt):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i,:c, ST_SetSRID(ST_GeomFromText(:w),4326), ST_Transform(ST_SetSRID(ST_GeomFromText(:w),4326),2975)) "
        "ON CONFLICT (idu) DO NOTHING"), {"i": idu, "c": commune, "w": wkt})


def _ensure_adresses(db):
    from labuse.ingestion.ban_adresses import DDL_ADRESSES
    for stmt in DDL_ADRESSES.strip().split(";"):
        if stmt.strip():
            db.execute(text(stmt))
    db.execute(text("DELETE FROM adresse_parcelles"))
    db.execute(text("DELETE FROM adresses"))


def _adresse(db, id_ban, numero, voie, insee, lon, lat, idu):
    db.execute(text(
        "INSERT INTO adresses (id_ban, numero, voie, insee, geom, geom_2975, idu, rattachement) "
        "VALUES (:b,:n,:v,:i, ST_SetSRID(ST_Point(:lon,:lat),4326), "
        " ST_Transform(ST_SetSRID(ST_Point(:lon,:lat),4326),2975), :idu, 'parcelle') "
        "ON CONFLICT (id_ban) DO NOTHING"),
        {"b": id_ban, "n": numero, "v": voie, "i": insee, "lon": lon, "lat": lat, "idu": idu})


PARCEL_WKT = "POLYGON((55.290 -21.010, 55.292 -21.010, 55.292 -21.008, 55.290 -21.008, 55.290 -21.010))"


@pytest.mark.db
def test_rattachement_ban_locale_et_passoire(db_session):
    """Passe 1 : identifiant_ban → table adresses (IDU déjà rattaché)."""
    _ensure_adresses(db_session)
    _parcel(db_session, "97415000AB0001", "Saint-Paul", PARCEL_WKT)
    _adresse(db_session, "97415_9999_00012", "12", "Rue des Bougainvilliers", "97415",
             55.291, -21.009, "97415000AB0001")
    db_session.flush()
    res = ingest_commune(db_session, "97415", "Saint-Paul", connector=_StubDpe([REC]))
    assert res == {"dpe": 1, "geocodes": 1, "rattaches_parcelle": 1}

    row = db_session.execute(text(
        "SELECT parcelle_idu, rattachement FROM dpe_records WHERE numero_dpe='2397E0123456X'")).first()
    assert row[0] == "97415000AB0001" and row[1] == "ban_locale"

    # signal passoire : maison G récente rattachée → parcelle signalée
    passoire = db_session.execute(text(
        "SELECT idu, etiquette_dpe FROM v_passoire_thermique WHERE code_insee='97415'")).first()
    assert passoire[0] == "97415000AB0001" and passoire[1] == "G"

    rep = sample_report(db_session, "97415")
    assert rep["dpe"] == 1 and rep["maisons_fg"] == 1 and rep["parcelles_passoire"] == 1


@pytest.mark.db
def test_rattachement_point_ban(db_session):
    """Passe 2 : id_ban inconnu de la table locale → point BAN natif EPSG:2975 → ST_Contains."""
    _ensure_adresses(db_session)
    _parcel(db_session, "97415000AB0001", "Saint-Paul", PARCEL_WKT)
    db_session.flush()
    xy = db_session.execute(text(
        "SELECT ST_X(q.p), ST_Y(q.p) FROM "
        "(SELECT ST_Transform(ST_SetSRID(ST_Point(55.291,-21.009),4326),2975) AS p) q")).first()
    rec = {**REC, "identifiant_ban": "97415_0000",  # niveau voie → absent de `adresses`
           "coordonnee_cartographique_x_ban": xy[0], "coordonnee_cartographique_y_ban": xy[1]}
    res = ingest_commune(db_session, "97415", "Saint-Paul", connector=_StubDpe([rec]))
    assert res["rattaches_parcelle"] == 1
    row = db_session.execute(text(
        "SELECT parcelle_idu, rattachement FROM dpe_records WHERE numero_dpe='2397E0123456X'")).first()
    assert row[0] == "97415000AB0001" and row[1] == "point_ban"


@pytest.mark.db
def test_rattachement_adresse_locale(db_session):
    """Passe 3 : ni id_ban ni point BAN → adresse brute normalisée contre `adresses`."""
    _ensure_adresses(db_session)
    _parcel(db_session, "97415000AB0001", "Saint-Paul", PARCEL_WKT)
    _adresse(db_session, "97415_1234_00012", "12", "Rue des Bougainvilliers", "97415",
             55.291, -21.009, "97415000AB0001")
    db_session.flush()
    rec = {**REC, "identifiant_ban": None, "score_ban": None,
           "coordonnee_cartographique_x_ban": None, "coordonnee_cartographique_y_ban": None}
    res = ingest_commune(db_session, "97415", "Saint-Paul", connector=_StubDpe([rec]))
    assert res["rattaches_parcelle"] == 1
    row = db_session.execute(text(
        "SELECT parcelle_idu, rattachement FROM dpe_records WHERE numero_dpe='2397E0123456X'")).first()
    assert row[0] == "97415000AB0001" and row[1] == "adresse_locale"


@pytest.mark.db
def test_sans_rattachement_honnete(db_session):
    """Aucune passe ne matche → 'aucun', pas de faux signal (un aucun honnête vaut mieux)."""
    _ensure_adresses(db_session)
    rec = {**REC, "identifiant_ban": None, "score_ban": None,
           "coordonnee_cartographique_x_ban": None, "coordonnee_cartographique_y_ban": None}
    res = ingest_commune(db_session, "97415", "Saint-Paul", connector=_StubDpe([rec]))
    assert res["rattaches_parcelle"] == 0
    row = db_session.execute(text(
        "SELECT parcelle_idu, rattachement FROM dpe_records WHERE numero_dpe='2397E0123456X'")).first()
    assert row[0] is None and row[1] == "aucun"
    assert db_session.execute(text("SELECT count(*) FROM v_passoire_thermique")).scalar() == 0


@pytest.mark.db
def test_adresse_locale_ambigue_refusee(db_session):
    """Même (numéro, voie) → 2 parcelles DIFFÉRENTES : on refuse (pas de pari)."""
    _ensure_adresses(db_session)
    _parcel(db_session, "97415000AB0001", "Saint-Paul", PARCEL_WKT)
    _parcel(db_session, "97415000AB0002", "Saint-Paul",
            "POLYGON((55.294 -21.010, 55.296 -21.010, 55.296 -21.008, 55.294 -21.008, 55.294 -21.010))")
    _adresse(db_session, "97415_1234_00012", "12", "Rue des Bougainvilliers", "97415",
             55.291, -21.009, "97415000AB0001")
    _adresse(db_session, "97415_5678_00012", "12", "Rue des Bougainvilliers", "97415",
             55.295, -21.009, "97415000AB0002")
    db_session.flush()
    rec = {**REC, "identifiant_ban": None, "score_ban": None,
           "coordonnee_cartographique_x_ban": None, "coordonnee_cartographique_y_ban": None}
    res = ingest_commune(db_session, "97415", "Saint-Paul", connector=_StubDpe([rec]))
    assert res["rattaches_parcelle"] == 0


@pytest.mark.db
def test_ingest_idempotent(db_session):
    _ensure_adresses(db_session)
    conn = _StubDpe([{**REC, "identifiant_ban": None,
                      "coordonnee_cartographique_x_ban": None, "coordonnee_cartographique_y_ban": None}])
    ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)
    ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)   # re-run
    assert db_session.execute(text("SELECT count(*) FROM dpe_records")).scalar() == 1  # ON CONFLICT numero
