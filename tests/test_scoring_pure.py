"""PHASE 0 « Le Juge » — J1.c : fonctions de scoring PURES (aucune base).

`icd.compute_from_row` (indice de complétude des données, borné 0–100, invariant POIDS_TOTAL == 100)
et `status.decide_status` (les trois règles dures : exclusion, plancher de complétude, seuil+flag fort).
"""
from __future__ import annotations

from types import SimpleNamespace

from labuse.enums import EvaluationStatus
from labuse.scoring.icd import ICD_GROUPS, POIDS_TOTAL, compute_from_row
from labuse.scoring.status import decide_status

# ligne « tout présent » : une valeur non nulle / non « inconnu » pour CHAQUE groupe ICD.
_FULL = {
    "pct_potentiel": 0.4, "zone_plu": "U", "canopee_pct": 12.0,
    "med_pm2_terrain_36m": 120, "med_pm2_bati_36m": 2200, "filo_snv_pp": 21000,
    "tenure_bin": "proprietaire", "tendance_pm2_bati": 0.03, "pente_moy_deg": 6.0,
}


# ───────────────────────────── ICD ─────────────────────────────

def test_icd_poids_total_invariant_100():
    assert POIDS_TOTAL == 100
    assert sum(g.poids for g in ICD_GROUPS) == 100


def test_icd_row_vide_donne_zero():
    total, detail = compute_from_row({})
    assert total == 0
    assert all(v is False for v in detail.values())


def test_icd_row_complet_donne_100():
    total, detail = compute_from_row(_FULL)
    assert total == 100 == POIDS_TOTAL
    assert all(detail.values())


def test_icd_toujours_borne_0_100():
    for row in ({}, {"pct_potentiel": 0.1}, {"zone_plu": "U", "pente_moy_deg": 5}, _FULL):
        total, _ = compute_from_row(row)
        assert 0 <= total <= 100


def test_icd_valeur_inconnu_compte_comme_absente():
    # « inconnu » explicite (zone_plu, tenure) = donnée absente, PAS présente.
    _, detail = compute_from_row({"zone_plu": "inconnu", "tenure_bin": "inconnu"})
    assert detail["zone_plu"] is False and detail["tenure"] is False


def test_icd_partiel_somme_des_poids_presents():
    total, detail = compute_from_row({"pente_moy_deg": 5.0})
    poids_pente = next(g.poids for g in ICD_GROUPS if g.key == "pente")
    assert total == poids_pente
    assert detail["pente"] is True and detail["residuel"] is False


# ───────────────────────────── decide_status ─────────────────────────────

CFG = {"status_rules": {"completeness_floor": 50, "opportunity_threshold": 65}}


def _opp(hard_exclude=False, exclude_kind=None, score=0, has_fort_flag=False):
    return SimpleNamespace(hard_exclude=hard_exclude, exclude_kind=exclude_kind,
                           score=score, has_fort_flag=has_fort_flag)


def test_status_regle1_hard_exclude_exclue():
    # exclusion dure « exclue » → EXCLUE, même complétude/score parfaits (l'exclusion prime).
    assert decide_status(_opp(hard_exclude=True, exclude_kind="exclue", score=99),
                         100, CFG) == EvaluationStatus.EXCLUE


def test_status_regle1_hard_exclude_faux_positif():
    assert decide_status(_opp(hard_exclude=True, exclude_kind="faux_positif"),
                         100, CFG) == EvaluationStatus.FAUX_POSITIF_PROBABLE


def test_status_regle2_completude_sous_plancher_a_creuser():
    # score au-dessus du seuil MAIS complétude < plancher → jamais une opportunité chaude.
    assert decide_status(_opp(score=90), 49, CFG) == EvaluationStatus.A_CREUSER


def test_status_regle3_opportunite_si_seuil_atteint_et_pas_de_flag_fort():
    assert decide_status(_opp(score=65), 50, CFG) == EvaluationStatus.OPPORTUNITE


def test_status_regle3_flag_fort_bloque_opportunite():
    assert decide_status(_opp(score=90, has_fort_flag=True), 90, CFG) == EvaluationStatus.A_CREUSER


def test_status_regle3_sous_le_seuil_a_creuser():
    assert decide_status(_opp(score=64), 90, CFG) == EvaluationStatus.A_CREUSER
