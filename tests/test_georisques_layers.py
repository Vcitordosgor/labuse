"""Géorisques Vague B — parsing des 3 couches (sol pollué, cavité, ICPE) + croisement parcelles.

Schémas figés sur des objets RÉELS vérifiés live 05/07/2026 (INSEE 97415 Saint-Paul).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion.georisques_layers import (
    KIND_SOURCE,
    _point,
    ingest_commune,
    parcelles_croisees,
    parse_cavite,
    parse_icpe,
    parse_mvt,
    parse_sol_pollue,
    sample_report,
)

# Objets RÉELS (simplifiés) — Saint-Paul.
CASIAS = {"identifiant_ssp": "SSP4037996", "identifiant_casias": "REU97400011",
          "nom_etablissement": "Sucrerie Domaine de Clermont", "adresse": "160 rue Evariste de Parny",
          "statut": "En arrêt", "code_insee": "97415",
          "fiche_risque": "https://fiches-risques.brgm.fr/georisques/casias/SSP4037996",
          "date_maj": "2014-12-04", "geom": {"type": "Point", "coordinates": [55.318224, -21.00714]}}
INSTRUCTION = {"identifiant_ssp": "SSP001101601", "nom_etablissement": "décharge de Cambaie",
               "statut": "En cours", "code_insee": "97415", "geom": {"type": "Point", "coordinates": [55.294626, -20.960209]}}
CAVITE = {"identifiant": "REUAW0021778", "type": "naturelle", "nom": "Lotissement des Cactées",
          "longitude": 55.22784, "latitude": -21.05505, "code_insee": "97415"}
ICPE = {"raisonSociale": "communauté d’agglomération du TCO", "regime": "Autorisation",
        "statutSeveso": "Non Seveso", "codeNaf": "75", "commune": "Saint-Paul",
        "codeInsee": "97415", "longitude": 55.294626, "latitude": -20.960209}


# ───────────────────────── parsing (pur) ─────────────────────────

def test_point_helper():
    assert _point(55.27, -21.01) == {"type": "Point", "coordinates": [55.27, -21.01]}
    assert _point(None, -21.01) is None
    assert _point("x", 1) is None


def test_parse_sol_pollue_casias():
    p = parse_sol_pollue("casias", CASIAS)
    assert p["kind"] == "sol_pollue" and p["subtype"] == "casias"
    assert p["name"] == "Sucrerie Domaine de Clermont"
    assert p["geometry"]["type"] == "Point"
    assert p["attrs"]["identifiant_casias"] == "REU97400011"
    assert "brgm.fr" in p["attrs"]["fiche_risque"]
    assert p["attrs"]["statut"] == "En arrêt"


def test_parse_sol_pollue_sans_geometrie_ignore():
    # Un site sans geom (fréquent sur casias) est inexploitable pour un croisement → écarté.
    assert parse_sol_pollue("casias", {**CASIAS, "geom": None}) is None
    assert parse_sol_pollue("casias", {**CASIAS, "geom": {"type": "Point"}}) is None  # pas de coords


def test_parse_cavite():
    p = parse_cavite(CAVITE)
    assert p["kind"] == "cavite" and p["subtype"] == "naturelle"
    assert p["name"] == "Lotissement des Cactées"
    assert p["geometry"]["coordinates"] == [55.22784, -21.05505]
    assert p["attrs"]["identifiant"] == "REUAW0021778"
    assert parse_cavite({"nom": "X"}) is None                    # pas de coordonnées → None


def test_parse_icpe():
    p = parse_icpe(ICPE)
    assert p["kind"] == "icpe" and p["subtype"] == "Autorisation"
    assert p["name"] == "communauté d’agglomération du TCO"
    assert p["attrs"]["statut_seveso"] == "Non Seveso"
    assert p["attrs"]["code_naf"] == "75"
    assert parse_icpe({"raisonSociale": "X"}) is None            # pas de coordonnées → None


def test_kind_source_mapping():
    assert set(KIND_SOURCE) == {"sol_pollue", "cavite", "icpe", "mvt"}


def test_parse_mvt():
    item = {"identifiant": "12700005", "type": "Coulée", "fiabilite": "Fort",
            "lieu": None, "longitude": 55.300026, "latitude": -21.007004, "code_insee": "97415"}
    p = parse_mvt(item)
    assert p["kind"] == "mvt" and p["subtype"] == "Coulée"
    assert p["name"] == "Coulée"                       # fallback sur le type quand lieu est null
    assert p["geometry"]["coordinates"] == [55.300026, -21.007004]
    assert p["attrs"]["fiabilite"] == "Fort"
    assert parse_mvt({"type": "Glissement"}) is None   # pas de coordonnées → None


# ───────────────────────── ingestion / croisement (DB) ─────────────────────────

class _StubGeo:
    """Connecteur Géorisques factice : rejoue des objets bruts, sans réseau."""

    def __init__(self, casias=(), instr=(), cav=(), icpe=()):
        self._casias, self._instr, self._cav, self._icpe = casias, instr, cav, icpe

    def sites_pollues(self, insee):
        for it in self._casias:
            yield "casias", it
        for it in self._instr:
            yield "instruction", it

    def cavites(self, insee):
        yield from self._cav

    def installations_classees(self, insee):
        yield from self._icpe


def _parcel(db, idu, commune, wkt):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i, :c, ST_SetSRID(ST_GeomFromText(:w), 4326), "
        " ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 4326), 2975)) "
        "ON CONFLICT (idu) DO NOTHING"),
        {"i": idu, "c": commune, "w": wkt})


@pytest.mark.db
def test_ingest_commune_et_volumetrie(db_session):
    conn = _StubGeo(casias=[CASIAS], instr=[INSTRUCTION], cav=[CAVITE], icpe=[ICPE])
    counts = ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)
    assert counts == {"sol_pollue": 2, "cavite": 1, "icpe": 1}

    rep = sample_report(db_session, "Saint-Paul")
    assert rep["volumetrie"] == {"sol_pollue": 2, "cavite": 1, "icpe": 1}
    assert len(rep["exemples"]) >= 1
    kinds = {e["kind"] for e in rep["exemples"]}
    assert kinds <= {"sol_pollue", "cavite", "icpe"}


@pytest.mark.db
def test_ingest_commune_idempotent(db_session):
    conn = _StubGeo(casias=[CASIAS], cav=[CAVITE])
    ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)
    ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)   # re-run purge + réinsère
    n = db_session.execute(text(
        "SELECT count(*) FROM spatial_layers WHERE commune='Saint-Paul' AND kind = ANY(:k)"),
        {"k": list(KIND_SOURCE)}).scalar()
    assert n == 2   # pas de doublon (1 casias + 1 cavité)


@pytest.mark.db
def test_parcelles_croisees_proximite(db_session):
    # Parcelle SOUS le point casias (Clermont) ; parcelle LOIN → non croisée.
    conn = _StubGeo(casias=[CASIAS])
    ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)
    _parcel(db_session, "97415000ZZ0001", "Saint-Paul",
            "POLYGON((55.3181 -21.0072, 55.3184 -21.0072, 55.3184 -21.0070, 55.3181 -21.0070, 55.3181 -21.0072))")
    _parcel(db_session, "97415000ZZ0002", "Saint-Paul",
            "POLYGON((55.20 -21.20, 55.201 -21.20, 55.201 -21.199, 55.20 -21.199, 55.20 -21.20))")
    db_session.flush()
    croise = parcelles_croisees(db_session, "Saint-Paul", rayon_m=50)
    assert croise["sol_pollue"] == 1     # seule la parcelle proche du site est croisée
    assert croise["cavite"] == 0 and croise["icpe"] == 0
