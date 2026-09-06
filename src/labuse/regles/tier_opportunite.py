"""Fiche de règle — scoring P v2 (tiers) : un MODÈLE, pas une règle. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("tier_opportunite", "rang_tier", "stock_opportunites", "verdict_couche"),
    formule_codee=(
        "Modèle m36-l2f-2026 (scoring/p_v2) : score de mutation par parcelle (features p_model_*, "
        "artefact GELÉ sha256, recalé par run) → tiers brûlante/chaude/à_creuser/réserve/écartée "
        "par paliers de score ; rang = ordre dans le tier ; stock = count(brûlante+chaude) par "
        "commune ; la couche verdict = aplat des tiers du run servi (tuiles MVT reconstruites à la "
        "bascule). PAS de formule officielle : la justesse est la VALIDATION (backtest, PR-AUC, "
        "calibration, stabilité de classement — golden 119 parcelles épinglées + garde de bascule)."),
    entrees=("p_model_* (cosia, sitadel, dvf, filosofi, bd_topo)", "parcel_v_score", "parcel_residuel"),
    classe="modele",
    fonction="src/labuse/scoring/p_v2/pipeline.py:run_score_v2",
    verdict="modele_valide",
    choix=None,
    exemple_temoin="tests/test_golden_run_servi.py (golden 119 : le run servi reproduit les témoins)",
    verifie_le="2026-09-06",
))
