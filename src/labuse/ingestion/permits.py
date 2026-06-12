"""Ingestion des autorisations d'urbanisme (permis/SITADEL) — Région ODS 974  [✓ live].

Le dataset ODS « liste des permis de construire… » porte les références cadastrales
(sec_cadastre / num_cadastre) : on reconstruit l'IDU 14 caractères et on géolocalise
par jointure à parcels (centroïde). Alimente sitadel_permits → signal de veille
new_permit_nearby (§7bis : rattachement IDU vs proximité).
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

ODS = "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets"
PERMIS_DS = "liste-des-permis-de-construire-et-autres-autorisations-d-urbanisme-a-la-reunion"


def _idu(insee: str, sec, num) -> str | None:
    if not sec or num in (None, ""):
        return None
    return f"{insee}000{str(sec).strip().upper().zfill(2)}{str(num).strip().zfill(4)}"


def ingest_permits(session: Session, insee: str, commune: str, run_id: int | None = None,
                   *, page: int = 100, cap: int = 10000) -> int:
    """Télécharge les permis de la commune (ODS) et les ingère, géolocalisés par IDU."""
    sel = ("type_dau,num_dau,date_reelle_autorisation,"
           "sec_cadastre1,num_cadastre1,sec_cadastre2,num_cadastre2,sec_cadastre3,num_cadastre3")
    recs: list[dict] = []
    with httpx.Client(timeout=max(get_settings().http_timeout_s, 60.0),
                      headers={"User-Agent": constants.USER_AGENT}, follow_redirects=True) as c:
        off = 0
        while off < cap:
            r = c.get(f"{ODS}/{PERMIS_DS}/records",
                      params={"where": f'comm="{insee}"', "limit": page, "offset": off, "select": sel})
            r.raise_for_status()
            res = r.json().get("results", []) or []
            recs.extend(res)
            if len(res) < page:
                break
            off += page
    n = 0
    for rec in recs:
        idus = []
        for si, ni in (("sec_cadastre1", "num_cadastre1"), ("sec_cadastre2", "num_cadastre2"),
                       ("sec_cadastre3", "num_cadastre3")):
            idu = _idu(insee, rec.get(si), rec.get(ni))
            if idu:
                idus.append(idu)
        if not idus:
            continue
        session.execute(
            text(
                """INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw)
                   SELECT :pid, :typ, :dt, CAST(:idus AS jsonb), :c,
                          (SELECT centroid FROM parcels WHERE idu = ANY(:idu_arr) LIMIT 1),
                          CAST(:raw AS jsonb)"""
            ),
            {"pid": rec.get("num_dau"), "typ": rec.get("type_dau"), "dt": rec.get("date_reelle_autorisation"),
             "idus": json.dumps(idus), "idu_arr": idus, "c": commune,
             "raw": json.dumps({"src": "Région ODS — permis 974"})},
        )
        n += 1
    session.flush()
    return n


def nearby_permits(session, parcel_id: int, radius_m: float = 300.0, limit: int = 12) -> dict:
    """Historique des autorisations d'urbanisme à proximité (Lot C4) — pour la fiche.

    Permis rattachés à la parcelle (par IDU) ET permis géolocalisés dans le rayon. Renvoie la
    liste ordonnée (rattachés d'abord, puis par distance) + un résumé. Lecture seule."""
    rows = session.execute(
        text(
            """
            WITH p AS (SELECT idu, centroid FROM parcels WHERE id = :pid)
            SELECT s.permit_id, s.type, s.date,
                   jsonb_exists(s.idu_codes, p.idu) AS rattache,
                   CASE WHEN s.geom IS NULL THEN NULL
                        ELSE round(ST_Distance(ST_Transform(p.centroid, 2975),
                                               ST_Transform(s.geom, 2975))) END AS dist_m
            FROM sitadel_permits s, p
            WHERE jsonb_exists(s.idu_codes, p.idu)
               OR (s.geom IS NOT NULL
                   AND ST_DWithin(ST_Transform(p.centroid, 2975), ST_Transform(s.geom, 2975), :r))
            ORDER BY rattache DESC, dist_m NULLS LAST
            LIMIT :lim
            """
        ), {"pid": parcel_id, "r": radius_m, "lim": limit},
    ).mappings().all()
    items = [{"num": r["permit_id"], "type": r["type"],
              "date": r["date"].date().isoformat() if r["date"] else None,
              "rattache": bool(r["rattache"]),
              "distance_m": int(r["dist_m"]) if r["dist_m"] is not None else None}
             for r in rows]
    rattaches = sum(1 for i in items if i["rattache"])
    return {"radius_m": int(radius_m), "count": len(items), "rattaches": rattaches,
            "items": items, "source": "SITADEL / Région ODS 974"}
