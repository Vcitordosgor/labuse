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


def _refs_courts(idus) -> str:
    """« AW 99, 451, 624, 625 » (section une fois + numéros) — compact pour le cartouche (anti-débordement)."""
    sec, nums = "", []
    for i in sorted(idus or []):
        if len(i) >= 12:
            sec = i[8:10]
            nums.append(str(int(i[10:])) if i[10:].isdigit() else i[10:])
    return (f"{sec} " + ", ".join(nums)) if nums else ""


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


def _g_bati_assiette(ctx: Contexte, vue, *, libere: bool) -> str:
    # DOCS-COHERENCE-1 (F1) — bâti EXISTANT sur l'assiette, gris pointillé. Sur une étude terrain libéré,
    # il est « supposé démoli » (écrit au §3 du PDF, dessiné ici) : il ne fait pas partie du projet.
    if not ctx.batis_assiette:
        return ""
    # Convention archi : l'existant à démolir se montre en POINTILLÉ SANS remplissage, par-dessus le
    # projet, pour rester lisible (le bâtiment proposé occupe souvent la même emprise).
    b = ['<g id="g-bati-assiette" clip-path="url(#plan)">']
    for g in ctx.batis_assiette:
        b.append(_poly(g, vue, fill="none", stroke="#6B7280", stroke_width="1.1", stroke_dasharray="5 3"))
    try:
        from shapely.ops import unary_union
        c = unary_union(ctx.batis_assiette).representative_point()
        X, Y = vue.px(c.x, c.y)
        lab = "existant · supposé démoli" if libere else "existant"
        b.append(_txt(X, Y, lab, size=8, anchor="middle", fill="#6B7280"))
    except Exception:
        pass
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
    """Cotes RÉELLES (format « 13,00 ») : largeur + longueur de l'ASSIETTE le long de son rectangle
    minimal orienté. (Les cotes du bâtiment sont retirées : elles tombaient sur les places — recette Vic ;
    les dimensions du volume sont dans le tableau des surfaces / la coupe.)"""
    b = ['<g id="g-cotes">', _cotes_mrr(terrain.assiette, vue, off_px=16), "</g>"]
    _ = scene
    return "".join(b)


def _nord_echelle(vue) -> str:
    b = []
    # flèche du nord DANS l'aire de plan (coin haut-droit), plus sur la colonne de légende (recette Vic).
    nx, ny = PX1 - 22, PY0 + 34
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
        ("none", "#6B7280", "5 3", "Bâti existant (supposé démoli)"),
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
    # ETUDE-V6-8 (item 4) — en sous-sol, l'emprise enterrée ET la RAMPE d'accès sont COMPTÉES dans le tableau
    # des surfaces (la rampe n'est jamais 0 m² : il faut bien descendre au −1).
    if getattr(cap, "stationnement_mode", "aerien") == "sous_sol":
        lignes.insert(4, ("Emprise du sous-sol", m2_fr(getattr(cap, "emprise_sous_sol_m2", 0.0))))
        lignes.insert(5, ("Rampe d’accès au sous-sol", m2_fr(getattr(cap, "rampe_m2", 0.0))))
    y = 326
    b = [_txt(COL_X, y, "SURFACES (mesurées sur le plan)", size=10, weight="700")]
    y += 16
    for k, v in lignes:
        b.append(_txt(COL_X, y, k, size=10, fill="#333"))
        b.append(_txt(1164, y, v, size=10, anchor="end", weight="600"))
        b.append(f'<line x1="{COL_X}" y1="{y+4}" x2="1164" y2="{y+4}" stroke="#DDD"/>')
        y += 16
    return "".join(b)


def _mode_statio(cap) -> str:
    """ETUDE-V6-7 (item 5) — libellé du MODE RÉEL de stationnement, jamais « aérien » en sous-sol."""
    if getattr(cap, "stationnement_mode", "aerien") == "sous_sol":
        return "sous-sol (niveau −1)"
    return "aérien"


def _cartouche(entrees: dict, cap, forme: str, niveaux: int, ref: str, *, genere_le: str,
               numero: str, millesime_plu: Optional[str]) -> str:
    x, y0 = COL_X, 566
    commune = entrees.get("commune") or ""
    zone = entrees.get("zone") or ""
    parcelles = _refs_courts(entrees.get("idus"))
    # commune·zone et parcelles sur DEUX lignes (anti-débordement, recette Vic).
    b = [f'<rect x="{x}" y="{y0}" width="292" height="158" fill="#fff" stroke="#111" stroke-width="1.2"/>']
    b.append(_txt(x + 12, y0 + 20, "LABUSE", size=15, weight="800"))
    b.append(_txt(x + 12, y0 + 37, "Étude de faisabilité — plan masse", size=10.5, weight="600"))
    b.append(_txt(x + 12, y0 + 53, f"{commune} · zone {zone}", size=9.5))
    b.append(_txt(x + 12, y0 + 68, f"Parcelles {parcelles}", size=9.5))
    b.append(_txt(x + 12, y0 + 84, f"{forme.replace('_', ' ').capitalize()} R+{max(0, niveaux-1)} · stationnement {_mode_statio(cap)}", size=9))
    b.append(_txt(x + 12, y0 + 100, f"PLU {millesime_plu or 'millésime en vigueur'} · LiDAR HD IGN · BD TOPO", size=8.5, fill="#555"))
    b.append(_txt(x + 12, y0 + 115, f"Généré le {genere_le} · {numero}", size=8.5, fill="#555"))
    b.append(_txt(x + 12, y0 + 134, "Esquisse indicative — pas une étude d’architecte", size=9, fill="#B45309", weight="600"))
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
        _g_projet(scene, vue),
        # F1 — existant « supposé démoli » APRÈS le projet : pointillé lisible par-dessus l'emprise neuve.
        _g_bati_assiette(contexte, vue, libere=(ent.get("terrain") or "libere") == "libere"),
        # PPR APRÈS la pleine terre / les objets : sinon l'aplat vert des espaces libres recouvrait les
        # hachures (bug recette Vic). Dessinée au-dessus du sol, sous les limites rouges et les cotes.
        _g_ppr(terrain, vue),
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


# ── COUPE DE PRINCIPE ───────────────────────────────────────────────────────────────────────
# Même esprit que la planche (UN SEUL SVG, écran + PDF, dessiné depuis la géométrie) : une coupe
# SCHÉMATIQUE — terrain naturel LiDAR (rouge), limites de propriété, bâtiment en coupe avec ses niveaux
# nommés (RDC, R+1…), hauteurs à l'égout/au faîtage en pointillé bleu, prospect si CHIFFRÉ, stationnement,
# cotes, légende, cartouche. Les hauteurs sont à l'échelle ; l'axe horizontal suit la profondeur du terrain.
CW, CH = 1180.0, 560.0
CPX0, CPY0, CPX1, CPY1 = 60.0, 60.0, 860.0, 480.0     # aire de dessin de la coupe
CCOL = 884.0                                          # colonne de droite (légende/cartouche)


def coupe_svg(scenario, contexte: Contexte, *, ref: str, genere_le: str, numero: str,
              entrees: Optional[dict] = None) -> str:
    terrain = scenario.terrain
    if terrain is None or terrain.assiette is None or terrain.assiette.is_empty:
        return ""
    conv, regles = scenario.conventions, scenario.regles
    scene = scenario.scene
    niveaux = max(1, int(scenario.niveaux or 1))
    h_et = float(getattr(conv, "hauteur_etage_m", 3.0) or 3.0)
    H_bat = niveaux * h_et
    h_eg = regles.hauteur_egout.valeur if regles.hauteur_egout.validee else None
    h_ft = regles.hauteur_faitage.valeur if regles.hauteur_faitage.validee else None
    recul = float(regles.recul_voie.valeur or 0.0)
    prof = float(getattr(conv, "profondeur_m", 13.0) or 13.0)
    prospect = getattr(regles, "prospect", None)
    prospect_val = prospect.valeur if (prospect is not None and getattr(prospect, "valeur", None)) else None

    # IMPLANTATION-4 (recette Vic) — COUPE À TRAVERS LE PLAN RÉEL : axe perpendiculaire à la voie, on
    # PROJETTE le bâtiment et le stationnement à leur VRAIE position le long de l'axe (plus « collés à
    # la voie »), et le TN suit le profil LiDAR échantillonné sur cet axe.
    axe = contexte.axe
    if axe:
        ox, oy, ux, uy, L = axe["ox"], axe["oy"], axe["ux"], axe["uy"], axe["L"]
        def proj(x, y):   # distance le long de l'axe depuis l'origine « voie »
            return (x - ox) * ux + (y - oy) * uy
    else:
        L = max(recul + prof + 6.0, 20.0)
        def proj(x, y):   # repli (pas de voie servie) : bâtiment au recul
            return recul
    span = max(L, 6.0)

    def dspan(kind):
        ds = []
        for o in _of(scene, kind):
            g = _geom(o)
            polys = g.geoms if getattr(g, "geom_type", "").startswith("Multi") else [g]
            for p in polys:
                ds += [proj(x, y) for x, y in p.exterior.coords]
        return (min(ds), max(ds)) if ds else None

    bld = dspan("batiment_emprise")
    if not bld:
        bld = (recul, recul + prof)
    bf, bb = max(0.0, bld[0]), min(span, bld[1])
    if bb - bf < 1.0:
        bf, bb = recul, recul + prof
    park = None
    for k in ("place", "allee", "acces"):
        dp = dspan(k)
        if dp:
            park = (min(park[0], dp[0]), max(park[1], dp[1])) if park else dp

    # profil TN le long de l'axe (relatif au point bas) ; plat si pas de LiDAR
    tnpts = [(p["d_m"], p["alt_m"]) for p in (contexte.tn_section or []) if p.get("alt_m") is not None]
    tnpts = [(max(0.0, min(span, d)), a) for d, a in tnpts]
    if len(tnpts) >= 2:
        amin = min(a for _, a in tnpts)
        tn = sorted((d, a - amin) for d, a in tnpts)
        tn_abs0 = amin
    else:
        tn = [(0.0, 0.0), (span, 0.0)]
        tn_abs0 = None

    def tn_at(d):
        if d <= tn[0][0]:
            return tn[0][1]
        if d >= tn[-1][0]:
            return tn[-1][1]
        for i in range(1, len(tn)):
            if d <= tn[i][0]:
                (d0, a0), (d1, a1) = tn[i - 1], tn[i]
                return a0 + (a1 - a0) * ((d - d0) / ((d1 - d0) or 1.0))
        return tn[-1][1]

    relief = max(a for _, a in tn) - min(a for _, a in tn)
    hmax = max(H_bat, h_ft or 0.0, h_eg or 0.0, prospect_val or 0.0) + relief + 2.5
    sc = min((CPX1 - CPX0) / span, (CPY1 - CPY0) / hmax)

    def X(d):   # noqa: E743
        return CPX0 + d * sc

    def Y(h):   # noqa: E743
        return CPY1 - h * sc

    sol = tn_at((bf + bb) / 2.0)                   # plateforme du bâtiment = TN sous son milieu
    b = [f'<rect x="0" y="0" width="{CW:.0f}" height="{CH:.0f}" fill="#fff"/>']

    # ── stationnement (sous le bâtiment dans l'ordre de dessin) — à sa vraie position, au niveau du TN
    b.append('<g id="g-places">')
    if park:
        pf, pb = max(0.0, park[0]), min(span, park[1])
        if pb > pf:
            yb = min(Y(tn_at(pf)), Y(tn_at(pb)))
            b.append(f'<rect x="{X(pf):.1f}" y="{yb - 6:.1f}" width="{(X(pb) - X(pf)):.1f}" height="6" '
                     'fill="#E5E7EB" stroke="#111" stroke-width="0.6"/>')
    b.append("</g>")

    # ── terrain naturel (LiDAR), rouge — polyligne du profil échantillonné
    b.append('<g id="g-tn">')
    pts = " ".join(f"{X(d):.1f},{Y(a):.1f}" for d, a in tn)
    b.append(f'<polyline points="{pts}" fill="none" stroke="#DC2626" stroke-width="1.6"/>')
    b.append(_txt(X(span * 0.6), Y(tn_at(span * 0.6)) + 14, "Terrain naturel (LiDAR)", size=10, fill="#B91C1C"))
    if tn_abs0 is not None:
        b.append(_txt(X(0) - 6, Y(tn[0][1]), dec_fr(tn_abs0 + tn[0][1], 1), size=9, anchor="end", fill="#B91C1C"))
        b.append(_txt(X(span) + 6, Y(tn[-1][1]), dec_fr(tn_abs0 + tn[-1][1], 1), size=9, anchor="start", fill="#B91C1C"))
    b.append("</g>")

    # ── limites de propriété (verticales)
    b.append('<g id="g-limites">')
    for xm, lab, anc in ((0.0, "limite sur voie", "start"), (span, "limite de fond", "end")):
        b.append(f'<line x1="{X(xm):.1f}" y1="{Y(tn_at(xm)):.1f}" x2="{X(xm):.1f}" y2="{Y(hmax):.1f}" '
                 'stroke="#111" stroke-width="1" stroke-dasharray="4 3"/>')
        b.append(_txt(X(xm), Y(hmax) - 4, lab, size=9, anchor=anc, fill="#555"))
    b.append("</g>")

    # ── hauteurs réglementaires égout / faîtage : MESURÉES DEPUIS LE TN → polylignes PARALLÈLES au terrain
    b.append('<g id="g-hauteurs">')
    for h, lab in ((h_eg, "hauteur à l’égout"), (h_ft, "hauteur au faîtage")):
        if h is None:
            continue
        hp = " ".join(f"{X(d):.1f},{Y(a + h):.1f}" for d, a in tn)
        b.append(f'<polyline points="{hp}" fill="none" stroke="#2563EB" stroke-width="1" stroke-dasharray="6 3"/>')
        b.append(_txt(CPX1 - 4, Y(tn[-1][1] + h) - 3, f"{lab} {dec_fr(h, 2)} m", size=9, anchor="end", fill="#1D4ED8"))
    b.append("</g>")

    # ── prospect (seulement s'il est CHIFFRÉ) : droite de pente depuis la limite de fond
    if prospect_val:
        b.append('<g id="g-prospect">')
        b.append(f'<line x1="{X(span):.1f}" y1="{Y(tn_at(span)):.1f}" x2="{X(bf):.1f}" '
                 f'y2="{Y(sol + prospect_val):.1f}" stroke="#B45309" stroke-width="1" stroke-dasharray="2 2"/>')
        b.append(_txt(X(span * 0.8), Y(sol + prospect_val * 0.5), "prospect", size=9, fill="#B45309"))
        b.append("</g>")

    # ── bâtiment en coupe à sa VRAIE position (bf→bb), plateforme au TN, niveaux nommés
    # DOCS-COHERENCE-1 (F8) — si le contrôle « hauteur sur terrain en pente » conclut EN GRADINS (une
    # toiture plate dépasserait le plafond à l'égout côté aval), la coupe DOIT dessiner les gradins —
    # sinon le plan/coupe (volume droit) contredit le texte. Le relief sous le bâti se mesure sur le TN
    # entre bf et bb ; même seuil et même nombre de gradins que controles.py (décrochement d'un étage).
    b.append('<g id="g-batiment">')
    bX, bW = X(bf), X(bb) - X(bf)
    relief_bati = abs(tn_at(bb) - tn_at(bf))
    en_gradins = bool(h_eg and relief_bati >= 0.5 and (H_bat + relief_bati) > h_eg + 1e-9)
    if en_gradins:
        import math as _m
        n_grad = max(2, _m.ceil(relief_bati / h_et) + 1)
        # pente du TN sous le bâti : le bas (aval) est à sol_bas, le haut (amont) à sol_haut
        sol_f, sol_b = tn_at(bf), tn_at(bb)
        amont_cote_f = sol_f >= sol_b          # True si le côté voie (bf) est le plus haut
        for g in range(n_grad):
            gx0 = bf + (bb - bf) * g / n_grad
            gx1 = bf + (bb - bf) * (g + 1) / n_grad
            base = tn_at((gx0 + gx1) / 2.0)    # plateforme du gradin = TN sous son milieu
            gX, gW = X(gx0), X(gx1) - X(gx0)
            b.append(f'<rect x="{gX:.1f}" y="{Y(base + H_bat):.1f}" width="{gW:.1f}" height="{H_bat * sc:.1f}" '
                     'fill="#F5C6B8" stroke="#111" stroke-width="1.2"/>')
            for n in range(niveaux):
                yb = Y(base + (n + 1) * h_et)
                b.append(f'<line x1="{gX:.1f}" y1="{yb:.1f}" x2="{gX + gW:.1f}" y2="{yb:.1f}" stroke="#111" stroke-width="0.5"/>')
            b.append(_txt(gX + 4, Y(base) - 4, f"RDC" if niveaux == 1 else f"R+{niveaux - 1}", size=7.5, fill="#7A3B2C"))
        b.append(_txt((bX + bX + bW) / 2.0, Y(max(tn_at(bf), tn_at(bb)) + H_bat) - 8,
                      f"bâtiment en {n_grad} gradins (un décrochement par étage)", size=8.5, anchor="middle", fill="#7A3B2C"))
    else:
        b.append(f'<rect x="{bX:.1f}" y="{Y(sol + H_bat):.1f}" width="{bW:.1f}" height="{H_bat * sc:.1f}" '
                 'fill="#F5C6B8" stroke="#111" stroke-width="1.4"/>')
        for n in range(niveaux):
            yb = Y(sol + (n + 1) * h_et)
            b.append(f'<line x1="{bX:.1f}" y1="{yb:.1f}" x2="{bX + bW:.1f}" y2="{yb:.1f}" stroke="#111" stroke-width="0.6"/>')
            b.append(_txt(bX + 6, Y(sol + n * h_et) - 4, "RDC" if n == 0 else f"R+{n}", size=9, fill="#7A3B2C"))
        if h_ft and h_eg and h_ft > h_eg:
            yft = Y(sol + h_ft)
            b.append(f'<polygon points="{bX:.1f},{Y(sol + H_bat):.1f} {bX + bW / 2:.1f},{yft:.1f} '
                     f'{bX + bW:.1f},{Y(sol + H_bat):.1f}" fill="#E8D5CE" stroke="#111" stroke-width="0.8"/>')
    b.append("</g>")

    # ── cote de hauteur du bâtiment (à gauche du volume, côté voie)
    b.append('<g id="g-cotes">')
    cx = bX - 10
    b.append(f'<line x1="{cx:.1f}" y1="{Y(sol):.1f}" x2="{cx:.1f}" y2="{Y(sol + H_bat):.1f}" stroke="#111" stroke-width="0.8"/>')
    for yy in (Y(sol), Y(sol + H_bat)):
        b.append(f'<line x1="{cx - 3:.1f}" y1="{yy:.1f}" x2="{cx + 3:.1f}" y2="{yy:.1f}" stroke="#111" stroke-width="0.8"/>')
    b.append(_txt(cx - 5, (Y(sol) + Y(sol + H_bat)) / 2, f"{dec_fr(H_bat, 2)} m", size=9, anchor="end", fill="#111"))
    b.append("</g>")

    # ── légende + cartouche (colonne de droite)
    # ETUDE-V6-7 (item 5) — la légende dit le MODE RÉEL (jamais « aérien » sur une étude en sous-sol).
    _stat_lab = ("Stationnement sous-sol (−1)" if getattr(scene, "sous_sol", None)
                 else "Stationnement aérien")
    leg = [("#DC2626", "Terrain naturel (LiDAR)"), ("#2563EB", "Hauteur égout / faîtage (règle)"),
           ("#F5C6B8", "Bâtiment en coupe"), ("#E5E7EB", _stat_lab)]
    b.append(_txt(CCOL, CPY0 + 6, "LÉGENDE", size=10, weight="700"))
    ly = CPY0 + 22
    for col, lab in leg:
        b.append(f'<rect x="{CCOL}" y="{ly}" width="16" height="10" fill="{col}" stroke="#111" stroke-width="0.6"/>')
        b.append(_txt(CCOL + 24, ly + 9, lab, size=10))
        ly += 18
    ent = entrees or {}
    commune = ent.get("commune") or ""
    parcelles = _refs_courts(ent.get("idus"))
    cy = CPY0 + 150
    b.append(f'<rect x="{CCOL}" y="{cy}" width="280" height="150" fill="#fff" stroke="#111" stroke-width="1.2"/>')
    b.append(_txt(CCOL + 12, cy + 20, "LABUSE", size=15, weight="800"))
    b.append(_txt(CCOL + 12, cy + 37, "Étude de faisabilité — coupe de principe", size=10.5, weight="600"))
    b.append(_txt(CCOL + 12, cy + 53, f"{commune} · zone {ent.get('zone') or ''}", size=9.5))
    b.append(_txt(CCOL + 12, cy + 68, f"Parcelles {parcelles}", size=9.5))
    b.append(_txt(CCOL + 12, cy + 84, f"Scénario {ref} · R+{max(0, niveaux - 1)} · {niveaux} niveaux × {dec_fr(h_et, 2)} m", size=9))
    b.append(_txt(CCOL + 12, cy + 100, "TN LiDAR HD IGN · règles PLU servies", size=8.5, fill="#555"))
    b.append(_txt(CCOL + 12, cy + 115, f"Généré le {genere_le} · {numero}", size=8.5, fill="#555"))
    b.append(_txt(CCOL + 12, cy + 134, "Esquisse indicative — pas une étude d’architecte", size=9, fill="#B45309", weight="600"))

    return (f'<svg viewBox="0 0 {CW:.0f} {CH:.0f}" width="100%" xmlns="http://www.w3.org/2000/svg" '
            f'class="coupe" font-family="Inter, Arial, sans-serif">' + "".join(b) + "</svg>")
