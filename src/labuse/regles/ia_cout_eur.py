"""Fiche de règle — coût IA (ledger). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("ia_cout_eur",),
    formule_codee=(
        "cout = Σ cout_eur du ledger ia_log sur le mois courant (date_trunc('month')) + nombre "
        "d'appels ; ventilation 30 j : par jour, par licence, cumul 7 j. Le cout_eur unitaire est "
        "écrit à l'appel par ai/core._log_cost (tarifs par modèle, tokens in/out, caching)."),
    entrees=("ia_log (cout_eur, ts, compte_id, modele)",),
    classe="choix_labuse",
    fonction="src/labuse/registre/moteurs/plateforme.py:conso_ia_mois (+ conso_ia_30j)",
    verdict="choix_assume",
    choix=("Coût = somme du ledger interne (tarifs indicatifs par modèle posés dans ai/core.PRICE), "
           "pas la facture Anthropic — l'écart éventuel est celui des tarifs catalogue."),
    exemple_temoin="tests/regles/test_compteurs_simples.py::test_conso_ia_somme",
    verifie_le="2026-09-06",
    moteur_fonctions=("plateforme.conso_ia_mois", "plateforme.conso_ia_30j"),
))
