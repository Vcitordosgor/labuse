"""Fiche de règle — potentiel solaire de toiture (PVGIS). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("prod_spec_kwh_kwc", "azimut_bati_deg"),
    formule_codee=(
        "prod_spec = productible spécifique PVGIS (kWh/kWc/an, base SARAH3) au point de la grille "
        "solaire la plus proche, gelé au run du builder (parcel_solar, millésime porté en base) ; "
        "azimut_bati = azimut du bâti principal estimé de l'orientation du rectangle englobant "
        "orienté (ST_OrientedEnvelope) du bâtiment — ÉTIQUETÉ Estimé."),
    entrees=("solar_grid (PVGIS SARAH3)", "spatial_layers kind=batiment", "parcel_vegetation",
             "filosofi_carreaux_200m"),
    classe="methode_standard",
    fonction="src/labuse/ingestion/solaire.py:build_grid/build_solar",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_solaire.py::test_azimut_rectangle_oriente",
    verifie_le="2026-09-06",
))
