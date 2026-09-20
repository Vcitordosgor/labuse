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
    # COUCHES-RETRAIT-1 lot 3 — servie en carte par le TUYAU (l'ancien endpoint V1 /map/layers.geojson
    # + _MAP_LAYER_KINDS/_RICH_POPUP_KINDS est retiré ; la couche vit dans les déclarations du tuyau).
    from labuse.registre.declarations import couches_carte
    assert "cimetiere" in {c["kind"] for c in couches_carte()}
    from labuse.ingestion.layers_ingest import KIND_SOURCE
    assert KIND_SOURCE["cimetiere"] == "BD TOPO IGN"


def test_bdtopo_4_couches_declarees_et_servies():
    """SOURCES-4 lot 2 — les 4 thèmes BD TOPO (constructions lin/surf, zone d'activité, bassin
    versant) sont rattachés au réservoir bd_topo (V1c) et servis carte + popup riche."""
    from labuse.registre import tables
    from labuse.registre.declarations import couches_carte
    from labuse.ingestion.layers_ingest import KIND_SOURCE
    _servies = {c["kind"] for c in couches_carte()}   # COUCHES-RETRAIT-1 lot 3 — servies par le tuyau
    for k in ("construction_lineaire", "construction_surfacique", "zone_activite", "bassin_versant"):
        assert k in tables.RESERVOIR_TABLES["bd_topo"].couches, k
        assert k in _servies, k
        assert KIND_SOURCE[k] == "BD TOPO IGN", k


def test_piscine_hors_tuyau_vit_dans_solaire():
    """DONNEES-1 lot 2.1 — la couche Piscines (piscine_cosia) A QUITTÉ le panneau Couches / le tuyau
    (compteur du tuyau 56→55) et vit désormais dans le mode Piscines de Prospection solaire (points
    GeoJSON du module). Le kind spatial_layers reste rattaché au réservoir cosia (fiche : n_piscines /
    piscine_m2), mais il n'est plus une couche SERVIE par le tuyau."""
    from labuse.registre import tables
    from labuse.ingestion.cosia_couverture import PISCINE_KIND
    assert PISCINE_KIND in tables.RESERVOIR_TABLES["cosia"].couches   # kind stocké (fiche) : intact
    from labuse.registre.declarations import couches_carte
    assert PISCINE_KIND not in {c["kind"] for c in couches_carte()}   # plus servie par le tuyau
    from labuse.api.couches_tuyau import registre
    assert PISCINE_KIND not in registre()                            # compteur du tuyau ne la compte plus
