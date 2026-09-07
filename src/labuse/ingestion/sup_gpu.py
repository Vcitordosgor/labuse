"""LOT 4 (data-gap) — Servitudes d'Utilité Publique (assiettes GPU, API Carto IGN).

Source : API Carto GPU (https://apicarto.ign.fr/api/gpu), endpoints `assiette-sup-s`
(surfaciques), `assiette-sup-l` (linéaires), `assiette-sup-p` (ponctuelles) — VÉRIFIÉ live
10/07/2026 sur le 974 (Le Port : pm1/pm2/ac2/ac3/el10). Requête par BBOX de commune
(GeoJSON `geom`), une commune = une unité committée, purge kind='sup' par commune avant
réinsertion (idempotent, même pattern que Géorisques).

Stockage : spatial_layers kind='sup', subtype = code SUP GPU (`suptype` : i4, t5, ac1, pm1…),
attrs = {idass, nomass, typeass, partition, nomsuplitt, urlreg, geo ('s'|'l'|'p')}.

⚠ ANTI-DOUBLE-COMPTE (scoring, couche cascade `sup`) : les catégories DÉJÀ scorées ailleurs
sont neutralisées (INFO ×0) — pm* (PPR → couche `risques`), ac1/ac2 (monuments/sites → `abf`),
el10 (parc national → `parc_national`). Le malus ne porte que sur les catégories NOUVELLES :
aéronautiques t4/t5/t7, lignes électriques i4, canalisations i1/i3, autres → faible.

⚠ Plafond API Carto = 1000 features/réponse : compté et LOGGÉ si atteint (bbox de commune —
jamais observé au 974, données SUP éparses ; consigné par honnêteté).
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .layers_ingest import _insert_layer

BASE = "https://apicarto.ign.fr/api/gpu"
SOURCE_NAME = "SUP — assiettes GPU (API Carto)"
ENDPOINTS = {"s": "assiette-sup-s", "l": "assiette-sup-l", "p": "assiette-sup-p"}
CAP_API = 1000

# ── SOURCES-1 lot 1 — inventaire catégoriel des documents SUP publiés pour le 974 ──
# L'API du service de téléchargement du GPU (le même service que le flux Atom
# `atom/download-feed`, non filtrable par territoire — décision : on interroge son API JSON)
# rend les documents SUP du département : catégorie, gestionnaire, millésime AAAAMMJJ, statut.
# Vérifié live 06/09/2026 : 9 catégories EN VIGUEUR (AC1, AC2, AC4, PM1, PM2, PM3, PT1, PT2,
# T5), dont 3 RESTREINTES au téléchargement (T5, PT1, PT2 — HTTP 403 volontaire du
# gestionnaire). Les autres catégories du standard (AS1 captages, A4/A5, EL3/EL7, I3, T1, T7,
# AC3) ne sont PAS publiées pour le 974 — listées « non publiées », surveillées par la sonde.
URL_INVENTAIRE_974 = ("https://www.geoportail-urbanisme.gouv.fr/api/document"
                      "?documentType%5B%5D=SUP&grid=974")
#: catégories suivies par le mandat SOURCES-1 (inventaire catégorie par catégorie)
CATEGORIES_SUIVIES = ("AC1", "AC2", "AC3", "AC4", "AS1", "A4", "A5", "EL3", "EL7",
                      "I3", "I4", "PM1", "PM2", "PM3", "PT1", "PT2", "T1", "T5", "T7")


def inventaire_974(client: httpx.Client | None = None) -> dict:
    """Inventaire RÉEL des documents SUP 974 (sonde catégorielle). Rend, par catégorie
    suivie : {"etat": "publiee"|"non_publiee", "millesime": AAAAMMJJ|None,
    "gestionnaires": [idGest…]}. Appelle vraiment l'API — lève en cas d'échec réseau
    (l'appelant note « injoignable », jamais un inventaire deviné)."""
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 60.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    try:
        r = c.get(URL_INVENTAIRE_974)
        r.raise_for_status()
        docs = r.json()
    finally:
        if own:
            c.close()
    publiees: dict[str, dict] = {}
    for d in docs if isinstance(docs, list) else []:
        if d.get("effectiveStatus") != "EN_VIGUEUR" or d.get("status") != "document.production":
            continue
        cat = ((d.get("supCategory") or {}).get("name") or "").upper()
        if not cat:
            continue
        nom = d.get("originalName") or ""
        millesime = nom[-8:] if nom[-8:].isdigit() else None
        gest = (d.get("name") or "").split("_")[0]
        e = publiees.setdefault(cat, {"millesime": None, "gestionnaires": []})
        if gest and gest not in e["gestionnaires"]:
            e["gestionnaires"].append(gest)
        if millesime and (e["millesime"] is None or millesime > e["millesime"]):
            e["millesime"] = millesime
    out: dict[str, dict] = {}
    for cat in sorted(set(CATEGORIES_SUIVIES) | set(publiees)):
        if cat in publiees:
            out[cat] = {"etat": "publiee", **publiees[cat]}
        else:
            out[cat] = {"etat": "non_publiee", "millesime": None, "gestionnaires": []}
    return out


def _bbox_geom(session: Session, commune: str) -> dict | None:
    row = session.execute(text(
        "SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) FROM "
        "(SELECT ST_Extent(geom) AS e FROM parcels WHERE commune = :c) x"), {"c": commune}).first()
    if not row or row[0] is None:
        return None
    x1, y1, x2, y2 = row
    return {"type": "Polygon",
            "coordinates": [[[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]]}


def ingest_commune(session: Session, commune: str, run_id: int | None = None,
                   source_id: int | None = None, log=print) -> dict:
    """Ingère les assiettes SUP (3 géométries) d'une commune. Purge avant (idempotent)."""
    geom = _bbox_geom(session, commune)
    if geom is None:
        return {"sup": 0}
    session.execute(text(
        "DELETE FROM spatial_layers WHERE kind = 'sup' AND commune = :c"), {"c": commune})
    n = 0
    with httpx.Client(timeout=max(get_settings().http_timeout_s, 90.0),
                      headers={"User-Agent": constants.USER_AGENT}, follow_redirects=True) as c:
        for geo_kind, ep in ENDPOINTS.items():
            r = c.get(f"{BASE}/{ep}", params={"geom": json.dumps(geom)})
            if r.status_code >= 500:      # une géométrie qui échoue n'arrête pas la commune
                log(f"  ⚠ {commune} {ep} : HTTP {r.status_code}, sauté")
                continue
            r.raise_for_status()
            feats = r.json().get("features") or []
            if len(feats) >= CAP_API:
                log(f"  ⚠ {commune} {ep} : {len(feats)} features = plafond API — possible troncature")
            for f in feats:
                p = f.get("properties") or {}
                if not f.get("geometry"):
                    continue
                _insert_layer(session, "sup", (p.get("suptype") or "").lower() or None,
                              p.get("nomsuplitt") or p.get("nomass"),
                              f["geometry"], source_id, commune, run_id,
                              attrs={"idass": p.get("idass"), "nomass": p.get("nomass"),
                                     "typeass": p.get("typeass"), "partition": p.get("partition"),
                                     "nomsuplitt": p.get("nomsuplitt"), "urlreg": p.get("urlreg"),
                                     "geo": geo_kind})
                n += 1
    session.flush()
    return {"sup": n}
