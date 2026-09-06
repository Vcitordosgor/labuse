"""Fiche de règle — compteurs de la cascade d'exclusion. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_vigilances", "verdict_icd", "simulplu_resultat"),
    formule_codee=(
        "n_vigilances = compte des couches de la cascade au verdict SOFT_FLAG ou HARD_EXCLUDE pour "
        "la parcelle (dryrun_cascade_results du run servi). verdict_icd = complétude des couches "
        "au moment de l'évaluation + liste des manquantes (l'incomplétude est DITE, jamais un "
        "verdict silencieusement partiel). simulplu = re-verdict de la cascade sous un zonage "
        "HYPOTHÉTIQUE (dryrun, jamais servi comme réel). Les SEUILS de chaque couche (pente, "
        "aléas, périmètres) sont déclarés couche par couche dans cascade/ ; chaque couche cite sa "
        "source réglementaire au registre (domaine_source)."),
    entrees=("dryrun_cascade_results (run servi)", "spatial_layers (17 couches)"),
    classe="choix_labuse",
    fonction="src/labuse/cascade/engine.py:evaluate_parcels",
    verdict="choix_assume",
    choix=("La PARTITION en 17 étages, l'ordre, et la sévérité (HARD/SOFT) par couche sont des "
           "choix LABUSE d'instruction (dits à l'écran étage par étage) ; les PÉRIMÈTRES des "
           "couches sont réglementaires (passe-plats sourcés)."),
    exemple_temoin="tests/regles/test_cascade_compteurs.py::test_compte_vigilances",
    verifie_le="2026-09-06",
))
