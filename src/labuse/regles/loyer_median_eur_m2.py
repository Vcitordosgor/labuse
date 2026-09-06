"""Fiche de règle — estimation locative. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("loyer_median_eur_m2",),
    formule_codee=("Estimation loyers.py — le DOUTE du catalogue des moteurs (moteurs.csv) est "
                   "reconduit tel quel : les entrées exactes restent à confirmer (fiche honnête, "
                   "pas une formule inventée)."),
    entrees=("à confirmer (DOUTE porté par moteurs.csv depuis CIRCUIT-2)",),
    classe="methode_standard",
    fonction="src/labuse/loyers.py:estimation",
    verdict="reference_introuvable",
    exemple_temoin=None,
    verifie_le="2026-09-06",
))
