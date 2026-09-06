"""Fiche de règle — nature et pente du toit (LiDAR HD). FICHE-1 lot 1 (CIRCUIT-4)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    # une fiche pour LE calcul de toiture (nature + pente, mêmes producteur et entrées).
    donnees=("nature_toit", "pente_toit_deg"),
    formule_codee=(
        "Sur le MNH LiDAR HD (IGN, 50 cm, EPSG:2975) du plus grand bâtiment de la parcelle : pente "
        "= médiane du gradient d'altitude ; orientation des pans = histogramme de l'aspect en 16 "
        "secteurs, pics détectés, confiance = masse expliquée par les pics ± 1 secteur. La NATURE "
        "(plat / monopente / double_pente / croupe_complexe) n'est SERVIE que si confiance ≥ 0,70 "
        "(seuil calibré à l'œil sur 50 bâtiments contre l'ortho, 0 faux au seuil) ; sinon « non "
        "déterminée — pans non nets ». La PENTE médiane (mesure directe) est servie même sous le "
        "seuil. Échec technique WMS → « non calculée — LiDAR indisponible » (jamais une absence)."),
    entrees=("WMS MNH LiDAR HD IGN (bbox du bâtiment)", "spatial_layers (kind='batiment') plus "
             "grand bâtiment intersectant", "cache toiture_lidar"),
    classe="choix_labuse",
    fonction="src/labuse/solaire_toiture.py:analyse_toiture (_classify)",
    verdict="choix_assume",
    choix=("Choix LABUSE : classification heuristique du toit gelée au seuil de confiance 0,70 "
           "(RETOURS-15 S11), calibrée à l'ŒIL sur 50 bâtiments contre l'ortho (0 faux au seuil, "
           "~36 % des toits classés) — les autres restent honnêtement « non déterminée ». Sans "
           "norme externe opposable ; le témoin numérique n'est pas constructible hors du raster "
           "MNH LiDAR (SANS_TEMOIN_ASSUME, comme les autres calculs dépendant d'une source réseau)."),
    valide_par="cc",
    verifie_le="2026-09-06",
))
