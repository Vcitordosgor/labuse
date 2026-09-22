"""Plan 2D du gabarit — SVG serveur (GABARIT-5).

Miroir EXACT du mini-plan React (`GabaritLine.tsx`) : mêmes géométries servies, mêmes couleurs,
même projection (lon/lat schématique, aucune carte, aucun recalcul). Rendu ici en Python pour que
le Dossier / Flash / Pré-dossier PC impriment le MÊME plan que l'écran (WeasyPrint rend le SVG
inline). C'est un schéma des géométries réglementaires, pas un plan de masse.
"""
from __future__ import annotations

from typing import Any, Iterator, Optional

C_ZONE = "#36c99a"       # zone d'implantation
C_RETRAIT = "#e0a44a"    # bandes de retrait
C_EXCL = "#e8491d"       # exclusions (PPR rouge)
C_CONTOUR = "#9aa0a6"    # contour cadastral


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

    PAD = 8
    LEG = 54  # bandeau de légende sous le dessin
    W, H = width, height
    plot_h = H - LEG
    minx = miny = 1e18
    maxx = maxy = -1e18
    for geom in (contour, zone, retrait, excl):
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
    if contour:
        parts.append(f'<path d="{path(contour)}" fill="none" stroke="{C_CONTOUR}" '
                     f'stroke-width="1" stroke-dasharray="4 2"/>')
    # légende
    y0 = plot_h + 12
    leg = [(C_ZONE, "Zone d'implantation"), (C_RETRAIT, "Retraits"),
           (C_EXCL, "Exclusion (PPR rouge)"), (C_CONTOUR, "Contour cadastral")]
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
