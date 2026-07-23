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
from ..enums import Severity
from ..models import (
    CascadeResult,
    DryrunCascadeResult,
    DryrunParcelEvaluation,
    Parcel,
    ParcelEvaluation,
)
from ..scoring import (
    CompletenessResult,
    OpportunityResult,
    apply_declassement,
    apply_feedback,
    compute_completeness,
    compute_declass_signals,
    compute_opportunity,
    decide_status,
)
from .base import Verdict, soft_flag
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
    dryrun_label: str | None = None,
) -> list[EvaluationOutcome]:
    """Évalue un ensemble de parcelles (offre A : N=1 ; offre B : toute la commune).

    Si `ai_provider` est fourni, l'agent IA (§9) produit un JSON borné validé, dont
    l'`opportunity_score_adjustment` (∈ [−20, 20]) corrige le score, et l'ensemble
    est stocké dans parcel_evaluations.ai_payload.
    """
    ctx = EvalContext(session)
    ctx.prime(parcel_ids)  # précalcul batch (commune entière) — sinon 1 requête/parcelle×couche
    parcels = _load_parcel_refs(session, parcel_ids)
    # Signaux du garde-fou faux positifs, calculés AVANT la cascade : leur volet FRANC (surface/
    # pente/OSM/bâti) alimente désormais l'ÉTAGE 0 (couches d'élimination phase 1) — la couche
    # `bati` les lit via ctx ; le volet NON-franc reste un flag qualité appliqué en aval (étage 1).
    signals_by = compute_declass_signals(session, parcel_ids)
    ctx.declass_signals = signals_by
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

        # Feedback terrain réinjecté (§10, agrégé par zone) — après l'IA, garde la règle d'or.
        fp, gl, ni = ctx.feedback_counts(p.id)
        if fp or gl or ni:
            status, fb_display = apply_feedback(opportunity, completeness.score, fp, gl, ni)
            outcome.status = status.value
            if fb_display is not None:
                verdicts.append(fb_display)
                opportunity.weights.append(0.0)

        # Garde-fou faux positifs — volet NON-franc (flags QUALITÉ, étage 1 à venir) : surface
        # réduite (100–250 m²), pente 40–60 %, OSM 30–50 %, occupation partielle, accès à vérifier.
        # Les bloquants FRANCS sont désormais éliminés à l'ÉTAGE 0 (cascade phase 1) ; ce volet
        # n'agit donc QUE sur les survivants et ne produit JAMAIS de HARD_EXCLUDE (l'élimination
        # est le monopole de l'étage 0 — cf. invariant test_cascade). Il peut au plus rétrograder
        # une opportunité en « à creuser », avec un motif visible ; le score brut est conservé.
        if not opportunity.hard_exclude:
            final_status, motif = apply_declassement(status, signals_by.get(p.id, {}))
            if motif:
                status = final_status
                outcome.status = status.value
                verdicts.append(soft_flag("declassement", motif, Severity.FORT,
                                          source="LABUSE — garde-fou faux positifs"))
                opportunity.weights.append(0.0)

        if persist:
            if dryrun_label:
                # DRY-RUN : écrit UNIQUEMENT dans les tables parallèles ; ne touche JAMAIS le live.
                _persist_dryrun(session, ctx, dryrun_label, p, verdicts, completeness, opportunity, status, rules_v)
            else:
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
    # IA = NARRATIF ONLY (décision produit) : l'ajustement IA n'entre PLUS dans le score.
    # On conserve ai_payload (affiché) mais ai_adjustment=0 partout — aucun chemin ne l'injecte.
    opportunity = compute_opportunity(outcome.verdicts, ai_adjustment=0)
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


def _persist_dryrun(
    session: Session,
    ctx: EvalContext,
    run_label: str,
    parcel: ParcelRef,
    verdicts: list[Verdict],
    completeness: CompletenessResult,
    opportunity: OpportunityResult,
    status,
    rules_v: str,
) -> None:
    """DRY-RUN : écrit dans les tables PARALLÈLES (jamais le live). Idempotent par
    (run_label, parcel_id) : on purge d'abord ce couple, puis on réinsère (rejouable/résumable).

    Traçabilité : chaque ligne porte `weight_applied` (base + Σ = score) et `source_table/source_id`
    (cliquable — lus depuis verdict.extra quand la couche les renseigne, sinon NULL en baseline)."""
    session.execute(
        text("DELETE FROM dryrun_cascade_results WHERE run_label=:r AND parcel_id=:p"),
        {"r": run_label, "p": parcel.id})
    session.execute(
        text("DELETE FROM dryrun_parcel_evaluations WHERE run_label=:r AND parcel_id=:p"),
        {"r": run_label, "p": parcel.id})
    for v, weight in zip(verdicts, opportunity.weights):
        session.add(
            DryrunCascadeResult(
                run_label=run_label,
                parcel_id=parcel.id,
                layer_name=v.layer_name,
                result=v.result.value,
                severity=(v.severity.value if isinstance(v.severity, Severity) else v.severity),
                weight_applied=weight if weight else None,
                detail=v.detail,
                data_source_id=ctx.source_id(v.data_source_name),
                source_table=v.extra.get("source_table"),
                source_id=(str(v.extra["source_id"]) if v.extra.get("source_id") is not None else None),
                evenement=v.extra.get("evenement"),
            )
        )
    base = int(config.opportunity_weights()["base_score"])
    session.add(
        DryrunParcelEvaluation(
            run_label=run_label,
            parcel_id=parcel.id,
            completeness_score=completeness.score,
            opportunity_score=opportunity.score,
            opportunity_base=base,
            status=status.value if hasattr(status, "value") else str(status),
            rules_version=rules_v,
        )
    )
