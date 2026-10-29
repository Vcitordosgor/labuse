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

from ..flash.carte import (IGN_ORTHO_ATTRIBUTION, IGN_ORTHO_URL, VIEW_H, VIEW_W, ZOOM_MAX,
                           ZOOM_MIN, _lonlat_to_px, _rings, build_situation_map)

# Contour DA (mint) posé sur un halo sombre → net et sans ambiguïté sur une photo aérienne.
_MINT = (74, 222, 128)
_HALO = (10, 12, 11)

# ANNONCE-5 — la carte CADASTRALE (2ᵉ carte de la variante parcelle) : fond neutre, parcelles voisines
# (cadastre), zonage PLU en aplats, aléas en aplats sable, la parcelle en menthe. Teintes de la DA.
_FOND_CADASTRE = (247, 246, 243)        # fond neutre clair (≠ ortho sombre)
_ZONE_DOMINANTE = (122, 170, 130, 34)   # aplat zone PLU de la parcelle (menthe TRÈS clair, désaturé)
_ZONE_AUTRE = (203, 198, 188, 52)       # aplats des zones voisines (gris chaud)
_ZONE_TRAIT = (126, 146, 128, 150)      # liseré des limites de zone
_ALEA_FILL = (222, 178, 116, 120)       # aplat sable des aléas (PPR / Géorisques) — contrasté
_CADASTRE_TRAIT = (198, 196, 190)       # liseré des parcelles voisines (cadastre)
_SUJET_FILL = (74, 200, 120, 120)       # aplat de la parcelle sujet (menthe franc, ≠ aplat de zone)


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
               target_aspect: float | None = None, min_px: int | None = None,
               zoom_max: int | None = None) -> dict:
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
                            focus_points=focus_points, zoom_max=zoom_max)
    if m is None:
        return {"ok": False, "echec": "fond cartographique indisponible — service ortho ou réseau injoignable"}
    if not m.get("tiles"):
        return {"ok": False, "echec": "fond cartographique indisponible — aucune tuile ortho sur l'emprise"}

    w, h = int(m["width"]), int(m["height"])
    # DOCS-COHERENCE-1 (E5) — fond « sans imagerie » en GRIS CLAIR neutre (et non quasi-noir) : une tuile
    # absente (réseau) ou un pixel no-data (pleine mer, blanc pur masqué ci-dessous) se lisait comme un
    # CARRÉ NOIR, perçu comme un bug. Le gris clair se lit « pas de cliché ici » sans fausse alerte ;
    # l'ortho couvre la parcelle, ce fond n'apparaît qu'aux bords / trous.
    img = Image.new("RGB", (w, h), (233, 231, 227))
    for t in m["tiles"]:
        try:
            raw = base64.b64decode(t["data_uri"].split(",", 1)[1])
            tile = Image.open(io.BytesIO(raw)).convert("RGB")
            # RECETTE-OUTILS-3 (S6) — hors couverture (pleine mer au large), l'ortho IGN ne rend PAS un
            # 404 mais du BLANC PUR. R12 (mandat 2) ne masquait que les tuiles ENTIÈREMENT blanches ; or
            # sur la côte le blanc n'occupe qu'une PORTION de tuile (le reste = vrai cliché) → le « carré
            # blanc » revenait. On masque donc les PIXELS no-data (quasi blancs) et non la tuile entière :
            # le fond neutre sombre reste là où il n'y a pas de donnée, qu'il s'agisse d'une tuile ou d'un
            # coin. On teste la LUMINANCE (L) : le blanc no-data est achromatique (L≥250) ; un vrai
            # élément clair MAIS coloré (toit, écume) garde une luminance < 250 et n'est pas effacé.
            gris = tile.convert("L")
            if gris.getextrema()[1] >= 250:                 # du quasi-blanc présent dans la tuile
                masque = gris.point(lambda p: 0 if p >= 250 else 255)   # 0 = no-data (transparent)
                img.paste(tile, (int(t["left"]), int(t["top"])), masque)
            else:
                img.paste(tile, (int(t["left"]), int(t["top"])))
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


# ═══════════════════════════ ANNONCE-5 — la carte CADASTRALE (zonage + aléas) ═══════════════════════
def _rings_lonlat(gj_str: str | None) -> list[list[tuple[float, float]]]:
    """Anneaux (lon, lat) d'un GeoJSON (Polygon/MultiPolygon/GeometryCollection), ou []."""
    if not gj_str:
        return []
    try:
        return _rings(json.loads(gj_str))
    except Exception:  # noqa: BLE001
        return []


def _zoom_pour(bbox: tuple[float, float, float, float], zoom_delta: int) -> int:
    """Zoom le plus serré où la parcelle tient dans ~55 % de la vue (même logique que build_situation_map,
    mais sans tuiles : on peut monter à z20 pour un cadastre net)."""
    zmax = ZOOM_MAX + 2
    zoom = ZOOM_MIN
    for z in range(zmax, ZOOM_MIN - 1, -1):
        x0, y1 = _lonlat_to_px(bbox[0], bbox[1], z)
        x1, y0 = _lonlat_to_px(bbox[2], bbox[3], z)
        if (x1 - x0) <= VIEW_W * 0.55 and (y1 - y0) <= VIEW_H * 0.55:
            zoom = z
            break
    return max(ZOOM_MIN, min(zmax, zoom + zoom_delta))


def plan_zonage(subject_gj: str | None, *, neighbors: list[str] | None = None,
                zones: list[dict] | None = None, aleas: list[str] | None = None,
                crop_margin_m: float = 16.0, target_aspect: float | None = 3.6,
                min_px: int | None = 900, zoom_delta: int = 0) -> dict:
    """La 2ᵉ carte de la variante parcelle : fond NEUTRE + parcelles VOISINES (cadastre) + zonage PLU en
    APLATS + aléas en APLATS sable + la parcelle sujet en menthe. 100 % vectorielle depuis la base
    (aucune tuile réseau) → déterministe, hors-ligne, reproductible en test. Renvoie TOUJOURS un dict :
    succès {ok:True, jpeg, width, height, parcel_px, metres_par_px} ; échec {ok:False, echec:"…"}.
    `zones` = [{"gj": <geojson>, "dominant": bool}] ; `aleas` = [<geojson>, …] (déjà filtrés sur l'emprise)."""
    subj = _rings_lonlat(subject_gj)
    if not subj:
        return {"ok": False, "echec": "parcelle sans géométrie — contour non projetable"}
    lons = [c[0] for r in subj for c in r]
    lats = [c[1] for r in subj for c in r]
    bbox = (min(lons), min(lats), max(lons), max(lats))
    zoom = _zoom_pour(bbox, zoom_delta)
    cx, cy = _lonlat_to_px((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2, zoom)
    left, top = cx - VIEW_W / 2, cy - VIEW_H / 2

    def proj(rings):
        out = []
        for ring in rings:
            out.append([(_lonlat_to_px(lon, lat, zoom)[0] - left,
                         _lonlat_to_px(lon, lat, zoom)[1] - top) for lon, lat in ring])
        return out

    w, h = VIEW_W, VIEW_H
    base = Image.new("RGB", (w, h), _FOND_CADASTRE)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    # 1) aplats des zones PLU (dominante = la zone de la parcelle, en menthe ; les autres en gris chaud).
    for z in (zones or []):
        for pts in proj(_rings_lonlat(z.get("gj"))):
            if len(pts) >= 3:
                od.polygon(pts, fill=(_ZONE_DOMINANTE if z.get("dominant") else _ZONE_AUTRE),
                           outline=_ZONE_TRAIT)
    # 2) aplats sable des aléas (PPR / Géorisques) — au-dessus des zones, sous le cadastre.
    for gj in (aleas or []):
        for pts in proj(_rings_lonlat(gj)):
            if len(pts) >= 3:
                od.polygon(pts, fill=_ALEA_FILL)
    # 3) liseré des parcelles voisines (le cadastre) — fin, par-dessus les aplats.
    for gj in (neighbors or []):
        for pts in proj(_rings_lonlat(gj)):
            if len(pts) >= 2:
                od.line(pts + [pts[0]], fill=_CADASTRE_TRAIT, width=1, joint="curve")
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    # 4) la parcelle sujet : aplat menthe + halo sombre + trait menthe (même DA que l'ortho).
    rings = proj(subj)
    sub_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sod = ImageDraw.Draw(sub_overlay)
    for pts in rings:
        if len(pts) >= 3:
            sod.polygon(pts, fill=_SUJET_FILL)
    base = Image.alpha_composite(base.convert("RGBA"), sub_overlay).convert("RGB")
    mint_w = max(2, round(w / 300))
    draw = ImageDraw.Draw(base)
    for pts in rings:
        draw.line(pts + [pts[0]], fill=_HALO, width=mint_w + 2, joint="curve")
    for pts in rings:
        draw.line(pts + [pts[0]], fill=_MINT, width=mint_w, joint="curve")

    lat = sum(lats) / len(lats)
    metres_par_px = 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)
    # recadrage identique au plan ortho : parcelle + marge, au format de la boîte, plancher de résolution.
    allpx = [pt for r in rings for pt in r]
    xs, ys = [x for x, _ in allpx], [y for _, y in allpx]
    mpx = crop_margin_m / metres_par_px
    cw = (max(xs) - min(xs)) + 2 * mpx
    ch = (max(ys) - min(ys)) + 2 * mpx
    if target_aspect:
        if cw / ch > target_aspect:
            ch = cw / target_aspect
        else:
            cw = ch * target_aspect
    if min_px and cw < min_px:
        f = min_px / cw
        cw, ch = min_px, ch * f
    cw, ch = min(cw, w), min(ch, h)
    if target_aspect:
        if cw / ch > target_aspect:
            cw = ch * target_aspect
        else:
            ch = cw / target_aspect

    def _win(lo, hi, want, lim):
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
        base = base.crop((l0, t0, r0, b0))
        w, h = r0 - l0, b0 - t0
        rings = [[(x - l0, y - t0) for x, y in r] for r in rings]

    buf = io.BytesIO()
    base.save(buf, format="JPEG", quality=82, optimize=True)
    return {"ok": True, "jpeg": buf.getvalue(), "width": w, "height": h, "zoom": zoom,
            "metres_par_px": metres_par_px, "attribution": "© DGFiP (cadastre), commune (PLU), Géorisques",
            "parcel_px": rings, "focus_px": []}
