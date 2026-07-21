"""Wave ANC & Végétation, Lot B — canopée par NDVI (BD ORTHO IRC) × hauteur (MNH LiDAR HD).

RÉUTILISE l'infrastructure tuiles du mandat Détection Ortho telle quelle : même grille
`ortho_tiles` (5 041 tuiles 512 m ciblées bâti ∪ parkings, EPSG:2975), même mécanique
d'acquisition WMS (cache purgé après le run RVB → l'IRC se télécharge dans SON cache,
checkpoint = colonne `irc_acquise_at`).

Méthode (constatée le 11/07/2026, pas supposée) :
- IRC : `ORTHOIMAGERY.ORTHOPHOTOS.IRC` (WMS Géoplateforme), 0,4 m/px suffit au NDVI.
  Pseudo-NDVI = (PIR − R) / (PIR + R) avec PIR = canal rouge de l'image IRC, R = canal
  vert (composition IRC standard). JPEG → NDVI approché, assumé (masque, pas mesure).
- Hauteur : le LiDAR HD IGN couvre la TOTALITÉ du 974 (dalles MNH 50 cm publiées le
  25/06/2025) → `methode_hauteur='lidar'`, `confiance='haute'` partout. Le MNH est
  streamé par tuile en GeoTIFF float32 via WMS-R à 1 m/px et JAMAIS stocké (seuls les
  agrégats parcellaires persistent). Fallbacks MNS/texture du mandat : non nécessaires.
- Canopée = NDVI ≥ seuil ∧ MNH > seuil hauteur (le MNH inclut le bâti : le NDVI l'écarte).

Agrégats par parcelle (grille commune 1 m/px, accumulation multi-tuiles dans
`vegetation_zonal_acc`, une parcelle pouvant chevaucher plusieurs tuiles) :
- canopee_pct         : % de la parcelle sous canopée ;
- canopee_limite_pct  : % de la bande intérieure de 3 m le long des limites ;
- canopee_bati_pct    : % du buffer de 8 m autour de l'emprise bâtie (V0
  OMNIDIRECTIONNELLE — TODO v1.1 : pondération directionnelle nord/est/ouest,
  hémisphère sud, hors mandat) ;
- ndvi_moyen          : NDVI moyen de la parcelle (tous pixels).

Attribution : BD ORTHO IRC & LiDAR HD © IGN (Licence Ouverte).
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import _repo_root, load_yaml_config
from .ortho_tiles import _fetch_tile
from .ortho_tiles import tile_path as rvb_tile_path

DDL = """
CREATE TABLE IF NOT EXISTS vegetation_zonal_acc (
  idu         varchar(14) NOT NULL,
  zone        varchar(10) NOT NULL,             -- 'parcelle' | 'limite' | 'bati8'
  px_total    bigint NOT NULL DEFAULT 0,        -- pixels 1 m² de la zone vus
  px_canopee  bigint NOT NULL DEFAULT 0,        -- dont sous canopée (NDVI ∧ MNH)
  ndvi_sum    double precision NOT NULL DEFAULT 0,
  PRIMARY KEY (idu, zone)
);
CREATE TABLE IF NOT EXISTS parcel_vegetation (
  idu                 varchar(14) PRIMARY KEY REFERENCES parcels (idu),
  ndvi_moyen          float,
  canopee_pct         float,
  canopee_limite_pct  float,
  canopee_bati_pct    float,                    -- NULL si parcelle sans emprise bâtie
  methode_hauteur     text,                     -- 'lidar' | 'mns' | 'texture_fallback'
  confiance           text,                     -- 'haute' | 'moyenne'
  bati_voisin_10m     boolean,                  -- bâti d'une AUTRE parcelle < 10 m de la limite
  updated_at          timestamptz DEFAULT now()
);
"""


def _cfg() -> dict[str, Any]:
    return load_yaml_config("anc_vegetation")["vegetation"]


def _ensure_schema(session: Session) -> None:
    """DDL idempotent SANS verrou exclusif inutile : un `ALTER TABLE … IF NOT EXISTS`
    prend l'ACCESS EXCLUSIVE même quand la colonne existe — derrière la transaction
    longue d'une acquisition, il gèle TOUTES les lectures d'ortho_tiles (vécu 11/07).
    On ne tente l'ALTER que si la colonne manque réellement."""
    session.execute(text(DDL))
    cols = {c for (c,) in session.execute(text(
        "SELECT column_name FROM information_schema.columns"
        " WHERE table_name = 'ortho_tiles'")).all()}
    for col in ("irc_acquise_at", "veg_traite_at"):
        if col not in cols:
            session.execute(text(
                f"ALTER TABLE ortho_tiles ADD COLUMN IF NOT EXISTS {col} timestamptz"))
    signal_len = session.execute(text(
        "SELECT character_maximum_length FROM information_schema.columns"
        " WHERE table_name = 'parcel_signals' AND column_name = 'signal_type'")).scalar()
    if signal_len is not None and signal_len < 32:
        # 'vegetation_haute_limite' (23) déborde le varchar(17) historique de l'enum
        session.execute(text(
            "ALTER TABLE parcel_signals ALTER COLUMN signal_type TYPE varchar(32)"))
    session.commit()


def irc_cache_dir() -> Path:
    p = Path(_cfg()["irc"]["cache_dir"])
    p = p if p.is_absolute() else _repo_root() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def irc_tile_path(tile_id: str) -> Path:
    return irc_cache_dir() / f"{tile_id}.jpg"


def acquire_irc(session: Session, *, limit: int | None = None, log=print) -> dict[str, int]:
    """Télécharge l'IRC des tuiles de la grille existante (checkpoint irc_acquise_at) —
    même mécanique que l'acquisition RVB du mandat Ortho, cache séparé."""
    _ensure_schema(session)
    cfg = {**_cfg()["irc"], "taille_m": 512}
    rows = [t for (t,) in session.execute(text(
        "SELECT tile_id FROM ortho_tiles WHERE irc_acquise_at IS NULL ORDER BY tile_id"
        + (" LIMIT :lim" if limit else "")), {"lim": limit} if limit else {}).all()]
    session.commit()   # ne JAMAIS rester « idle in transaction » pendant des heures de WMS
    deja = [t for t in rows if irc_tile_path(t).exists() and irc_tile_path(t).stat().st_size > 0]
    a_faire = [t for t in rows if t not in set(deja)]
    ok_ids: list[str] = list(deja)
    echecs = 0
    t0 = time.monotonic()

    async def main() -> None:
        nonlocal echecs
        sem = asyncio.Semaphore(int(cfg["concurrence"]))

        async def one(tid: str) -> None:
            nonlocal echecs
            async with sem:
                if await _fetch_tile(client, cfg, tid, dest=irc_tile_path(tid)):
                    ok_ids.append(tid)
                    n = len(ok_ids)
                    if n % 200 == 0:
                        log(f"  IRC {n}/{len(rows)} tuiles"
                            f" ({(n - len(deja)) / max(1e-9, time.monotonic() - t0):.1f}/s)")
                else:
                    echecs += 1

        async with httpx.AsyncClient(headers={"User-Agent": "labuse/vegetation-974"}) as client:
            await asyncio.gather(*(one(t) for t in a_faire))

    asyncio.run(main())
    for i in range(0, len(ok_ids), 500):
        session.execute(text(
            "UPDATE ortho_tiles SET irc_acquise_at = now() WHERE tile_id = ANY(:ids)"),
            {"ids": ok_ids[i:i + 500]})
        session.commit()
    return {"demandees": len(rows), "acquises": len(ok_ids), "echecs": echecs}


def purge_irc_cache() -> int:
    n = 0
    for f in irc_cache_dir().glob("*.jpg"):
        f.unlink()
        n += 1
    return n


# ── Traitement par tuile : NDVI (IRC cache) × MNH (streamé, jamais stocké) ──────

def _fetch_mnh(client: httpx.Client, cfg_mnh: dict, tile_id: str) -> np.ndarray | None:
    """MNH GeoTIFF float32 de la tuile via WMS-R, décodé en mémoire (0,5-4 Mo)."""
    xmin, ymin = (int(v) for v in tile_id.split("_"))
    px = int(cfg_mnh["pixels"])
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": cfg_mnh["wms_layer"], "STYLES": "", "CRS": "EPSG:2975",
        "BBOX": f"{xmin},{ymin},{xmin + 512},{ymin + 512}",
        "WIDTH": px, "HEIGHT": px, "FORMAT": "image/geotiff",
    }
    for attempt in range(4):
        try:
            r = client.get(cfg_mnh["wms_url"] + "/wms", params=params, timeout=90)
            if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                arr = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_UNCHANGED)
                if arr is not None and arr.dtype == np.float32 and arr.ndim == 2:
                    return arr
        except httpx.HTTPError:
            pass
        time.sleep(2 ** attempt)
    return None


def _rasterize(gj: dict, xmin: int, ymin: int, px: int) -> np.ndarray | None:
    """GeoJSON (EPSG:2975) → masque binaire sur la grille 1 m de la tuile.
    Anneaux extérieurs remplis, trous soustraits (bande limite = anneau troué)."""
    if gj is None:
        return None
    geoms = gj.get("geometries", [gj]) if gj.get("type") == "GeometryCollection" else [gj]
    polys: list[list[list[list[float]]]] = []
    for g in geoms:
        if g["type"] == "Polygon":
            polys.append(g["coordinates"])
        elif g["type"] == "MultiPolygon":
            polys.extend(g["coordinates"])
    if not polys:
        return None
    ymax = ymin + 512
    scale = px / 512.0
    mask = np.zeros((px, px), np.uint8)
    for rings in polys:
        for i, ring in enumerate(rings):
            pts = np.array([[(x - xmin) * scale, (ymax - y) * scale] for x, y in
                            ((c[0], c[1]) for c in ring)], np.int32)
            cv2.fillPoly(mask, [pts], 1 if i == 0 else 0)
    return mask


_SQL_ZONES_TUILE = """
WITH t AS (SELECT geom FROM ortho_tiles WHERE tile_id = :tid),
par AS (
  SELECT p.idu, ST_MakeValid(p.geom_2975) AS g
  FROM parcels p CROSS JOIN t
  WHERE p.geom_2975 && t.geom AND ST_Intersects(p.geom_2975, t.geom)
    AND p.surface_m2 >= 2
)
SELECT par.idu,
       ST_AsGeoJSON(ST_Intersection(par.g, t.geom), 1)                    AS gj_parcelle,
       ST_AsGeoJSON(ST_Intersection(
           ST_Difference(par.g, ST_Buffer(par.g, -:bande)), t.geom), 1)   AS gj_limite,
       ST_AsGeoJSON(CASE WHEN b.g IS NULL THEN NULL
            ELSE ST_Intersection(ST_Buffer(b.g, :buf), t.geom) END, 1)    AS gj_bati
FROM par
CROSS JOIN t
LEFT JOIN LATERAL (
  SELECT ST_Union(ST_MakeValid(sl.geom_2975)) AS g FROM spatial_layers sl
  WHERE sl.kind = 'batiment' AND sl.geom_2975 && par.g
    AND ST_Intersects(sl.geom_2975, par.g)
) b ON true
"""

_SQL_ACC_UPSERT = """
INSERT INTO vegetation_zonal_acc AS a (idu, zone, px_total, px_canopee, ndvi_sum)
SELECT e ->> 'idu', e ->> 'zone', (e ->> 'pt')::bigint, (e ->> 'pc')::bigint,
       (e ->> 'ns')::float
FROM jsonb_array_elements(CAST(:payload AS jsonb)) e
ON CONFLICT (idu, zone) DO UPDATE SET
  px_total = a.px_total + EXCLUDED.px_total,
  px_canopee = a.px_canopee + EXCLUDED.px_canopee,
  ndvi_sum = a.ndvi_sum + EXCLUDED.ndvi_sum
"""


def process_tiles(session: Session, *, limit: int | None = None, log=print) -> dict[str, Any]:
    """NDVI × MNH par tuile IRC acquise, accumulation zonale (checkpoint veg_traite_at)."""
    _ensure_schema(session)
    cfg = _cfg()
    seuils = cfg["seuils"]
    ndvi_min = float(seuils["ndvi_canopee"])
    h_min = float(seuils["hauteur_vegetation_haute_m"])
    bande = float(seuils["bande_limite_m"])
    buf = float(seuils["buffer_bati_m"])
    px = int(cfg["mnh"]["pixels"])   # grille commune 1 m/px
    rows = session.execute(text(
        "SELECT tile_id FROM ortho_tiles WHERE irc_acquise_at IS NOT NULL"
        " AND veg_traite_at IS NULL ORDER BY tile_id"
        + (" LIMIT :lim" if limit else "")), {"lim": limit} if limit else {}).scalars().all()
    n_tiles = n_parc = n_mnh_echec = 0
    t0 = time.monotonic()
    with httpx.Client(headers={"User-Agent": "labuse/vegetation-974"}) as client:
        for tid in rows:
            p = irc_tile_path(tid)
            img = cv2.imread(str(p)) if p.exists() else None
            if img is None:
                session.execute(text(
                    "UPDATE ortho_tiles SET irc_acquise_at = NULL WHERE tile_id = :t"),
                    {"t": tid})   # image manquante/corrompue → re-file d'acquisition
                continue
            mnh = _fetch_mnh(client, cfg["mnh"], tid)
            if mnh is None:
                n_mnh_echec += 1
                continue   # pas de checkpoint : la tuile restera en file (relance)
            pir = img[:, :, 2].astype(np.float32)
            red = img[:, :, 1].astype(np.float32)
            ndvi = (pir - red) / np.maximum(pir + red, 1.0)
            if ndvi.shape != (px, px):
                ndvi = cv2.resize(ndvi, (px, px), interpolation=cv2.INTER_AREA)
            if mnh.shape != (px, px):
                mnh = cv2.resize(mnh, (px, px), interpolation=cv2.INTER_NEAREST)
            canopee = (ndvi >= ndvi_min) & (mnh > h_min)
            xmin, ymin = (int(v) for v in tid.split("_"))
            payload: list[dict] = []
            for r in session.execute(text(_SQL_ZONES_TUILE),
                                     {"tid": tid, "bande": bande, "buf": buf}):
                for zone, gj_txt in (("parcelle", r.gj_parcelle), ("limite", r.gj_limite),
                                     ("bati8", r.gj_bati)):
                    m = _rasterize(json.loads(gj_txt) if gj_txt else None, xmin, ymin, px)
                    if m is None:
                        continue
                    pt = int(m.sum())
                    if not pt:
                        continue
                    mb = m.astype(bool)
                    payload.append({"idu": r.idu, "zone": zone, "pt": pt,
                                    "pc": int(canopee[mb].sum()),
                                    "ns": float(ndvi[mb].sum()) if zone == "parcelle" else 0.0})
                n_parc += 1
            if payload:
                session.execute(text(_SQL_ACC_UPSERT), {"payload": json.dumps(payload)})
            session.execute(text(
                "UPDATE ortho_tiles SET veg_traite_at = now() WHERE tile_id = :t"), {"t": tid})
            n_tiles += 1
            if n_tiles % 50 == 0:
                session.commit()   # checkpoint : relançable, seules les non-traitées restent
                log(f"  végétation {n_tiles}/{len(rows)} tuiles"
                    f" ({n_tiles / (time.monotonic() - t0):.2f} t/s)")
    session.commit()
    return {"tuiles": n_tiles, "parcelles_vues": n_parc, "mnh_echecs": n_mnh_echec}


def finalize(session: Session, log=print) -> dict[str, Any]:
    """vegetation_zonal_acc → parcel_vegetation (+ bâti voisin < 10 m de la limite)."""
    cfg = _cfg()
    n = session.execute(text("""
        INSERT INTO parcel_vegetation (idu, ndvi_moyen, canopee_pct, canopee_limite_pct,
                                       canopee_bati_pct, methode_hauteur, confiance, updated_at)
        SELECT a.idu,
               round((a.ndvi_sum / NULLIF(a.px_total, 0))::numeric, 3),
               round((100.0 * a.px_canopee / NULLIF(a.px_total, 0))::numeric, 1),
               round((100.0 * l.px_canopee / NULLIF(l.px_total, 0))::numeric, 1),
               round((100.0 * b.px_canopee / NULLIF(b.px_total, 0))::numeric, 1),
               'lidar', 'haute', now()
        FROM vegetation_zonal_acc a
        LEFT JOIN vegetation_zonal_acc l ON l.idu = a.idu AND l.zone = 'limite'
        LEFT JOIN vegetation_zonal_acc b ON b.idu = a.idu AND b.zone = 'bati8'
        JOIN parcels p ON p.idu = a.idu
        WHERE a.zone = 'parcelle' AND a.px_total > 0
        ON CONFLICT (idu) DO UPDATE SET
          ndvi_moyen = EXCLUDED.ndvi_moyen, canopee_pct = EXCLUDED.canopee_pct,
          canopee_limite_pct = EXCLUDED.canopee_limite_pct,
          canopee_bati_pct = EXCLUDED.canopee_bati_pct,
          methode_hauteur = EXCLUDED.methode_hauteur, confiance = EXCLUDED.confiance,
          updated_at = now()
    """)).rowcount
    session.commit()
    # bâti voisin < 10 m : uniquement pour les candidates élagage (bande limite végétalisée)
    seuil = float(cfg["seuils"]["vegetation_haute_limite_pct"])
    dist = float(cfg["seuils"]["bati_voisin_m"])
    n_vois = session.execute(text("""
        UPDATE parcel_vegetation v SET bati_voisin_10m = EXISTS (
          SELECT 1 FROM spatial_layers sl
          WHERE sl.kind = 'batiment'
            AND ST_DWithin(sl.geom_2975, p.geom_2975, :dist)
            AND NOT ST_Contains(p.geom_2975, ST_Centroid(sl.geom_2975))
        )
        FROM parcels p
        WHERE p.idu = v.idu AND v.canopee_limite_pct >= :seuil AND v.bati_voisin_10m IS NULL
    """), {"dist": dist, "seuil": seuil}).rowcount
    session.commit()
    log(f"  parcel_vegetation : {n} parcelles, bâti voisin calculé sur {n_vois} candidates")
    return {"parcelles": n, "bati_voisin_calcule": n_vois}


def signal_vegetation(session: Session) -> int:
    """Signal `vegetation_haute_limite` (lead élagueur) — canopée en limite > seuil."""
    seuil = float(_cfg()["seuils"]["vegetation_haute_limite_pct"])
    _ensure_schema(session)
    session.execute(text(
        "DELETE FROM parcel_signals WHERE signal_type = 'vegetation_haute_limite'"))
    n = session.execute(text("""
        INSERT INTO parcel_signals (parcel_id, signal_type, payload, detected_at)
        SELECT p.id, 'vegetation_haute_limite',
               jsonb_build_object(
                 'canopee_limite_pct', v.canopee_limite_pct,
                 'canopee_pct', v.canopee_pct,
                 'bati_voisin_10m', v.bati_voisin_10m,
                 'methode_hauteur', v.methode_hauteur, 'confiance', v.confiance,
                 'source', 'BD ORTHO IRC + LiDAR HD (MNH) © IGN'),
               now()
        FROM parcel_vegetation v
        JOIN parcels p ON p.idu = v.idu
        WHERE v.canopee_limite_pct > :seuil
    """), {"seuil": seuil}).rowcount
    session.commit()
    return n


def sanity_est_ouest(session: Session) -> dict[str, Any]:
    """Sanity physique : l'Est au vent (pluvieux) DOIT être plus vert que l'Ouest.
    Pondéré par PIXEL (surface), pas par parcelle : la moyenne par parcelle est dominée
    par les micro-parcelles urbaines, identiques des deux côtés, et noie le gradient
    (vécu 11/07 : 0,063 = 0,063 par parcelle ; 0,213 vs 0,157 par pixel)."""
    est = ["Saint-Benoît", "Bras-Panon", "Saint-André", "Sainte-Rose", "Saint-Philippe"]
    ouest = ["Le Port", "Saint-Paul", "La Possession", "Saint-Leu", "Les Trois-Bassins",
             "L'Étang-Salé"]
    m_est, m_ouest = session.execute(text("""
        SELECT
          (SELECT sum(a.ndvi_sum) / NULLIF(sum(a.px_total), 0)
           FROM vegetation_zonal_acc a JOIN parcels p ON p.idu = a.idu
           WHERE a.zone = 'parcelle' AND p.commune = ANY(:est)),
          (SELECT sum(a.ndvi_sum) / NULLIF(sum(a.px_total), 0)
           FROM vegetation_zonal_acc a JOIN parcels p ON p.idu = a.idu
           WHERE a.zone = 'parcelle' AND p.commune = ANY(:ouest))
    """), {"est": est, "ouest": ouest}).one()
    return {"ndvi_pondere_est": round(float(m_est or 0), 3),
            "ndvi_pondere_ouest": round(float(m_ouest or 0), 3),
            "ok": (m_est or 0) > (m_ouest or 0)}


def preparer_validation(session: Session, log=print) -> dict[str, Any]:
    """Session Vic : 20 vignettes « végétation haute en limite détectée » dans l'outil de
    validation ortho (type='vegetation'). Le contour affiché = la parcelle. Les tuiles RVB
    purgées nécessaires aux vignettes sont re-téléchargées (elles seules)."""
    quota = int(_cfg()["validation"]["quota"])
    seuil = float(_cfg()["seuils"]["vegetation_haute_limite_pct"])
    deja = session.execute(text(
        "SELECT count(*) FROM ortho_detections WHERE type = 'vegetation'")).scalar_one()
    if deja < quota:
        session.execute(text("""
            INSERT INTO ortho_detections (type, geom, geom_2975, surface_m2, confiance,
                                          criteres, idu, tile_id)
            SELECT 'vegetation', ST_Transform(g.geom, 4326), g.geom, p.surface_m2,
                   round((v.canopee_limite_pct / 100.0)::numeric, 3),
                   jsonb_build_object('canopee_limite_pct', v.canopee_limite_pct,
                                      'canopee_pct', v.canopee_pct,
                                      'ndvi_moyen', v.ndvi_moyen,
                                      'methode_hauteur', v.methode_hauteur),
                   p.idu, t.tile_id
            FROM parcel_vegetation v
            JOIN parcels p ON p.idu = v.idu
            CROSS JOIN LATERAL (
              SELECT ST_MakePolygon(ST_ExteriorRing(d.geom)) AS geom
              FROM ST_Dump(ST_CollectionExtract(ST_MakeValid(p.geom_2975), 3)) d
              ORDER BY ST_Area(d.geom) DESC LIMIT 1
            ) g
            JOIN LATERAL (
              SELECT ot.tile_id FROM ortho_tiles ot
              WHERE ST_Contains(ot.geom, ST_Centroid(p.geom_2975)) LIMIT 1
            ) t ON true
            WHERE v.canopee_limite_pct > :seuil
              AND coalesce(v.bati_voisin_10m, false)
              AND NOT EXISTS (SELECT 1 FROM ortho_detections d
                              WHERE d.type = 'vegetation' AND d.idu = p.idu)
            ORDER BY random() LIMIT :n
        """), {"seuil": seuil, "n": quota - deja})
        session.commit()
    tiles = session.execute(text(
        "SELECT DISTINCT tile_id FROM ortho_detections WHERE type = 'vegetation'"
        " AND validation IS NULL")).scalars().all()
    manquantes = [t for t in tiles if not rvb_tile_path(t).exists()]
    if manquantes:
        cfg_rvb = load_yaml_config("detection_ortho")["tuiles"]

        async def dl() -> list[str]:
            async with httpx.AsyncClient(headers={"User-Agent": "labuse/ortho-974"}) as client:
                res = await asyncio.gather(*(_fetch_tile(client, cfg_rvb, t) for t in manquantes))
            return [t for t, ok in zip(manquantes, res) if not ok]

        echecs = asyncio.run(dl())
        log(f"  tuiles RVB re-téléchargées pour les vignettes : "
            f"{len(manquantes) - len(echecs)}/{len(manquantes)}")
    n = session.execute(text(
        "SELECT count(*) FROM ortho_detections WHERE type = 'vegetation'")).scalar_one()
    return {"vignettes": n, "quota": quota,
            "url": "http://127.0.0.1:8000/ortho/validation?type=vegetation"
                   f"&profil=vegetation&quota={quota}"}
