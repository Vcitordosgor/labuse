"""Fiche de règle — « autres logés » (complément des statuts d'occupation INSEE). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("autres_loges_pct",),
    formule_codee=("pct = max(0 ; 100 − locataires_pct − proprietaires_pct), arrondi 0,1 "
                   "(round(x×10)/10). Calculé au serveur (CIRCUIT-1 lot 2.4), jamais au front."),
    entrees=("locataires_pct, proprietaires_pct (INSEE RP, statuts d'occupation)",),
    classe="regle_externe",
    fonction="src/labuse/registre/moteurs/commune.py:autres_loges_pct",
    verdict="reference_introuvable",
    choix=("Plancher 0 : des parts INSEE arrondies peuvent sommer à > 100 ; on ne sert jamais un "
           "complément négatif."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_autres_loges_complement",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.autres_loges_pct",),
))
