"""DPE ADEME (Vague C2) — parsing + rattachement parcelle (géocodage BAN) + signal passoire.

Champs figés sur un enregistrement RÉEL vérifié live 05/07/2026 (jeu dpe03existant, INSEE 97415).
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text

from labuse.connectors.dpe import in_reunion
from labuse.ingestion.dpe import ingest_commune, parse_record, sample_report

REC = {"numero_dpe": "2397E0123456X", "etiquette_dpe": "G", "etiquette_ges": "E",
       "type_batiment": "maison", "surface_habitable_logement": "112.5",
       "annee_construction": "1985", "adresse_ban": "12 Rue des Bougainvilliers 97460 Saint-Paul",
       "code_insee_ban": "97415", "code_postal_ban": "97460", "date_etablissement_dpe": "2025-03-01"}


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


def test_parse_record_sans_numero():
    assert parse_record({"etiquette_dpe": "G"}) is None


# ───────────────────────── DB : ingestion + signal ─────────────────────────

class _StubDpe:
    """Connecteur DPE factice : rejoue des enregistrements et un géocodage déterministe."""

    def __init__(self, records, coords):
        self._records = records
        self._coords = coords          # numero_dpe → (lon, lat, score) ou None

    def fetch_commune(self, insee):
        yield from self._records

    def geocode(self, adresse, citycode):
        # renvoie les coords associées au 1er record dont l'adresse matche (simplification test)
        return self._coords


def _parcel(db, idu, commune, wkt):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i,:c, ST_SetSRID(ST_GeomFromText(:w),4326), ST_Transform(ST_SetSRID(ST_GeomFromText(:w),4326),2975)) "
        "ON CONFLICT (idu) DO NOTHING"), {"i": idu, "c": commune, "w": wkt})


@pytest.mark.db
def test_ingest_rattachement_et_passoire(db_session):
    _parcel(db_session, "97415000AB0001", "Saint-Paul",
            "POLYGON((55.290 -21.010, 55.292 -21.010, 55.292 -21.008, 55.290 -21.008, 55.290 -21.010))")
    db_session.flush()
    # géocodage tombe DANS la parcelle → rattachement 'geocode'
    conn = _StubDpe([REC], coords=(55.291, -21.009, 0.7))
    res = ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)
    assert res == {"dpe": 1, "geocodes": 1, "rattaches_parcelle": 1}

    row = db_session.execute(text(
        "SELECT parcelle_idu, rattachement FROM dpe_records WHERE numero_dpe='2397E0123456X'")).first()
    assert row[0] == "97415000AB0001" and row[1] == "geocode"

    # signal passoire : maison G récente rattachée → parcelle signalée
    passoire = db_session.execute(text(
        "SELECT idu, etiquette_dpe FROM v_passoire_thermique WHERE code_insee='97415'")).first()
    assert passoire[0] == "97415000AB0001" and passoire[1] == "G"

    rep = sample_report(db_session, "97415")
    assert rep["dpe"] == 1 and rep["maisons_fg"] == 1 and rep["parcelles_passoire"] == 1


@pytest.mark.db
def test_geocode_hors_reunion_non_rattache(db_session):
    # géocodage hors Réunion (faux geopoint) → non rattaché, pas de faux signal.
    conn = _StubDpe([REC], coords=None)   # geocode() renvoie None (hors Réunion filtré en amont)
    res = ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)
    assert res["rattaches_parcelle"] == 0
    row = db_session.execute(text(
        "SELECT parcelle_idu, rattachement FROM dpe_records WHERE numero_dpe='2397E0123456X'")).first()
    assert row[0] is None and row[1] == "aucun"
    assert db_session.execute(text("SELECT count(*) FROM v_passoire_thermique")).scalar() == 0


@pytest.mark.db
def test_ingest_idempotent(db_session):
    conn = _StubDpe([REC], coords=None)
    ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)
    ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)   # re-run
    assert db_session.execute(text("SELECT count(*) FROM dpe_records")).scalar() == 1  # ON CONFLICT numero
