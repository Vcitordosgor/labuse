"""SOLAIRE M1 — garde-fous du builder parcel_solar (ingestion/solaire.py).

Le builder complet a besoin du réseau (PVGIS) et du parc entier : il ne se teste pas en CI. Ici on
verrouille ce qui EST hermétique — la config, le millésime porté, et le SCHÉMA CIBLE (14 colonnes,
proxys morts abandonnés). Le test « ordres de grandeur vs donnée gelée » (100 parcelles témoins) vit
dans qa/solaire/temoin.py (il compare la base reconstruite au snapshot d'avant reconstruction)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import solaire


def test_config_et_millesime():
    c = solaire._cfg()
    assert c["pvgis"]["aspect_deg"] == 180          # plein nord (hémisphère sud)
    assert c["pvgis"]["grid_step_m"] == 400
    assert {"proprio_min", "proprio_max", "azimut_elongation_min"} <= set(c["flags"])
    m = solaire.source_millesime()
    assert "PVGIS" in m and "SARAH3" in m            # millésime porté, lisible


@pytest.mark.db
def test_ensure_schema_14_colonnes_proxys_abandonnes(db_session):
    solaire.ensure_schema(db_session)
    cols = {r[0] for r in db_session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'parcel_solar'"))}
    assert len(cols) == 14, f"parcel_solar doit avoir 14 colonnes, a {len(cols)} : {sorted(cols)}"
    # proxys morts ABANDONNÉS (mandat)
    assert not ({"pv_existant", "conso_est_kwh_an", "facture_est_eur_mois",
                 "flag_amiante", "repowering"} & cols)
    # colonnes servies / mensuel présentes
    assert {"prod_spec_kwh_kwc", "prod_mensuel", "mois_optimal", "azimut_bati_deg",
            "azimut_confiance", "flag_abf", "flag_topo_ombrage", "flag_ombrage_vegetal",
            "proba_proprio_occupant", "source_millesime"} <= cols
    # solar_grid porte le mensuel
    gcols = {r[0] for r in db_session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'solar_grid'"))}
    assert "prod_mensuel" in gcols and "ghi_kwh_m2_an" in gcols
