"""O3 — ANTI-FICHE (« pourquoi PAS »): les motifs d'écartement d'une parcelle, hiérarchisés et sourcés.

La fiche dit pourquoi une parcelle est intéressante ; l'anti-fiche dit **pourquoi elle ne l'est pas**
(ou pas assez). CONNEXIONS-2 Lot 1 (KO-2) : on lit la cascade SERVIE run-scopée
(`served_cascade_lines` → `dryrun_cascade_results` du run épinglé, dédupliquée + arbitrée) — la MÊME
que la fiche écran — et le tier du run servi. Fini la lecture de la table LIVE `cascade_results`
(non run-scopée, dernier calcul par parcelle) qui pouvait contredire la fiche. Aucun recalcul. Deux niveaux :
  · **RÉDHIBITOIRE** (HARD_EXCLUDE) : motifs bloquants — la parcelle est écartée (étage 0).
  · **VIGILANCE** (SOFT_FLAG) : contraintes non bloquantes qui pèsent.
Chaque motif porte son libellé (déjà rédigé, ex. « Exclue : PPR zone rouge »), sa couche et sa source.

Honnêteté : si aucun motif, on le dit ; si la parcelle est bien classée, l'anti-fiche liste les rares
points de vigilance plutôt que d'en inventer.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.score_v_constants import Q_A_RUN_LABEL

log = logging.getLogger("labuse.anti_fiche")
router = APIRouter(prefix="/anti-fiche", tags=["anti-fiche"])

_TIER_CADRE = {
    "ecartee": "Écartée — au moins un motif rédhibitoire.",
    "a_creuser": "Retenue avec réserves — potentiel partiel, points de vigilance à lever.",
    "reserve_fonciere": "Potentiel long terme — intéressant à moyen terme, quelques contraintes.",
    "chaude": "Bien classée — peu de points bloquants.",
    "brulante": "Très bien classée — signaux forts, points bloquants rares.",
}


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.get("/{idu}")
def anti_fiche(idu: str, db: Session = Depends(get_db)) -> dict:
    """IDU → motifs d'écartement/vigilance hiérarchisés (RÉDHIBITOIRE puis VIGILANCE), chacun sourcé."""
    p = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")

    tier = db.execute(text(
        "SELECT tier FROM parcel_p_score_v2 WHERE parcelle_id = :i AND run_id = :r"),
        {"i": idu, "r": Q_A_RUN_LABEL}).scalar()

    # KO-2 : cascade SERVIE du run épinglé (dédup + arbitrée), pas la table LIVE `cascade_results`.
    from .served_cascade import served_cascade_lines
    lignes = [l for l in served_cascade_lines(db, idu, Q_A_RUN_LABEL)
              if l["result"] in ("HARD_EXCLUDE", "SOFT_FLAG")]
    rows = sorted(lignes, key=lambda l: (l["result"] != "HARD_EXCLUDE", l["layer_name"]))

    def _motif(r) -> dict:
        # source réelle si la couche en porte une ; sinon motif dérivé de la cascade (géométrie/règle)
        return {"couche": r["layer_name"],
                "motif": r["detail"] or r["layer_name"],
                "source": r["source"] or "cascade (dérivé)"}

    # dédup par couche (une couche = un motif, le plus fort gagne — HARD trié en premier)
    seen, redhibitoires, vigilances = set(), [], []
    for r in rows:
        if r["layer_name"] in seen:
            continue
        seen.add(r["layer_name"])
        (redhibitoires if r["result"] == "HARD_EXCLUDE" else vigilances).append(_motif(r))

    cadre = _TIER_CADRE.get(tier, "Parcelle non évaluée par le run servi.")
    if not redhibitoires and not vigilances:
        synthese = "Aucun motif d'écartement ni point de vigilance relevé dans les couches analysées."
    elif redhibitoires:
        synthese = (f"{len(redhibitoires)} motif(s) rédhibitoire(s) — la parcelle est écartée."
                    + (f" S'y ajoute(nt) {len(vigilances)} point(s) de vigilance." if vigilances else ""))
    else:
        synthese = f"Pas de motif bloquant ; {len(vigilances)} point(s) de vigilance à considérer."

    return {"idu": idu, "tier": tier, "cadre": cadre, "synthese": synthese,
            "redhibitoire": redhibitoires, "vigilance": vigilances,
            "n_redhibitoire": len(redhibitoires), "n_vigilance": len(vigilances),
            "avertissement": "Motifs lus dans la cascade déjà calculée ; sourcés, non recalculés."}
