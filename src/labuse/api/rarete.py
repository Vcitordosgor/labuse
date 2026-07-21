"""O9 — PIPELINE DE RARETÉ : horizon d'épuisement du foncier constructible par commune.

Projection arithmétique, ESTIMÉ, à caveat LARGE : à quel rythme une commune consomme ses espaces
(ENAF, Cerema) et combien d'ANNÉES il reste avant d'épuiser son enveloppe ZAN 2031 à ce rythme.

  rythme  = consommation ENAF 2021-2024 / 3 ans (ha/an, Sourcé Cerema)
  budget  = 50 % de la consommation 2011-2021 (enveloppe loi Climat & Résilience / TRACE, Estimé doctrine)
  reste   = budget − consommation déjà réalisée 2021-2024
  horizon = reste / rythme   (années avant d'atteindre le plafond ZAN, à rythme constant)

Le stock d'opportunités DÉTECTÉ (ha de parcelles brûlantes + chaudes) est fourni en CONTEXTE — il ne se
substitue pas à l'enveloppe ZAN (couverture partielle). Zéro donnée nouvelle.

CAVEAT (assumé) : rythme supposé CONSTANT (or il varie) ; budget ZAN = interprétation −50 % (la loi TRACE a
assoupli la trajectoire, cf. mandat ZAN) ; épuisement de l'enveloppe ≠ interdiction de construire (densification
hors ENAF possible). Outil de HIÉRARCHISATION de la pression, pas une date couperet.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.score_v_constants import Q_A_RUN_LABEL

log = logging.getLogger("labuse.rarete")
router = APIRouter(prefix="/pipeline-rarete", tags=["pipeline-rarete"])

CAVEAT = ("Estimé — rythme supposé constant ; budget ZAN = interprétation −50 % (loi TRACE assouplie) ; "
          "épuisement de l'enveloppe ENAF ≠ interdiction de bâtir (densification possible). Hiérarchisation, pas une date couperet.")

_SQL = """
WITH stock AS (
  SELECT left(p.idu,5) AS insee, sum(p.surface_m2)/10000.0 AS ha
  FROM parcels p JOIN parcel_p_score_v2 v ON v.parcelle_id = p.idu
  WHERE v.run_id = :run AND v.tier IN ('brulante','chaude') GROUP BY 1)
SELECT e.insee, e.commune,
  e.conso_2021_2024_m2 / 3.0 / 10000.0 AS conso_ha_an,
  e.conso_2011_2021_m2 * 0.5 / 10000.0 AS budget_zan_ha,
  (e.conso_2011_2021_m2 * 0.5 - e.conso_2021_2024_m2) / 10000.0 AS reste_zan_ha,
  coalesce(st.ha, 0) AS stock_opp_ha,
  e.source_nom
FROM commune_conso_enaf e LEFT JOIN stock st ON st.insee = e.insee;
"""


def get_db():
    from .app import get_db as _g
    yield from _g()


def _horizon(reste_ha, rythme_ha_an):
    """Années avant épuisement de l'enveloppe. None si rythme nul (non projetable) ; 0 si déjà dépassé."""
    if rythme_ha_an is None or rythme_ha_an <= 0:
        return None
    if reste_ha is None:
        return None
    if reste_ha <= 0:
        return 0.0
    return round(reste_ha / rythme_ha_an, 1)


def compute_rarete(db: Session) -> list[dict]:
    if db.execute(text("SELECT to_regclass('commune_conso_enaf')")).scalar() is None:
        return []
    rows = [{k: (float(v) if hasattr(v, "__float__") else v) for k, v in dict(r).items()}
            for r in db.execute(text(_SQL), {"run": Q_A_RUN_LABEL}).mappings().all()]
    out = []
    for r in rows:
        horizon = _horizon(r["reste_zan_ha"], r["conso_ha_an"])
        out.append({
            "insee": r["insee"], "commune": r["commune"],
            "rythme_conso_ha_an": round(r["conso_ha_an"], 1) if r["conso_ha_an"] is not None else None,
            "budget_zan_ha": round(r["budget_zan_ha"], 1) if r["budget_zan_ha"] is not None else None,
            "reste_zan_ha": round(r["reste_zan_ha"], 1) if r["reste_zan_ha"] is not None else None,
            "horizon_epuisement_ans": horizon,
            "statut": ("budget dépassé" if horizon == 0 else
                       "non projetable" if horizon is None else
                       "tension forte" if horizon <= 5 else
                       "tension modérée" if horizon <= 15 else "détendu"),
            "stock_opportunites_ha": round(r["stock_opp_ha"], 1),
            "source": r["source_nom"],
        })
    # trié par pression : horizon court d'abord (None en fin)
    out.sort(key=lambda x: (x["horizon_epuisement_ans"] is None, x["horizon_epuisement_ans"] or 0))
    return out


@router.get("")
def pipeline_rarete(db: Session = Depends(get_db)) -> dict:
    """Horizon d'épuisement de l'enveloppe ZAN par commune (années au rythme actuel), trié par pression."""
    communes = compute_rarete(db)
    return {"communes": communes, "n": len(communes),
            "methode": ("horizon = reste ZAN / rythme de consommation ENAF ; reste = 50 % conso 2011-2021 "
                        "− conso 2021-2024 ; rythme = conso 2021-2024 / 3 ans (Cerema)."),
            "caveat": CAVEAT,
            "avertissement": "Projection Estimé à rythme constant — hiérarchise la pression foncière, ne fixe pas une date."}
