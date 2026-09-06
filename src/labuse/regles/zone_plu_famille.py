"""Fiche de règle — zone PLU servie d'une parcelle (dominante par surface). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("zone_plu_famille", "zonage_plu_couche"),
    formule_codee=(
        "Zone servie = la zone GPU couvrant la PLUS GRANDE SURFACE de la parcelle (parcel_zone_plu, "
        "PK idu — même source que l'écran, la couche et la faisabilité depuis ZONE-1) ; famille "
        "U/AU/A/N par préfixe du subtype GPU (AU avant A ; U ; N ; autre). Drapeau a_cheval si "
        "aucune zone n'atteint 90 % de la surface (SEUIL_A_CHEVAL_PCT) — les parts par zone sont "
        "alors servies. La couche peint chaque parcelle de SA famille, code exact au zoom/clic."),
    entrees=("parcel_zone_plu (idu, zone, zone_fam, parts)", "GPU (Géoportail de l'urbanisme, zonages)"),
    classe="regle_externe",
    fonction="src/labuse/faisabilite/zone_servie.py:zone_dominante",
    verdict="reference_introuvable",
    choix=("Zone DOMINANTE PAR SURFACE (jamais le centroïde) : décision ZONE-1 après l'audit EXPORTS "
           "(deux moteurs divergeaient sur les parcelles à cheval) ; seuil a_cheval 90 % = "
           "convention LABUSE d'affichage, les parts restent servies."),
    exemple_temoin="tests/regles/test_zone_dominante.py::test_dominante_par_surface",
    verifie_le="2026-09-06",
))
