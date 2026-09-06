"""Fiche de règle — marge de surélévation sous la règle de hauteur. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("marge_surelevation_m",),
    formule_codee=(
        "marge = hauteur_règle − hauteur_bâti, avec hauteur_règle = hé (hauteur à l'ÉGOUT du "
        "règlement de zone, YAML calibré) en priorité, repli hf (faîtage) SEULEMENT si l'égout est "
        "absent, avec avertissement. possible = marge ≥ 2,8 m (un niveau habitable) ; None (jamais "
        "un faux « non ») quand une des deux hauteurs manque."),
    entrees=("config/plu_<commune>.yaml (he_m, hf_m)", "hauteur_bati_m (BD TOPO)"),
    classe="regle_externe",
    fonction="src/labuse/faisabilite/potentiel.py:surelevation",
    verdict="reference_introuvable",
    choix=("Seuil 2,8 m = un niveau habitable (marge minimale pour qu'une surélévation ait un "
           "sens) — convention LABUSE reprise du mandat segments, affichée avec le verdict."),
    exemple_temoin="tests/regles/test_surelevation.py::test_marge_egout_prioritaire",
    verifie_le="2026-09-06",
))
