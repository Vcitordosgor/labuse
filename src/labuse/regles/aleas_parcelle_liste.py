"""Fiche de règle — la liste des aléas de la parcelle. FICHE-1 lot 3 (CIRCUIT-4)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("aleas_parcelle_liste",),
    formule_codee=(
        "La liste est dérivée des LIGNES DE CASCADE SERVIES (`layer='risques'`, résultat "
        "HARD_EXCLUDE/SOFT_FLAG) — exactement celles que sert « Pièges et risques » (point de "
        "vérité unique M73, aucune relecture de spatial_layers pour DÉCIDER un aléa). Par aléa : "
        "nature lue sur le libellé arbitré (Inondation / Mouvement de terrain / PPR / …), niveau = "
        "severity, part concernée = premier « N % » du libellé (None si la source ne la dit pas). "
        "Pour un aléa PPR : référence de l'arrêté communal (document + date d'approbation les plus "
        "récents par type), une CITATION adossée à l'aléa déjà retenu, jamais une seconde décision."),
    entrees=("dryrun_cascade_results (run servi, layer='risques')", "data_sources (source, "
             "millésime)", "spatial_layers (kind='ppr') — arrêté communal, référence seule"),
    classe="choix_labuse",
    fonction="src/labuse/api/app.py:_aleas_block",
    verdict="choix_assume",
    choix=("Choix LABUSE : servir le DÉTAIL des aléas depuis la MÊME cascade servie que l'outil "
           "Pièges et risques (accord garanti, contrôle épinglé) plutôt qu'une relecture "
           "géométrique (qui contredirait la fiche — cause racine RAPPORT_M73). La date "
           "d'approbation PPR est une référence de commune, pas un recalcul d'aléa."),
    exemple_temoin="tests/test_fiche1_aleas.py::test_alea_nature_lue_sur_le_libelle",
    valide_par="cc",
    verifie_le="2026-09-06",
))
