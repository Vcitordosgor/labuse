"""Fiche de règle — bâti révélé (emprise + compte). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("emprise_batie_m2", "n_batiments"),
    formule_codee=(
        "Par parcelle : emprise = aire de l'intersection géométrique des bâtiments (BD TOPO "
        "kind=batiment) avec la parcelle, COMPLÉTÉE par l'emprise CoSIA (couverture du sol IA) là "
        "où BD TOPO rate le bâti — on retient la mesure la plus grande (bâti « révélé », M32) ; "
        "n_batiments = compte des bâtiments intersectants. Table parcel_bati_revele, versionnée au "
        "run."),
    entrees=("spatial_layers kind=batiment (BD TOPO)", "CoSIA (emprise_cosia_m2)", "parcels.geom_2975"),
    classe="methode_standard",
    fonction="src/labuse/faisabilite/bati_revele.py:build_parcel_bati_revele",
    verdict="reference_introuvable",
    exemple_temoin=None,
    verifie_le="2026-09-06",
))
