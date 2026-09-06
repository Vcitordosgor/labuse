"""Fiche de règle — population et revenu d'une zone (carreaux Filosofi). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("population_zone", "revenu_approche_eur"),
    formule_codee=(
        "population_zone = Σ ind (individus) des carreaux Filosofi 200 m INTERSECTANT l'isochrone "
        "(un carreau touché compte entier — maille source, pas de proratisation). "
        "revenu_approche_eur = niveau de vie APPROCHÉ : moyenne des carreaux COUVERTS portant la "
        "donnée, servie « valeur approchée N/M carreaux » (piloté i_est_200 : l'INSEE impute une "
        "partie des carreaux — l'affichage le dit, jamais une précision inventée)."),
    entrees=("filosofi_carreaux_200m (ind, revenus, i_est_200 — INSEE Filosofi 2019, carreaux 200 m)",
             "isochrone (fiche zone)"),
    classe="regle_externe",
    fonction="src/labuse/zone.py:population_zone",
    verdict="reference_introuvable",
    choix=("Un carreau INTERSECTANT compte ENTIER (pas de découpe au prorata de surface) : choix de "
           "prudence sur une maille déjà floutée par l'INSEE — l'ordre de grandeur est honnête, la "
           "proratisation simulerait une précision que la source n'a pas."),
    exemple_temoin="tests/regles/test_zone_insee.py::test_somme_carreaux_intersectants",
    verifie_le="2026-09-06",
))
