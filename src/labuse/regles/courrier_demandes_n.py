"""Fiche de règle — demandes de courrier. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("courrier_demandes_n",),
    formule_codee="Délégation : courrier.py:demandes_de — count des demandes de courrier du compte.",
    entrees=("courrier_demandes (compte_id)",),
    classe="choix_labuse",
    fonction="src/labuse/courrier.py:demandes_de (délégation plateforme_compteurs)",
    verdict="choix_assume",
    choix="Compte brut par périmètre de compte.",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_compteurs_delegues_existent",
    verifie_le="2026-09-06",
))
