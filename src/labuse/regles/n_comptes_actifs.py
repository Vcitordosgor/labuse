"""Fiche de règle — comptes actifs. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_comptes_actifs",),
    formule_codee="n = count(comptes WHERE statut = 'actif').",
    entrees=("comptes.statut",),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/plateforme.py:comptes_actifs",
    verdict="choix_assume",
    choix="Actif = statut applicatif 'actif' (suspendu/essai expiré exclus).",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_comptes_actifs",
    verifie_le="2026-09-06",
    moteur_fonctions=("plateforme.comptes_actifs",),
))
