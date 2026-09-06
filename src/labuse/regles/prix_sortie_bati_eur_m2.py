"""Fiche de règle — prix de secteur DVF fiabilisé (méthode « état de l'art »). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("prix_sortie_bati_eur_m2", "prix_terrain_secteur_eur_m2"),
    formule_codee=(
        "Médiane des €/m² DVF sur un segment HOMOGÈNE type × période, rayon ADAPTATIF : 500 m → "
        "1 000 m → 1 500 m → commune, on prend le plus serré atteignant n ≥ 8 (MIN_N_SECTEUR) ; "
        "période 5 ans récents, élargie si n insuffisant. Robustification : bornes de bon sens "
        "[1 000 ; 12 000] €/m² bâti, puis exclusion des 5 % extrêmes (2,5 % par queue, "
        "k = ⌊n×0,025⌋ — sous ~20 ventes k=0, on ne trime pas un petit échantillon). Fiabilité "
        "fiable/fragile/insuffisant (n, récence, dispersion interquartile, type, rayon élargi) ; "
        "« insuffisant » → aucun prix servi. Dédoublonnage des mutations multi-parcelles ; type "
        "prioritaire appartements, repli mixte signalé ; distribution avant/après rendue."),
    entrees=("dvf_mutations_parcelle (prix, surface, type, date, geom)", "parcels.geom_2975",
             "constantes SECTEUR-2 T1 : MIN_N_SECTEUR=8, RAYONS 500/1000/1500, TRIM 5 %, période 5 ans"),
    classe="methode_standard",
    fonction="src/labuse/faisabilite/bilan.py:sector_price",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_sector_price.py::test_trim_et_mediane_independants",
    verifie_le="2026-09-06",
))
