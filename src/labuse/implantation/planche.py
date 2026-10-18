"""PLANCHE PLAN MASSE « façon archi » — UN SEUL SVG, le même à l'écran (feuille blanche dans l'app
sombre) et dans le PDF, GÉNÉRÉ depuis la géométrie du scénario (jamais redessiné à la main).

Projection : géométrie MONDE EPSG:2975 (mètres, nord ≈ en haut) → SVG, Y inversé. Cadré sur l'assiette
+ une marge ; le contexte (voisins, bâti, voies) est détouré au cadre de dessin. Codes archi : fond
blanc, traits noirs, bâtiment rose, zone d'implantation en pointillé vert, allée/accès gris, places
blanches NUMÉROTÉES (le nombre dessiné = le nombre affiché), pleine terre verte, PPR hachurée.

Les couches activables de l'écran montrent/masquent des GROUPES `<g id="g-…">` de CE MÊME SVG
(aucun second dessin) : g-batiment, g-modules, g-places, g-allee, g-cotes, g-voisins, g-ppr.
"""
from __future__ import annotations

import hashlib
import html
import math
import re
from typing import Optional

from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from .contexte import Contexte
from .format import dec_fr, groupe_fr, m2_fr

# ── feuille ───────────────────────────────────────────────────────────────────────────────────
W, H = 1180.0, 780.0
# aire de dessin (plan) : marge gauche, colonne de droite réservée (légende / tableau / cartouche).
PX0, PY0, PX1, PY1 = 40.0, 44.0, 852.0, 704.0
COL_X = 872.0                 # colonne de droite (x de départ)

_ESC = lambda s: html.escape(str(s), quote=True)   # noqa: E731


def numero_etude(idus: list[str], genere_le: str) -> str:
    """N° de document DÉTERMINISTE : EF-AAAAMMJJ-XXXX (XXXX stable par assiette → rejeu à l'identique).
    Source UNIQUE, partagée par la planche (cartouche) et le PDF (cartouche + crible de provenance)."""
    d = re.sub(r"\D", "", genere_le)[:8] or "00000000"
    h = hashlib.md5((",".join(sorted(idus))).encode()).hexdigest()
    return f"EF-{d}-{int(h[:4], 16) % 10000:04d}"


def _rings(geom: BaseGeometry):
    """Anneaux extérieurs (liste de [(x,y)…]) d'un Polygon/MultiPolygon monde 2975."""
    if geom is None or geom.is_empty:
        return []
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    out = []
    for p in polys:
        if isinstance(p, Polygon) and not p.is_empty:
            out.append(list(p.exterior.coords))
    return out


class _Vue:
    """Projection 2975 → SVG, cadrée sur l'assiette + marge, Y inversé (nord en haut)."""

    def __init__(self, assiette: BaseGeometry):
        minx, miny, maxx, maxy = assiette.bounds
        w_m, h_m = (maxx - minx) or 1.0, (maxy - miny) or 1.0
        marge = max(10.0, 0.10 * max(w_m, h_m))
        minx -= marge; miny -= marge; maxx += marge; maxy += marge
        self.minx, self.miny = minx, miny
        self.w_m, self.h_m = maxx - minx, maxy - miny
        aw, ah = PX1 - PX0, PY1 - PY0
        self.sc = min(aw / self.w_m, ah / self.h_m)
        self.ox = PX0 + (aw - self.sc * self.w_m) / 2.0
        self.oy = PY0 + (ah - self.sc * self.h_m) / 2.0

    def px(self, x: float, y: float) -> tuple[float, float]:
        return (self.ox + (x - self.minx) * self.sc,
                PY1 - (self.oy - PY0) - (y - self.miny) * self.sc)

    def pts(self, ring) -> str:
        return " ".join(f"{X:.1f},{Y:.1f}" for X, Y in (self.px(x, y) for x, y in ring))


def _poly(geom, vue, **attr) -> str:
    a = " ".join(f'{k.replace("_","-")}="{v}"' for k, v in attr.items())
    return "".join(f'<polygon points="{vue.pts(r)}" {a}/>' for r in _rings(geom))


def _txt(x, y, s, size=11, anchor="start", fill="#111", weight=None, rot=None) -> str:
    extra = (f' font-weight="{weight}"' if weight else "") + (f' transform="rotate({rot} {x} {y})"' if rot else "")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Inter, Arial, sans-serif" '
            f'font-size="{size}" fill="{fill}" text-anchor="{anchor}"{extra}>{_ESC(s)}</text>')


def _of(scene, kind: str):
    return [o for o in scene.objets if o.kind == kind]


def _geom(o):
    return o.geom_world if getattr(o, "geom_world", None) is not None else o.geom_local


def _bbox_dims_m(geom) -> tuple[float, float]:
    minx, miny, maxx, maxy = geom.bounds
    return (maxx - minx, maxy - miny)


# ── groupes de dessin ───────────────────────────────────────────────────────────────────────
def _g_voisins(ctx: Contexte, vue) -> str:
    b = ['<g id="g-voisins" clip-path="url(#plan)">']
    for g in ctx.batis_voisins:                      # bâti voisin BD TOPO, gris
        b.append(_poly(g, vue, fill="#D9D9D9", stroke="#111", stroke_width="0.6"))
    for v in ctx.voisins:                            # parcelles voisines, trait fin + numéro
        b.append(_poly(v.geom_2975, vue, fill="none", stroke="#111", stroke_width="0.6"))
        if v.numero and not v.geom_2975.is_empty:
            c = v.geom_2975.representative_point()
            X, Y = vue.px(c.x, c.y)
            b.append(_txt(X, Y, v.numero, size=9, anchor="middle", fill="#555"))
    b.append("</g>")
    return "".join(b)


def _g_voies(ctx: Contexte, vue) -> str:
    b = ['<g id="g-voies" clip-path="url(#plan)">']
    vus = set()
    for v in ctx.voies:
        geoms = v.geom_2975.geoms if v.geom_2975.geom_type.startswith("Multi") else [v.geom_2975]
        for g in geoms:
            if g.geom_type != "LineString" or g.is_empty:
                continue
            pts = " ".join(f"{X:.1f},{Y:.1f}" for X, Y in (vue.px(x, y) for x, y in g.coords))
            b.append(f'<polyline points="{pts}" fill="none" stroke="#C9B9B9" stroke-width="3" stroke-linecap="round"/>')
        if v.nom and v.nom not in vus:               # étiquette du toponyme, une fois, au milieu
            vus.add(v.nom)
            g0 = max((g for g in geoms if g.geom_type == "LineString"), key=lambda g: g.length, default=None)
            if g0 is not None:
                mid = g0.interpolate(0.5, normalized=True)
                X, Y = vue.px(mid.x, mid.y)
                b.append(_txt(X, Y, v.nom, size=10, anchor="middle", fill="#7A5A5A", weight="600"))
    b.append("</g>")
    return "".join(b)


def _g_ppr(terrain, vue) -> str:
    b = ['<g id="g-ppr" clip-path="url(#plan)">']
    if getattr(terrain, "ppr_rouge", None) is not None and not terrain.ppr_rouge.is_empty:
        b.append(_poly(terrain.ppr_rouge, vue, fill="url(#ppr)", stroke="#DC2626", stroke_width="1"))
    if getattr(terrain, "ppr_bleue", None) is not None and not terrain.ppr_bleue.is_empty:
        b.append(_poly(terrain.ppr_bleue, vue, fill="url(#pprb)", stroke="#2563EB", stroke_width="1"))
    b.append("</g>")
    return "".join(b)


def _g_projet(scene, vue) -> str:
    """Espaces libres, zone d'implantation, allée/accès, places numérotées, bâtiment, modules."""
    b = []
    # pleine terre (sous le reste)
    b.append('<g id="g-libres" clip-path="url(#plan)">')
    for o in _of(scene, "espace_libre"):
        b.append(_poly(_geom(o), vue, fill="#CDE8C6", stroke="none"))
    b.append("</g>")
    # allée
    b.append('<g id="g-allee" clip-path="url(#plan)">')
    for o in _of(scene, "allee"):
        b.append(_poly(_geom(o), vue, fill="#E5E7EB", stroke="#111", stroke_width="0.7"))
    b.append("</g>")
    # accès
    b.append('<g id="g-acces" clip-path="url(#plan)">')
    for o in _of(scene, "acces"):
        b.append(_poly(_geom(o), vue, fill="#E5E7EB", stroke="#111", stroke_width="0.7"))
    b.append("</g>")
    # places NUMÉROTÉES (le nombre dessiné = le nombre affiché)
    b.append('<g id="g-places" clip-path="url(#plan)">')
    for i, o in enumerate(_of(scene, "place"), start=1):
        g = _geom(o)
        b.append(_poly(g, vue, fill="#fff", stroke="#111", stroke_width="0.7"))
        c = g.representative_point(); X, Y = vue.px(c.x, c.y)
        b.append(_txt(X, Y + 3, str(i), size=8, anchor="middle", fill="#555"))
    b.append("</g>")
    # bâtiment(s) rose + coursive
    b.append('<g id="g-batiment" clip-path="url(#plan)">')
    for o in _of(scene, "coursive"):
        b.append(_poly(_geom(o), vue, fill="#fff", stroke="#111", stroke_width="0.8"))
    for o in _of(scene, "batiment_emprise"):
        b.append(_poly(_geom(o), vue, fill="#F5C6B8", stroke="#111", stroke_width="1.6"))
    for o in _of(scene, "noyau"):
        b.append(_poly(_geom(o), vue, fill="#9CA3AF", stroke="#4B5563", stroke_width="0.6"))
    b.append("</g>")
    # modules T2/T3/T4 (couche optionnelle, masquée par défaut côté écran)
    b.append('<g id="g-modules" clip-path="url(#plan)">')
    for o in _of(scene, "module"):
        if o.niveau not in (0, None):
            continue
        g = _geom(o)
        b.append(_poly(g, vue, fill="none", stroke="#7A3B2C", stroke_width="0.6", stroke_dasharray="2 2"))
        if o.type_logement:
            c = g.representative_point(); X, Y = vue.px(c.x, c.y)
            b.append(_txt(X, Y, o.type_logement, size=8, anchor="middle", fill="#7A3B2C"))
    b.append("</g>")
    return "".join(b)


def _g_zone_limites(terrain, vue) -> str:
    """Zone d'implantation (vert pointillé) + limites des parcelles étudiées (rouge pointillé) +
    limites INTERNES entre parcelles de l'assiette + numéro de chaque parcelle."""
    b = ['<g id="g-zone" clip-path="url(#plan)">']
    b.append(_poly(terrain.zone_implantation, vue, fill="none", stroke="#15803D",
                   stroke_width="1", stroke_dasharray="5 4"))
    b.append("</g>")
    b.append('<g id="g-limites" clip-path="url(#plan)">')
    wminx = terrain.assiette.bounds[0]               # bord ouest de l'assiette → étiquettes à gauche
    for p in terrain.parcelles:                      # chaque parcelle : contour + numéro (limites internes)
        if p.geom_2975 is None or p.geom_2975.is_empty:
            continue
        b.append(_poly(p.geom_2975, vue, fill="none", stroke="#DC2626", stroke_width="1",
                       stroke_dasharray="3 3"))
        c = p.geom_2975.representative_point(); X, Y = vue.px(wminx, c.y)
        b.append(_txt(X - 6, Y + 3, f"AW {p.numero}" if p.numero and p.numero.isdigit() else (p.numero or ""),
                      size=10, anchor="end", fill="#B91C1C", weight="600"))
    # contour EXTÉRIEUR de l'assiette, plus épais
    b.append(_poly(terrain.assiette, vue, fill="none", stroke="#DC2626", stroke_width="2",
                   stroke_dasharray="8 4"))
    b.append("</g>")
    return "".join(b)


def _g_tn(ctx: Contexte, vue) -> str:
    b = ['<g id="g-tn">']
    for c in ctx.tn_coins:
        X, Y = vue.px(c["x"], c["y"])
        b.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="2.3" fill="#DC2626"/>')
        if c.get("alt_m") is not None:
            dx = 6 if X < (PX0 + PX1) / 2 else -6
            anc = "start" if dx > 0 else "end"
            b.append(_txt(X + dx, Y - 4, f"TN {dec_fr(c['alt_m'], 1)}", size=9, anchor=anc, fill="#B91C1C"))
    b.append("</g>")
    return "".join(b)


def _cote_segment(a, b, vue, label, *, off_px, centroide) -> str:
    """Une cote le long du segment monde a→b, décalée perpendiculairement VERS L'EXTÉRIEUR (loin du
    centroïde), étiquette alignée sur le segment (format « 13,00 »)."""
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L                                   # perpendiculaire unitaire (monde)
    mx, my = (ax + bx) / 2, (ay + by) / 2
    # sens extérieur : le signe qui éloigne du centroïde
    if (mx + nx - centroide[0]) ** 2 + (my + ny - centroide[1]) ** 2 < (mx - centroide[0]) ** 2 + (my - centroide[1]) ** 2:
        nx, ny = -nx, -ny
    om = off_px / vue.sc
    A = vue.px(ax + nx * om, ay + ny * om)
    B = vue.px(bx + nx * om, by + ny * om)
    ang = math.degrees(math.atan2(B[1] - A[1], B[0] - A[0]))
    if ang > 90: ang -= 180
    if ang < -90: ang += 180
    tx, ty = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
    s = [f'<line x1="{A[0]:.1f}" y1="{A[1]:.1f}" x2="{B[0]:.1f}" y2="{B[1]:.1f}" stroke="#111" stroke-width="0.8"/>']
    for X, Y in (A, B):
        s.append(f'<line x1="{X-3:.1f}" y1="{Y+3:.1f}" x2="{X+3:.1f}" y2="{Y-3:.1f}" stroke="#111" stroke-width="0.8"/>')
    s.append(f'<text x="{tx:.1f}" y="{ty-3:.1f}" font-family="Inter, Arial, sans-serif" font-size="9" '
             f'text-anchor="middle" fill="#111" transform="rotate({ang:.1f} {tx:.1f} {ty:.1f})">{_ESC(label)}</text>')
    return "".join(s)


def _cotes_mrr(geom, vue, *, off_px) -> str:
    """Cote les DEUX côtés distincts du rectangle minimal orienté (= largeur et longueur RÉELLES de la
    forme, même si elle est en biais dans le repère monde nord-en-haut)."""
    try:
        mrr = geom.minimum_rotated_rectangle
        cs = list(mrr.exterior.coords)[:4]
    except Exception:
        return ""
    c = geom.centroid
    out = []
    for i in (0, 1):
        a, b = cs[i], cs[i + 1]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        out.append(_cote_segment(a, b, vue, dec_fr(length, 2), off_px=off_px, centroide=(c.x, c.y)))
    return "".join(out)


def _g_cotes(terrain, scene, vue) -> str:
    """Cotes RÉELLES (format « 13,00 ») : largeur + longueur de l'assiette et du bâtiment, le long de
    leur rectangle minimal orienté (cotes d'enveloppe du terrain et du volume proposé)."""
    b = ['<g id="g-cotes">', _cotes_mrr(terrain.assiette, vue, off_px=16)]
    batis = _of(scene, "batiment_emprise")
    if batis:
        b.append(_cotes_mrr(_geom(batis[0]), vue, off_px=8))
    b.append("</g>")
    return "".join(b)


def _nord_echelle(vue) -> str:
    b = []
    nx, ny = W - 150, PY0 + 34
    b.append(f'<polygon points="{nx},{ny-16} {nx+8},{ny+14} {nx},{ny+6} {nx-8},{ny+14}" fill="#111"/>')
    b.append(_txt(nx, ny - 22, "N", size=13, anchor="middle", weight="700"))
    # échelle graphique : 10 m par segment, 2 segments
    seg = 10.0 * vue.sc
    bx, by = PX0 + 8, PY1 + 26
    b.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{seg:.1f}" height="6" fill="#111"/>')
    b.append(f'<rect x="{bx+seg:.1f}" y="{by:.1f}" width="{seg:.1f}" height="6" fill="#fff" stroke="#111"/>')
    for k, lab in ((0, "0"), (1, "10"), (2, "20 m")):
        b.append(_txt(bx + k * seg, by + 16, lab, size=9, anchor="middle" if k else "start"))
    # échelle nominale ~ 1 : N (hypothèse d'impression ≈ 0,19 m de large pour l'aire de plan)
    n = (vue.w_m / 0.19)
    nominal = min((100, 200, 250, 500, 1000, 2000, 5000), key=lambda s: abs(s - n))
    b.append(_txt(bx, by - 6, f"Échelle ≈ 1 : {nominal}", size=9, fill="#555"))
    return "".join(b)


def _legende() -> str:
    items = [
        ("none", "#DC2626", "6 3", "Limite des parcelles étudiées"),
        ("none", "#15803D", "4 3", "Zone d’implantation réglementaire"),
        ("#F5C6B8", "#111", "", "Bâtiment proposé"),
        ("#fff", "#111", "", "Place de stationnement 2,50 × 5,00"),
        ("#E5E7EB", "#111", "", "Allée, accès"),
        ("#CDE8C6", "#CDE8C6", "", "Espaces libres, pleine terre"),
        ("#D9D9D9", "#111", "", "Bâti voisin (BD TOPO)"),
        ("url(#ppr)", "#DC2626", "", "PPR zone rouge (retirée)"),
        ("url(#pprb)", "#2563EB", "", "PPR zone bleue (signalée)"),
    ]
    b = [_txt(COL_X, PY0 + 10, "LÉGENDE", size=10, weight="700")]
    y = PY0 + 26
    for fill, stroke, dash, label in items:
        da = f' stroke-dasharray="{dash}"' if dash else ""
        b.append(f'<rect x="{COL_X}" y="{y}" width="18" height="11" fill="{fill}" stroke="{stroke}" stroke-width="1"{da}/>')
        b.append(_txt(COL_X + 26, y + 10, label, size=10))
        y += 18
    return "".join(b)


def _tableau(terrain, cap) -> str:
    cont = terrain.contenance_totale_m2
    emp = cap.emprise_sol_m2
    pct = f" · {round(100 * emp / cont)} %" if cont else ""
    pt = cap.pleine_terre_m2
    lignes = [
        ("Terrain (contenance)", m2_fr(cont)),
        ("Emprise bâtie", f"{m2_fr(emp)}{pct}"),
        (f"SDP du scénario (R+{max(0, getattr(cap, 'niveaux', 1) - 1)})", m2_fr(cap.sdp_m2)),
        ("Stationnement + allée", m2_fr(cap.surface_stationnement_m2)),
        ("Pleine terre", m2_fr(pt)),
        ("Places dessinées / imposées", f"{cap.places} / {cap.places_imposees if cap.places_imposees is not None else '—'}"),
        ("Logements", f"{cap.logements} · " + " · ".join(f"{t} ×{n}" for t, n in cap.par_type.items()) if cap.par_type else str(cap.logements)),
    ]
    y = 326
    b = [_txt(COL_X, y, "SURFACES (mesurées sur le plan)", size=10, weight="700")]
    y += 16
    for k, v in lignes:
        b.append(_txt(COL_X, y, k, size=10, fill="#333"))
        b.append(_txt(1164, y, v, size=10, anchor="end", weight="600"))
        b.append(f'<line x1="{COL_X}" y1="{y+4}" x2="1164" y2="{y+4}" stroke="#DDD"/>')
        y += 16
    return "".join(b)


def _cartouche(entrees: dict, cap, forme: str, niveaux: int, ref: str, *, genere_le: str,
               numero: str, millesime_plu: Optional[str]) -> str:
    x, y0 = COL_X, 566
    commune = entrees.get("commune") or ""
    zone = entrees.get("zone") or ""
    nums = ", ".join((p or "").replace(commune, "") for p in [])  # placeholder (numéros ci-dessous)
    parcelles = ", ".join(sorted({i[8:] for i in (entrees.get("idus") or [])}))
    b = [f'<rect x="{x}" y="{y0}" width="292" height="150" fill="#fff" stroke="#111" stroke-width="1.2"/>']
    b.append(_txt(x + 12, y0 + 20, "LABUSE", size=15, weight="800"))
    b.append(_txt(x + 12, y0 + 38, "Étude de faisabilité — plan masse", size=11, weight="600"))
    b.append(_txt(x + 12, y0 + 56, f"{commune} · {parcelles} · zone {zone}", size=10))
    b.append(_txt(x + 12, y0 + 72, f"Scénario {ref} · {forme.replace('_', ' ')} R+{max(0, niveaux-1)} · stationnement aérien", size=10))
    b.append(_txt(x + 12, y0 + 88, f"PLU {millesime_plu or 'millésime en vigueur'} · LiDAR HD IGN · BD TOPO", size=9, fill="#555"))
    b.append(_txt(x + 12, y0 + 104, f"Généré le {genere_le} · {numero}", size=9, fill="#555"))
    b.append(_txt(x + 12, y0 + 122, "Esquisse indicative — pas une étude d’architecte", size=9, fill="#B45309", weight="600"))
    _ = nums
    return "".join(b)


def _defs() -> str:
    return ('<defs>'
            '<clipPath id="plan"><rect x="%.0f" y="%.0f" width="%.0f" height="%.0f"/></clipPath>'
            '<pattern id="ppr" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<line x1="0" y1="0" x2="0" y2="8" stroke="#DC2626" stroke-width="1.5"/></pattern>'
            '<pattern id="pprb" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<line x1="0" y1="0" x2="0" y2="8" stroke="#2563EB" stroke-width="1.5"/></pattern>'
            '</defs>') % (PX0, PY0, PX1 - PX0, PY1 - PY0)


def planche_svg(scenario, contexte: Contexte, *, ref: str, genere_le: str, numero: str,
                millesime_plu: Optional[str] = None, entrees: Optional[dict] = None) -> str:
    """Le SVG complet de la planche (chaîne autonome, `<svg …>…</svg>`)."""
    terrain, scene, cap = scenario.terrain, scenario.scene, scenario.capacite
    if terrain is None or terrain.assiette is None or terrain.assiette.is_empty:
        return ""
    # cap n'a pas .niveaux : on le pose pour le tableau/cartouche
    try:
        setattr(cap, "niveaux", scenario.niveaux)
    except Exception:
        pass
    vue = _Vue(terrain.assiette)
    ent = entrees or {}
    body = [
        f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="#fff"/>',
        _defs(),
        _g_voisins(contexte, vue),
        _g_voies(contexte, vue),
        _g_ppr(terrain, vue),
        _g_projet(scene, vue),
        _g_zone_limites(terrain, vue),
        _g_tn(contexte, vue),
        _g_cotes(terrain, scene, vue),
        _nord_echelle(vue),
        _legende(),
        _tableau(terrain, cap),
        _cartouche(ent, cap, scenario.forme, scenario.niveaux, ref,
                   genere_le=genere_le, numero=numero, millesime_plu=millesime_plu),
    ]
    # width="100%" (ATTRIBUT) : WeasyPrint dimensionne le SVG via le viewBox (comme _svg_plan) → la
    # planche s'imprime en pleine page paysage. À l'écran, PlanMasseSvg réimpose width/height de toute façon.
    return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" xmlns="http://www.w3.org/2000/svg" '
            f'class="planche" font-family="Inter, Arial, sans-serif">' + "".join(body) + "</svg>")
