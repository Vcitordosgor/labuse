"""Fiche de règle — ACV/PVD/ORT et condition Denormandie. SOURCES-1 lot 5."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("ort_statut",),
    formule_codee=(
        "Passe-plat de la table DGALN (grist, export tableId=BDD complet) : statut = acv si "
        "flag ACV, sinon pvd si flag PVD, sinon autre ; « hors » si la commune n'y figure "
        "pas (table peuplée). Convention ORT signée + date servies telles quelles. "
        "Denormandie : phrase d'ÉTAT (« condition communale remplie — logement dans le "
        "périmètre conventionné requis, périmètre non publié »), jamais un calcul d'avantage "
        "fiscal."),
    entrees=("table BDD grist DGALN (Code commune, ACV, PVD, Signée ?, date)",
             "commune_ort (table servie)"),
    classe="choix_labuse",
    fonction="src/labuse/ingestion/ort.py:ort_commune",
    verdict="choix_assume",
    choix=(
        "SOURCES-1 lot 5 : l'éligibilité Denormandie est une INDICATION à trois conditions "
        "(commune ORT/ACV/PVD signée · logement dans le périmètre conventionné · travaux "
        "≥ 25 % du coût, jusqu'au 31/12/2027 — fiche 10 du rapport) ; LABUSE ne sert que la "
        "condition COMMUNALE (la seule publiée : les périmètres infra-communaux sont dans "
        "les conventions EPCI non diffusées — demande lot 7). Les taux (12/18/21 %) ne sont "
        "PAS servis (pas de calcul d'avantage sans le périmètre). ÉCART producteur mesuré "
        "07/09/2026 et contrôlé au filtre : Saint-Louis, attendu ACV (fiche 10), est absent "
        "de la table DGALN — 4 ACV servies (Le Port, Saint-André, Saint-Joseph, "
        "Saint-Pierre), l'écart est visible, jamais corrigé en silence."),
    exemple_temoin="tests/test_sources1_lot5.py::test_ort_statut_et_denormandie",
    verifie_le="2026-09-07",
))
