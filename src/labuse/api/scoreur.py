"""O2 — SCOREUR D'ADRESSE INVERSÉ : « je visite ce terrain, qu'en dit LA BUSE ? »

Entrée : une adresse (+ optionnellement le prix DEMANDÉ, saisi À LA MAIN — jamais scrapé).
Chemin : adresse → BAN (géocodage) → point → parcelle CONTENANT le point (déjà en base, déjà
scorée) → verdict compact. Si un prix est saisi, on le confronte à la charge foncière supportable
et au prix probable du foncier (Score É V2, O0) — sans jamais prétendre que c'est LE prix.

Réutilise l'existant : géocodage BAN (comme `audit.audit_by_address`), run servi `q_v7_defisc`,
table `score_e`. Île entière (pas de restriction commune-pilote : on lit une parcelle déjà en base,
aucune ingestion live). Zéro scraping.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config
from ..scoring.score_v_constants import Q_A_RUN_LABEL

log = logging.getLogger("labuse.scoreur")
router = APIRouter(prefix="/scoreur-adresse", tags=["scoreur-adresse"])

BAN_URL = "https://api-adresse.data.gouv.fr/search/"

_TIER_LABELS = {
    "brulante": "Brûlante — signal de vendabilité fort",
    "chaude": "Chaude — opportunité foncière",
    "reserve_fonciere": "Réserve foncière — potentiel à moyen terme",
    "a_creuser": "À creuser — potentiel partiel",
    "ecartee": "Écartée — hors critères",
}


class ScoreurIn(BaseModel):
    q: str                              # adresse libre
    prix_demande_eur: float | None = None   # prix affiché/demandé, saisi manuellement


def _geocode(q: str) -> dict:
    q = (q or "").strip()
    if len(q) < 3:
        raise HTTPException(422, "Adresse trop courte.")
    ban, last = None, None
    for _ in range(2):   # BAN rate-limite parfois : 2e tentative
        try:
            with httpx.Client(timeout=config.get_settings().http_timeout_s,
                              headers={"User-Agent": "LA-BUSE/0.1 (+scoreur)"}) as c:
                r = c.get(BAN_URL, params={"q": q, "limit": 1})
                r.raise_for_status()
                ban = r.json()
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
    if ban is None:
        raise HTTPException(503, f"Géocodage (BAN) injoignable : {type(last).__name__}.")
    feats = ban.get("features") or []
    if not feats:
        raise HTTPException(404, f"Adresse « {q} » non trouvée.")
    lon, lat = feats[0]["geometry"]["coordinates"]
    return {"lon": lon, "lat": lat, "label": feats[0].get("properties", {}).get("label", q)}


def _prix_verdict(prix: float, charge, prix_probable, surface) -> dict:
    """Confronte le prix demandé (Estimé du marché) à la charge foncière supportable et au prix probable."""
    out: dict = {"prix_demande_eur": round(prix)}
    if surface and surface > 0:
        out["prix_demande_m2_terrain"] = round(prix / surface)
    if charge is not None:
        out["marge_a_ce_prix_eur"] = round(charge - prix)   # >0 : reste de la marge sous la charge supportable
        if prix <= charge:
            out["verdict"] = "opportunite"
            out["message"] = "Sous la charge foncière supportable estimée — marge résiduelle pour un opérateur."
        elif prix_probable is not None and prix <= prix_probable * 1.1:
            out["verdict"] = "dans_le_marche"
            out["message"] = "Proche du prix probable du foncier — dans le marché, marge de promotion serrée."
        else:
            out["verdict"] = "cher"
            out["message"] = "Au-dessus du prix probable et de la charge supportable estimés — cher pour un opérateur."
    else:
        out["verdict"] = "non_estimable"
        out["message"] = "Charge foncière non estimable pour cette parcelle — le prix ne peut pas être qualifié."
    out["avertissement"] = "Estimé — ni un prix ni une promesse ; hypothèses de bilan génériques."
    return out


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.post("")
def scoreur_adresse(body: ScoreurIn, db: Session = Depends(get_db)) -> dict:
    """Adresse → parcelle en base → verdict compact (+ confrontation du prix demandé si fourni)."""
    geo = _geocode(body.q)
    row = db.execute(text(
        """SELECT p.idu, p.commune, p.section, p.numero, round(p.surface_m2) AS surface_m2,
                  s2.tier, s2.rang, s2.percentile
           FROM parcels p
           LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :run
           WHERE ST_Contains(p.geom, ST_SetSRID(ST_Point(:lon, :lat), 4326))
           ORDER BY p.surface_m2 DESC NULLS LAST LIMIT 1"""),
        {"run": Q_A_RUN_LABEL, "lon": geo["lon"], "lat": geo["lat"]}).mappings().first()
    if not row:
        return {"ok": False, "adresse": geo["label"],
                "message": "Aucune parcelle en base à cette adresse — hors périmètre couvert, "
                           "ou terrain non cadastré. Essayez l'audit par référence cadastrale."}

    tier = row["tier"]
    verdict = {"tier": tier, "libelle": _TIER_LABELS.get(tier, "Non évaluée"),
               "rang": row["rang"], "percentile": float(row["percentile"]) if row["percentile"] is not None else None}

    # Score É (marge €) — guardé
    score_e = None
    charge = prix_probable = None
    try:
        if db.execute(text("SELECT to_regclass('score_e')")).scalar() is not None:
            se = db.execute(text(
                "SELECT estimable, marge_estimee, charge_supportable, prix_probable, niveau_prix, libelle_court "
                "FROM score_e WHERE idu = :i"), {"i": row["idu"]}).mappings().first()
            if se:
                score_e = dict(se)
                if se["estimable"]:
                    charge, prix_probable = se["charge_supportable"], se["prix_probable"]
    except Exception:  # noqa: BLE001
        pass

    out = {"ok": True, "adresse": geo["label"], "idu": row["idu"], "commune": row["commune"],
           "section": row["section"], "numero": row["numero"], "surface_m2": row["surface_m2"],
           "verdict": verdict, "score_e": score_e,
           "fiche_url": f"/parcels/{row['idu']}"}
    if body.prix_demande_eur is not None:
        out["prix"] = _prix_verdict(float(body.prix_demande_eur), charge, prix_probable, row["surface_m2"])
    return out
