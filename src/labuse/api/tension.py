"""O8 — INDICE DE TENSION FONCIÈRE (0-100 par micro-secteur) — LIVRÉ MASQUÉ (flag) + finding.

Objectif : demande vs offre par secteur (`left(idu,10)`). Formule documentée ci-dessous, bornée [0-100],
distribution renvoyée. **Mais** : conformément au point dur du mandat (« si non calibrable défendablement
→ livré MASQUÉ + finding »), une **sonde de calibrabilité** confronte l'indice à un exutoire INDÉPENDANT
(le prix relatif du secteur vs sa commune = désirabilité révélée par le marché). Résultat mesuré :
**Spearman ≈ −0,04 (n≈616)** → corrélation nulle : l'indice ne suit PAS la tension révélée.

→ **Décision : indice MASQUÉ** (`expose = false`). Le moteur est livré (documenté, distribution) pour être
prêt le jour où une source de calibration existera (série de prix, taux d'absorption permis/stock daté),
**jamais affiché en l'état** — pas de faux signal « pour faire joli ». La sonde est recalculée à la volée
(reproductible). Zéro exposition en fiche.

FORMULE (Estimé) : demande = moyenne(normalisé[densité de permis 24 mois par parcelle], normalisé[déficit SRU
commune]) ; offre = normalisé[part d'opportunités du secteur] ; tension = 100 × demande / (demande + offre).
Normalisation min-max sur les secteurs présents. LIMITES : deux entrées sur trois sont soit clairsemées
(permis) soit constantes à l'échelle communale (SRU) — la granularité « micro-secteur » est en partie factice.
"""
from __future__ import annotations

import logging
import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.score_v_constants import Q_A_RUN_LABEL

log = logging.getLogger("labuse.tension")
router = APIRouter(prefix="/tension-fonciere", tags=["tension-fonciere"])

# Décision d'exposition : MASQUÉ tant que la sonde de calibrabilité échoue (voir finding).
EXPOSE = False
SEUIL_RHO_DEFENDABLE = 0.20   # |Spearman| minimal vs exutoire indépendant pour envisager d'exposer

_SQL = """
WITH sect AS (SELECT DISTINCT left(idu,10) AS s, left(idu,5) AS insee, commune FROM parcels),
stock AS (SELECT left(parcelle_id,10) AS s, count(*) AS tot,
  count(*) FILTER (WHERE tier IN ('brulante','chaude')) AS opp
  FROM parcel_p_score_v2 WHERE run_id = :run GROUP BY 1),
permis AS (SELECT left(e,10) AS s, count(*) AS n FROM sitadel_permits sp,
  jsonb_array_elements_text(sp.idu_codes) e
  WHERE sp.date >= CURRENT_DATE - INTERVAL '24 months' GROUP BY 1),
sru AS (SELECT insee, greatest(objectif_pct - taux_lls, 0) AS deficit FROM commune_contexte_sru),
terr AS (SELECT secteur AS s, mediane_prix_m2 AS px FROM dvf_secteur_medianes
         WHERE type_bien='terrain' AND n_ventes >= 3),
commed AS (SELECT left(secteur,5) AS insee, percentile_cont(0.5) WITHIN GROUP (ORDER BY mediane_prix_m2) AS cpx
           FROM dvf_secteur_medianes WHERE type_bien='terrain' AND n_ventes >= 3 GROUP BY 1)
SELECT sect.s, sect.commune,
  coalesce(permis.n,0)::float / greatest(stock.tot,1) AS d_permis,
  coalesce(sru.deficit,0)::float AS d_sru,
  coalesce(stock.opp,0)::float / greatest(stock.tot,1) AS o_stock,
  terr.px::float AS px, commed.cpx::float AS cpx
FROM sect
LEFT JOIN stock ON stock.s = sect.s
LEFT JOIN permis ON permis.s = sect.s
LEFT JOIN sru ON sru.insee = sect.insee
LEFT JOIN terr ON terr.s = sect.s
LEFT JOIN commed ON commed.insee = sect.insee
WHERE stock.tot IS NOT NULL;
"""


def get_db():
    from .app import get_db as _g
    yield from _g()


def _minmax(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return (min(vals), max(vals)) if vals else (None, None)


def _spearman(xs, ys) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        rk = [0.0] * n
        for pos, i in enumerate(order):
            rk[i] = float(pos)
        return rk
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    sx = math.sqrt(sum((v - mx) ** 2 for v in rx)); sy = math.sqrt(sum((v - my) ** 2 for v in ry))
    return cov / (sx * sy) if sx * sy > 0 else 0.0


_REQUIS = ("parcel_p_score_v2", "sitadel_permits", "commune_contexte_sru", "dvf_secteur_medianes")


def compute_tension(db: Session) -> dict:
    """Calcule l'indice par secteur (0-100), sa distribution, et la sonde de calibrabilité (Spearman).
    Tables requises absentes → résultat vide masqué (additif, jamais bloquant)."""
    vide = {"expose": EXPOSE, "n": 0, "indices": [], "distribution": None, "calibration": None}
    for tbl in _REQUIS:
        if db.execute(text("SELECT to_regclass(:t)"), {"t": tbl}).scalar() is None:
            return vide
    rows = [{k: (float(v) if hasattr(v, "__float__") else v) for k, v in dict(r).items()}
            for r in db.execute(text(_SQL), {"run": Q_A_RUN_LABEL}).mappings().all()]
    if not rows:
        return {"expose": EXPOSE, "n": 0, "indices": [], "distribution": None, "calibration": None}
    bornes = {k: _minmax(rows, k) for k in ("d_permis", "d_sru", "o_stock")}

    def norm(r, k):
        lo, hi = bornes[k]
        return (r[k] - lo) / (hi - lo) if (lo is not None and hi > lo) else 0.5

    for r in rows:
        demande = (norm(r, "d_permis") + norm(r, "d_sru")) / 2.0
        offre = norm(r, "o_stock")
        r["tension"] = round(100 * demande / (demande + offre), 1) if (demande + offre) > 0 else 50.0
        r["prix_rel"] = (r["px"] / r["cpx"]) if (r.get("px") and r.get("cpx")) else None

    ts = sorted(r["tension"] for r in rows)
    n = len(ts)
    distribution = {"min": ts[0], "p25": ts[n // 4], "median": ts[n // 2], "p75": ts[(3 * n) // 4],
                    "max": ts[-1], "n": n}

    cal_rows = [r for r in rows if r["prix_rel"] is not None]
    rho = _spearman([r["tension"] for r in cal_rows], [r["prix_rel"] for r in cal_rows])
    calibration = {"exutoire": "prix relatif secteur / commune (désirabilité révélée)",
                   "spearman": round(rho, 3), "n": len(cal_rows), "seuil_defendable": SEUIL_RHO_DEFENDABLE,
                   "defendable": abs(rho) >= SEUIL_RHO_DEFENDABLE}
    return {"expose": EXPOSE, "n": n,
            "indices": [{"secteur": r["s"], "commune": r["commune"], "tension": r["tension"]} for r in rows],
            "distribution": distribution, "calibration": calibration}


@router.get("")
def tension_fonciere(db: Session = Depends(get_db),
                     inclure_indices: bool = Query(False, description="Inclure le détail par secteur.")) -> dict:
    """Indice de tension foncière — MASQUÉ (non calibrable défendablement). Renvoie la sonde + la distribution."""
    res = compute_tension(db)
    out = {
        "expose": res["expose"],
        "masque": not res["expose"],
        "calibration": res["calibration"],
        "distribution": res["distribution"],
        "n_secteurs": res["n"],
        "finding": ("Indice NON exposé : la sonde de calibrabilité (Spearman vs prix relatif, exutoire indépendant) "
                    f"donne {res['calibration']['spearman'] if res['calibration'] else 'n/a'} — sous le seuil "
                    f"±{SEUIL_RHO_DEFENDABLE}. Deux entrées sur trois sont clairsemées (permis) ou communales (SRU) : "
                    "la granularité micro-secteur est en partie factice. Moteur livré, prêt pour une future source de "
                    "calibration (série de prix datée, taux d'absorption permis/stock) ; jamais affiché en l'état."),
        "formule": ("demande = moyenne(norm[densité permis 24 mois/parcelle], norm[déficit SRU commune]) ; "
                    "offre = norm[part d'opportunités] ; tension = 100 × demande / (demande + offre). Bornes [0-100]."),
    }
    if inclure_indices:
        out["indices"] = res["indices"]     # détail réservé (diagnostic), l'UI ne l'affiche pas
    return out
