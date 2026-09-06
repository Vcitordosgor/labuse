"""Fiche de règle — concurrents/emplois d'une zone (SIRENE). CIRCUIT-4 (lot 2)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("n_concurrents_zone", "emplois_fourchette"),
    formule_codee=(
        "n_concurrents = count(sirene_etablissements ACTIFS du code NAF choisi dans l'isochrone), "
        "chacun servi avec son temps d'accès (bande d'isochrone) ; les établissements en diffusion "
        "partielle ('P') sont masqués nominativement. emplois_fourchette = SOMME DES TRANCHES "
        "d'effectifs SIRENE (bornes basses et hautes des tranches sommées séparément) — toujours "
        "une FOURCHETTE, jamais un point (la source ne donne que des tranches)."),
    entrees=("sirene_etablissements (NAF, tranche d'effectifs, geo, statut de diffusion)", "isochrone"),
    classe="regle_externe",
    fonction="src/labuse/zone.py:comptages_zone (+ etude_de_zone)",
    verdict="conforme",
    reference=Reference(
        titre="INSEE SIRENE — nomenclature des tranches d'effectifs salariés (établissement)",
        article="variable trancheEffectifsEtablissement (codes NN, 00, 01…53)",
        url="https://entreprise.api.gouv.fr/catalogue/insee/etablissements",
        version="nomenclature SIRENE en vigueur (consultée 2026-09-06)",
        extrait=("Codes des tranches : « NN : Unités non employeuses ; 00 : 0 salarié ; 01 : 1 ou "
                 "2 salariés ; 02 : 3 à 5 salariés ; 03 : 6 à 9 salariés ; 11 : 10 à 19 ; 12 : 20 "
                 "à 49 ; 21 : 50 à 99 ; 22 : 100 à 199 ; 31 : 200 à 249 ; 32 : 250 à 499 ; 41 : "
                 "500 à 999 ; 42 : 1 000 à 1 999 ; 51 : 2 000 à 4 999 ; 52 : 5 000 à 9 999 ; 53 : "
                 "10 000 salariés et plus » — la source ne donne que des TRANCHES, jamais un "
                 "effectif exact."),
        lu_le="2026-09-06"),
    exemple_temoin="tests/regles/test_zone_insee.py::test_emplois_somme_de_tranches",
    valide_par="cc",
    verifie_le="2026-09-06",
))
