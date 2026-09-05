"""CIRCUIT-3 lot 6 — SOURCES-1 par la vanne.

6.1 CatNat : ingestion PAGINÉE (plus de troncature à 10/commune) + filtre de complétude vs le
producteur. 6.2 Taxe d'aménagement : la calculette utilise le taux PUBLIC dès qu'il existe (n'exige
plus le saisi) et expose l'écart saisi↔public.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import filtres, taxe_amenagement as ta
from labuse.filtres import cadre
from labuse.filtres.cadre import Filtre
from labuse.ingestion import catnat as catnat_mod

pytestmark = pytest.mark.db


class _FakeConnector:
    """Rend 15 arrêtés pour une commune (au-delà de l'ancienne troncature à 10)."""
    def catnat_arretes(self, code_insee):
        for i in range(15):
            yield {"libelle_risque_jo": f"peril-{i}", "libelle_commune": "Test",
                   "date_publication_arrete": f"0{1+i%9}/01/2020",
                   "date_debut_evt": f"0{1+i%9}/01/2020", "date_fin_evt": "02/01/2020"}


def test_catnat_ingest_ne_tronque_plus(db_session):
    for stmt in catnat_mod.DDL.split(";"):
        if stmt.strip():
            db_session.execute(text(stmt))
    db_session.execute(text("DELETE FROM catnat_arretes WHERE insee = '97499'"))
    db_session.commit()
    res = catnat_mod.ingest_catnat(db_session, connector=_FakeConnector(), insee_list=["97499"])
    db_session.commit()
    assert res["arretes"] == 15          # les 15, pas 10
    n = db_session.execute(text("SELECT count(*) FROM catnat_arretes WHERE insee='97499'")).scalar()
    assert n == 15
    db_session.execute(text("DELETE FROM catnat_arretes WHERE insee='97499'"))
    db_session.commit()


def test_catnat_connector_a_une_methode_paginee():
    from labuse.connectors.georisques import GeorisquesConnector
    assert hasattr(GeorisquesConnector, "catnat_arretes")


def test_catnat_completude_vs_reference(db_session):
    """Le contrôle de complétude KO si une commune est SOUS sa référence producteur."""
    for stmt in catnat_mod.DDL.split(";"):
        if stmt.strip():
            db_session.execute(text(stmt))
    from labuse.filtres.sources import CATNAT_REFERENCE
    assert sum(CATNAT_REFERENCE.values()) > 400  # référence producteur réelle (~427)
    f = filtres.get_filtre("catnat")
    assert f is not None and any(c.id == "d_completude_catnat" for c in f.propres)
    # une commune servie SOUS sa référence → KO
    insee = "97415"
    db_session.execute(text("DELETE FROM catnat_arretes WHERE insee = :i"), {"i": insee})
    db_session.execute(text(
        "INSERT INTO catnat_arretes (insee, type_peril, date_arrete, date_debut) "
        "VALUES (:i,'p','2020-01-01','2020-01-01')"), {"i": insee})
    db_session.commit()
    ctrl = [c for c in f.propres if c.id == "d_completude_catnat"][0]
    r = ctrl.mesure(db_session, f, "v")
    assert r.verdict == "ko"
    assert any(x["insee"] == insee for x in r.details["sous_reference"])


def test_taxe_public_prime_quand_pas_de_saisi():
    """Sans taux saisi mais AVEC taux public → la calculette calcule (n'exige plus le saisi)."""
    r = ta.calculer(surface_taxable_m2=100, taux_communal_pct=None,
                    taux_departemental_pct=2.5, taux_communal_public_pct=3.0,
                    taux_communal_public_source="délibération 2024")
    assert r["taux_communal_source"] == "public"
    assert r["taux_communal_manquant"] is False
    assert r["total_eur"] is not None


def test_taxe_ecart_saisi_public_expose():
    """Saisi + public présents → le saisi prime, l'écart est exposé (contrôle qualité)."""
    r = ta.calculer(surface_taxable_m2=100, taux_communal_pct=3.5,
                    taux_departemental_pct=2.5, taux_communal_public_pct=3.0)
    assert r["taux_communal_source"] == "saisi"
    assert r["ecart_saisi_public_pct"] == 0.5


def test_taxe_toujours_sans_taux_reste_non_calcule():
    r = ta.calculer(surface_taxable_m2=100, taux_communal_pct=None, taux_departemental_pct=2.5)
    assert r["taux_communal_manquant"] is True
    assert r["total_eur"] is None


def test_taxe_filtre_couverture(db_session):
    db_session.execute(text(ta._TAUX_DDL))
    f = filtres.get_filtre("taxe_amenagement")
    assert f is not None
    v = cadre.jouer(db_session, f, version="t1")
    db_session.commit()
    r = {x["controle"]: x for x in v.resultats}["d_taux_public_couverture"]
    assert r["verdict"] in ("ko", "ok")  # ko tant que < 24 communes (état pending honnête)
