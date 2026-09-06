"""Fiche de règle — distances aux objets les plus proches (KNN). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("distance_arret_m",),
    formule_codee=(
        "Objet `kind` le plus proche de la parcelle par KNN PostGIS (ORDER BY sl.geom_2975 <-> "
        "p.geom_2975 LIMIT 1), distance = round(ST_Distance(geom_2975, geom_2975))::int en MÈTRES "
        "(projection métrique RGR92 / UTM 40S, EPSG:2975) — distance euclidienne plane « à vol "
        "d'oiseau », jamais un temps de trajet. Doctrine M106 : PROXIMITÉ servie, jamais une "
        "appartenance — le lecteur juge. Le drapeau « stationnement allégé < 800 m d'une station "
        "TCSP » (art. L151-36) est dérivé de CETTE distance en aval (sous_800m = distance_m < 800)."),
    entrees=("spatial_layers (kind, subtype, geom_2975)", "parcels.geom_2975"),
    classe="methode_standard",
    fonction="src/labuse/registre/moteurs/parcelle.py:plus_proche",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_distance_knn.py::test_distance_euclidienne_temoin",
    verifie_le="2026-09-06",
    moteur_fonctions=("parcelle.plus_proche",),
))
