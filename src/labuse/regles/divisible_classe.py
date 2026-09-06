"""Fiche de règle — divisibilité (« division d'or »). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("divisible_classe",),
    formule_codee=("Présence dans division_or_candidates (candidates à la division parcellaire : "
                   "géométrie, bâti CoSIA, zone PLU — heuristique du builder division-or), run figé "
                   "q_v10, workflow de REVUE humaine par commune (la classe dit la revue, pas une "
                   "certitude)."),
    entrees=("parcels (géométrie)", "CoSIA (bâti)", "parcel_zone_plu"),
    classe="choix_labuse",
    fonction="src/labuse/ingestion/division_or.py:build",
    verdict="choix_assume",
    choix=("Heuristique LABUSE assumée (candidates À REVOIR, jamais « divisible » certifié) ; le "
           "run q_v10 en retard est une dette connue du catalogue des moteurs (toléré par la "
           "garde, workflow de revue)."),
    exemple_temoin=None,
    verifie_le="2026-09-06",
))
