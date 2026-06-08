"""Score d'OPPORTUNITÉ (0–100), dérivé de la cascade (brief §7B).

    HARD_EXCLUDE présent      -> 0
    sinon : clamp(50 − Σpénalités + Σbonus + ai_adjustment, 1, 100)

`weights` (signés) est aligné sur la liste de verdicts en entrée → on les recopie
dans cascade_results.weight_applied.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import opportunity_weights
from ..enums import CascadeVerdict, Severity


@dataclass
class OpportunityResult:
    score: int
    hard_exclude: bool
    exclude_kind: str | None            # "exclue" | "faux_positif" | None
    has_fort_flag: bool
    weights: list[float] = field(default_factory=list)   # aligné sur les verdicts
    ai_adjustment: int = 0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_opportunity(verdicts, ai_adjustment: int = 0, cfg: dict | None = None) -> OpportunityResult:
    cfg = cfg or opportunity_weights()
    base = cfg["base_score"]
    penalty = cfg["penalty_per_flag"]
    mult = cfg["severity_multipliers"]
    bonuses = cfg["bonuses"]
    lo, hi = cfg["score_bounds"]
    adj_lo, adj_hi = cfg["ai_adjustment_bounds"]
    ai_adjustment = int(_clamp(ai_adjustment, adj_lo, adj_hi))

    weights = [0.0] * len(verdicts)

    hard = [v for v in verdicts if v.result == CascadeVerdict.HARD_EXCLUDE]
    if hard:
        exclude_kind = "exclue" if any(v.exclude_kind == "exclue" for v in hard) else "faux_positif"
        return OpportunityResult(
            score=0, hard_exclude=True, exclude_kind=exclude_kind, has_fort_flag=False,
            weights=weights, ai_adjustment=ai_adjustment,
        )

    score = float(base)
    has_fort = False
    for i, v in enumerate(verdicts):
        if v.result == CascadeVerdict.SOFT_FLAG:
            sev = v.severity.value if isinstance(v.severity, Severity) else (v.severity or "moyen")
            w = -(penalty * mult.get(sev, 1))
            weights[i] = float(w)
            score += w
            if sev == Severity.FORT.value:
                has_fort = True
        elif v.result == CascadeVerdict.POSITIVE and v.bonus_key:
            # poids config = PLAFOND ; magnitude ∈ [0,1] = intensité calculée par la couche.
            # Arrondi entier → chaque ligne reste un nombre de points lisible et la somme est exacte.
            mag = max(0.0, min(1.0, float(getattr(v, "magnitude", 1.0))))
            b = float(round(float(bonuses.get(v.bonus_key, 0)) * mag))
            weights[i] = b
            score += b

    score = _clamp(score, lo, hi)
    score = _clamp(score + ai_adjustment, lo, hi)
    return OpportunityResult(
        score=int(round(score)), hard_exclude=False, exclude_kind=None, has_fort_flag=has_fort,
        weights=weights, ai_adjustment=ai_adjustment,
    )
