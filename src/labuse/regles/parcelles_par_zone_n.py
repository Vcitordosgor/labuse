"""Fiche de règle — compte de parcelles par zone (filtres). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("parcelles_par_zone_n",),
    formule_codee=(
        "Compte de parcelles par famille puis par zone_filtre : n(fam, zone) = count(parcel_zone_plu "
        "WHERE zone_filtre IS NOT NULL), groupé par (zone_fam, zone_filtre), optionnellement restreint "
        "aux communes demandées. Servi comme un NOMBRE de filtre (« parcelles en zone … »), jamais "
        "comme une part."),
    entrees=("parcel_zone_plu.zone_fam", "parcel_zone_plu.zone_filtre", "parcels.commune"),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/zonage.py:parcelles_par_zone",
    verdict="choix_assume",
    choix=(
        "Le compte de parcelles par zone survit UNIQUEMENT dans les filtres, sous un autre nom — "
        "décision Vic 05/09/2026 : le mot « part » n'y apparaît jamais (voir part_zone_U_pct)."),
    exemple_temoin="tests/regles/test_part_zone_pct.py::test_parcelles_par_zone_temoin",
    valide_par="vic",
    verifie_le="2026-09-06",
    moteur_fonctions=("zonage.parcelles_par_zone",),
))
