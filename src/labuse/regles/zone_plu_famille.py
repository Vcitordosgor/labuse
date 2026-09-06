"""Fiche de règle — zone PLU servie (dominante par surface). CIRCUIT-4 (lot 2 : extrait daté)."""
from . import FicheRegle, Reference, declarer

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
    verdict="conforme",
    reference=Reference(
        titre="Code de l'urbanisme — délimitation des zones des PLU",
        article="art. R151-18 (U) ; R151-20 (AU) ; R151-22 (A) ; R151-24 (N) — même sous-section",
        url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031720615",
        version="en vigueur au 01/01/2016 (décret n° 2015-1783 du 28/12/2015)",
        extrait=("R151-18 : « Les zones urbaines sont dites “zones U”. Peuvent être classés en zone "
                 "urbaine, les secteurs déjà urbanisés et les secteurs où les équipements publics "
                 "existants ou en cours de réalisation ont une capacité suffisante pour desservir "
                 "les constructions à implanter. » (R151-20 : « Les zones à urbaniser sont dites "
                 "“zones AU” » — même sous-section R151-17 à R151-26.)"),
        lu_le="2026-09-06"),
    choix=("Zone DOMINANTE PAR SURFACE (jamais le centroïde) : décision ZONE-1 après l'audit "
           "EXPORTS ; seuil a_cheval 90 % = convention LABUSE d'affichage, les parts restent "
           "servies. Les familles U/AU/A/N sont la partition réglementaire des PLU."),
    exemple_temoin="tests/regles/test_zone_dominante.py::test_dominante_par_surface",
    valide_par="cc",
    verifie_le="2026-09-06",
))
