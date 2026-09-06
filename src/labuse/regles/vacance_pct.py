"""Fiche de règle — taux de vacance des logements (INSEE RP). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("vacance_pct",),
    formule_codee=("pct = 100 × logements_vacants ÷ logements_total (INSEE RP de la commune), "
                   "arrondi 0,1 ; None si le dénominateur manque ou est nul."),
    entrees=("commune_insee_logement (logements, vacants — INSEE RP)",),
    classe="regle_externe",
    fonction="src/labuse/registre/moteurs/commune.py:vacance_pct",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_vacance_pct",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.vacance_pct",),
))
