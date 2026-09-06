"""Fiche de règle — taux de vacance (INSEE RP). CIRCUIT-4 (lot 2 : extrait daté)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("vacance_pct",),
    formule_codee=("pct = 100 × logements_vacants ÷ logements_total (INSEE RP de la commune), "
                   "arrondi 0,1 ; None si le dénominateur manque ou est nul."),
    entrees=("commune_insee_logement (logements, vacants — INSEE RP)",),
    classe="regle_externe",
    fonction="src/labuse/registre/moteurs/commune.py:vacance_pct",
    verdict="conforme",
    reference=Reference(
        titre="INSEE — définition « Logement vacant »",
        article="métadonnées, définition c1059",
        url="https://www.insee.fr/fr/metadonnees/definition/c1059",
        version="mise à jour du 25/01/2021",
        extrait=("« Un logement est vacant s'il est inoccupé et proposé à la vente, à la location, "
                 "déjà attribué à un acheteur ou un locataire et en attente d'occupation, en "
                 "attente de règlement de succession, conservé par un employeur pour un usage "
                 "futur au profit d'un de ses employés, sans affectation précise par le "
                 "propriétaire (logement vétuste, etc.). »"),
        lu_le="2026-09-06"),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_vacance_pct",
    valide_par="cc",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.vacance_pct",),
))
