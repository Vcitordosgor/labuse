"""SOURCES-4 lot 2 — CoSIA toutes classes par parcelle : la table est déclarée et le module
ordonne correctement le débit... non — ici on garde le contrat : `parcel_cosia_couverture` existe
au registre (sous le réservoir cosia) et le DDL/ensure_table est idempotent.
"""
from __future__ import annotations

from sqlalchemy import text
import pytest

from labuse.ingestion.cosia_couverture import TABLE, ensure_table


def test_parcel_cosia_couverture_declaree_au_registre():
    """La table de couverture CoSIA est rattachée au réservoir cosia (sinon V1c la voit orpheline)."""
    from labuse.registre import tables
    rt = tables.RESERVOIR_TABLES["cosia"]
    assert TABLE in rt.tables


@pytest.mark.db
def test_ensure_table_idempotent(db_session):
    ensure_table(db_session)
    ensure_table(db_session)   # idempotent
    cols = {r[0] for r in db_session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
        {"t": TABLE}).all()}
    assert {"idu", "classe", "m2", "source_millesime"} <= cols


def test_couche_cimetiere_declaree_et_servie():
    """SOURCES-4 lot 2 — cimetière (thème BD TOPO non doublon) rattaché au réservoir bd_topo (V1c)
    et servi en carte à popup riche (toponyme + nature au clic)."""
    from labuse.registre import tables
    assert "cimetiere" in tables.RESERVOIR_TABLES["bd_topo"].couches
    from labuse.api.app import _MAP_LAYER_KINDS, _RICH_POPUP_KINDS
    assert "cimetiere" in _MAP_LAYER_KINDS and "cimetiere" in _RICH_POPUP_KINDS
    from labuse.ingestion.layers_ingest import KIND_SOURCE
    assert KIND_SOURCE["cimetiere"] == "BD TOPO IGN"


def test_couche_piscine_declaree_et_servie():
    """SOURCES-4 lot 2 — la couche Piscines (polygones CoSIA) est rattachée au réservoir cosia
    (V1c) ET servie en carte à popup riche (surface + parcelle au clic)."""
    from labuse.registre import tables
    from labuse.ingestion.cosia_couverture import PISCINE_KIND
    assert PISCINE_KIND in tables.RESERVOIR_TABLES["cosia"].couches
    from labuse.api.app import _MAP_LAYER_KINDS, _RICH_POPUP_KINDS
    assert PISCINE_KIND in _MAP_LAYER_KINDS and PISCINE_KIND in _RICH_POPUP_KINDS
