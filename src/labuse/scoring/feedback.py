"""Réinjection du feedback terrain (§10) — agrégation par ZONE, version simple/traçable.

Pas de ML : on agrège le retour terrain par proximité (rayon, cf.
config/opportunity_weights.yaml : `feedback`). Une zone qui accumule des
« false_positive » applique une décote au score d'opportunité des parcelles de la
zone ; les « good_lead » remontent légèrement. L'ajustement est borné, et TRACÉ
comme un verdict « feedback_terrain » dans la cascade (visible dans la fiche :
« score ajusté par retour terrain »). Ne court-circuite jamais la règle d'or :
decide_status garde la main (la complétude plafonne toujours).
"""
from __future__ import annotations

from ..config import opportunity_weights
from .opportunity import OpportunityResult
from .status import decide_status


def feedback_adjustment(fp: int, gl: int, ni: int, cfg: dict) -> int:
    """Ajustement borné du score d'opportunité d'après le feedback agrégé de la zone."""
    fb = cfg.get("feedback", {})
    adj = (gl * fb.get("good_lead_bonus", 6)
           - fp * fb.get("false_positive_decote", 8)
           - ni * fb.get("not_interested_decote", 3))
    m = fb.get("max_adjustment", 20)
    return int(max(-m, min(m, adj)))


def apply_feedback(opp: OpportunityResult, completeness_score: int, fp: int, gl: int, ni: int = 0,
                   cfg: dict | None = None):
    """Applique l'ajustement de zone à `opp` (score muté). Renvoie (statut, verdict d'affichage|None)."""
    cfg = cfg or opportunity_weights()
    if opp.hard_exclude:
        return decide_status(opp, completeness_score, cfg), None
    adj = feedback_adjustment(fp, gl, ni, cfg)
    if adj == 0:
        return decide_status(opp, completeness_score, cfg), None

    lo, hi = cfg["score_bounds"]
    opp.score = int(max(lo, min(hi, opp.score + adj)))
    radius = cfg.get("feedback", {}).get("zone_radius_m", 300)

    from ..cascade.base import positive, soft_flag  # import local : évite tout cycle
    from ..enums import Severity

    detail = (f"Score ajusté par retour terrain (Δ{adj:+d}) : "
              f"{fp} faux positif(s), {gl} bon(s) lead(s), {ni} pas intéressé à ≤ {radius} m.")
    verdict = (positive("feedback_terrain", detail, None) if adj > 0
               else soft_flag("feedback_terrain", detail, Severity.MOYEN))
    return decide_status(opp, completeness_score, cfg), verdict
