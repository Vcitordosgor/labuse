"""Fiche de règle — concurrents et emplois d'une zone (SIRENE). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_concurrents_zone", "emplois_fourchette"),
    formule_codee=(
        "n_concurrents = count(sirene_etablissements ACTIFS du code NAF choisi dans l'isochrone), "
        "chacun servi avec son temps d'accès (bande d'isochrone) ; les établissements en diffusion "
        "partielle ('P') sont masqués nominativement. emplois_fourchette = SOMME DES TRANCHES "
        "d'effectifs SIRENE (bornes basses et hautes des tranches sommées séparément) — toujours "
        "une FOURCHETTE, jamais un point (la source ne donne que des tranches)."),
    entrees=("sirene_etablissements (NAF, tranche d'effectifs, geo, statut de diffusion — INSEE "
             "SIRENE géolocalisé, 158 515 actifs 974)", "isochrone"),
    classe="regle_externe",
    fonction="src/labuse/zone.py:comptages_zone (+ etude_de_zone)",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_zone_insee.py::test_emplois_somme_de_tranches",
    verifie_le="2026-09-06",
))
