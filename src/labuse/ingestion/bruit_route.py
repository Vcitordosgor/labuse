"""LOT 3 (data-gap) — Classement sonore des infrastructures de transports terrestres (974).

Source : Cerema / Cartagène, service ArcGIS REST « Routes_classement_sonore_La_Reunion_V2 »
(export GeoJSON intégral en une requête — 1 004 tronçons, maxRecordCount 2000, VÉRIFIÉ live
10/07/2026). Millésime : étude Cerema 2022, classement EN VIGUEUR (arrêtés préfectoraux des
14-15/12/2023, remplace 2014).

Le flux livre les AXES classés (lignes) + la LARGEUR du secteur affecté (`sect_bruit`, en m,
de part et d'autre — art. R.571-32 CE : c'est dans cette bande que l'isolement acoustique
renforcé des bâtiments est OBLIGATOIRE). On matérialise donc la BANDE : buffer de
`sect_bruit` m sur l'axe (calcul en EPSG:2975), stockée dans spatial_layers kind='bruit_route',
subtype='cat<n>' (catégorie 1 = la plus bruyante, secteur 300 m … 5 = 10 m).

⚠ PEB (zones A/B/C/D des aérodromes) : INTROUVABLE en SIG open data (PDF préfecture
uniquement — Roland-Garros AP 2017-2123 du 17/10/2017, Pierrefonds AP du 29/03/2017) →
lot PEB BLOQUÉ, consigné au rapport. Le classement sonore n'en est PAS un substitut.
"""
from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

URL = ("https://cartagene.cerema.fr/server/rest/services/Hosted/"
       "Routes_classement_sonore_La_Reunion_V2/FeatureServer/0/query"
       "?where=1%3D1&outFields=*&f=geojson")
SOURCE_NAME = "Classement sonore ITT (Cerema)"


def ingest_bruit_route(session: Session, run_id: int | None = None, log=print) -> dict:
    """Télécharge le flux, matérialise les bandes (buffer sect_bruit en 2975) — idempotent."""
    with httpx.Client(timeout=max(get_settings().http_timeout_s, 120.0),
                      headers={"User-Agent": constants.USER_AGENT}, follow_redirects=True) as c:
        r = c.get(URL)
        r.raise_for_status()
        feats = r.json().get("features") or []
    if len(feats) >= 2000:
        log(f"  ⚠ {len(feats)} tronçons = plafond ArcGIS — pagination à ajouter (troncature)")
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'bruit_route'"))
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    import json as _json
    n = 0
    for f in feats:
        p = f.get("properties") or {}
        cat = p.get("catégorie") or p.get("categorie")
        largeur = p.get("sect_bruit")
        if not f.get("geometry") or cat is None or not largeur:
            continue
        session.execute(text(
            """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune, ingestion_run_id)
               VALUES ('bruit_route', :sub, :n,
                       ST_Transform(ST_Buffer(ST_Transform(
                           ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326), 2975), :larg), 4326),
                       CAST(:a AS jsonb), :sid, :c, :run)"""),
            {"sub": f"cat{int(cat)}", "n": f"Classement sonore cat.{cat} — {p.get('nom_comm') or ''}",
             "g": _json.dumps(f["geometry"]), "larg": float(largeur),
             "a": _json.dumps({"categorie": int(cat), "sect_bruit_m": largeur,
                               "tissu": p.get("tissu"), "nb_voies": p.get("nb_voies"),
                               "insee_comm": p.get("insee_comm"), "gestion": p.get("gestion"),
                               "millesime": "Cerema 2022 / AP 14-15.12.2023"}),
             "sid": sid, "c": p.get("nom_comm"), "run": run_id})
        n += 1
    session.flush()
    return {"troncons": len(feats), "bandes": n}
