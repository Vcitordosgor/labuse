"""Plan 2D du gabarit — SVG serveur (GABARIT-5).

Miroir EXACT du mini-plan React (`GabaritLine.tsx`) : mêmes géométries servies, mêmes couleurs,
même projection (lon/lat schématique, aucune carte, aucun recalcul). Rendu ici en Python pour que
le Dossier / Flash / Pré-dossier PC impriment le MÊME plan que l'écran (WeasyPrint rend le SVG
inline). C'est un schéma des géométries réglementaires, pas un plan de masse.
"""
from __future__ import annotations

import math
from typing import Any, Iterator, Optional

C_ZONE = "#36c99a"       # zone d'implantation
C_RETRAIT = "#e0a44a"    # bandes de retrait
C_EXCL = "#e8491d"       # exclusions (PPR rouge)
C_CONTOUR = "#9aa0a6"    # contour cadastral
C_BATI = "#7c828a"       # EXPORTS-FIX-1 F5 — bâti existant (GABARIT-6, comme l'outil Gabarit.tsx)


def _rings(geom: Optional[dict]) -> Iterator[list]:
    if not geom:
        return
    co = geom.get("coordinates")
    t = geom.get("type")
    if t == "Polygon":
        for r in co or []:
            yield r
    elif t == "MultiPolygon":
        for poly in co or []:
            for r in poly:
                yield r


def gabarit_svg(result: Any, *, width: int = 340, height: int = 250) -> Optional[str]:
    """Construit le SVG (chaîne) depuis un GabaritResult servi (status ok). None si rien à tracer.
    `result` peut être un GabaritResult (attributs) ou un dict équivalent."""
    def g(name):
        return getattr(result, name, None) if not isinstance(result, dict) else result.get(name)

    contour = g("contourGeoJSON")
    zone = g("zoneImplantationGeoJSON")
    retrait = g("retraitsGeoJSON")
    excl = g("exclusionsGeoJSON")
    bati = g("batiExistantGeoJSON")   # EXPORTS-FIX-1 F5 — bâti existant (fait contextuel, GABARIT-6 P4)

    PAD = 8
    LEG = 54  # bandeau de légende sous le dessin
    W, H = width, height
    plot_h = H - LEG
    minx = miny = 1e18
    maxx = maxy = -1e18
    for geom in (contour, zone, retrait, excl, bati):
        for r in _rings(geom):
            for pt in r:
                x, y = pt[0], pt[1]
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    if minx > maxx:
        return None
    sx = (W - 2 * PAD) / max(maxx - minx, 1e-9)
    sy = (plot_h - 2 * PAD) / max(maxy - miny, 1e-9)
    s = min(sx, sy)
    # centrage horizontal
    off_x = (W - (maxx - minx) * s) / 2.0

    def px(x): return off_x + (x - minx) * s
    def py(y): return plot_h - PAD - (y - miny) * s   # flip : latitude vers le haut

    def path(geom):
        d = ""
        for r in _rings(geom):
            if not r:
                continue
            d += "M" + "L".join(f"{px(x):.1f},{py(y):.1f}" for x, y in ((p[0], p[1]) for p in r)) + "Z"
        return d

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             f'role="img" aria-label="Plan de la zone d\'implantation réglementaire" '
             f'style="border:1px solid #d5d7db;background:#fafbfc">']
    if retrait:
        parts.append(f'<path d="{path(retrait)}" fill="{C_RETRAIT}" fill-opacity="0.30" stroke="none"/>')
    if excl:
        parts.append(f'<path d="{path(excl)}" fill="{C_EXCL}" fill-opacity="0.45" stroke="none"/>')
    if zone:
        parts.append(f'<path d="{path(zone)}" fill="{C_ZONE}" fill-opacity="0.55" '
                     f'stroke="{C_ZONE}" stroke-width="0.8"/>')
    # EXPORTS-FIX-1 F5 — bâti EXISTANT (emprise BD TOPO), aplat gris comme dans l'outil : le schéma
    # montre ce qui est déjà là (côté « rue » lisible via le bâti et le contour), pas une parcelle nue.
    if bati:
        parts.append(f'<path d="{path(bati)}" fill="{C_BATI}" fill-opacity="0.38" '
                     f'stroke="{C_BATI}" stroke-width="0.6"/>')
    if contour:
        parts.append(f'<path d="{path(contour)}" fill="none" stroke="{C_CONTOUR}" '
                     f'stroke-width="1" stroke-dasharray="4 2"/>')
    # légende — EXPORTS-FIX-1 F5 : uniquement les éléments PRÉSENTS (plus de « PPR rouge » sur une
    # parcelle qui n'a aucune exclusion).
    y0 = plot_h + 12
    leg = [(c, l) for c, l, present in (
        (C_ZONE, "Zone d'implantation", zone), (C_RETRAIT, "Retraits", retrait),
        (C_BATI, "Bâti existant", bati), (C_EXCL, "Exclusion réglementaire (PPR rouge / SUP)", excl),
        (C_CONTOUR, "Contour cadastral", contour)) if present]
    parts.append(f'<text x="{PAD}" y="{plot_h + 2}" font-size="8" fill="#6b7075">'
                 f'Zone d\'implantation réglementaire (schéma — pas un plan de masse)</text>')
    for i, (col, lab) in enumerate(leg):
        cx = PAD + (i % 2) * (W / 2)
        cy = y0 + (i // 2) * 15
        parts.append(f'<rect x="{cx}" y="{cy}" width="9" height="9" fill="{col}" '
                     f'fill-opacity="0.6" stroke="{col}" stroke-width="0.6"/>')
        parts.append(f'<text x="{cx + 13}" y="{cy + 8}" font-size="8" fill="#33383d">{lab}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── RECETTE-OUTILS-2 (R16) — vue 3D du gabarit pour le PDF ───────────────────────────────────────
# L'outil montre la 3D en WebGL (non reproductible côté serveur). Le PDF a donc SA vue 3D : une
# projection axonométrique (isométrique) des MÊMES géométries servies — l'enveloppe réglementaire
# extrudée à la hauteur sourcée + le bâti existant extrudé à ses hauteurs mesurées, sur un sol PLAT.
# Aucun calcul : on lit `hauteurReglementaireM` et `properties.hauteur_m`, comme l'écran. Centrée sur
# la parcelle, angle par défaut. Légende « Volume indicatif — terrain supposé plat » (R16).
_ISO = math.radians(30.0)
_COS, _SIN = math.cos(_ISO), math.sin(_ISO)


def _bati_features(fc) -> list[tuple[dict, float]]:
    """(geometry, hauteur_m) par bâtiment ; hauteur manquante → 3 m (comme l'extrusion de l'outil)."""
    out: list[tuple[dict, float]] = []
    for f in (fc or {}).get("features", []) if isinstance(fc, dict) else []:
        geom = f.get("geometry")
        if not geom:
            continue
        h = (f.get("properties") or {}).get("hauteur_m")
        out.append((geom, float(h) if isinstance(h, (int, float)) and h > 0 else 3.0))
    return out


def gabarit_svg_3d(result: Any, *, width: int = 560, height: int = 380) -> Optional[str]:
    """Vue 3D (axonométrie) du gabarit — None si l'on n'a pas de volume à montrer (hauteur absente)."""
    def g(name):
        return getattr(result, name, None) if not isinstance(result, dict) else result.get(name)

    contour = g("contourGeoJSON")
    zone = g("zoneImplantationGeoJSON")
    haut = g("hauteurReglementaireM")
    batis = _bati_features(g("batiExistantGeoJSON"))
    if not zone or not isinstance(haut, (int, float)) or haut <= 0:
        return None   # pas de hauteur sourcée → pas de volume (l'outil dit « 3D indisponible »)

    # repère local en MÈTRES, centré sur la parcelle (pour que les hauteurs soient à l'échelle du plan)
    pts = [(p[0], p[1]) for geom in (contour, zone) for r in _rings(geom) for p in r]
    lon0 = sum(p[0] for p in pts) / len(pts)
    lat0 = sum(p[1] for p in pts) / len(pts)
    m_lon = 111320.0 * math.cos(math.radians(lat0))
    m_lat = 110540.0

    def iso(lon, lat, z):
        mx = (lon - lon0) * m_lon
        my = (lat - lat0) * m_lat
        return ((mx - my) * _COS, (mx + my) * _SIN - z)   # z vers le haut (py décroît)

    def depth(lon, lat):   # plus grand = plus proche (devant) → peint en dernier
        return (lon - lon0) * m_lon + (lat - lat0) * m_lat

    # bornes projetées (sol + sommets) pour caler l'échelle
    LEG = 54
    plot_h = height - LEG
    proj_pts = []
    for r in _rings(contour) or []:
        for p in r:
            proj_pts.append(iso(p[0], p[1], 0))
    for r in _rings(zone):
        for p in r:
            proj_pts += [iso(p[0], p[1], 0), iso(p[0], p[1], haut)]
    for geom, h in batis:
        for r in _rings(geom):
            for p in r:
                proj_pts += [iso(p[0], p[1], 0), iso(p[0], p[1], h)]
    xs = [q[0] for q in proj_pts]
    ys = [q[1] for q in proj_pts]
    if not xs:
        return None
    PAD = 14
    s = min((width - 2 * PAD) / max(max(xs) - min(xs), 1e-9),
            (plot_h - 2 * PAD) / max(max(ys) - min(ys), 1e-9))
    ox = (width - (max(xs) - min(xs)) * s) / 2.0 - min(xs) * s
    oy = PAD - min(ys) * s

    def P(lon, lat, z):
        qx, qy = iso(lon, lat, z)
        return (ox + qx * s, oy + qy * s)

    def poly(ptsxy, fill, op, stroke, sw):
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in ptsxy)
        return f'<polygon points="{d}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"/>'

    def extrude(geom, h, top_fill, wall_fill, stroke):
        """Prisme : murs (triés arrière→avant) + toit. Renvoie (frags, depth représentatif)."""
        frags = []
        reps = []
        for r in _rings(geom):
            ring = [(p[0], p[1]) for p in r]
            if len(ring) < 3:
                continue
            reps.append(sum(depth(x, y) for x, y in ring) / len(ring))
            walls = []
            for i in range(len(ring) - 1):
                a, b = ring[i], ring[i + 1]
                quad = [P(a[0], a[1], 0), P(b[0], b[1], 0), P(b[0], b[1], h), P(a[0], a[1], h)]
                walls.append(((depth(a[0], a[1]) + depth(b[0], b[1])) / 2.0, quad))
            for _, quad in sorted(walls, key=lambda w: w[0]):   # arrière (petit) d'abord
                frags.append(poly(quad, wall_fill, "0.92", stroke, "0.5"))
            top = [P(x, y, h) for x, y in ring]
            frags.append(poly(top, top_fill, "0.85", stroke, "0.8"))
        return "".join(frags), (max(reps) if reps else 0.0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'width="{width}" height="{height}" role="img" aria-label="Vue 3D indicative du gabarit" '
             f'style="border:1px solid #d5d7db;background:#fafbfc">']
    # sol : contour cadastral à plat (repère)
    if contour:
        for r in _rings(contour):
            ground = [P(p[0], p[1], 0) for p in r]
            parts.append(poly(ground, "#eef0f2", "0.6", C_CONTOUR, "1"))
    # volumes peints de l'arrière vers l'avant (bâti gris + enveloppe verte mêlés → occlusion correcte)
    vols = []
    for geom, h in batis:
        vols.append(extrude(geom, h, "#9298a0", "#7c828a", "#5c6066"))
    vols.append(extrude(zone, float(haut), C_ZONE, "#2c9f7c", "#1f6f57"))
    for frag, d in sorted(vols, key=lambda v: v[1]):
        parts.append(frag)
    # légende R16
    parts.append(f'<text x="{PAD}" y="{plot_h + 14}" font-size="9" fill="#33383d" font-weight="600">'
                 f'Volume indicatif — terrain supposé plat</text>')
    leg = [(C_ZONE, f"Enveloppe réglementaire (hauteur {haut:g} m)")]
    if batis:
        leg.append(("#7c828a", "Bâti existant"))
    for i, (col, lab) in enumerate(leg):
        cy = plot_h + 24 + i * 13
        parts.append(f'<rect x="{PAD}" y="{cy}" width="9" height="9" fill="{col}" fill-opacity="0.85"/>')
        parts.append(f'<text x="{PAD + 13}" y="{cy + 8}" font-size="8" fill="#33383d">{lab}</text>')
    parts.append("</svg>")
    return "".join(parts)
