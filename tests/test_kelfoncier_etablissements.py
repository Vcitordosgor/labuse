"""KELFONCIER-FIX-1 (Lot H) — établissements sur la parcelle (rattachement BAN).

Le backfill île réel a rattaché 131 187 / 152 871 établissements de précision « adresse » (~9 s,
bien sous le plafond 30 min). Ici on verrouille (base de test) : la table est bien matérialisée,
et `_etablissements_block` sert nom · NAF fin · tranche d'effectif · état + régime collectif, en
MASQUANT le nom des unités non diffusibles (RGPD) et en n'affichant que la précision « adresse ».
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.42 -20.88,55.4203 -20.88,55.4203 -20.8797,55.42 -20.8797,55.42 -20.88))"


def test_constantes_precision_adresse():
    from labuse.ingestion.etablissement_parcelle import QUALITE_ADRESSE
    # « adresse » = 11 (plaque) + 12 (interpolée) ; « voie » (21) et « commune » (33) EXCLUES.
    assert QUALITE_ADRESSE == ("11", "12")
    assert "21" not in QUALITE_ADRESSE and "33" not in QUALITE_ADRESSE


def test_etablissements_block_nom_masque_et_naf(db_session):
    from labuse.api.app import _etablissements_block
    from labuse.ingestion.etablissement_parcelle import DDL
    for stmt in DDL.strip().split(";"):
        if stmt.strip():
            db_session.execute(text(stmt))
    idu = "97499000ET0001"
    db_session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'EtabVille','S','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": _WKT})
    # une unité DIFFUSIBLE (nom montré) et une NON diffusible (nom masqué RGPD), toutes deux précision 11
    db_session.execute(text(
        "INSERT INTO sirene_etablissements (siret, siren, naf, denomination, commune, insee, actif, diffusible, tranche_effectif, qualite_xy) "
        "VALUES ('99900000100011','999000001','6820B','SCI ETAB TEST','EtabVille','97499',true,true,'12','11')"))
    db_session.execute(text(
        "INSERT INTO sirene_etablissements (siret, siren, naf, denomination, commune, insee, actif, diffusible, qualite_xy) "
        "VALUES ('99900000200022','999000002','4711D','SECRET SARL','EtabVille','97499',true,false,'11')"))
    db_session.execute(text(
        "INSERT INTO etablissement_parcelle (siret, idu, precision) VALUES "
        "('99900000100011',:i,'11'),('99900000200022',:i,'11')"), {"i": idu})

    b = _etablissements_block(db_session, idu)
    assert b is not None and b["n"] == 2
    par_siret = {x["siret"]: x for x in b["liste"]}
    diff = par_siret["99900000100011"]
    assert diff["nom"] == "SCI ETAB TEST" and diff["nom_masque"] is False
    assert diff["naf"] == "6820B" and diff["precision"] == "11"
    assert diff["tranche_effectif"] == "20 à 49 salariés"      # code 12 → tranche lisible (jamais l'exact)
    masque = par_siret["99900000200022"]
    assert masque["nom_masque"] is True and "non diffusible" in masque["nom"].lower()


def test_etablissements_block_none_si_aucun(db_session):
    from labuse.api.app import _etablissements_block
    from labuse.ingestion.etablissement_parcelle import DDL
    for stmt in DDL.strip().split(";"):
        if stmt.strip():
            db_session.execute(text(stmt))
    assert _etablissements_block(db_session, "97499000ZZ9999") is None
