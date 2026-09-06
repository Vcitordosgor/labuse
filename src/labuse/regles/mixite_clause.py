"""Fiche de règle — clause de mixité sociale (règlement PLU, Art. 2). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("mixite_clause",),
    formule_codee=(
        "Déclenchement si SDP projetée ≥ seuil du règlement OU logements ≥ seuil OU terrain > seuil "
        "— seuils LUS de la calibration du règlement de la zone (YAML par commune ; bornes du texte "
        "type 1 500/1 800 m²), jamais des constantes nationales. Verdict affiché avec la source "
        "d'article."),
    entrees=("config/plu_<commune>.yaml (seuils Art. 2 calibrés)", "SDP/logements du scénario"),
    classe="regle_externe",
    fonction="src/labuse/faisabilite/engine.py (clause mixité, hypothèses mixite_sdp_seuil_m2)",
    verdict="reference_introuvable",
    exemple_temoin="tests/regles/test_mixite.py::test_seuils_du_reglement",
    verifie_le="2026-09-06",
))
