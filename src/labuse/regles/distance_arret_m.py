"""Fiche de règle — distances KNN + drapeau stationnement (L151-36). CIRCUIT-4 (lot 2)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    # FICHE-1 lot 4 — tcsp_stationnement_allege (fiche parcelle) est le MÊME drapeau sous_800m
    # (station de transport en site propre, L151-36), servi comme classe : même règle, même calcul.
    donnees=("distance_arret_m", "tcsp_stationnement_allege",),
    formule_codee=(
        "Objet `kind` le plus proche de la parcelle par KNN PostGIS (ORDER BY sl.geom_2975 <-> "
        "p.geom_2975 LIMIT 1), distance = round(ST_Distance(geom_2975, geom_2975))::int en MÈTRES "
        "(projection métrique EPSG:2975) — distance euclidienne plane « à vol d'oiseau ». Doctrine "
        "M106 : PROXIMITÉ servie, jamais une appartenance. Le drapeau « stationnement allégé » "
        "(app.py) est dérivé de CETTE distance : sous_800m = (d < 800), STRICT comme le texte."),
    entrees=("spatial_layers (kind, subtype, geom_2975)", "parcels.geom_2975"),
    classe="methode_standard",
    fonction="src/labuse/registre/moteurs/parcelle.py:plus_proche (+ api/app.py drapeau sous_800m)",
    verdict="conforme",
    reference=Reference(
        titre="Code de l'urbanisme — plafond de stationnement près des transports",
        article="art. L151-36 (mod. loi n° 2025-1129 du 26/11/2025, art. 20) ; art. L151-35 (0,5 aire)",
        url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031211239",
        version="en vigueur depuis le 28/11/2025",
        extrait=("L151-36 : « Pour les constructions destinées à l'habitation, autres que celles "
                 "mentionnées aux 1° à 3° de l'article L. 151-34, situées à moins de huit cents "
                 "mètres d'une gare ou d'une station de transport public guidé ou de transport "
                 "collectif en site propre et dès lors que la qualité de la desserte le permet, il "
                 "ne peut, nonobstant toute disposition du plan local d'urbanisme, être exigé la "
                 "réalisation de plus d'une aire de stationnement par logement. » L151-35 (même "
                 "version) : à moins de 800 m, « il ne peut être exigé la réalisation de plus de "
                 "0,5 aire de stationnement par logement » pour les logements aidés/résidences "
                 "des 1° à 3° de L151-34."),
        lu_le="2026-09-06"),
    choix=("CORRIGÉ AU LOT 6 (E1, arithmétique pure) : le code posait `d <= 800` (large) quand le "
           "texte dit « à MOINS de » (strict) — désormais `d < 800`, témoin épinglé "
           "(test_drapeau_800_strict). L'interprétation « à vol d'oiseau » (euclidienne plane "
           "2975) est un choix dit — le texte ne précise pas le mode de mesure."),
    exemple_temoin="tests/regles/test_distance_knn.py::test_distance_euclidienne_temoin",
    valide_par="cc",
    verifie_le="2026-09-06",
    moteur_fonctions=("parcelle.plus_proche",),
))
