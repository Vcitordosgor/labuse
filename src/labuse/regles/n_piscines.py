"""Fiche de règle — compte de piscines détectées. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_piscines",),
    formule_codee=(
        "count(parcel_equipements WHERE piscine IS TRUE), filtres alignés sur le listing : bâti "
        "(emprise p_model_bati > 0 / = 0 / tous), surface piscine ≥ seuil demandé, confiance "
        "(SEUIL_PISCINE_HAUTE sauf inclusion des incertaines), corrections humaines EXCLUES "
        "(piscine_corrections) ; total + ventilation par commune décroissante."),
    entrees=("parcel_equipements (piscine, piscine_surface_m2, confiance)", "p_model_bati.emprise_bati_m2",
             "piscine_corrections"),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/commune.py:compte_piscines",
    verdict="choix_assume",
    choix=("Détection GELÉE (BD ORTHO 2025, seuil de confiance mesuré ~90,7 % — RETOURS-14 : seuil "
           "toiture 0,70 = 0 faux positif sur 50 contrôles) ; les corrections humaines priment "
           "toujours la détection."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_piscines_corrections_excluses",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.compte_piscines",),
))
