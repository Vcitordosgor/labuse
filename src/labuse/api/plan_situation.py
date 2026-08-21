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
               zoom_delta: int = 0, extra_geojson: str | None = None,
               crop_margin_m: float | None = None, focus_points: list | None = None,
               target_aspect: float | None = None, min_px: int | None = None) -> dict:
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
                            zoom_delta=zoom_delta, extra_geojson=extra_geojson,
                            focus_points=focus_points)
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

    # M129-4 §3.1 : épaisseur du contour PROPORTIONNELLE à la taille image (sinon, à échelle
    # rapprochée, un trait fixe de 3 px agrandi 4× donne un « double trait » épais). ~0,5 mm au rendu.
    mint_w = max(2, round(w / 300))
    halo_w = mint_w + 2
    draw = ImageDraw.Draw(img)
    for pts in rings:                                    # halo sombre épais D'ABORD
        draw.line(pts + [pts[0]], fill=_HALO, width=halo_w, joint="curve")
    for pts in rings:                                    # trait mint net PAR-DESSUS
        draw.line(pts + [pts[0]], fill=_MINT, width=mint_w, joint="curve")

    lat = _lat_repr(geojson_str)
    zoom = int(m.get("zoom") or 0)
    metres_par_px = (156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)) if (lat and zoom) else None

    # M129-2 C : le pyramidal ortho plafonne à z18 (~0,56 m/px) → une petite parcelle occupe ~1/20 de
    # la vue. Pour un PLAN DE MASSE lisible, on RECADRE l'image sur l'emprise de la parcelle + une
    # marge courte (mètres) : la parcelle remplit alors la feuille, à une échelle du domaine plan de
    # masse. Le mètre/px (échelle graphique) est INCHANGÉ (même zoom, simple recadrage).
    focus_px = list(m.get("focus_px") or [])
    if crop_margin_m is not None and metres_par_px:
        # M129-3 §1.3 : le recadrage CONTIENT la parcelle ET tous les points d'intérêt (prises de vue)
        # + la marge — si un point sort, c'est le cadrage qui s'élargit, jamais le point qui déborde.
        allpx = [pt for r in rings for pt in r] + focus_px
        xs, ys = [x for x, _ in allpx], [y for _, y in allpx]
        mpx = crop_margin_m / metres_par_px
        cw = (max(xs) - min(xs)) + 2 * mpx        # emprise du contenu (parcelle + points + marge)
        ch = (max(ys) - min(ys)) + 2 * mpx
        # M129-4 §3.2 : caler le recadrage sur le FORMAT de la page (portrait) pour REMPLIR la feuille
        # au lieu d'une demi-page blanche — on agrandit l'axe déficient, jamais on ne rogne le contenu.
        if target_aspect:
            if cw / ch > target_aspect:
                ch = cw / target_aspect
            else:
                cw = ch * target_aspect
        # M129-4 §3.3 : plancher de résolution NATIVE — ne jamais sur-agrandir une petite emprise (ortho
        # plafonnée à z18). Si le recadrage est plus petit que min_px, on l'élargit (plus de contexte,
        # net) plutôt que de zoomer dans les pixels. On garde le format page.
        if min_px and cw < min_px:
            f = min_px / cw
            cw, ch = min_px, ch * f
        cw, ch = min(cw, w), min(ch, h)           # borné à l'image disponible
        if target_aspect:                          # ré-imposer le format après bornage éventuel
            if cw / ch > target_aspect:
                cw = ch * target_aspect
            else:
                ch = cw / target_aspect

        def _win(lo: float, hi: float, want: float, lim: int) -> tuple[int, int]:
            """Fenêtre de longueur `want` centrée sur [lo,hi], décalée pour rester dans [0,lim]."""
            c = (lo + hi) / 2
            a, b = c - want / 2, c + want / 2
            if a < 0:
                a, b = 0, want
            if b > lim:
                a, b = lim - want, lim
            return max(0, int(a)), min(lim, int(round(b)))

        l0, r0 = _win(min(xs), max(xs), cw, w)
        t0, b0 = _win(min(ys), max(ys), ch, h)
        if r0 - l0 >= 60 and b0 - t0 >= 60:
            img = img.crop((l0, t0, r0, b0))
            w, h = r0 - l0, b0 - t0
            rings = [[(x - l0, y - t0) for x, y in r] for r in rings]
            focus_px = [(x - l0, y - t0) for x, y in focus_px]

    # JPEG (photo aérienne) : ~10× plus léger que PNG pour le poids du PDF ; le contour mint survit à q78.
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=78, optimize=True)
    return {"ok": True, "jpeg": buf.getvalue(), "width": w, "height": h,
            "zoom": zoom, "metres_par_px": metres_par_px, "attribution": m.get("attribution"),
            "parcel_px": rings,          # contour parcelle en pixels de l'image RENDUE (recadrée si crop)
            "focus_px": focus_px}        # points de vue projetés dans le MÊME repère (recadré)
