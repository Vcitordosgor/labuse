"""Fiche de règle — mutations DVF sur 12 mois de données. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("mutations_12m_n",),
    formule_codee=(
        "n = count(dvf_mutations de la commune) WHERE date_mutation > max(date_mutation de la "
        "commune) − 12 mois — fenêtre ancrée sur la DERNIÈRE mutation CONNUE de la commune, pas "
        "sur la date du jour."),
    entrees=("dvf_mutations.date_mutation/commune",),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/commune.py:mutations_12m",
    verdict="choix_assume",
    choix=("Fenêtre « 12 derniers mois DE DONNÉES » : DVF est publié avec ~6 mois de retard ; une "
           "fenêtre calendaire afficherait un effondrement artificiel du marché. Choix documenté "
           "dans le code (CIRCUIT-2 lot 1.6)."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_mutations_12m_fenetre_donnees",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.mutations_12m",),
))
