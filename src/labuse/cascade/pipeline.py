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
    parcel_ids: list[int], session: Session, *, persist: bool = True, ai_adjustments: dict[int, int] | None = None
) -> list[EvaluationOutcome]:
    ai_adjustments = ai_adjustments or {}
    ctx = EvalContext(session)
    parcels = _load_parcel_refs(session, parcel_ids)
    verdicts_by = run_cascade(parcels, ctx)
    rules_v = config.rules_version()

    outcomes: list[EvaluationOutcome] = []
    for p in parcels:
        verdicts = verdicts_by[p.id]
        completeness = compute_completeness(verdicts, parcel_ingested=True)
        opportunity = compute_opportunity(verdicts, ai_adjustment=ai_adjustments.get(p.id, 0))
        status = decide_status(opportunity, completeness.score)

        if persist:
            _persist(session, ctx, p, verdicts, completeness, opportunity, status, rules_v)

        outcomes.append(
            EvaluationOutcome(
                parcel_id=p.id, idu=p.idu, verdicts=verdicts,
                completeness=completeness, opportunity=opportunity,
                status=status.value, promoted=is_promoted(verdicts),
            )
        )

    if persist:
        session.flush()
    return outcomes


def _persist(
    session: Session,
    ctx: EvalContext,
    parcel: ParcelRef,
    verdicts: list[Verdict],
    completeness: CompletenessResult,
    opportunity: OpportunityResult,
    status,
    rules_v: str,
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
            rules_version=rules_v,
        )
    )
