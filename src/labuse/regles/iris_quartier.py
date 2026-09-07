"""Fiche de règle — quartier INSEE (IRIS, RP2022) : chiffres bruts et dérivées.
SOURCES-1 lot 6."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("iris_quartier", "iris_commune_quartiers"),
    formule_codee=(
        "Passe-plat des bases infra-communales RP2022 (colonnes curées _LOG_COLS/_POP_COLS "
        "d'iris_rp.py) + dérivées à UN SEUL point de calcul (_derives) : "
        "vacance_pct = 100·LOGVAC/LOG ; part_bati_avant_1990_pct = "
        "100·(ACH1919+ACH1945+ACH1970+ACH1990)/ACHTOT (périodes d'achèvement des résidences "
        "principales) ; taille_menages = NPER_RP/RP ; part_60_plus_pct = "
        "100·(POP6074+POP75P)/POP ; part_locataires_pct = 100·RP_LOC/RP ; part_hlm_pct = "
        "100·RP_LOCHLMV/RP. IRIS de la parcelle = contour (kind iris_insee, géographie 2024) "
        "contenant ST_PointOnSurface(parcelle). Commune : n IRIS + vacance min/médiane/max "
        "(médiane = élément central du tri, n pair → élément haut)."),
    entrees=("iris_rp (colonnes P22_* curées, millésime RP2022)",
             "spatial_layers (kind=iris_insee, subtype=code IRIS)"),
    classe="methode_standard",
    fonction="src/labuse/ingestion/iris_rp.py:stats_iris / quartiers_commune / _derives",
    verdict="choix_assume",
    choix=(
        "Les dénominateurs sont ceux de l'INSEE (LOG pour la vacance, RP pour les statuts "
        "d'occupation, ACHTOT pour l'âge du bâti — ACHTOT ≠ RP : résidences principales "
        "d'achèvement connu). La maille IRIS est DITE partout (« quartier INSEE ») ; l'IRIS "
        "AFFINE la commune et ne la remplace jamais (commune_insee_logement reste la vérité "
        "communale). Variables candidates scoring (vacance IRIS, âge du bâti) NOTÉES pour le "
        "banc K0 — rien au modèle sans banc."),
    exemple_temoin="tests/test_sources1_lot6.py::test_iris_derives_a_la_main",
    verifie_le="2026-09-07",
))
