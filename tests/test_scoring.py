"""Tests du scoring (§7) — math pure, sans base.

Vérifie : opportunité (HARD_EXCLUDE→0, base 50, pénalités×sévérité, bonus, clamp,
ai_adjustment borné), complétude (familles couvertes), et les règles de statut (§7C).
"""
from __future__ import annotations

from labuse.cascade.base import hard_exclude, passed, positive, soft_flag
from labuse.enums import EvaluationStatus, Severity
from labuse.scoring import compute_completeness, compute_opportunity, decide_status

# ───────────────────────────── opportunité ─────────────────────────────

def test_hard_exclude_donne_zero():
    v = [hard_exclude("eau", "sur l'eau", kind="exclue")]
    opp = compute_opportunity(v)
    assert opp.score == 0 and opp.hard_exclude and opp.exclude_kind == "exclue"


def test_base_sans_flag_vaut_50():
    opp = compute_opportunity([passed("surface", "ok")])
    assert opp.score == 50 and not opp.hard_exclude


def test_un_flag_fort_retire_15():
    opp = compute_opportunity([soft_flag("sar", "agricole", Severity.FORT)])
    assert opp.score == 35 and opp.has_fort_flag
    assert opp.weights == [-15.0]


def test_bonus_et_penalite_se_combinent():
    v = [positive("zonage_plu_gpu", "U", "zonage_u_au"), soft_flag("safer", "SAFER", Severity.MOYEN)]
    opp = compute_opportunity(v)
    # 50 + 8 (zonage_u_au) - 10 (moyen ×2 × 5) = 48
    assert opp.score == 48
    assert opp.weights == [8.0, -10.0]


def test_clamp_plancher_a_1():
    v = [soft_flag(f"l{i}", "x", Severity.FORT) for i in range(10)]  # -150
    opp = compute_opportunity(v)
    assert opp.score == 1  # jamais 0 hors HARD_EXCLUDE


def test_ai_adjustment_est_borne():
    opp = compute_opportunity([passed("x")], ai_adjustment=999)
    assert opp.ai_adjustment == 20 and opp.score == 70  # 50 + 20


# ───────────────────────────── complétude ─────────────────────────────

ALL_FAMILY_LAYERS = [
    "zonage_plu_gpu", "sar", "risques", "safer", "parc_national",
    "pente", "dvf", "sitadel", "ocs_ge", "acces", "proprietaire",
]


def test_completude_pleine_vaut_100():
    verdicts = [passed(name, "ok") for name in ALL_FAMILY_LAYERS]
    comp = compute_completeness(verdicts, parcel_ingested=True)
    assert comp.score == 100 and comp.band == "forte"


def test_unknown_ne_compte_pas():
    from labuse.cascade.base import unknown

    verdicts = [unknown("sar", "absent"), passed("zonage_plu_gpu", "ok")]
    comp = compute_completeness(verdicts, parcel_ingested=True)
    # cadastre(8) + zonage(12) couverts ; sar non couvert
    assert comp.score == 20
    assert comp.by_family["sar"]["covered"] is False
    assert comp.by_family["cadastre"]["covered"] is True


# ───────────────────────────── statut (§7C) ─────────────────────────────

def test_statut_exclue_vs_faux_positif():
    opp_excl = compute_opportunity([hard_exclude("ppr", "rouge", kind="exclue")])
    assert decide_status(opp_excl, 80) == EvaluationStatus.EXCLUE
    opp_fp = compute_opportunity([hard_exclude("foret_publique", "domaniale", kind="faux_positif")])
    assert decide_status(opp_fp, 80) == EvaluationStatus.FAUX_POSITIF_PROBABLE


def test_completude_faible_plafonne_a_creuser():
    # opportunité forte mais complétude < 50 → on ne déclare PAS opportunité chaude
    opp = compute_opportunity([positive("zonage_plu_gpu", "U", "zonage_u_au")])  # 58
    assert decide_status(opp, completeness_score=30) == EvaluationStatus.A_CREUSER


def test_opportunite_exige_seuil_et_pas_de_flag_fort():
    strong = compute_opportunity([
        positive("zonage_plu_gpu", "U", "zonage_u_au"),
        positive("potentiel_foncier_region", "îlot", "potentiel_foncier_region"),
    ])  # 50 + 8 + 12 = 70 ≥ 65
    assert decide_status(strong, completeness_score=80) == EvaluationStatus.OPPORTUNITE

    with_fort = compute_opportunity([
        positive("zonage_plu_gpu", "U", "zonage_u_au"),
        positive("potentiel_foncier_region", "îlot", "potentiel_foncier_region"),
        positive("dvf", "liquide", "contexte_dvf_favorable"),
        soft_flag("risques", "aléa fort", Severity.FORT),
    ])  # score ≥ 65 mais flag fort présent → a_creuser
    assert with_fort.has_fort_flag
    assert decide_status(with_fort, completeness_score=80) == EvaluationStatus.A_CREUSER
