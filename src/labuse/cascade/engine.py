"""Orchestrateur de la cascade.

Le moteur accepte un ENSEMBLE de parcelles (brief §0 : N=1 est un cas particulier).
Phase 1 sur toutes les parcelles ; seules les SURVIVANTES (aucun HARD_EXCLUDE) sont
promues en phase 2 (coûteuse). Ne persiste rien : renvoie les verdicts au pipeline.
"""
from __future__ import annotations

from collections.abc import Iterable

from .base import REGISTRY, Verdict
from .context import EvalContext, ParcelRef


def _as_list(out: Verdict | list[Verdict] | None) -> list[Verdict]:
    if out is None:
        return []
    return out if isinstance(out, list) else [out]


def _layers_for_phase(rules: dict, phase: int) -> list[dict]:
    return [
        lc for lc in rules.get("layers", [])
        if lc.get("phase") == phase and lc.get("enabled", True) and lc.get("name") in REGISTRY
    ]


def run_cascade(
    parcels: Iterable[ParcelRef], ctx: EvalContext, phases: tuple[int, ...] = (1, 2)
) -> dict[int, list[Verdict]]:
    """Renvoie {parcel_id: [Verdict, ...]} pour l'ensemble de parcelles."""
    parcels = list(parcels)
    results: dict[int, list[Verdict]] = {p.id: [] for p in parcels}

    if 1 in phases:
        for lc in _layers_for_phase(ctx.rules, 1):
            layer = REGISTRY[lc["name"]]
            params = lc.get("params", {}) or {}
            for p in parcels:
                results[p.id].extend(_as_list(layer.evaluate(p, ctx, params)))

    # Promotion : survivantes de la phase 1 (pas de HARD_EXCLUDE).
    promoted = [p for p in parcels if not any(v.is_hard_exclude() for v in results[p.id])]

    if 2 in phases:
        for lc in _layers_for_phase(ctx.rules, 2):
            layer = REGISTRY[lc["name"]]
            params = lc.get("params", {}) or {}
            for p in promoted:
                results[p.id].extend(_as_list(layer.evaluate(p, ctx, params)))

    return results


def is_promoted(verdicts: list[Verdict]) -> bool:
    return not any(v.is_hard_exclude() for v in verdicts)
