"""Réinjection du retour promoteur (§10) dans le scoring — boucle d'apprentissage.

Le feedback n'écrase JAMAIS la règle d'or : un « bon lead » ne fait passer en
opportunité que si la complétude reste suffisante (decide_status garde la main).
Un « faux positif » rétrograde le statut. Poids tunables
(config/opportunity_weights.yaml : section `feedback`).
"""
from __future__ import annotations

from ..config import opportunity_weights
from ..enums import EvaluationStatus
from .opportunity import OpportunityResult
from .status import decide_status


def apply_feedback(opp: OpportunityResult, completeness_score: int, feedback_verdict: str | None,
                   cfg: dict | None = None):
    """Ajuste `opp` (score muté) selon le dernier retour promoteur.

    Renvoie (statut, verdict d'affichage | None) — le verdict sert à tracer le
    réajustement dans la cascade (la traçabilité est le produit).
    """
    cfg = cfg or opportunity_weights()
    status = decide_status(opp, completeness_score, cfg)
    if not feedback_verdict or opp.hard_exclude:
        return status, None

    from ..cascade.base import passed, positive, soft_flag  # import local : évite tout cycle
    from ..enums import Severity

    fb = cfg.get("feedback", {})
    lo, hi = cfg["score_bounds"]

    if feedback_verdict == "false_positive" and fb.get("false_positive_demote", True):
        return EvaluationStatus.FAUX_POSITIF_PROBABLE, soft_flag(
            "feedback", "Retour promoteur : faux positif → rétrogradé.", Severity.FORT)

    if feedback_verdict == "good_lead":
        delta = int(fb.get("good_lead_bonus", 10))
        opp.score = int(max(lo, min(hi, opp.score + delta)))
        return decide_status(opp, completeness_score, cfg), positive(
            "feedback", f"Retour promoteur : bon lead (+{delta}).", bonus_key=None)

    if feedback_verdict == "not_interested":
        delta = int(fb.get("not_interested_penalty", 5))
        opp.score = int(max(lo, min(hi, opp.score - delta)))
        return decide_status(opp, completeness_score, cfg), passed(
            "feedback", f"Retour promoteur : pas intéressé (-{delta}).")

    return status, None
