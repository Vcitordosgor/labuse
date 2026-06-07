"""Décision de STATUT (règles dures, brief §7C).

- HARD_EXCLUDE présent → `exclue` (eau/cœur Parc/PPR rouge) ou `faux_positif_probable`.
- Complétude < 50 → statut PLAFONNÉ à `a_creuser` quel que soit le score d'opportunité.
- Sinon : opp ≥ 65 ET complétude ≥ 50 (et pas de SOFT_FLAG fort) → `opportunite` ;
  entre-deux ou présence d'un SOFT_FLAG fort → `a_creuser`.
"""
from __future__ import annotations

from ..config import opportunity_weights
from ..enums import EvaluationStatus
from .opportunity import OpportunityResult


def decide_status(opp: OpportunityResult, completeness_score: int, cfg: dict | None = None) -> EvaluationStatus:
    if opp.hard_exclude:
        return EvaluationStatus.EXCLUE if opp.exclude_kind == "exclue" else EvaluationStatus.FAUX_POSITIF_PROBABLE

    rules = (cfg or opportunity_weights())["status_rules"]
    floor = rules["completeness_floor"]
    threshold = rules["opportunity_threshold"]

    # Complétude trop mince : on ne déclare jamais une opportunité chaude.
    if completeness_score < floor:
        return EvaluationStatus.A_CREUSER

    if opp.score >= threshold and not opp.has_fort_flag:
        return EvaluationStatus.OPPORTUNITE

    return EvaluationStatus.A_CREUSER
