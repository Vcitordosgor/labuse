"""Rendu : plan.png (depuis la géométrie 2975, cadastre + objets + légende) et scenario.json complet.

Aucune dépendance au front : matplotlib (Agg) pour l'image, json pour l'archive rejouable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shapely.geometry import MultiPolygon, Polygon

from .moteur import Scenario

# palette (reprend la maquette)
_COUL = {
    "parcelle": ("#FBFCFB", "#9AA0A6"),
    "assiette": (None, "#DC2626"),
    "zone": ("#4ADE80", "#15803D"),
    "espace_libre": ("#BBF7D0", "#86EFAC"),
    "allee": ("#D1D5DB", "#9CA3AF"),
    "place": ("#FFFFFF", "#6B7280"),
    "acces": ("#B45309", "#B45309"),
    "batiment_emprise": ("#1F2A24", "#1F2A24"),
    "noyau": ("#9CA3AF", "#4B5563"),
    "coursive": ("#E5E7EB", "#9CA3AF"),
    "module": ("#ECFDF3", "#15803D"),
    "voie": (None, "#B45309"),
}


def _rings(geom) -> list[tuple[list, list]]:
    out = []
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    for p in polys:
        if isinstance(p, Polygon) and not p.is_empty:
            out.append(p)
    return out


def _fill(ax, geom, face, edge, *, lw=0.8, alpha=1.0, ls="-", z=1, hatch=None):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath
    for p in _rings(geom):
        verts, codes = [], []
        for ring in [p.exterior, *p.interiors]:
            xy = list(ring.coords)
            verts.extend(xy)
            codes.append(MplPath.MOVETO)
            codes.extend([MplPath.LINETO] * (len(xy) - 2))
            codes.append(MplPath.CLOSEPOLY)
        patch = PathPatch(MplPath(verts, codes),
                          facecolor=(face or "none"), edgecolor=(edge or "none"),
                          lw=lw, alpha=alpha, ls=ls, zorder=z, hatch=hatch)
        ax.add_patch(patch)


def rendre_plan_png(scenario: Scenario, path: str | Path, *, dpi: int = 150) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    t = scenario.terrain
    sc = scenario.scene
    fig, ax = plt.subplots(figsize=(9, 9))

    # cadastre
    for p in t.parcelles:
        if p.geom_2975 is not None:
            _fill(ax, p.geom_2975, *_COUL["parcelle"], lw=0.6, z=1)
            c = p.geom_2975.representative_point()
            ax.annotate(f"AW {p.numero}", (c.x, c.y), ha="center", va="center",
                        fontsize=7, color="#6B7280", zorder=2)
    _fill(ax, t.assiette, None, _COUL["assiette"][1], lw=1.8, ls=(0, (6, 3)), z=3)
    _fill(ax, t.zone_implantation, _COUL["zone"][0], _COUL["zone"][1], lw=1.0, alpha=0.12,
          ls=(0, (4, 3)), z=2)

    # objets dessinés (ordre d'empilement)
    for o in sc.of("espace_libre"):
        _fill(ax, o.geom_world, *_COUL["espace_libre"], lw=0.3, alpha=0.5, z=2)
    for o in sc.of("allee"):
        _fill(ax, o.geom_world, *_COUL["allee"], lw=0.4, z=4)
    for o in sc.of("acces"):
        _fill(ax, o.geom_world, *_COUL["acces"], lw=0.4, alpha=0.85, z=5)
    for o in sc.of("place"):
        _fill(ax, o.geom_world, *_COUL["place"], lw=0.5, z=5)
    for o in sc.of("batiment_emprise"):
        _fill(ax, o.geom_world, *_COUL["batiment_emprise"], lw=0.8, alpha=0.9, z=6)
    # niveau de référence : modules + noyau + coursive (plan de principe)
    for o in sc.of("coursive"):
        if o.niveau == 0:
            _fill(ax, o.geom_world, *_COUL["coursive"], lw=0.3, alpha=0.6, z=7)
    for o in sc.of("module"):
        if o.niveau == 0:
            _fill(ax, o.geom_world, *_COUL["module"], lw=0.4, alpha=0.65, z=8)
            c = o.geom_world.representative_point()
            ax.annotate(o.type_logement, (c.x, c.y), ha="center", va="center",
                        fontsize=5.5, color="#15803D", zorder=9)
    for o in sc.of("noyau"):
        if o.niveau == 0:
            _fill(ax, o.geom_world, *_COUL["noyau"], lw=0.4, alpha=0.9, z=8)

    # cadastre par-dessus (limites des 4 parcelles, pour que le fond cadastral reste lisible)
    for p in t.parcelles:
        if p.geom_2975 is not None:
            x, y = p.geom_2975.exterior.xy
            ax.plot(x, y, color="#6B7280", lw=0.7, ls=(0, (3, 2)), alpha=0.9, zorder=9)

    # voie (surlignée)
    for g in t.voie_edges:
        x, y = g.xy
        ax.plot(x, y, color=_COUL["voie"][1], lw=3.2, solid_capstyle="round", zorder=10)

    # cadrage + échelle + nord
    minx, miny, maxx, maxy = t.assiette.buffer(8).bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal")
    ax.axis("off")
    # barre d'échelle 10 m
    x0 = minx + 3
    y0 = miny + 3
    ax.plot([x0, x0 + 10], [y0, y0], color="#1F2A24", lw=2, zorder=11)
    ax.annotate("10 m", (x0 + 5, y0 + 1.2), ha="center", fontsize=7, color="#1F2A24", zorder=11)
    ax.annotate("N\n↑", (maxx - 4, maxy - 6), ha="center", fontsize=9, color="#1F2A24", zorder=11)

    cap = scenario.capacite
    ax.set_title(f"Implantation {t.commune} · AW 99-451-624-625 · zone UA\n"
                 f"{scenario.forme} R+{scenario.niveaux - 1} · {cap.logements} logements · "
                 f"{cap.places} places aériennes · {scenario.statut}", fontsize=10)

    legende = [
        Patch(fc="none", ec=_COUL["assiette"][1], ls="--", label="Parcelles / assiette"),
        Patch(fc=_COUL["zone"][0], ec=_COUL["zone"][1], alpha=0.3, label="Zone d'implantation"),
        Patch(fc=_COUL["batiment_emprise"][0], ec="none", label="Bâtiment proposé"),
        Patch(fc=_COUL["module"][0], ec=_COUL["module"][1], label="Module logement (R0)"),
        Patch(fc=_COUL["noyau"][0], ec=_COUL["noyau"][1], label="Noyau"),
        Patch(fc=_COUL["place"][0], ec=_COUL["place"][1], label="Place 2,5×5 m"),
        Patch(fc=_COUL["allee"][0], ec=_COUL["allee"][1], label="Allée 5 m"),
        Patch(fc=_COUL["espace_libre"][0], ec=_COUL["espace_libre"][1], label="Espaces libres"),
        Patch(fc=_COUL["acces"][0], ec="none", label="Accès"),
        Line2D([0], [0], color=_COUL["voie"][1], lw=3, label="Limite classée voie"),
    ]
    ax.legend(handles=legende, loc="upper left", fontsize=7, framealpha=0.9, ncol=2)
    fig.tight_layout()
    fig.savefig(str(path), dpi=dpi, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------- scenario.json
def _coords(geom) -> list:
    return [list(p.exterior.coords) for p in _rings(geom)]


def scenario_dict(scenario: Scenario, *, genere_le: str | None = None) -> dict[str, Any]:
    t = scenario.terrain
    r = scenario.regles
    conv = scenario.conventions
    cap = scenario.capacite
    sc = scenario.scene

    objets = []
    for o in sc.objets:
        objets.append({
            "kind": o.kind, "niveau": o.niveau, "type_logement": o.type_logement, "ref": o.ref,
            "coords_2975": _coords(o.geom_world if o.geom_world is not None else o.geom_local),
            "aire_m2": round((o.geom_world or o.geom_local).area, 2),
        })

    def regle_json(rg):
        return {"nom": rg.nom, "valeur": rg.valeur, "unite": rg.unite, "validee": rg.validee,
                "article": rg.article, "page_pdf": rg.page_pdf, "citation": rg.citation}

    return {
        "livrable": "IMPLANTATION-1",
        "genere_le": genere_le,
        "crs": "EPSG:2975",
        "entrees": {
            "parcelles": [p.idu for p in t.parcelles], "commune": t.commune, "insee": t.insee,
            "zone": r.zone, "objectif": scenario.objectif,
            "type_projet": "collectif", "stationnement": "aérien", "terrain": "libéré",
            "commerce": False,
        },
        "version_regles": {
            "insee": r.insee, "zone": r.zone,
            "hauteur_egout": regle_json(r.hauteur_egout), "hauteur_faitage": regle_json(r.hauteur_faitage),
            "emprise_ces": regle_json(r.emprise_ces), "recul_voie": regle_json(r.recul_voie),
            "recul_separatives": regle_json(r.recul_separatives), "pleine_terre": regle_json(r.pleine_terre),
            "mixite": {**regle_json(r.mixite), "seuil_m2": r.mixite_seuil_m2, "quota_pct": r.mixite_quota_pct},
            "stationnement_bareme": {
                "validee": r.stationnement.validee, "article": r.stationnement.article,
                "page_pdf": r.stationnement.page_pdf, "citation": r.stationnement.citation,
                "lignes": [{"pieces_min": a, "pieces_max": b, "places": c, "destination": d, "libelle": e}
                           for (a, b, c, d, e) in r.stationnement.lignes],
            },
        },
        "conventions": conv.source,
        "terrain": {
            "contenance_totale_m2": round(t.contenance_totale_m2, 1),
            "aire_dessin_m2": round(t.aire_dessin_m2, 1),
            "zone_implantation_m2": round(t.aire_zone_m2, 1),
            "has_voie": t.has_voie, "note_limites": t.note_limites,
            "contraintes": t.contraintes,
            "parcelles": [{"idu": p.idu, "numero": p.numero, "contenance_m2": p.contenance_m2,
                           "aire_dessin_m2": round(p.aire_dessin_m2, 1)} for p in t.parcelles],
            "assiette_coords_2975": _coords(t.assiette),
            "zone_implantation_coords_2975": _coords(t.zone_implantation),
            "voie_coords_2975": [list(g.coords) for g in t.voie_edges],
        },
        "scenario": {
            "forme": scenario.forme, "niveaux": scenario.niveaux,
            "statut_etude": scenario.statut,
        },
        "tableau_capacite": {
            "logements": cap.logements, "par_type": cap.par_type, "niveaux": cap.niveaux,
            "sdp_m2": cap.sdp_m2, "shab_estimee_m2": cap.shab_estimee_m2,
            "shab_par_type_m2": cap.shab_par_type_m2,
            "emprise_sol_m2": cap.emprise_sol_m2, "pleine_terre_m2": cap.pleine_terre_m2,
            "places": cap.places, "places_imposees": cap.places_imposees,
            "details_places": cap.details_places,
            "mixite_applicable": cap.mixite_applicable,
            "logements_aides_imposes": cap.logements_aides_imposes,
            "sdp_aidee_imposee_m2": cap.sdp_aidee_imposee_m2,
            "distribution_niveaux": cap.distribution_niveaux,
        },
        "controles_reglementaires": [
            {"nom": c.nom, "regle": c.regle, "mesure": c.mesure, "resultat": c.resultat,
             "citation": c.citation, "detail": c.detail} for c in scenario.controles
        ],
        "controles_geometriques": [
            {"nom": c.nom, "ok": c.ok, "detail": c.detail} for c in scenario.checks_geo
        ],
        "geometrie_objets": objets,
    }


def ecrire_scenario_json(scenario: Scenario, path: str | Path, *, genere_le: str | None = None) -> None:
    d = scenario_dict(scenario, genere_le=genere_le)
    Path(path).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
