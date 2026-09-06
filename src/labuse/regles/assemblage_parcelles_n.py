"""Fiche de règle — assemblage d'assiette (compte + surface). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("assemblage_parcelles_n", "assemblage_surface_m2"),
    formule_codee=(
        "assemblage_parcelles_n = compte des parcelles retenues dans l'assemblage courant ; "
        "assemblage_surface_m2 = Σ surface_m2 cadastrale des parcelles retenues. Délégation : la "
        "logique (contiguïté, agrégation fiche_payload, valorisation, plafonds config) vit dans "
        "api/moteurs.py:assemblage — une seule vérité."),
    entrees=("parcels.surface_m2", "sélection client (idus)"),
    classe="choix_labuse",
    fonction="src/labuse/api/moteurs.py:assemblage (délégation registre/moteurs/parcelle.py)",
    verdict="choix_assume",
    choix=("Surface d'assemblage = somme des surfaces CADASTRALES (pas une union géométrique "
           "dédoublonnée) : les parcelles cadastrales sont disjointes par construction."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_assemblage_somme",
    verifie_le="2026-09-06",
    moteur_fonctions=("parcelle.assemblage_assiette",),
))
