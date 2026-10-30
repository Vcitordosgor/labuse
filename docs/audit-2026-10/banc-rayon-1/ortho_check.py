#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RADAR-SOURCES-3 (Lot B) — VÉRIFICATION ORTHO des auto-rattachements Bien'ici.

Pour chaque parcelle auto-rattachée (AUTO_RATTACHES.json), on compose une image : orthophoto IGN
(Géoplateforme, imagerie publique de La Réunion) + le CONTOUR de la parcelle rattachée (cyan) + le
POINT flouté de l'annonce (rouge) + le DISQUE de floutage ~50 m (jaune). On lit ensuite l'image à l'œil :
la parcelle porte-t-elle bien un bâti de maison cohérent avec l'annonce (emprise + terrain), et le point
flouté tombe-t-il sur/à côté d'elle ? Un seul faux → on le dit et on durcit la règle.

Lecture seule base `labuse`. Images écrites dans ortho/. L'IGN ne reçoit que des bbox publiques.
Lancer : LABUSE_DATABASE_URL=postgresql+psycopg:///labuse PYTHONPATH=src \
         ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/banc-rayon-1/ortho_check.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import requests
import sqlalchemy as sa
from PIL import Image, ImageDraw
from io import BytesIO

ICI = Path(__file__).resolve().parent
OUT = ICI / "ortho"
OUT.mkdir(exist_ok=True)
ENGINE = sa.create_engine("postgresql+psycopg:///labuse")
WMS = "https://data.geopf.fr/wms-r/wms"
LAYER = "HR.ORTHOIMAGERY.ORTHOPHOTOS"
W = H = 640
DEMI_M = 70.0    # demi-fenêtre en mètres autour du centroïde parcelle (zoom serré pour la lecture)


def _bbox(lon, lat):
    dlat = DEMI_M / 111000.0
    dlon = DEMI_M / (111000.0 * math.cos(math.radians(lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat  # minx,miny,maxx,maxy


def _ortho(minx, miny, maxx, maxy):
    # WMS 1.3.0 + EPSG:4326 → axe lat,lon → BBOX = miny,minx,maxy,maxx
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": LAYER,
        "STYLES": "", "CRS": "EPSG:4326", "BBOX": f"{miny},{minx},{maxy},{maxx}",
        "WIDTH": W, "HEIGHT": H, "FORMAT": "image/png",
    }
    r = requests.get(WMS, params=params, timeout=60)
    r.raise_for_status()
    return Image.open(BytesIO(r.content)).convert("RGB")


def _px(lon, lat, bb):
    minx, miny, maxx, maxy = bb
    x = (lon - minx) / (maxx - minx) * W
    y = (maxy - lat) / (maxy - miny) * H
    return x, y


def main():
    autos = json.loads((ICI / "AUTO_RATTACHES.json").read_text())
    # dédoublonner par idu (CM0143 apparaît 2×)
    vus = {}
    for a in autos:
        vus.setdefault(a["idu"], a)
    print(f"{len(autos)} auto-rattachements · {len(vus)} parcelles distinctes à vérifier")

    index = []
    with ENGINE.connect() as c:
        for i, (idu, a) in enumerate(sorted(vus.items()), 1):
            row = c.execute(sa.text(
                "SELECT ST_AsGeoJSON(ST_Transform(p.geom,4326)) gj, "
                "       ST_X(ST_Transform(p.centroid,4326)) lon, ST_Y(ST_Transform(p.centroid,4326)) lat, "
                "       p.surface_m2, COALESCE(mb.emprise_bati_m2,0) emprise "
                "FROM parcels p LEFT JOIN p_model_bati mb ON mb.idu=p.idu WHERE p.idu=:i"),
                {"i": idu}).mappings().first()
            if not row:
                print(f"  [{i}] {idu} : parcelle absente ?!")
                continue
            lon, lat = float(row["lon"]), float(row["lat"])
            bb = _bbox(lon, lat)
            img = _ortho(*bb)
            dr = ImageDraw.Draw(img, "RGBA")
            # contour parcelle
            gj = json.loads(row["gj"])
            rings = gj["coordinates"] if gj["type"] == "Polygon" else [r for poly in gj["coordinates"] for r in poly]
            for ring in rings:
                pts = [_px(x, y, bb) for x, y in ring]
                dr.line(pts + [pts[0]], fill=(255, 0, 255, 255), width=4)   # contour parcelle = magenta épais
            # point annonce + disque floutage 50 m
            if a.get("lng") is not None and a.get("lat") is not None:
                ax, ay = _px(a["lng"], a["lat"], bb)
                rpx = 50.0 / (2 * DEMI_M) * W
                dr.ellipse([ax - rpx, ay - rpx, ax + rpx, ay + rpx], outline=(255, 230, 0, 255), width=2)
                dr.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=(255, 0, 0, 255))
            # distance point→centroïde parcelle
            d_m = None
            if a.get("lng") is not None:
                d_m = round(math.hypot((a["lng"] - lon) * 111000 * math.cos(math.radians(lat)),
                                       (a["lat"] - lat) * 111000))
            path = OUT / f"{i:02d}_{idu}.png"
            img.save(path)
            print(f"  [{i:02d}] {a['commune']:<13} {a['type']} hab={a['surface_hab']} terr={a['surface_terrain']} "
                  f"| parcelle surf={row['surface_m2']:.0f} emprise={row['emprise']:.0f} "
                  f"| point→centroïde {d_m} m | {path.name}")
            index.append({"n": i, "idu": idu, "img": path.name, "commune": a["commune"],
                          "hab": a["surface_hab"], "terr": a["surface_terrain"],
                          "parcelle_surface": float(row["surface_m2"]), "emprise": float(row["emprise"]),
                          "point_to_centroid_m": d_m, "subject": a.get("subject")})
    (ICI / "ortho_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"\nécrit : {OUT}/  et  {ICI/'ortho_index.json'}")


if __name__ == "__main__":
    main()
