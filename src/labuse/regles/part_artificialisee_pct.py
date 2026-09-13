"""Fiche de règle — OCS GE à la parcelle : part artificialisée + usage du sol dominant.
TESTS-1 lot 1 (dette SOURCES-2/REPARATIONS-1 lot 5 : données servies sans fiche)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("part_artificialisee_pct", "usage_sol_dominant"),
    formule_codee=(
        "Précalcul parcel_ocsge (ingestion/ocsge.py:precalcul_parcelles) par intersection "
        "parcelle × îlots OCS GE (millésime récent, 2022) : part_artif_pct = 100 × Σ aires "
        "intersectées ARTIFICIALISÉES ÷ surface parcelle, où « artificialisé » = "
        "artif_decret(code_cs, code_us), la matrice du décret 2023-1096 (étape 1, avant lissage "
        "des seuils réglementaires) ; cs_dominant / us_dominant = le code de couverture / d'usage "
        "de PLUS GRANDE aire intersectée ((array_agg(code ORDER BY aire DESC))[1]). Servi par "
        "bati.py:le_bien_block (arrondi 0,1 ; table absente → None, jamais un tiroir cassé)."),
    entrees=("parcel_ocsge (précalcul, millésime 2022)",
             "OCS GE (IGN) — GPKG couverture/usage, produit différentiel officiel"),
    classe="methode_standard",
    fonction="src/labuse/ingestion/ocsge.py:precalcul_parcelles · src/labuse/bati.py:le_bien_block",
    verdict="choix_assume",
    choix=(
        "Donnée d'ÎLOT projetée sur l'assiette cadastrale — jamais la précision de la parcelle, "
        "et la fiche le DIT (« d'après OCS GE, donnée d'îlot »). Le dominant est choisi par aire "
        "intersectée (aucun seuil de majorité) ; la matrice artif est celle du décret (étape 1) "
        "sans le lissage réglementaire des petites surfaces. Aucun effet score."),
    exemple_temoin=None,
    verifie_le="2026-09-14",
))
