"""Fiche de règle — part des parcelles touchées par une couche (PPR, mouvements). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("ppr_pct",),
    formule_codee=(
        "pct = 100 × count(DISTINCT parcelles de la commune intersectant la couche kind) ÷ "
        "total_parcelles(commune), arrondi 0,1 ; None si le dénominateur est nul. Intersection "
        "géométrique ST_Intersects(geom_2975)."),
    entrees=("parcels.geom_2975/commune", "spatial_layers.kind/geom_2975"),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/commune.py:pct_parcelles_couche",
    verdict="choix_assume",
    choix=(
        "Dénominateur = TOUTES les parcelles de la commune (pas la surface) ; numérateur = toute "
        "parcelle TOUCHÉE (une intersection même marginale compte). C'est une part d'EXPOSITION "
        "parcellaire, pas une part de territoire — le niveau d'aléa lui-même est un passe-plat du "
        "règlement DEAL (domaine de classes au registre)."),
    exemple_temoin="tests/regles/test_ppr_pct.py::test_part_intersection_temoin",
    verifie_le="2026-09-06",
    moteur_fonctions=("commune.pct_parcelles_couche",),
))
