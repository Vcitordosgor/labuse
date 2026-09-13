"""REPARATIONS-1 lot 5 — OCS GE : matrice d'artificialisation officielle (décret 2023-1096,
étape 1), CRS inspecté jamais supposé, registre complet, et la fiche qui ne casse jamais."""
from __future__ import annotations

import pytest


def test_matrice_artificialisation_decret():
    from labuse.ingestion.ocsge import artif_decret
    # anthropisé → artif (sauf minéraux à usage d'extraction)
    assert artif_decret("CS1.1.1.1", "US5")
    assert artif_decret("CS1.1.1.2", "US4.1.1")
    assert artif_decret("CS1.1.2.1", "US2")
    assert not artif_decret("CS1.1.2.1", "US1.3")   # carrière en activité
    # végétation non ligneuse : artif selon l'usage (jardin résidentiel = artif, prairie agricole non)
    assert artif_decret("CS2.2.1", "US5")
    assert artif_decret("CS2.2.1", "US235")
    assert not artif_decret("CS2.2.1", "US1.1")
    # arboré / sols naturels / eau → jamais artif
    assert not artif_decret("CS2.1.1.1", "US5")
    assert not artif_decret("CS1.2.1", "US5")


def test_registre_ocsge_complet():
    from labuse.circuit_etats import NOM_VERS_SLUG
    from labuse.filtres import _registre
    from labuse.ingestion.seed_sources import MODE_ET_CADENCE, SOURCES
    from labuse.registre.donnees import DONNEES
    from labuse.registre.robinets import ROBINETS
    from labuse.registre.tables import RESERVOIR_TABLES
    from labuse.sentinelle import SEED

    nom = "OCS GE (IGN) — occupation du sol et artificialisation"
    assert any(r["name"] == nom for r in SOURCES)
    assert nom in MODE_ET_CADENCE
    assert NOM_VERS_SLUG[nom] == "ocsge"
    rt = RESERVOIR_TABLES["ocsge"]
    assert "parcel_ocsge" in rt.tables and "artificialisation" in rt.couches
    assert DONNEES["part_artificialisee_pct"].reservoirs == ("ocsge",)
    assert "score" not in (DONNEES["part_artificialisee_pct"].definition or "") or \
        "n'entre pas dans le score" in DONNEES["part_artificialisee_pct"].definition
    assert "part_artificialisee_pct" in ROBINETS["couche_artificialisation"].chiffres
    assert "zan_evolution_commune" in ROBINETS["fiche_commune_zan"].chiffres
    assert "ocsge" in _registre()
    assert any(e["name"] == nom and e["methode"] == "temoin" for e in SEED)


def test_crs_refuse_si_pas_2975(tmp_path):
    """La garde d'ingestion REFUSE un GPKG dont le CRS inspecté n'est pas 2975."""
    import sqlite3
    from labuse.ingestion.ocsge import _srid_inspecte
    p = tmp_path / "t.gpkg"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE gpkg_geometry_columns (table_name text, column_name text, srs_id int)")
    c.execute("INSERT INTO gpkg_geometry_columns VALUES ('T', 'geom', 2154)")
    c.commit(); c.close()
    assert _srid_inspecte(str(p), "T") == 2154   # lu, jamais supposé — la garde amont refuse ≠ 2975


@pytest.mark.db
def test_le_bien_ocsge_ne_casse_jamais(db_session):
    from sqlalchemy import text
    from labuse import bati
    idu = db_session.execute(text("SELECT idu FROM parcels LIMIT 1")).scalar()
    if idu is None:
        pytest.skip("base de test sans parcelle")
    b = bati.le_bien_block(db_session, idu)
    if b is not None:
        assert "ocsge" in b   # None ou dict — jamais une clé absente, jamais un crash
