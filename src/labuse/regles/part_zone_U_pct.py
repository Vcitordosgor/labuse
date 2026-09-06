"""Fiche de règle — parts de zonage d'une commune (surface). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("part_zone_U_pct", "part_zone_AU_pct", "part_zone_A_pct", "part_zone_N_pct"),
    formule_codee=(
        "Part de SURFACE d'une famille de zones (U, AU, A, N) dans la surface cadastrée zonée de la "
        "commune. part_fam = 100 × Σ surface_m2(parcelles de la famille) ÷ Σ surface_m2(parcelles "
        "zonées U+AU+A+N), arrondi 0,1. Familles par préfixe du zone_fam de parcel_zone_plu "
        "(AU d'abord, puis A hors AU, U, N) ; une parcelle porte UNE zone (PK idu, zone dominante) "
        "→ jamais de double comptage ; les quatre parts somment à 100 %."),
    entrees=("parcels.surface_m2", "parcel_zone_plu.zone_fam (PK idu)"),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/zonage.py:parts_zonage_surface",
    verdict="choix_assume",
    choix=(
        "LA part de zonage est la part de SURFACE, jamais la part de parcelles — décision Vic du "
        "05/09/2026 (CIRCUIT-1 lot 2.1) : les parts de parcelles ne représentent pas le territoire "
        "(à La Réunion U domine en nombre mais A+N couvrent l'essentiel de l'aire ; Saint-Paul : "
        "A = 35,8 % en surface vs 17,8 % en parcelles). Dénominateur = surface cadastrée ZONÉE "
        "(les parcelles sans zone n'y entrent pas)."),
    exemple_temoin="tests/regles/test_part_zone_pct.py::test_parts_zonage_surface_temoin",
    valide_par="vic",
    verifie_le="2026-09-06",
    moteur_fonctions=("zonage.parts_zonage_surface",),
))
