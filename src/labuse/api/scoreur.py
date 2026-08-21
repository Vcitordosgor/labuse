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


def _prix_verdict(prix: float, charge, prix_probable, surface) -> dict:
    """Confronte le prix demandé à DEUX repères DISTINCTS, chacun NOMMÉ à l'écran (M137-S) :

      - le BADGE juge la position sur le MARCHÉ DU FONCIER (prix probable du terrain), ± 10 % —
        un seul référentiel pour ses trois états (sous/dans/au-dessus du marché) ;
      - la MARGE juge la rentabilité d'une OPÉRATION DE PROMOTION neuve (charge supportable).

    Les deux DIVERGENT pour la majorité des parcelles estimables (~69 % : terrain vendu à son prix
    de marché mais non rentable en promotion, SDP résiduelle faible). L'ancien badge mélangeait les
    repères (« opportunité » = prix ≤ charge = opération ; « dans le marché »/« cher » = marché) →
    deux verdicts contradictoires. Le seuil « opportunité » quitte le badge (il juge l'opération, pas
    le marché) ; la `synthese` réconcilie explicitement badge et marge."""
    out: dict = {"prix_demande_eur": round(prix)}
    if surface and surface > 0:
        out["prix_demande_m2_terrain"] = round(prix / surface)
    if charge is None or prix_probable is None:
        out["verdict"] = "non_estimable"
        out["message"] = "Charge foncière / prix du foncier non estimables — le prix ne peut pas être qualifié."
        out["avertissement"] = _AVERT
        return out
    marge = round(charge - prix)
    out["marge_a_ce_prix_eur"] = marge                      # repère OPÉRATION (promotion neuve)
    # 1) BADGE — repère UNIQUE : le marché du foncier (prix probable du terrain), bande ± 10 %.
    if prix < prix_probable * 0.9:
        out["verdict"] = "sous_marche"
        out["message"] = "En dessous du prix probable du foncier pour ce secteur."
    elif prix <= prix_probable * 1.1:
        out["verdict"] = "dans_marche"
        out["message"] = "Au niveau du prix probable du foncier pour ce secteur."
    else:
        out["verdict"] = "sur_marche"
        out["message"] = "Au-dessus du prix probable du foncier pour ce secteur."
    # 2) SYNTHÈSE — réconcilie badge (marché) et marge (opération) quand ils divergent.
    if marge >= 0:
        out["synthese"] = ("À ce prix, une opération de promotion neuve reste rentable "
                           "(sous la charge foncière supportable estimée).")
    elif out["verdict"] == "dans_marche":
        out["synthese"] = ("Ce terrain se vend à son prix, mais une opération de promotion neuve "
                           "n'y est pas rentable (SDP résiduelle faible).")
    elif out["verdict"] == "sous_marche":
        out["synthese"] = ("Même sous le prix du marché, une opération de promotion neuve n'est pas "
                           "rentable à ce prix (charge foncière supportable très faible).")
    else:   # sur_marche
        out["synthese"] = ("Au-dessus du marché ET au-dessus de ce qu'une opération de promotion "
                           "neuve peut porter à ce prix.")
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

    # M128-5-§2 : la MARGE score_e (méthode barème sectoriel) n'est plus servie à un tiers dans la
    # réponse du scoreur — elle est systématiquement plus optimiste que le document (bilan à rebours),
    # jusqu'au signe opposé, et les deux méthodes divergent (registre de dette M128). On ne lit plus
    # que la charge/prix probable pour QUALIFIER un prix saisi (badge marché, repère prix_probable
    # non divergent) ; aucun chiffre de marge auto-affiché.
    charge = prix_probable = None
    try:
        if db.execute(text("SELECT to_regclass('score_e')")).scalar() is not None:
            se = db.execute(text(
                "SELECT estimable, charge_supportable, prix_probable "
                "FROM score_e WHERE idu = :i"), {"i": row["idu"]}).mappings().first()
            if se and se["estimable"]:
                charge, prix_probable = se["charge_supportable"], se["prix_probable"]
    except Exception:  # noqa: BLE001
        pass

    out = {"ok": True, "adresse": label, "idu": row["idu"], "commune": row["commune"],
           "section": row["section"], "numero": row["numero"], "surface_m2": row["surface_m2"],
           "verdict": verdict,
           "fiche_url": f"/parcels/{row['idu']}"}
    if body.prix_demande_eur is not None:
        out["prix"] = _prix_verdict(float(body.prix_demande_eur), charge, prix_probable, row["surface_m2"])
    return out
