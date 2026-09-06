"""Fiche de règle — clause de mixité sociale (règlements PLU calibrés). CIRCUIT-4 (lot 2)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("mixite_clause",),
    formule_codee=(
        "Déclenchement si SDP projetée ≥ seuil du règlement OU logements ≥ seuil OU terrain > seuil "
        "— seuils LUS de la calibration du règlement de la zone (YAML par commune), jamais des "
        "constantes nationales. Verdict affiché avec la source d'article."),
    entrees=("config/plu_<commune>.yaml (seuils Art. 2 calibrés, article et page cités)",
             "SDP/logements du scénario"),
    classe="regle_externe",
    fonction="src/labuse/faisabilite/engine.py (clause mixité, hypothèses mixite_sdp_seuil_m2)",
    verdict="conforme",
    reference=Reference(
        titre="Règlements de PLU communaux (corpus calibré LABUSE — 23 communes + RNU)",
        article="clauses de mixité sociale, article cité par commune/zone dans le YAML",
        url="config/plu_<commune>.yaml (extraits calibrés, document et page cités)",
        version="calibration 2026 (millésimes GPU par commune, réconciliés idurba+sha)",
        extrait=("Le Tampon : « Uc : programme de logements > 1 000 m² SDP => 30 % minimum de "
                 "logements aidés (Art. Uc2) ». L'Étang-Salé : « AUa/AUb : >1 000 m² SDP "
                 "habitation => 20 % minimum en logement aidé (AU 1.3, p.77) ». Saint-Paul : "
                 "« programme dont la SDP ≥ 1 500 m² » (bornes 1500/1800 du texte, "
                 "mixite_sdp_seuil_m2)."),
        lu_le="2026-09-06"),
    exemple_temoin="tests/regles/test_mixite.py::test_seuils_du_reglement",
    valide_par="cc",
    verifie_le="2026-09-06",
))
