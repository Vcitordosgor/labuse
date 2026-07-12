"""API scoring v2 (M5 lot 4) — endpoints ADDITIFS, lecture de la table
précalculée UNIQUEMENT (parcel_p_score_v2, index run+rang / run+tier ; P95 < 200 ms).

Décisions produit gravées : jamais de probabilité brute (mult_base « ×N » +
percentile + rang), univers par défaut HORS copro (toggle include_copro),
réserve foncière ≠ pipeline. Les champs matrice historiques restent servis par
les endpoints existants — marqués deprecated (cf. GET /v2/modele).
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.p_v2 import MODEL_FREEZE, MODEL_VERSION

router = APIRouter(prefix="/v2", tags=["scoring-v2"])

AVERTISSEMENT_CENSURE = ("les ventes récentes apparaissent dans DVF avec 1 à 3 ans "
                         "de retard — les niveaux 2025-2026 sont provisoires, "
                         "le classement est fiable")


def get_db():
    from .app import get_db as _g
    yield from _g()


def _latest_run(db: Session) -> dict:
    row = db.execute(text(
        "SELECT run_id, model_version, model_sha256, params, computed_at, snapshot_label "
        "FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).mappings().one_or_none()
    if row is None:
        raise HTTPException(503, "aucun run score-v2 — lancer `labuse score-v2`.")
    return dict(row)


def _row_payload(r, run: dict) -> dict:
    top5 = r["top5_contributions"]
    if isinstance(top5, str):
        top5 = json.loads(top5)
    return {
        "parcelle_id": r["parcelle_id"],
        "mult_base": r["mult_base"],              # « ×N vs moyenne » — l'affichage produit
        "percentile": r["percentile"],
        "rang": r["rang"],
        "tier": r["tier"],
        "contrib_z": r["contrib_z"], "contrib_d": r["contrib_d"],
        "pourquoi": top5,                          # 5 contributions lisibles (signe + bin)
        "badges": {
            "copro": bool(r["copro"]),
            "evenement_date": str(r["event_date"]) if r["event_date"] else None,
            "veille_succession": bool(r.get("veille_succession", False)),
        },
        "model_version": run["model_version"],
        "run_id": run["run_id"],
        "avertissement": AVERTISSEMENT_CENSURE,
    }


@router.get("/score/{idu}")
def score_parcelle(idu: str, db: Session = Depends(get_db)) -> dict:
    """Score P v2 d'une parcelle : ×N, percentile, rang, tier, 5 contributions
    lisibles, badges (copro, veille_succession, événement daté). p_raw stocké
    mais non exposé ici (défaut produit — saturation isotonique en tête)."""
    run = _latest_run(db)
    r = db.execute(text("""
        SELECT s.*, (vs.parcelle_id IS NOT NULL) AS veille_succession
        FROM parcel_p_score_v2 s
        LEFT JOIN parcel_veille_succession vs ON vs.parcelle_id = s.parcelle_id
        WHERE s.run_id = :run AND s.parcelle_id = :idu"""),
        {"run": run["run_id"], "idu": idu}).mappings().one_or_none()
    if r is None:
        raise HTTPException(404, f"parcelle {idu} absente du run {run['run_id']}")
    return _row_payload(r, run)


@router.get("/liste")
def liste(tier: str | None = Query(None),
          commune: str | None = Query(None, description="code INSEE (5 chiffres)"),
          include_copro: bool = Query(False, description="défaut produit : hors copro"),
          limit: int = Query(100, le=1000), offset: int = Query(0, ge=0),
          db: Session = Depends(get_db)) -> dict:
    """Liste triée par P (rang croissant), filtres tier/commune, toggle copro."""
    run = _latest_run(db)
    where, params = ["s.run_id = :run"], {"run": run["run_id"],
                                          "limit": limit, "offset": offset}
    if not include_copro:
        where.append("NOT s.copro")
    if tier:
        where.append("s.tier = :tier")
        params["tier"] = tier
    if commune:
        where.append("left(s.parcelle_id, 5) = :com")
        params["com"] = commune
    rows = db.execute(text(f"""
        SELECT s.*, (vs.parcelle_id IS NOT NULL) AS veille_succession
        FROM parcel_p_score_v2 s
        LEFT JOIN parcel_veille_succession vs ON vs.parcelle_id = s.parcelle_id
        WHERE {' AND '.join(where)}
        ORDER BY s.rang ASC NULLS LAST LIMIT :limit OFFSET :offset"""),
        params).mappings().all()
    return {"run_id": run["run_id"], "n": len(rows),
            "items": [_row_payload(r, run) for r in rows],
            "avertissement": AVERTISSEMENT_CENSURE}


@router.get("/brulantes")
def brulantes(db: Session = Depends(get_db)) -> dict:
    """Vue Brûlantes v2 (chaude ∧ contribution D minimale ∧ événement daté < 12
    mois ou top décile D — un contexte seul ne franchit jamais un seuil)."""
    return liste(tier="brulante", commune=None, include_copro=False,
                 limit=200, offset=0, db=db)


@router.get("/reserve-fonciere")
def reserve(commune: str | None = Query(None), limit: int = Query(200, le=1000),
            db: Session = Depends(get_db)) -> dict:
    """Réserve foncière (C fort, P faible) — VITRINE CAPACITÉ, pas un pipeline :
    la sélection négative de ce segment est prouvée (Phase 0)."""
    out = liste(tier="reserve_fonciere", commune=commune, include_copro=False,
                limit=limit, offset=0, db=db)
    out["note"] = ("réserve foncière = capacité forte, probabilité de mutation "
                   "FAIBLE — ne pas présenter comme pipeline")
    return out


@router.get("/modele")
def modele(db: Session = Depends(get_db)) -> dict:
    """« Sources & fraîcheur » côté modèle : version, sha court, date de gel,
    politique de recalibration, avertissement censure, note deprecated matrice."""
    run = _latest_run(db)
    freeze = json.loads(Path(MODEL_FREEZE).read_text())
    return {
        "model_version": MODEL_VERSION,
        "sha256_court": freeze["sha256"][:12],
        "gel": freeze["gel"],
        "provenance": freeze["provenance"],
        "politique_recalibration": freeze["politique"],
        "dernier_run": {"run_id": run["run_id"],
                        "computed_at": str(run["computed_at"]),
                        "snapshot": run["snapshot_label"]},
        "avertissement_censure": AVERTISSEMENT_CENSURE,
        "matrice_legacy": "les champs matrice (statut, q_score, a_score) restent "
                          "servis par les endpoints historiques — DEPRECATED, "
                          "remplacés par tier/rang/mult_base v2",
    }
