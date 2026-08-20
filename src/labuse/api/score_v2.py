"""API scoring v2 (M5 lot 4) — endpoints ADDITIFS, lecture de la table
précalculée UNIQUEMENT (parcel_p_score_v2, index run+rang / run+tier ; P95 < 200 ms).

Décisions produit gravées : jamais de probabilité brute (mult_base « ×N » +
percentile + rang), univers par défaut HORS copro (toggle include_copro),
réserve foncière ≠ pipeline. Les champs matrice historiques (statut/q_score/a_score)
sont RETIRÉS du produit (M129-B/M136) — plus servis nulle part (cf. GET /v2/modele).
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.p_v2 import MODEL_FREEZE, MODEL_VERSION
from ..scoring.p_v2.libelles_client import enrichir_contributions
from ..verdict_servi import COPRO_MOTIF as _COPRO_MOTIF   # M89 — motif copro (libellé unique)

router = APIRouter(prefix="/v2", tags=["scoring-v2"])


def _check_idu(idu: str) -> str:
    """M-K (P2-31) : garde de FORME d'IDU du rail principal (alphanumérique ≤ 20, sinon 404),
    absente du rail premium /v2. Délègue à app._check_idu (source unique)."""
    from .app import _check_idu as _c
    return _c(idu)

AVERTISSEMENT_CENSURE = ("les ventes récentes apparaissent dans DVF avec 1 à 3 ans "
                         "de retard — les niveaux 2025-2026 sont provisoires, "
                         "le classement est fiable")


def get_db():
    from .app import get_db as _g
    yield from _g()


def _served_run(db: Session) -> dict:
    """ALGO-1 item 6 (SCORING_SPEC §7-J) — le run /v2 est ÉPINGLÉ au label servi
    (Q_A_RUN_LABEL, source unique de vérité) : MÊME règle que la fiche
    (`app._score_v2_run_id`) et le scoreur d'adresse. Plus jamais « le dernier par
    computed_at » : un run CANDIDAT calculé après le servi ne doit JAMAIS fuir dans
    le produit. Label absent → 503 explicite (jamais un repli silencieux)."""
    from ..scoring.score_v_constants import Q_A_RUN_LABEL

    row = db.execute(text(
        "SELECT run_id, model_version, model_sha256, params, computed_at, snapshot_label "
        "FROM p_score_v2_runs WHERE run_id = :r"),
        {"r": Q_A_RUN_LABEL}).mappings().one_or_none()
    if row is None:
        raise HTTPException(503, f"run servi « {Q_A_RUN_LABEL} » absent de p_score_v2_runs — "
                                 "lancer `labuse score-v2` ou vérifier LABUSE_SERVED_RUN.")
    return dict(row)


#: alias rétro-compatible (imports externes éventuels) — même épinglage.
_latest_run = _served_run


def _row_payload(r, run: dict) -> dict:
    top5 = r["top5_contributions"]
    if isinstance(top5, str):
        top5 = json.loads(top5)
    from ..scoring.fraction_client import fraction_humaine as _fh   # M135 P2
    return {
        "parcelle_id": r["parcelle_id"],
        "mult_base": r["mult_base"],              # gardé pour l'audit interne (jamais affiché nu)
        "fraction": (_fh(r["p_raw"]) or {}).get("texte"),   # M135 P2 — la fraction humaine servie
        "percentile": r["percentile"],
        "rang": r["rang"],
        # M89 — copropriété sans rang : on DIT pourquoi (hors univers de classement), jamais un vide.
        # Même libellé que le banquier (source unique verdict_servi.COPRO_MOTIF).
        "hors_classement": (_COPRO_MOTIF if (bool(r["copro"]) and r["rang"] is None) else None),
        "tier": r["tier"],
        "contrib_z": r["contrib_z"], "contrib_d": r["contrib_d"],
        # M5.1 lot 3.3 : chaque contribution porte sa `phrase` en français client
        # (table versionnée libelles_client) — les champs techniques restent pour l'audit
        "pourquoi": enrichir_contributions(top5),
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
    _check_idu(idu)   # M-K (P2-31)
    run = _served_run(db)
    r = db.execute(text("""
        SELECT s.*, (vs.parcelle_id IS NOT NULL) AS veille_succession
        FROM parcel_p_score_v2 s
        LEFT JOIN parcel_veille_succession vs ON vs.parcelle_id = s.parcelle_id
        WHERE s.run_id = :run AND s.parcelle_id = :idu"""),
        {"run": run["run_id"], "idu": idu}).mappings().one_or_none()
    if r is None:
        # M102 P1.4 — pas d'identifiant de run dans un message servable à l'écran.
        raise HTTPException(404, f"Parcelle {idu} inconnue de l'analyse en cours.")
    return _row_payload(r, run)


# ⚠️ DORMANT (M137-K, 20/08/2026) — /v2/liste, /v2/brulantes et /v2/reserve-fonciere alimentaient
# l'outil « Radar des ventes » (front ScoringV2.tsx), RETIRÉ du produit car il recouvre l'Analyse
# LABUSE (même table, même run, même classement, sans carte ni filtres). Ces 3 endpoints RESTENT
# servis (aucun autre consommateur mesuré : ni partners, ni PDF, ni Copilote) + testés
# (test_p_v2_api.py). /v2/score/{idu} et /v2/modele, eux, restent CONSOMMÉS (fiche, scoreur).
@router.get("/liste")
def liste(tier: str | None = Query(None),
          commune: str | None = Query(None, description="code INSEE (5 chiffres)"),
          include_copro: bool = Query(False, description="défaut produit : hors copro"),
          limit: int = Query(100, le=1000), offset: int = Query(0, ge=0),
          db: Session = Depends(get_db)) -> dict:
    """Liste triée par P (rang croissant), filtres tier/commune, toggle copro."""
    run = _served_run(db)
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
    out["note"] = ("potentiel long terme = capacité forte, probabilité de mutation "
                   "FAIBLE — ne pas présenter comme pipeline")
    return out


@router.get("/modele")
def modele(db: Session = Depends(get_db)) -> dict:
    """« Sources & fraîcheur » côté modèle : version, sha court, date de gel,
    politique de recalibration, avertissement censure, note matrice RETIRÉE (M129-B/M136)."""
    _served_run(db)   # 404 explicite si aucun run servi (comportement inchangé)
    freeze = json.loads(Path(MODEL_FREEZE).read_text())
    # M55-H point 11 (décision Vic) : la DATE de gel (`gel`) et le NOM/date du run
    # (`dernier_run`) ne sont plus servis à cette surface CLIENTE — détails admin/interne
    # (ils restent lisibles via les surfaces ops : /readyz, santé, audit, config).
    return {
        "model_version": MODEL_VERSION,
        "sha256_court": freeze["sha256"][:12],
        "provenance": freeze["provenance"],
        "politique_recalibration": freeze["politique"],
        "avertissement_censure": AVERTISSEMENT_CENSURE,
        "matrice_legacy": "les champs matrice (statut, q_score, a_score) sont "
                          "RETIRÉS du produit (M129-B/M136) — plus servis nulle part ; "
                          "le classement est tier/rang/mult_base v2",
    }
