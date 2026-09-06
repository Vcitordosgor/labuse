"""Fiche de règle — compte de parcelles d'une commune. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_parcelles_commune",),
    formule_codee="n = count(*) FROM parcels WHERE commune = :c — compte brut, aucune fenêtre.",
    entrees=("parcels.commune",),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/commune.py:compte_parcelles_commune",
    verdict="choix_assume",
    choix=("Périmètre = les parcelles INGÉRÉES (cadastre Etalab, 24 communes) — un compte de base "
           "servie, pas un chiffre officiel DGFiP (le cadastre bouge ; le nôtre est daté par "
           "l'ingestion)."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_n_parcelles_commune",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.compte_parcelles_commune",),
))
