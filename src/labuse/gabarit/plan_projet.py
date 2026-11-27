"""Plan coté vectoriel dans le repère métrique du DXF."""
from html import escape
from fastapi import HTTPException

from ..exports.rendu import render_pdf


def plan_cote_html(idu, plan, sommets, bilan):
    points = [*sommets, *(pt for poly in plan["terrain"] for ring in poly for pt in ring)]
    xs, ys = zip(*points)
    x0, y1 = min(xs), max(ys)
    k = min(620 / max(max(xs)-x0, .01), 370 / max(y1-min(ys), .01))

    def xy(pt):
        return (20+(pt[0]-x0)*k, 20+(y1-pt[1])*k)

    def chemin(points):
        return "M"+" L".join("%.4f %.4f" % xy(p) for p in points)

    def fmt(n):
        return f"{n:.2f}".replace(".", ",")

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 410" width="660" height="410">']
    for cle, col in (("terrain", "#ecefee"), ("reculs", "#f6d7a5"), ("zone", "#b4e4ce"), ("bati", "#adb5ba")):
        for poly in plan[cle]:
            d = " ".join(chemin(r)+" Z" for r in poly)
            svg.append(f'<path d="{d}" fill="{col}" stroke="#58676b" fill-rule="evenodd"/>')
    svg.append(f'<path d="{chemin(sommets)} Z" fill="#b4d3ff" stroke="#185fa3" stroke-width="2"/>')
    lignes = []
    for i, c in enumerate(bilan["cotes"], 1):
        a, b = c["a"], c["b"]
        x, y = xy(b)
        svg.append(f'<path d="{chemin([a,b])}" fill="none" stroke="#975711" stroke-dasharray="3 2"/>'
                   f'<text x="{x+2:.2f}" y="{y-2:.2f}" font-size="10" fill="#753a00">{i}</text>')
        lignes.append(f'<tr><td>{escape(c["nom"])}</td><td>{fmt(c["m"])} m</td></tr>')
    svg.append('</svg>')
    alerte = ''
    if bilan["horsZone"] > .005:
        alerte += f' · {fmt(bilan["horsZone"])} m² hors zone disponible'
    if plan["solde"] is not None and bilan["aire"] > plan["solde"] + .05:
        alerte += f' · solde estimé dépassé ({fmt(plan["solde"])} m²)'
    return f"""
    <h2>Plan coté de l’implantation</h2><p>Parcelle {escape(idu)} · {fmt(bilan["aire"])} m² au sol{alerte}</p>
    {''.join(svg)}<p>Nord en haut · projet en bleu · bâti en gris · reculs en ocre · zone disponible en vert</p>
    <table><thead><tr><th>Limite</th><th>Distance horizontale minimale</th></tr></thead><tbody>{''.join(lignes)}</tbody></table>
    <p>RGR92 / UTM 40S · EPSG:2975 · cotes en mètres</p>"""


def plan_cote_pdf(idu, plan, sommets, bilan):
    html = f"""<html><meta charset="utf-8"><style>@page{{size:A4;margin:15mm}}
    body{{font:11pt sans-serif;color:#213437}}h1{{font-size:21pt}}svg{{max-width:100%}}
    td,th{{padding:3px 12px;text-align:left;border-bottom:1px solid #ccd3d4}}
    table{{border-collapse:collapse;width:100%}}tr{{break-inside:avoid}}</style>
    {plan_cote_html(idu, plan, sommets, bilan)}</html>"""
    return render_pdf(html)


def plan_metrique(gr):
    from shapely.geometry import shape
    from ..gabarit._geom import to_metric
    if gr.status != "ok":
        raise HTTPException(422, "Plan d’implantation indisponible.")
    raccord = gr.raccordement or {}

    def anneaux(geo):
        if not geo:
            return []
        g = to_metric(shape(geo))
        polys = g.geoms if g.geom_type == "MultiPolygon" else [g]
        return [[list(r.coords) for r in [p.exterior, *p.interiors]] for p in polys if p.geom_type == "Polygon"]

    return {"terrain": anneaux((raccord.get("parcelle") or {}).get("contour_entier") or gr.contourGeoJSON),
            "reculs": anneaux(gr.retraitsGeoJSON),
            "zone": anneaux(gr.zoneImplantationGeoJSON),
            "bati": [poly for f in (gr.batiExistantGeoJSON or {}).get("features", [])
                     for poly in anneaux(f["geometry"])],
            "limites": raccord.get("limites_implantation", []),
            "solde": gr.empriseSupplementaireM2}


def _mesurer_implantation(sommets, plan):
    from shapely.geometry import mapping
    from ..gabarit._geom import to_wgs
    import math
    from shapely.geometry import LineString, Polygon
    from shapely.ops import nearest_points, unary_union
    if not 3 <= len(sommets) <= 256 or not all(math.isfinite(v) for pt in sommets for v in pt):
        raise HTTPException(422, "Choisissez entre 3 et 256 sommets.")
    projet = Polygon(sommets)
    if not projet.is_valid or projet.area < 0.01:
        raise HTTPException(422, "Le contour doit avoir une surface et ne pas se croiser.")
    zone = unary_union([Polygon(p[0], p[1:]) for p in plan["zone"]])
    cotes = []
    for limite in plan["limites"]:
        a, b = nearest_points(projet, LineString(limite["ligne"]))
        cotes.append({"nom": limite["nom"], "a": list(a.coords[0]), "b": list(b.coords[0]), "m": a.distance(b),
                      "wgs": [list(to_wgs(pt).coords[0]) for pt in (a, b)]})
    return {"contour": mapping(to_wgs(projet)), "aire": projet.area, "horsZone": projet.difference(zone).area, "cotes": cotes}


