"""Score de COMPLÉTUDE (0–100) — combien on SAIT (brief §7A).

Une famille est couverte dès qu'une de ses couches a rendu un verdict ≠ UNKNOWN.
`cadastre` est spécial : couvert dès que la parcelle est ingérée.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import completeness_weights
from ..enums import CascadeVerdict


@dataclass
class CompletenessResult:
    score: int
    band: str
    by_family: dict[str, dict] = field(default_factory=dict)


def _band(score: int, bands: dict) -> str:
    for name, (lo, hi) in bands.items():
        if lo <= score <= hi:
            return name
    return "faible"


def compute_completeness(verdicts, parcel_ingested: bool = True, cfg: dict | None = None) -> CompletenessResult:
    cfg = cfg or completeness_weights()
    weights: dict[str, int] = cfg["weights"]
    family_layers: dict[str, list[str]] = cfg.get("family_layers", {})

    answered: set[str] = {
        v.layer_name for v in verdicts if v.result != CascadeVerdict.UNKNOWN
    }

    score = 0
    by_family: dict[str, dict] = {}
    for family, weight in weights.items():
        if family == "cadastre":
            covered = parcel_ingested
        else:
            covered = any(layer in answered for layer in family_layers.get(family, []))
        by_family[family] = {"weight": weight, "covered": covered}
        if covered:
            score += weight

    score = int(min(100, max(0, score)))
    return CompletenessResult(score=score, band=_band(score, cfg.get("bands", {})), by_family=by_family)
