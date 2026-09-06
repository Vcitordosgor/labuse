"""Fiche de règle — destinations autorisées d'une zone PLU (+ verrou CDAC). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("destination_statut", "reglement_plu_bloc"),
    formule_codee=(
        "Lecture du règlement CALIBRÉ de la zone (corpus PLU ingéré, extraits cités document/page/"
        "millésime) : destination autorisée / interdite / conditionnée par zone, servie avec son "
        "extrait. Verrou CDAC statique national : au-delà de 1 000 m² de surface de VENTE, "
        "autorisation d'exploitation commerciale obligatoire (CDAC_SEUIL_M2 = 1000, art. L752-1 "
        "code de commerce) — relayé comme point de vigilance, jamais instruit."),
    entrees=("corpus PLU calibré (extraits par zone)", "parcel_zone_plu", "CDAC_SEUIL_M2 = 1000"),
    classe="regle_externe",
    fonction="src/labuse/plu/destinations.py (+ api/moteurs.py:56-124)",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_cdac.py::test_seuil_cdac_1000",
    verifie_le="2026-09-06",
))
