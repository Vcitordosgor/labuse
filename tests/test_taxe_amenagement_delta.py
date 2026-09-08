"""TAXE-AMÉNAGEMENT-1 lot A — ingestion des taux communaux depuis le jeu DGFiP DELTA.

On gèle le COMPORTEMENT du chargeur (sans réseau, via des enregistrements injectés) :
- le taux communal GÉNÉRAL est retenu, l'INSEE est reconstruit (974 + 2 chiffres) ;
- deux délibérations successives → on garde la date d'effet la plus récente ;
- un taux hors bornes [0 ; 20] est écarté et listé (aucun taux aberrant n'entre) ;
- une commune absente de la source est signalée (jamais un taux inventé pour combler) ;
- la part départementale est REMONTÉE (confirmation) sans entrer dans la table communale.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import taxe_amenagement_delta as ta

pytestmark = pytest.mark.db


def _rec(commune, taux, effet="2022-01-01", dep="974", def_prov="DEFINITIF",
         zone="Communale", libelle="X"):
    return {"departement": dep, "commune": commune, "taux": taux, "date_effet": effet,
            "date_fin": None, "def_prov": def_prov, "zone_application": zone,
            "libelle_commune": libelle}


def test_ingestion_remplit_la_table_par_insee(db_session):
    recs = [_rec("01", 5.0, libelle="LES AVIRONS"),
            _rec("11", 3.0, libelle="SAINT-DENIS"),
            _rec("19", 1.0, libelle="SAINTE-ROSE")]
    res = ta.ingest_taxe_amenagement(
        db_session, records_communaux=recs,
        record_departemental=_rec(None, 2.5, zone="Départementale", libelle=None))
    assert res["n"] == 3
    assert set(res["communes"]) == {"97401", "97411", "97419"}
    assert res["taux_departemental_pct"] == 2.5
    rows = dict(db_session.execute(text(
        "SELECT insee, part_communale_pct FROM taxe_amenagement_taux")).all())
    assert rows == {"97401": 5.0, "97411": 3.0, "97419": 1.0}


def test_garde_la_deliberation_la_plus_recente(db_session):
    recs = [_rec("07", 5.0, effet="2022-01-01"),   # ancienne
            _rec("07", 3.0, effet="2025-01-01")]   # en vigueur
    ta.ingest_taxe_amenagement(db_session, records_communaux=recs)
    row = db_session.execute(text(
        "SELECT part_communale_pct, delib_date FROM taxe_amenagement_taux WHERE insee='97407'"
    )).one()
    assert float(row[0]) == 3.0
    assert row[1].isoformat() == "2025-01-01"


def test_taux_hors_bornes_ecarte_et_liste(db_session):
    recs = [_rec("01", 5.0), _rec("02", 99.0)]     # 99 % = aberrant → écarté
    res = ta.ingest_taxe_amenagement(db_session, records_communaux=recs)
    assert res["n"] == 1
    assert any("97402=99" in h for h in res["hors_bornes"])
    n = db_session.execute(text("SELECT count(*) FROM taxe_amenagement_taux")).scalar()
    assert n == 1


def test_commune_absente_signalee_jamais_inventee(db_session):
    res = ta.ingest_taxe_amenagement(db_session, records_communaux=[_rec("11", 3.0)])
    assert res["n"] == 1
    assert len(res["manquantes"]) == 23     # 24 attendues − 1 présente
    assert "Les Avirons" in res["manquantes"]


def test_source_datee_et_sourcee(db_session):
    ta.ingest_taxe_amenagement(db_session, records_communaux=[_rec("11", 3.0)])
    src = db_session.execute(text(
        "SELECT source FROM taxe_amenagement_taux WHERE insee='97411'")).scalar()
    assert "DELTA" in src and ta.DATASET in src
