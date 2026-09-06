"""Fiche de règle — scoring P v2 : un MODÈLE validé. CIRCUIT-4 (lot 3.3 : métriques)."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("tier_opportunite", "rang_tier", "stock_opportunites", "verdict_couche"),
    formule_codee=(
        "Modèle m36-l2f-2026 (scoring/p_v2) : WoE binning (min_count 200, monotonie PAV) + "
        "régression logistique (C=5.0, L2, seed 974), calibration ISOTONIQUE sur 2025, recalage "
        "d'intercept seul à chaque run (coefficients et binning INTACTS ; re-train = décision "
        "humaine annuelle) ; artifact GELÉ sha256 (le pipeline REFUSE un mismatch) → tiers "
        "brûlante/chaude/à_creuser/réserve/écartée par paliers ; rang = ordre dans le tier ; "
        "stock = count(brûlante+chaude) par commune ; la couche verdict = aplat des tiers du run "
        "servi. PAS de formule officielle : la justesse est la VALIDATION (walk-forward + golden "
        "119 parcelles + garde de bascule)."),
    entrees=("p_model_* (cosia, sitadel, dvf, filosofi, bd_topo)", "parcel_v_score", "parcel_residuel"),
    classe="modele",
    fonction="src/labuse/scoring/p_v2/pipeline.py:run_score_v2",
    verdict="modele_valide",
    reference=Reference(
        titre="LABUSE — spécification et métriques du scoring P v2 (walk-forward gelé)",
        article="docs/SCORING_SPEC.md §4 (modèle m36-l2f-2026) — métriques réelles par fold",
        url="docs/SCORING_SPEC.md",
        version="artifact gelé 2026-07-12 19:54, model_version = m36-l2f-2026, sha256 = 00a58008…4959b64",
        extrait=("« Walk-forward : 6 folds » ; « RR@k = taux de mutation dans le top-k / taux "
                 "global », protocole gelé k = 1158 hors copro : fold 2020 RR@1158 = 9,41 "
                 "[8,09;10,70], ECE 0,0013 ; fold 2021 = 8,61 [7,72;10,02], ECE 0,0033 ; fold "
                 "2022 = 8,63 [7,60;9,85], ECE 0,0024 ; « Calibration : isotonique ajustée sur "
                 "l'année de validation 2025 » ; « Le pipeline REFUSE de tourner si le sha256 ne "
                 "correspond pas au manifeste »."),
        lu_le="2026-09-06"),
    choix=None,
    exemple_temoin="tests/test_golden_run_servi.py (golden 119 : le run servi reproduit les témoins)",
    valide_par="cc",
    verifie_le="2026-09-06",
))
