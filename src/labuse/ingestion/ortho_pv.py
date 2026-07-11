"""Wave Détection Ortho, Lot 4 — détection PV V0 : candidats SCORÉS, attentes calibrées.

Plus difficile que les piscines (mandat : précision moyenne assumée, cible ≥ 75 %) :
- recherche UNIQUEMENT sur les emprises bâties BD TOPO + polygones parkings_aper
  (ombrières) — masque de zones autorisées rasterisé par tuile ;
- teinte sombre bleutée/anthracite à réflectance FAIBLE (V ≤ 110), formes rectilignes
  (rectangularité ≥ 0,75 après minAreaRect), surface ≥ 4 m² ;
- PIÈGE LOCAL n° 1 : les chauffe-eau solaires (RTAA DOM, le 974 en est couvert) —
  4-8 m² → `ces=true` dans criteres → `pv_probable_ces` (exclu des stats PV mais
  GARDÉ : signal « pas de CES à vendre ici » pour le segment chauffe-eau) ;
  ≥ 8 m² → PV probable ;
- confusions gérées : toit sombre uniforme (masque > 80 % de l'emprise du bâtiment →
  rejet de ses blobs), ombres portées (non rectilignes → rectangularité), velux
  (< 4 m²).

Les candidats vont dans ortho_detections type='pv' ; ils ne remontent dans
parcel_equipements QUE si la précision validée (échantillon 150, même outil que les
piscines : /ortho/validation?type=pv) atteint 75 % — règle du mandat, auto-appliquée
par ortho_equipements.materialiser_pv().
"""
from __future__ import annotations

import json
import time
from typing import Any

import cv2
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import load_yaml_config
from .ortho_piscines import DDL as DDL_DET
from .ortho_piscines import M_PER_PX, PX_AREA_M2, _px_to_wkt_2975
from .ortho_tiles import tile_path

_TILE_M = 512


def _cfg() -> dict[str, Any]:
    return load_yaml_config("detection_ortho")["pv"]


def _zones_autorisees(session: Session, tid: str, tile_px: int) -> np.ndarray | None:
    """Masque binaire (bâti ∪ parkings) de la tuile — None si tuile sans zone utile."""
    xmin, ymin = (int(v) for v in tid.split("_"))
    rows = session.execute(text("""
        SELECT ST_AsText(ST_Intersection(g, env)) FROM (
          SELECT sl.geom_2975 AS g,
                 ST_MakeEnvelope(:x0, :y0, :x1, :y1, 2975) AS env
          FROM spatial_layers sl
          WHERE sl.kind = 'batiment'
            AND sl.geom_2975 && ST_MakeEnvelope(:x0, :y0, :x1, :y1, 2975)
          UNION ALL
          SELECT pk.geom_2975, ST_MakeEnvelope(:x0, :y0, :x1, :y1, 2975)
          FROM parkings_aper pk
          WHERE pk.geom_2975 && ST_MakeEnvelope(:x0, :y0, :x1, :y1, 2975)
        ) t WHERE NOT ST_IsEmpty(ST_Intersection(g, env))
    """), {"x0": xmin, "y0": ymin, "x1": xmin + _TILE_M, "y1": ymin + _TILE_M}).scalars().all()
    if not rows:
        return None
    mask = np.zeros((tile_px, tile_px), np.uint8)
    ymax = ymin + _TILE_M
    for wkt in rows:
        if not wkt.startswith(("POLYGON", "MULTIPOLYGON", "GEOMETRYCOLLECTION")):
            continue
        for ring in _rings(wkt):
            pts = np.array([[(x - xmin) / M_PER_PX, (ymax - y) / M_PER_PX]
                            for x, y in ring], np.int32)
            cv2.fillPoly(mask, [pts], 255)
    return mask


def _rings(wkt: str) -> list[list[tuple[float, float]]]:
    """Anneaux extérieurs d'un (MULTI)POLYGON WKT — parseur minimal suffisant ici."""
    out = []
    depth = 0
    cur = ""
    for ch in wkt:
        if ch == "(":
            depth += 1
            cur = ""
        elif ch == ")":
            if depth >= 2 and cur.strip():
                ring = []
                for pair in cur.split(","):
                    xy = pair.strip().split(" ")
                    if len(xy) >= 2:
                        ring.append((float(xy[0]), float(xy[1])))
                if len(ring) >= 3:
                    out.append(ring)
            depth -= 1
            cur = ""
        else:
            cur += ch
    return out


def _detect_pv(img: np.ndarray, zones: np.ndarray, cfg: dict[str, Any]) -> list[dict]:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lo = np.array([cfg["hsv_h"][0], cfg["hsv_s"][0], cfg["hsv_v"][0]], np.uint8)
    hi = np.array([cfg["hsv_h"][1], cfg["hsv_s"][1], cfg["hsv_v"][1]], np.uint8)
    mask = cv2.inRange(hsv, lo, hi)
    mask = cv2.bitwise_and(mask, zones)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (int(cfg["morpho_px"]),) * 2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    # toit sombre uniforme : composantes du masque de zones où le sombre couvre > seuil
    n_lbl, labels = cv2.connectedComponents((zones > 0).astype(np.uint8))
    ratios = {}
    for lbl in range(1, n_lbl):
        zone_px = labels == lbl
        tot = int(zone_px.sum())
        if tot:
            ratios[lbl] = float((mask[zone_px] > 0).sum()) / tot
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    smin = cfg["surface_min_m2"] / PX_AREA_M2
    smax = cfg["surface_max_m2"] / PX_AREA_M2
    for c in contours:
        area = cv2.contourArea(c)
        if not smin <= area <= smax:
            continue
        (cx, cy), (w, h), _a = cv2.minAreaRect(c)
        rect_area = max(w * h, 1.0)
        rectangularite = area / rect_area
        if rectangularite < cfg["rectangularite_min"]:
            continue
        # ombres portées en rive de toit : bandes fines — un panneau fait ≥ 1 m de large
        if min(w, h) * M_PER_PX < float(cfg["largeur_min_m"]):
            continue
        lbl = int(labels[min(int(cy), labels.shape[0] - 1), min(int(cx), labels.shape[1] - 1)])
        if ratios.get(lbl, 0.0) > cfg["toit_uniforme_max"]:
            continue  # toit sombre uniforme : pas un panneau, le bâtiment entier est sombre
        surface_m2 = area * PX_AREA_M2
        m = np.zeros(mask.shape, np.uint8)
        cv2.drawContours(m, [c], -1, 255, -1)
        mh, ms, mv = (float(x) for x in cv2.mean(hsv, mask=m)[:3])
        score_couleur = max(0.0, 1 - mv / 140)  # plus c'est sombre, plus c'est panneau
        score_taille = 1.0 if 8 <= surface_m2 <= 100 else (0.5 if surface_m2 < 8 else 0.4)
        score_rect = min(1.0, (rectangularite - cfg["rectangularite_min"])
                         / (1 - cfg["rectangularite_min"]) + 0.3)
        conf = (cfg["poids_rectangularite"] * score_rect
                + cfg["poids_couleur"] * score_couleur
                + cfg["poids_taille"] * score_taille)
        approx = cv2.approxPolyDP(c, 1.5, True).reshape(-1, 2)
        if len(approx) < 3:
            continue
        out.append({
            "px": approx, "surface_m2": round(surface_m2, 1),
            "confiance": round(min(1.0, conf), 3),
            "scores": {"rectangularite": round(rectangularite, 3),
                       "couleur": round(score_couleur, 3), "taille": score_taille,
                       "hsv_moyen": [round(mh, 1), round(ms, 1), round(mv, 1)],
                       "ces": bool(surface_m2 < cfg["ces_max_m2"])},
        })
    return out


def detect_tiles(session: Session, *, limit: int | None = None, log=print) -> dict[str, Any]:
    """PV sur toutes les tuiles acquises (indépendant du traite_at piscines) —
    checkpoint dédié : tuiles sans détection PV enregistrée + marqueur jsonb."""
    session.execute(text(DDL_DET))
    session.execute(text(
        "ALTER TABLE ortho_tiles ADD COLUMN IF NOT EXISTS pv_traite_at timestamptz"))
    cfg = _cfg()
    tile_px = int(load_yaml_config("detection_ortho")["tuiles"]["pixels"])
    rows = session.execute(text(
        "SELECT tile_id FROM ortho_tiles WHERE acquise_at IS NOT NULL"
        " AND pv_traite_at IS NULL ORDER BY tile_id"
        + (" LIMIT :lim" if limit else "")), {"lim": limit} if limit else {}).scalars().all()
    n_tiles = n_cand = 0
    t0 = time.monotonic()
    for tid in rows:
        p = tile_path(tid)
        img = cv2.imread(str(p)) if p.exists() else None
        n_ins = 0
        if img is not None:
            zones = _zones_autorisees(session, tid, tile_px)
            if zones is not None:
                cands = _detect_pv(img, zones, cfg)
                xmin, ymin = (int(v) for v in tid.split("_"))
                if cands:
                    payload = json.dumps([
                        {"wkt": _px_to_wkt_2975(c["px"], xmin, ymin, tile_px),
                         "surf": c["surface_m2"], "conf": c["confiance"],
                         "scores": c["scores"]} for c in cands])
                    n_ins = session.execute(text("""
                        WITH cand AS (
                          SELECT ST_MakeValid(ST_GeomFromText(e ->> 'wkt', 2975)) AS g,
                                 (e ->> 'surf')::float AS surf,
                                 (e ->> 'conf')::float AS conf, e -> 'scores' AS scores
                          FROM jsonb_array_elements(CAST(:payload AS jsonb)) e
                        )
                        INSERT INTO ortho_detections (type, geom, geom_2975, surface_m2,
                                                      confiance, criteres, sur_bati, tile_id)
                        SELECT 'pv', ST_Transform(g, 4326), g, surf, conf, scores, true, :tid
                        FROM cand WHERE ST_GeometryType(g) = 'ST_Polygon'
                    """), {"payload": payload, "tid": tid}).rowcount
        session.execute(text(
            "UPDATE ortho_tiles SET pv_traite_at = now() WHERE tile_id = :tid"), {"tid": tid})
        n_cand += n_ins
        n_tiles += 1
        if n_tiles % 200 == 0:
            session.commit()
            log(f"  PV {n_tiles}/{len(rows)} tuiles, {n_cand} candidats"
                f" ({n_tiles / (time.monotonic() - t0):.1f} t/s)")
    session.commit()
    return {"tuiles": n_tiles, "candidats": n_cand}


def post_traitement(session: Session, log=print) -> dict[str, Any]:
    """Rattachement parcelle + ombrières parkings (equipe=TRUE)."""
    session.execute(text("""
        UPDATE ortho_detections d SET idu = sub.idu
        FROM (
          SELECT d2.id, coalesce(
            (SELECT p.idu FROM parcels p
             WHERE ST_Contains(p.geom_2975, ST_Centroid(d2.geom_2975)) LIMIT 1),
            (SELECT p.idu FROM parcels p
             WHERE ST_Intersects(p.geom_2975, d2.geom_2975)
             ORDER BY ST_Area(ST_Intersection(p.geom_2975, d2.geom_2975)) DESC LIMIT 1)
          ) AS idu
          FROM ortho_detections d2 WHERE d2.type = 'pv' AND d2.idu IS NULL
        ) sub WHERE sub.id = d.id
    """))
    n_equipe = session.execute(text("""
        UPDATE parkings_aper pk SET equipe = true, updated_at = now()
        WHERE equipe IS DISTINCT FROM true AND EXISTS (
          SELECT 1 FROM ortho_detections d
          WHERE d.type = 'pv' AND (d.criteres ->> 'ces') = 'false'
            AND ST_Intersects(d.geom_2975, pk.geom_2975))
    """)).rowcount
    session.commit()
    stats = session.execute(text("""
        SELECT count(*), count(*) FILTER (WHERE (criteres ->> 'ces') = 'true'),
               round(avg(confiance)::numeric, 2)
        FROM ortho_detections WHERE type = 'pv'
    """)).one()
    log(f"  PV : {stats[0]} candidats dont {stats[1]} CES probables · conf moy {stats[2]}"
        f" · parkings équipés : {n_equipe}")
    return {"candidats": stats[0], "ces": stats[1], "confiance_moy": float(stats[2] or 0),
            "parkings_equipes": n_equipe}
