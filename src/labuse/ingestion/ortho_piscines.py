"""Wave Détection Ortho, Lot 3 — détection piscines V0 (colorimétrique, OpenCV, CPU).

V0 DÉTERMINISTE + validation visuelle Vic avant tout ML (philosophie du mandat).
Pipeline par tuile (cache Lot 2, 2560×2560 px à 20 cm, EPSG:2975) :
1. HSV → masque cyan/turquoise (plages config) → morphologie ouverture/fermeture.
2. Contours + filtres géométriques : surface 6-150 m², solidité (formes de bassin,
   pas de filaments), ratio d'aspect < 6.
3. Filtres contextuels (SQL, post-insert) : centroïde dans une parcelle bâtie ou
   à < 30 m d'une emprise ; exclusion eau/ravines (spatial_layers) ; hors parcelle
   = hors cadastre = océan/espaces naturels → rejeté.
4. Faux positifs GÉRÉS : bâches/toits bleus (recouvrement emprise bâtie > 60 % →
   rejet), trampolines (sombres : V min du masque les écarte), terrains de sport
   (> 150 m²). Faux négatifs ASSUMÉS : piscines vertes/sales, couvertes, sous
   ombrage — c'est le recall qu'on MESURERA (échantillon 3 quartiers), pas qu'on
   fantasmera.
5. `confiance` composite (couleur, forme, taille typique 15-50 m², contexte) —
   détail dans `criteres` (debug/calibration). Rattachement : parcelle du centroïde,
   sinon plus grand recouvrement.

POSITIONNEMENT (non négociable, mandat) : qualification COMMERCIALE uniquement —
aucun usage, requête ou texte orienté détection fiscale.
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
from .ortho_tiles import MILLESIME, tile_path

DDL = """
CREATE TABLE IF NOT EXISTS ortho_detections (
  id            serial PRIMARY KEY,
  type          varchar(12) NOT NULL,           -- 'piscine' | 'pv'
  geom          geometry(Polygon, 4326) NOT NULL,
  geom_2975     geometry(Polygon, 2975),
  surface_m2    double precision,
  confiance     double precision,               -- 0-1 composite
  criteres      jsonb,                          -- détail scoring (debug/calibration)
  idu           varchar(14),
  sur_bati      boolean,
  validation    varchar(16),                    -- null | 'ok' | 'faux_positif' (outil Lot 3)
  tile_id       varchar(24),  -- pas de FK : la détection ne doit jamais attendre le job d'acquisition
  detected_at   timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ortho_detections_geom_2975_gix ON ortho_detections USING gist (geom_2975);
CREATE INDEX IF NOT EXISTS ortho_detections_idu_idx ON ortho_detections (idu);
CREATE INDEX IF NOT EXISTS ortho_detections_type_idx ON ortho_detections (type, validation);
"""

M_PER_PX = 0.2
PX_AREA_M2 = M_PER_PX * M_PER_PX


def _cfg() -> dict[str, Any]:
    return load_yaml_config("detection_ortho")["piscines"]


def _detect_in_image(img: np.ndarray, cfg: dict[str, Any]) -> list[dict]:
    """Candidats piscine dans une image BGR — géométrie en PIXELS + scores partiels."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lo = np.array([cfg["hsv_h_min"], cfg["hsv_s_min"], cfg["hsv_v_min"]], np.uint8)
    hi = np.array([cfg["hsv_h_max"], 255, 255], np.uint8)
    mask = cv2.inRange(hsv, lo, hi)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(cfg["morpho_px"]),) * 2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: list[dict] = []
    smin_px = cfg["surface_min_m2"] / PX_AREA_M2
    smax_px = cfg["surface_max_m2"] / PX_AREA_M2
    for c in contours:
        area = cv2.contourArea(c)
        if not smin_px <= area <= smax_px:
            continue
        hull = cv2.convexHull(c)
        solidite = area / max(cv2.contourArea(hull), 1.0)
        if solidite < cfg["solidite_min"]:
            continue
        (_, _), (w, h), _ = cv2.minAreaRect(c)
        if min(w, h) <= 0 or max(w, h) / min(w, h) > cfg["aspect_max"]:
            continue
        # pureté couleur : moyenne S/V et proximité de teinte au cœur de la plage
        m = np.zeros(mask.shape, np.uint8)
        cv2.drawContours(m, [c], -1, 255, -1)
        mh, ms, mv = (float(x) for x in cv2.mean(hsv, mask=m)[:3])
        h_centre = (cfg["hsv_h_min"] + cfg["hsv_h_max"]) / 2
        h_demi = (cfg["hsv_h_max"] - cfg["hsv_h_min"]) / 2
        # plateau : pleine note sur la moitié centrale de la plage (l'eau de piscine
        # réelle vit vers H 88-100 — un pic au centre pénaliserait à tort)
        exces = abs(mh - h_centre) / h_demi
        prox_h = 1.0 if exces <= 0.5 else max(0.0, (1 - exces) / 0.5)
        score_couleur = prox_h * min(1.0, ms / 160)
        score_forme = min(1.0, (solidite - cfg["solidite_min"]) / (1 - cfg["solidite_min"]) + 0.3)
        surface_m2 = area * PX_AREA_M2
        # taille typique 15-50 m² : plateau à 1, décroît vers les bornes 6/150
        if 15 <= surface_m2 <= 50:
            score_taille = 1.0
        elif surface_m2 < 15:
            score_taille = max(0.2, (surface_m2 - cfg["surface_min_m2"]) / (15 - cfg["surface_min_m2"]))
        else:
            score_taille = max(0.2, 1 - (surface_m2 - 50) / (cfg["surface_max_m2"] - 50))
        approx = cv2.approxPolyDP(c, 1.5, True).reshape(-1, 2)
        if len(approx) < 3:
            continue
        out.append({
            "px": approx, "surface_m2": round(surface_m2, 1),
            "scores": {"couleur": round(score_couleur, 3), "forme": round(score_forme, 3),
                       "taille": round(score_taille, 3), "solidite": round(solidite, 3),
                       "hsv_moyen": [round(mh, 1), round(ms, 1), round(mv, 1)]},
        })
    return out


def _px_to_wkt_2975(px: np.ndarray, xmin: int, ymin: int, tile_px: int) -> str:
    """(col, row) pixels → POLYGON EPSG:2975 (origine image = coin NW de la tuile)."""
    ymax = ymin + int(tile_px * M_PER_PX)
    pts = [(xmin + float(cx) * M_PER_PX, ymax - float(cy) * M_PER_PX) for cx, cy in px]
    pts.append(pts[0])
    return "POLYGON((" + ", ".join(f"{x:.2f} {y:.2f}" for x, y in pts) + "))"


def detect_tiles(session: Session, *, limit: int | None = None, log=print) -> dict[str, Any]:
    """Détection sur les tuiles acquises non traitées (checkpoint = traite_at)."""
    session.execute(text(DDL))
    cfg = _cfg()
    tuiles_cfg = load_yaml_config("detection_ortho")["tuiles"]
    tile_px = int(tuiles_cfg["pixels"])
    rows = session.execute(text(
        "SELECT tile_id FROM ortho_tiles WHERE acquise_at IS NOT NULL AND traite_at IS NULL"
        " ORDER BY tile_id" + (" LIMIT :lim" if limit else "")),
        {"lim": limit} if limit else {}).scalars().all()
    n_cand = n_garde = n_tiles = 0
    t0 = time.monotonic()
    dist_ctx = float(cfg["contexte_bati_m"])
    for tid in rows:
        p = tile_path(tid)
        if not p.exists():
            continue
        img = cv2.imread(str(p))
        if img is None:
            continue
        xmin, ymin = (int(v) for v in tid.split("_"))
        cands = _detect_in_image(img, cfg)
        n_ins = 0
        if cands:
            # une seule requête par tuile ; le lagon fragmenté produit des centaines de
            # blobs « taille piscine » hors cadastre → filtrés ICI (< 30 m d'une parcelle)
            payload = json.dumps([
                {"wkt": _px_to_wkt_2975(c["px"], xmin, ymin, tile_px),
                 "surf": c["surface_m2"], "scores": c["scores"]} for c in cands
            ])
            n_ins = session.execute(text("""
                WITH cand AS (
                  SELECT ST_MakeValid(ST_GeomFromText(e ->> 'wkt', 2975)) AS g,
                         (e ->> 'surf')::float AS surf, e -> 'scores' AS scores
                  FROM jsonb_array_elements(CAST(:payload AS jsonb)) e
                )
                INSERT INTO ortho_detections (type, geom, geom_2975, surface_m2,
                                              confiance, criteres, tile_id)
                SELECT 'piscine', ST_Transform(g, 4326), g, surf, NULL, scores, :tid
                FROM cand
                WHERE ST_GeometryType(g) = 'ST_Polygon'
                  AND EXISTS (SELECT 1 FROM parcels p
                              WHERE ST_DWithin(p.geom_2975, ST_Centroid(cand.g), :dist))
            """), {"payload": payload, "tid": tid, "dist": dist_ctx}).rowcount
        session.execute(text(
            "UPDATE ortho_tiles SET traite_at = now(), nb_detections = :n WHERE tile_id = :tid"),
            {"n": n_ins, "tid": tid})
        n_cand += len(cands)
        n_garde += n_ins
        n_tiles += 1
        if n_tiles % 100 == 0:
            session.commit()  # checkpoint
            log(f"  détection {n_tiles}/{len(rows)} tuiles, {n_garde}/{n_cand} candidats"
                f" ({n_tiles / (time.monotonic() - t0):.1f} t/s)")
    session.commit()
    return {"tuiles": n_tiles, "candidats_bruts": n_cand, "candidats_inseres": n_garde}


def post_traitement(session: Session, log=print) -> dict[str, Any]:
    """Filtres contextuels SQL + rattachement + confiance finale (candidats sans idu)."""
    cfg = _cfg()
    # 1. rattachement parcelle (centroïde, sinon plus grand recouvrement)
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
          FROM ortho_detections d2
          WHERE d2.type = 'piscine' AND d2.confiance IS NULL
        ) sub WHERE sub.id = d.id
    """))
    # 2. rejets contextuels — hors cadastre (océan/naturel), eau/ravines, toits bleus
    rejets = {}
    rejets["hors_cadastre"] = session.execute(text(
        "DELETE FROM ortho_detections WHERE type = 'piscine' AND confiance IS NULL"
        " AND idu IS NULL")).rowcount
    rejets["eau_ravine"] = session.execute(text("""
        DELETE FROM ortho_detections d
        WHERE d.type = 'piscine' AND d.confiance IS NULL
          AND EXISTS (SELECT 1 FROM spatial_layers sl
                      WHERE sl.kind IN ('water', 'ravine')
                        AND sl.geom_2975 && d.geom_2975
                        AND ST_Intersects(sl.geom_2975, d.geom_2975))
    """)).rowcount
    session.execute(text("""
        UPDATE ortho_detections d SET sur_bati = (sub.ratio > :seuil),
          criteres = d.criteres || jsonb_build_object('recouvrement_bati', round(sub.ratio::numeric, 2))
        FROM (
          SELECT d2.id, coalesce(sum(ST_Area(ST_Intersection(sl.geom_2975, d2.geom_2975))), 0)
                        / NULLIF(ST_Area(d2.geom_2975), 0) AS ratio
          FROM ortho_detections d2
          LEFT JOIN spatial_layers sl ON sl.kind = 'batiment'
            AND sl.geom_2975 && d2.geom_2975 AND ST_Intersects(sl.geom_2975, d2.geom_2975)
          WHERE d2.type = 'piscine' AND d2.confiance IS NULL
          GROUP BY d2.id, d2.geom_2975
        ) sub WHERE sub.id = d.id
    """), {"seuil": float(cfg["toit_bleu_recouvrement_bati"])})
    rejets["toit_bleu"] = session.execute(text(
        "DELETE FROM ortho_detections WHERE type = 'piscine' AND confiance IS NULL"
        " AND sur_bati")).rowcount
    # 3. contexte bâti : parcelle bâtie (1.0) ou bâtiment < 30 m (0.7), sinon rejet
    n_final = session.execute(text("""
        WITH ctx AS (
          SELECT d.id,
            CASE
              WHEN EXISTS (SELECT 1 FROM parcel_residuel_bati rb
                           WHERE rb.idu = d.idu AND rb.emprise_batie_m2 > 20) THEN 1.0
              WHEN EXISTS (SELECT 1 FROM spatial_layers sl WHERE sl.kind = 'batiment'
                           AND ST_DWithin(sl.geom_2975, d.geom_2975, :dist)) THEN 0.7
              ELSE 0.0
            END AS score_ctx
          FROM ortho_detections d
          WHERE d.type = 'piscine' AND d.confiance IS NULL
        )
        UPDATE ortho_detections d
        SET confiance = round(LEAST(1.0,
              :pc * (d.criteres ->> 'couleur')::float
            + :pf * (d.criteres ->> 'forme')::float
            + :pt * (d.criteres ->> 'taille')::float
            + :px * ctx.score_ctx)::numeric, 3),
            criteres = d.criteres || jsonb_build_object('contexte', ctx.score_ctx)
        FROM ctx WHERE ctx.id = d.id
    """), {"pc": float(cfg["poids_couleur"]), "pf": float(cfg["poids_forme"]),
           "pt": float(cfg["poids_taille"]), "px": float(cfg["poids_contexte"]),
           "dist": float(cfg["contexte_bati_m"])}).rowcount
    rejets["sans_contexte"] = session.execute(text(
        "DELETE FROM ortho_detections WHERE type = 'piscine'"
        " AND (criteres ->> 'contexte')::float = 0 AND validation IS NULL")).rowcount
    session.commit()
    stats = session.execute(text(
        "SELECT count(*), round(avg(confiance)::numeric, 2),"
        " count(*) FILTER (WHERE confiance >= 0.7)"
        " FROM ortho_detections WHERE type = 'piscine'")).one()
    log(f"  rejets : {rejets}")
    return {"scorees": n_final, "rejets": rejets,
            "detections": stats[0], "confiance_moy": float(stats[1] or 0),
            "confiance_haute": stats[2], "millesime": MILLESIME}
