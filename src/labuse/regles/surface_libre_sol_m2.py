"""Fiche de règle — surface au sol libre restante. FICHE-1 lot 1 (CIRCUIT-4)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("surface_libre_sol_m2",),
    formule_codee=(
        "surface_libre = max(0, surface_parcelle − emprise_bâtie_au_sol), en m². L'emprise est "
        "l'empreinte vecteur BD TOPO (somme des intersections bâtiment ∩ parcelle), la même que "
        "`emprise_batie_m2` (cohérence avec le nombre de bâtiments). Plancher à 0 : jamais une "
        "surface libre négative même si le bâti déborde légèrement du contour cadastral."),
    entrees=("parcels.surface_m2", "emprise BD TOPO (spatial_layers kind='batiment')"),
    classe="choix_labuse",
    fonction="src/labuse/bati.py:le_bien_block",
    verdict="choix_assume",
    choix=("Définition LABUSE : « surface au sol libre » = surface cadastrale moins l'emprise "
           "bâtie au sol (BD TOPO), plancher 0. C'est une lecture au sol (pas un droit à bâtir "
           "résiduel, qui est la SDP résiduelle du potentiel) — les deux vivent côte à côte."),
    exemple_temoin="tests/test_fiche1_le_bien.py::test_emprise_coherente_avec_le_bati",
    valide_par="cc",
    verifie_le="2026-09-06",
))
