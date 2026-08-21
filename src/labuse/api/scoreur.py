"""O2 — SCOREUR D'ADRESSE INVERSÉ : « je visite ce terrain, qu'en dit LA BUSE ? »

Entrée : une adresse (+ optionnellement le prix DEMANDÉ, saisi À LA MAIN — jamais scrapé).
Chemin : adresse → BAN (géocodage) → point → parcelle CONTENANT le point (déjà en base, déjà
scorée) → verdict compact. Si un prix est saisi, on le confronte à la charge foncière supportable
et au prix probable du foncier (Score É V2, O0) — sans jamais prétendre que c'est LE prix.

Réutilise l'existant : géocodage BAN (comme `audit.audit_by_address`), run servi lu depuis la
constante `Q_A_RUN_LABEL` (aujourd'hui `q_v8_calibre`, cf. config/served_run.txt), table `score_e`. Île entière (pas de restriction commune-pilote : on lit une parcelle déjà en base,
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

# M135 — échelle d'action, mapping canonique unique (tiers_client)
# M137 — le CHIP COURT (v[0]) : un seul vocabulaire servi partout, celui des chips.
from ..scoring.tiers_client import TIERS_CLIENT as _TC
_TIER_LABELS = {k: v[0] for k, v in _TC.items()}


class ScoreurIn(BaseModel):
    q: str                              # adresse libre
    prix_demande_eur: float | None = None   # prix affiché/demandé, saisi manuellement
    idu: str | None = None              # M82 (CAS E) : parcelle DÉJÀ résolue par l'autocomplétion interne


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


_AVERT = "Estimé — ni un prix ni une promesse ; hypothèses de bilan génériques."


def _prix_constat(prix: float, charge, prix_probable, surface) -> dict:
    """M128-6-§1 — CONSTAT chiffré nu confronté à un prix SAISI par un tiers. Deux règles :

      - §1 : la `charge` vient de la MÉTHODE DOCUMENTS (bilan à rebours, `compute_bilan`), jamais de
        `score_e` (barème sectoriel, systématiquement optimiste — cf. registre de dette M128).
      - §1.3 : AUCUN verdict, aucune conclusion. « bonne affaire », « au-dessus du marché »,
        « rentable », « validé » sont bannis — on sert les NOMBRES et leur méthode, le lecteur conclut.

    Le prix probable du foncier (médiane terrain sectorielle) est NON divergent : servi tel quel."""
    out: dict = {"prix_saisi_eur": round(prix)}
    if surface and surface > 0:
        out["prix_saisi_m2_terrain"] = round(prix / surface)
    if prix_probable is not None:
        out["prix_probable_foncier_eur"] = round(prix_probable)
        out["ecart_vs_prix_probable_pct"] = (round(100 * (prix - prix_probable) / prix_probable)
                                             if prix_probable else None)
    if charge is not None:
        out["charge_fonciere_supportable_eur"] = round(charge)   # méthode documents (bilan à rebours)
        out["marge_a_ce_prix_eur"] = round(charge - prix)
        out["methode"] = ("Constat chiffré, aucun verdict. Marge à ce prix = charge foncière "
                          "supportable (bilan à rebours, méthode documents) − prix saisi ; repère "
                          "foncier = médiane terrain sectorielle.")
    else:
        out["message"] = ("Charge foncière (méthode documents) non calculable pour cette parcelle — "
                          "marge non chiffrable.")
    out["avertissement"] = _AVERT
    return out


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.post("")
def scoreur_adresse(body: ScoreurIn, db: Session = Depends(get_db)) -> dict:
    """Adresse → parcelle en base → verdict compact (+ confrontation du prix demandé si fourni)."""
    # M82 (CAS E) : si l'autocomplétion interne a DÉJÀ rattaché une parcelle (idu), on l'utilise
    # directement — le re-géocodage BAN du label formaté (« 12 Rue…, Saint-Paul (97460) ») pouvait
    # retomber hors de la parcelle et fabriquer un « aucune parcelle » fantôme.
    _sel = """SELECT p.idu, p.commune, p.section, p.numero, round(p.surface_m2) AS surface_m2,
                     s2.tier, s2.rang, s2.percentile
              FROM parcels p
              LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :run """
    if body.idu:
        label = body.q
        row = db.execute(text(_sel + "WHERE p.idu = :idu LIMIT 1"),
                         {"run": Q_A_RUN_LABEL, "idu": body.idu}).mappings().first()
    else:
        geo = _geocode(body.q)
        label = geo["label"]
        row = db.execute(text(_sel + "WHERE ST_Contains(p.geom, ST_SetSRID(ST_Point(:lon, :lat), 4326)) "
                              "ORDER BY p.surface_m2 DESC NULLS LAST LIMIT 1"),
                         {"run": Q_A_RUN_LABEL, "lon": geo["lon"], "lat": geo["lat"]}).mappings().first()
    if not row:
        return {"ok": False, "adresse": label,
                "message": "Aucune parcelle en base à cette adresse — hors périmètre couvert, "
                           "ou terrain non cadastré. Essayez l'audit par référence cadastrale."}

    tier = row["tier"]
    verdict = {"tier": tier, "libelle": _TIER_LABELS.get(tier, "Non évaluée"),
               "rang": row["rang"], "percentile": float(row["percentile"]) if row["percentile"] is not None else None}

    # M128-5-§2 / M128-6-§1 : aucune marge score_e (barème sectoriel) servie à un tiers. Le prix
    # probable du foncier (médiane terrain sectorielle) est NON divergent → lu tel quel dans score_e.
    # La CHARGE, elle, ne vient plus de score_e mais de la MÉTHODE DOCUMENTS (compute_bilan), et
    # seulement si un prix est saisi (§1). Aucun chiffre de marge auto-affiché.
    prix_probable = None
    try:
        if db.execute(text("SELECT to_regclass('score_e')")).scalar() is not None:
            se = db.execute(text(
                "SELECT estimable, prix_probable FROM score_e WHERE idu = :i"),
                {"i": row["idu"]}).mappings().first()
            if se and se["estimable"]:
                prix_probable = se["prix_probable"]
    except Exception:  # noqa: BLE001
        pass

    out = {"ok": True, "adresse": label, "idu": row["idu"], "commune": row["commune"],
           "section": row["section"], "numero": row["numero"], "surface_m2": row["surface_m2"],
           "verdict": verdict,
           "fiche_url": f"/parcels/{row['idu']}"}
    if body.prix_demande_eur is not None:
        # M128-6-§1 : charge = bilan à rebours (compute_bilan), calculé à la volée (37–237 ms mesurés,
        # non prohibitif sur une route déjà géocodante). Éphémère : aucune bascule, aucun rebuild.
        charge = None
        try:
            from ..faisabilite.bilan import compute_bilan_servi
            from ..faisabilite.db import parcel_faisabilite
            pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": row["idu"]}).scalar()
            fa = parcel_faisabilite(db, pid) if pid else None
            if fa:
                b, ps = compute_bilan_servi(db, pid, fa)
                if b is not None and not (ps or {}).get("non_calculable"):
                    charge = (b.charge_fonciere or {}).get("central")
        except Exception:  # noqa: BLE001
            pass
        out["prix"] = _prix_constat(float(body.prix_demande_eur), charge, prix_probable, row["surface_m2"])
    return out
