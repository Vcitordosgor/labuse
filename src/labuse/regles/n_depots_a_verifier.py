"""Fiche de règle — file d'extraction Radar. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_depots_a_verifier",),
    formule_codee="n = count(pige_faits WHERE valide_at IS NULL) — faits déposés en attente de validation humaine.",
    entrees=("pige_faits.valide_at",),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/plateforme.py:depots_a_verifier",
    verdict="choix_assume",
    choix="La validation humaine est la porte du Radar (doctrine P0) : le compteur mesure la file.",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_depots_a_verifier",
    verifie_le="2026-09-06",
    moteur_fonctions=("plateforme.depots_a_verifier",),
))
