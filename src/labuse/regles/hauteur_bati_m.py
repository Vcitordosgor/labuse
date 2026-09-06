"""Fiche de règle — hauteur du bâti existant. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("hauteur_bati_m",),
    formule_codee=("h = max(hauteur des bâtiments BD TOPO intersectant la parcelle) en mètres "
                   "(attrs->>'hauteur' de spatial_layers kind=batiment) ; NULL si aucune hauteur "
                   "ingérée — jamais une invention."),
    entrees=("spatial_layers kind=batiment (attrs->hauteur, geom_2975)", "parcels.geom_2975"),
    classe="methode_standard",
    fonction="src/labuse/faisabilite/potentiel.py:_hauteur_bati_m",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_surelevation.py::test_hauteur_max_batiments",
    verifie_le="2026-09-06",
))
