"""Fiche de règle — population/revenu d'une zone (Filosofi 200 m). CIRCUIT-4 (lot 2)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("population_zone", "revenu_approche_eur"),
    formule_codee=(
        "population_zone = Σ ind (individus) des carreaux Filosofi 200 m INTERSECTANT l'isochrone "
        "(un carreau touché compte entier — maille source, pas de proratisation). "
        "revenu_approche_eur = niveau de vie APPROCHÉ : moyenne des carreaux COUVERTS portant la "
        "donnée, servie « valeur approchée N/M carreaux » (piloté i_est_200 : l'INSEE impute une "
        "partie des carreaux — l'affichage le dit, jamais une précision inventée)."),
    entrees=("filosofi_carreaux_200m (ind, revenus, i_est_200 — INSEE Filosofi, carreaux 200 m)",
             "isochrone (fiche zone)"),
    classe="regle_externe",
    fonction="src/labuse/zone.py:population_zone",
    verdict="conforme",
    reference=Reference(
        titre="INSEE — données carroyées Filosofi (documentation officielle)",
        article="documentation des données carroyées 200 m (indicateur d'imputation i_est_200)",
        url="https://www.insee.fr/fr/statistiques/fichier/8735106/documentation_donnees-carroyees_filosofi2021.pdf",
        version="millésime Filosofi 2021 (documentation INSEE, consultée 2026-09-06)",
        extrait=("« Sur certains carreaux, le nombre de ménages fiscaux peut être inférieur à 11, "
                 "qui est le seuil de confidentialité pour les sources fiscales. Dans ce cas, les "
                 "données présentes dans le fichier sont imputées, et l'utilisateur en est informé "
                 "par un indicateur i_est_200 qui vaut 1 en cas d'imputation. » (documentation "
                 "données carroyées Filosofi ; le carroyage 200 m couvre ind, ménages, logements "
                 "et revenus.)"),
        lu_le="2026-09-06"),
    choix=("Un carreau INTERSECTANT compte ENTIER (pas de prorata) : prudence sur une maille déjà "
           "floutée — la proratisation simulerait une précision que la source n'a pas."),
    exemple_temoin="tests/regles/test_zone_insee.py::test_somme_carreaux_intersectants",
    valide_par="cc",
    verifie_le="2026-09-06",
))
