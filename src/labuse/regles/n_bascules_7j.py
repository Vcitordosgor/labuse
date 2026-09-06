"""Fiche de règle — entrées dans les tiers hauts entre deux runs. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("n_bascules_7j",),
    formule_codee=(
        "count(parcelles dont le tier au run SERVI ∈ {brulante, chaude} ET dont le tier au run "
        "PRÉCÉDENT était NULL ou hors de ces deux tiers) — auto-jointure parcel_p_score_v2 sur "
        "parcelle_id entre les deux runs (pointeur vivant, DONNEES-2 B4)."),
    entrees=("parcel_p_score_v2 (tier, run_id) des deux runs",),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/plateforme.py:bascules_tiers_hauts",
    verdict="choix_assume",
    choix=("« Tiers hauts » = brûlante + chaude (paliers du modèle, voir fiche tier_opportunite) ; "
           "l'intitulé « 7 j » vaut « depuis le run précédent » (cadence de calcul réelle)."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_bascules_tiers_hauts",
    verifie_le="2026-09-06",
    moteur_fonctions=("plateforme.bascules_tiers_hauts",),
))
