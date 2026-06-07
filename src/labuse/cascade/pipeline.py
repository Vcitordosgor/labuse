"""Pipeline d'évaluation : cascade → scoring → persistance.

Produit, pour chaque parcelle : les verdicts (cascade_results), les deux scores
et le statut (parcel_evaluations, versionnée). C'est l'entrée appelée par la
qualification (offre A, N=1) comme par la découverte (offre B, toute la commune).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .. import config
from ..models import CascadeResult, Parcel, ParcelEvaluation
from ..scoring import (
    CompletenessResult,
    OpportunityResult,
    apply_feedback,
    compute_completeness,
    compute_opportunity,
    decide_status,
)
from .base import Verdict
from .context import EvalContext, ParcelRef
from .engine import is_promoted, run_cascade


@dataclass
class EvaluationOutcome:
    parcel_id: int
    idu: str
    verdicts: list[Verdict]
    completeness: CompletenessResult
    opportunity: OpportunityResult
    status: str
    promoted: bool


def _load_parcel_refs(session: Session, parcel_ids: list[int]) -> list[ParcelRef]:
    rows = session.execute(
        select(Parcel.id, Parcel.idu, Parcel.commune, Parcel.surface_m2).where(Parcel.id.in_(parcel_ids))
    ).all()
    return [ParcelRef(id=r[0], idu=r[1], commune=r[2], surface_m2=r[3]) for r in rows]


def evaluate_parcels(
    parcel_ids: list[int],
    session: Session,
    *,
    persist: bool = True,
    ai_provider=None,
) -> list[EvaluationOutcome]:
    """Évalue un ensemble de parcelles (offre A : N=1 ; offre B : toute la commune).

    Si `ai_provider` est fourni, l'agent IA (§9) produit un JSON borné validé, dont
    l'`opportunity_score_adjustment` (∈ [−20, 20]) corrige le score, et l'ensemble
    est stocké dans parcel_evaluations.ai_payload.
    """
    ctx = EvalContext(session)
    ctx.prime(parcel_ids)  # précalcul batch (commune entière) — sinon 1 requête/parcelle×couche
    parcels = _load_parcel_refs(session, parcel_ids)
    verdicts_by = run_cascade(parcels, ctx)
    rules_v = config.rules_version()

    outcomes: list[EvaluationOutcome] = []
    for p in parcels:
        verdicts = verdicts_by[p.id]
        completeness = compute_completeness(verdicts, parcel_ingested=True)
        opportunity = compute_opportunity(verdicts, ai_adjustment=0)
        status = decide_status(opportunity, completeness.score)

        outcome = EvaluationOutcome(
            parcel_id=p.id, idu=p.idu, verdicts=verdicts,
            completeness=completeness, opportunity=opportunity,
            status=status.value, promoted=is_promoted(verdicts),
        )

        ai_payload = None
        model_version = None
        if ai_provider is not None:
            ai_payload, opportunity, status = _apply_ai(ai_provider, outcome, p)
            outcome.opportunity = opportunity
            outcome.status = status.value
            model_version = getattr(ai_provider, "name", "ai")

        # Feedback promoteur réinjecté (§10) — après l'IA, ne court-circuite pas la règle d'or.
        fb_verdict = ctx.latest_feedback(p.id)
        if fb_verdict:
            status, fb_display = apply_feedback(opportunity, completeness.score, fb_verdict)
            outcome.status = status.value
            if fb_display is not None:
                verdicts.append(fb_display)
                opportunity.weights.append(0.0)

        if persist:
            _persist(session, ctx, p, verdicts, completeness, opportunity, status, rules_v, ai_payload, model_version)

        outcomes.append(outcome)

    if persist:
        session.flush()
    return outcomes


def _apply_ai(provider, outcome: EvaluationOutcome, parcel: ParcelRef):
    """Lance l'agent, applique l'ajustement borné, renvoie (ai_payload, opp, status)."""
    from ..ai.prompt import payload_from_outcome

    payload = payload_from_outcome(
        outcome, {"idu": parcel.idu, "commune": parcel.commune, "surface_m2": parcel.surface_m2}
    )
    ai_payload = provider.analyze(payload)
    adj = int(ai_payload.get("opportunity_score_adjustment", 0))
    opportunity = compute_opportunity(outcome.verdicts, ai_adjustment=adj)
    status = decide_status(opportunity, outcome.completeness.score)
    return ai_payload, opportunity, status


def _persist(
    session: Session,
    ctx: EvalContext,
    parcel: ParcelRef,
    verdicts: list[Verdict],
    completeness: CompletenessResult,
    opportunity: OpportunityResult,
    status,
    rules_v: str,
    ai_payload: dict | None = None,
    model_version: str | None = None,
) -> None:
    # cascade_results : on remplace les verdicts courants de la parcelle.
    session.execute(text("DELETE FROM cascade_results WHERE parcel_id = :pid"), {"pid": parcel.id})
    for v, weight in zip(verdicts, opportunity.weights):
        session.add(
            CascadeResult(
                parcel_id=parcel.id,
                layer_name=v.layer_name,
                result=v.result,
                severity=v.severity,
                weight_applied=weight if weight else None,
                detail=v.detail,
                data_source_id=ctx.source_id(v.data_source_name),
            )
        )
    # parcel_evaluations : versionnée (on empile une nouvelle ligne).
    session.add(
        ParcelEvaluation(
            parcel_id=parcel.id,
            completeness_score=completeness.score,
            opportunity_score=opportunity.score,
            status=status,
            ai_payload=ai_payload,
            model_version=model_version,
            rules_version=rules_v,
        )
    )
