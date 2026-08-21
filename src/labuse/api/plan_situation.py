"""M73-F — le PLAN DE SITUATION du premium (fpdf).

`build_situation_map` (flash/carte.py) produit des tuiles base64 pour WeasyPrint (HTML). Le premium est
en fpdf : on COMPOSITE ces tuiles en une image raster unique, on y projette le contour NET de la
parcelle, et on renvoie un PNG pour `pdf.image()`. Point d'appel UNIQUE : on réutilise
`build_situation_map` (jamais réécrit, jamais un fournisseur de tuiles appelé en direct) — comme DVF
passe par `marche_service`.

Un échec ne casse jamais le document : `plan_ortho` renvoie TOUJOURS un dict ; en cas d'échec, `ok=False`
et `echec` porte la RAISON explicite (réseau ≠ hors emprise), jamais un cadre vide.
"""
from __future__ import annotations

import base64
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from ..flash.carte import IGN_ORTHO_ATTRIBUTION, IGN_ORTHO_URL, build_situation_map

# Contour DA (mint) posé sur un halo sombre → net et sans ambiguïté sur une photo aérienne.
_MINT = (74, 222, 128)
_HALO = (10, 12, 11)


def _lat_repr(geojson_str: str) -> float | None:
    """Latitude représentative (moyenne des sommets) — pour l'échelle (mètres/pixel Web Mercator)."""
    try:
        g = json.loads(geojson_str)
        coords = g.get("coordinates") or []
        lats: list[float] = []

        def _walk(o):
            if (isinstance(o, list) and len(o) == 2 and all(isinstance(v, (int, float)) for v in o)):
                lats.append(float(o[1]))
            elif isinstance(o, list):
                for x in o:
                    _walk(x)
        _walk(coords)
        return sum(lats) / len(lats) if lats else None
    except Exception:  # noqa: BLE001
        return None


def plan_ortho(geojson_str: str | None, cache_dir: Path, *, timeout_s: float = 10.0,
               zoom_delta: int = 0, extra_geojson: str | None = None) -> dict:
    """Composite l'ortho + contour → PNG. Renvoie toujours un dict :
    - succès : {ok:True, jpeg, width, height, zoom, metres_par_px, attribution}
    - échec  : {ok:False, echec:"<raison explicite>"} (jamais un cadre vide, jamais masqué).

    `zoom_delta` (M129) : vue plus large (< 0) ou serrée (> 0) — deux vues PCMI1. `extra_geojson`
    (M129) : bâti existant, dessiné en aplat gris (plan de masse coté PCMI2)."""
    if not geojson_str:
        return {"ok": False, "echec": "parcelle sans géométrie — contour non projetable"}
    m = build_situation_map(geojson_str, cache_dir=cache_dir, timeout_s=timeout_s,
                            tile_url=IGN_ORTHO_URL, tile_mime="image/jpeg",
                            cache_prefix="ortho", attribution=IGN_ORTHO_ATTRIBUTION,
                            zoom_delta=zoom_delta, extra_geojson=extra_geojson)
    if m is None:
        return {"ok": False, "echec": "fond cartographique indisponible — service ortho ou réseau injoignable"}
    if not m.get("tiles"):
        return {"ok": False, "echec": "fond cartographique indisponible — aucune tuile ortho sur l'emprise"}

    w, h = int(m["width"]), int(m["height"])
    img = Image.new("RGB", (w, h), (28, 32, 30))
    for t in m["tiles"]:
        try:
            raw = base64.b64decode(t["data_uri"].split(",", 1)[1])
            img.paste(Image.open(io.BytesIO(raw)).convert("RGB"), (int(t["left"]), int(t["top"])))
        except Exception:  # noqa: BLE001 — une tuile absente ne casse pas la mosaïque
            continue

    rings: list[list[tuple[float, float]]] = []
    for poly in (m.get("polygons") or []):
        pts = []
        for tok in poly.split():
            xs, ys = tok.split(",")
            pts.append((float(xs), float(ys)))
        if len(pts) >= 2:
            rings.append(pts)
    if not rings:
        return {"ok": False, "echec": "parcelle hors emprise de la vue ortho — contour non projetable"}

    # bâti existant (M129 PCMI2) : aplat gris semi-opaque + liseré sombre, SOUS le contour parcelle.
    extra_rings: list[list[tuple[float, float]]] = []
    for poly in (m.get("extra_polygons") or []):
        pts = [(float(t.split(",")[0]), float(t.split(",")[1])) for t in poly.split() if "," in t]
        if len(pts) >= 3:
            extra_rings.append(pts)
    if extra_rings:
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for pts in extra_rings:
            od.polygon(pts, fill=(60, 66, 62, 130), outline=(20, 24, 22, 255))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    for pts in rings:                                    # halo sombre épais D'ABORD
        draw.line(pts + [pts[0]], fill=_HALO, width=6, joint="curve")
    for pts in rings:                                    # trait mint net PAR-DESSUS
        draw.line(pts + [pts[0]], fill=_MINT, width=3, joint="curve")

    lat = _lat_repr(geojson_str)
    zoom = int(m.get("zoom") or 0)
    metres_par_px = (156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)) if (lat and zoom) else None

    # JPEG (photo aérienne) : ~10× plus léger que PNG pour le poids du PDF ; le contour mint survit à q78.
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=78, optimize=True)
    return {"ok": True, "jpeg": buf.getvalue(), "width": w, "height": h,
            "zoom": zoom, "metres_par_px": metres_par_px, "attribution": m.get("attribution"),
            "parcel_px": [[(float(t.split(",")[0]), float(t.split(",")[1]))
                           for t in poly.split() if "," in t] for poly in (m.get("polygons") or [])]}
