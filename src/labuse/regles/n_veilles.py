"""Fiche de règle — veilles du compte. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_veilles",),
    formule_codee="Délégation : copilote_v2/veilles.py:lister — count des veilles du compte.",
    entrees=("veilles (compte_id)",),
    classe="choix_labuse",
    fonction="src/labuse/copilote_v2/veilles.py:lister (délégation plateforme_compteurs)",
    verdict="choix_assume",
    choix="Compte brut par périmètre de compte.",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_compteurs_delegues_existent",
    verifie_le="2026-09-06",
))
