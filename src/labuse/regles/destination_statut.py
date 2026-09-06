"""Fiche de règle — destinations PLU + verrou CDAC. CIRCUIT-4 (lot 2 : extrait daté)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("destination_statut", "reglement_plu_bloc"),
    formule_codee=(
        "Lecture du règlement CALIBRÉ de la zone (corpus PLU ingéré, extraits cités document/page/"
        "millésime) : destination autorisée / interdite / conditionnée par zone, servie avec son "
        "extrait. Verrou CDAC statique national : surface de vente STRICTEMENT supérieure à "
        "1 000 m² (code : float(seuil_m2) > CDAC_SEUIL_M2, CDAC_SEUIL_M2 = 1000) → mention "
        "« soumis à CDAC », relayée comme point de vigilance, jamais instruite."),
    entrees=("corpus PLU calibré (extraits par zone)", "parcel_zone_plu", "CDAC_SEUIL_M2 = 1000"),
    classe="regle_externe",
    fonction="src/labuse/plu/destinations.py (+ api/moteurs.py:56-124)",
    verdict="conforme",
    reference=Reference(
        titre="Code de commerce — autorisation d'exploitation commerciale",
        article="art. L752-1, 1° et 2°",
        url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037671151",
        version="en vigueur au 25/11/2018",
        extrait=("« 1° La création d'un magasin de commerce de détail d'une surface de vente "
                 "supérieure à 1 000 mètres carrés » ; « 2° L'extension de la surface de vente "
                 "d'un magasin de commerce de détail ayant déjà atteint le seuil des 1 000 mètres "
                 "carrés ou devant le dépasser par la réalisation du projet »."),
        lu_le="2026-09-06"),
    exemple_temoin="tests/regles/test_cdac.py::test_seuil_cdac_1000",
    valide_par="cc",
    verifie_le="2026-09-06",
))
