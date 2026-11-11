"""GABARIT-3D-1 (pilote) — SCÈNE commune du Gabarit : le terrain réel, le bâti, deux coupes.

Une SCÈNE rassemble, en MÈTRES autour d'une origine locale (coin SW de la bbox parcelle,
EPSG:2975), tout ce dont la vue 3D ET le PDF ont besoin — ils lisent la MÊME scène :

  - le TERRAIN au fond LiDAR HD 1 m (``config.mnt1m_cog_file``) : fin (1 m) sur la parcelle
    et son accès, plus lâche (2 m) sur le voisinage ~150 m. Les lacunes (hors emprise) RESTENT
    des lacunes (``None``) ;
  - la LIMITE (contour cadastral), la ZONE D'IMPLANTATION, les reculs, les exclusions ;
  - les BÂTIMENTS à leur altitude, avec hauteur et PROVENANCE (mesurée LiDAR / estimée BD TOPO) ;
  - les VALEURS DES RÈGLES en données (reprises telles quelles du moteur — AUCUN chiffre changé) ;
  - deux COUPES automatiques (profil au pas de 1 m) : la plus grande pente ; la voie→parcelle
    par l'accès identifié. Chaque coupe s'interrompt au droit d'une lacune (pente comprise) ;
  - les MÉTADONNÉES (produit, pas, référentiel, acquisition, lacunes) + un IDENTIFIANT de scène.

Doctrine LABUSE : la scène n'INVENTE aucun chiffre réglementaire — elle lit le GabaritResult servi
par ``api.gabarit.gabarit_detail`` (mêmes nombres que l'écran/outil). Le relief vient du fond LiDAR,
un FAIT mesuré, jamais un calcul réglementaire. AUCUN plafond de hauteur n'est dessiné (mandat).
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from ..config import get_settings

# ── Fond d'altitudes (COG 1 m) ───────────────────────────────────────────────────────────────────

_NODATA = -9999.0


@lru_cache(maxsize=4)
def _open_cog(path: str, mtime: float):
    """Ouvre le COG (mis en cache par chemin+mtime). None si absent/illisible (dégradation)."""
    import rasterio
    try:
        return rasterio.open(path)
    except Exception:  # noqa: BLE001 — fond absent → scène en lacune, jamais une erreur
        return None


def _cog():
    p: Path = get_settings().mnt1m_cog_file
    if not p.exists():
        return None
    return _open_cog(str(p), p.stat().st_mtime)


def _z(v) -> Optional[float]:
    try:
        f = float(v)
    except Exception:  # noqa: BLE001
        return None
    if not math.isfinite(f) or f <= -1000.0:
        return None
    return round(f, 2)


def sample_points(pts_2975: list[tuple[float, float]]) -> list[Optional[float]]:
    """Altitude du fond aux points (x,y 2975). None = lacune (hors emprise / nodata)."""
    ds = _cog()
    if ds is None or not pts_2975:
        return [None] * len(pts_2975)
    out: list[Optional[float]] = []
    # ds.sample lève hors emprise selon la version → on garde None par repli point par point
    for v in ds.sample(pts_2975):
        out.append(_z(v[0]))
    return out


def sample_grid(minx: float, miny: float, maxx: float, maxy: float, pas: float) -> dict:
    """Grille d'altitudes au PAS donné sur [minx,maxx]×[miny,maxy] (2975), lue au fond 1 m.

    Renvoie {pas, ox, oy, nx, ny, z} : ``z`` est une liste ligne par ligne (du NORD au SUD),
    ``None`` pour chaque lacune. Centres de pixels : (ox + (i+0.5)·pas, oy - (j+0.5)·pas)."""
    nx = max(1, int(round((maxx - minx) / pas)))
    ny = max(1, int(round((maxy - miny) / pas)))
    xs = [minx + (i + 0.5) * pas for i in range(nx)]
    ys = [maxy - (j + 0.5) * pas for j in range(ny)]
    pts = [(x, y) for y in ys for x in xs]
    vals = sample_points(pts)
    return {"pas": pas, "ox": minx, "oy": maxy, "nx": nx, "ny": ny, "z": vals}


# ── Géométrie (4326 → 2975 → repère local) ───────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _tf_4326_2975():
    from pyproj import Transformer
    return Transformer.from_crs(4326, 2975, always_xy=True)


def _geom_2975(geojson: dict):
    """GeoJSON 4326 → shapely en 2975 (None si vide/illisible)."""
    if not geojson:
        return None
    from shapely.geometry import shape
    from shapely.ops import transform as shp_transform
    try:
        g = shape(geojson)
        if g.is_empty:
            return None
        tf = _tf_4326_2975()
        return shp_transform(lambda x, y, z=None: tf.transform(x, y), g)
    except Exception:  # noqa: BLE001
        return None


def _rings_local(geom, ox: float, oy: float) -> list[list[list[float]]]:
    """Anneaux extérieurs d'un (Multi)Polygon en repère local (x-ox, y-oy), arrondis au cm."""
    if geom is None or geom.is_empty:
        return []
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    out = []
    for p in polys:
        if p.is_empty:
            continue
        out.append([[round(x - ox, 2), round(y - oy, 2)] for x, y in p.exterior.coords])
    return out


# ── Axes de coupe ────────────────────────────────────────────────────────────────────────────────

def _axe_plus_grande_pente(ds, assiette, centroid) -> Optional[dict]:
    """Axe A-A' : plus grande pente. Ajuste un plan z=a·x+b·y+c aux pixels du fond SOUS la parcelle ;
    la descente la plus raide est -(a,b). Axe centré sur le centroïde, longueur = extension de la
    parcelle le long de cette direction (+ marge). None si le fond ne couvre pas la parcelle."""
    import numpy as np
    minx, miny, maxx, maxy = assiette.bounds
    g = sample_grid(minx, miny, maxx, maxy, 1.0)
    # reconstruit les points valides SOUS la parcelle
    xs, ys, zs = [], [], []
    from shapely.geometry import Point
    k = 0
    for j in range(g["ny"]):
        yy = g["oy"] - (j + 0.5) * g["pas"]
        for i in range(g["nx"]):
            xx = g["ox"] + (i + 0.5) * g["pas"]
            z = g["z"][k]; k += 1
            if z is not None and assiette.covers(Point(xx, yy)):
                xs.append(xx); ys.append(yy); zs.append(z)
    if len(zs) < 8:
        return None
    A = np.column_stack([np.array(xs) - centroid.x, np.array(ys) - centroid.y, np.ones(len(xs))])
    coef, *_ = np.linalg.lstsq(A, np.array(zs), rcond=None)
    a, b = float(coef[0]), float(coef[1])
    n = math.hypot(a, b)
    if n < 1e-6:          # terrain plat → direction par défaut (grand côté du rectangle minimal)
        mrr = list(assiette.minimum_rotated_rectangle.exterior.coords)[:4]
        vx, vy = mrr[1][0] - mrr[0][0], mrr[1][1] - mrr[0][1]
        n2 = math.hypot(vx, vy) or 1.0
        ux, uy = vx / n2, vy / n2
    else:
        ux, uy = -a / n, -b / n   # sens de la descente
    ds_proj = [((x - centroid.x) * ux + (y - centroid.y) * uy) for x, y in assiette.exterior.coords]
    dmin, dmax = min(ds_proj), max(ds_proj)
    ox, oy = centroid.x + ux * dmin, centroid.y + uy * dmin
    return {"ox": ox, "oy": oy, "ux": ux, "uy": uy, "L": dmax - dmin, "pente_plan_pct": round(n * 100, 1)}


def _axe_acces(db, idu: str, assiette):
    """Axe B-B' : voie → parcelle, par l'accès identifié. Réutilise la classification des voies
    nommées et l'axe perpendiculaire de ``implantation.contexte`` (le même que la planche plan-masse).
    Étendu de ~25 m côté voie pour que la coupe DÉMARRE sur la chaussée. (voie, axe) ou (None, None)."""
    from ..implantation import contexte as ctx
    voies = ctx._voies(db, assiette.wkt)
    voie_edges = [v.geom_2975 for v in voies] or None
    axe = ctx._axe_coupe(assiette, voie_edges)
    if axe is None:
        return None, None
    if voie_edges:   # recule l'origine de 25 m vers la voie (hors parcelle) pour partir de la chaussée
        recul = 25.0
        axe = {**axe, "ox": axe["ox"] - axe["ux"] * recul, "oy": axe["oy"] - axe["uy"] * recul,
               "L": axe["L"] + recul}
    voie_nom = voies[0].nom if voies else None
    return voie_nom, axe


# ── Coupe (profil + annotations) ──────────────────────────────────────────────────────────────────

def _segments_valides(profil: list[dict]) -> list[list[dict]]:
    """Découpe le profil en RUNS continus séparés par les lacunes (pour pente/dénivelé par morceau)."""
    runs, cur = [], []
    for p in profil:
        if p["z"] is None:
            if cur:
                runs.append(cur); cur = []
        else:
            cur.append(p)
    if cur:
        runs.append(cur)
    return runs


def _stats_coupe(profil: list[dict]) -> dict:
    """Dénivelé/pente par morceaux (la lacune INTERROMPT le calcul). Altitudes extrêmes sur le valide."""
    runs = _segments_valides(profil)
    dpos = dneg = dist_valide = 0.0
    pente_max = 0.0
    alts = []
    for run in runs:
        alts += [p["z"] for p in run]
        for a, b in zip(run, run[1:]):
            dd = b["d"] - a["d"]
            if dd <= 0:
                continue
            dh = b["z"] - a["z"]
            if dh >= 0:
                dpos += dh
            else:
                dneg += -dh
            dist_valide += dd
            s = abs(dh) / dd
            pente_max = max(pente_max, s)
    if not alts:
        return {"disponible": False}
    return {
        "disponible": True,
        "altitude_min_m": round(min(alts), 2),
        "altitude_max_m": round(max(alts), 2),
        "denivele_m": round(max(alts) - min(alts), 2),
        "denivele_positif_m": round(dpos, 2),
        "denivele_negatif_m": round(dneg, 2),
        "pente_moyenne_pct": round((dpos + dneg) / dist_valide * 100, 1) if dist_valide > 0 else 0.0,
        "pente_max_pct": round(pente_max * 100, 1),
        "n_lacune": sum(1 for p in profil if p["z"] is None),
    }


def _spans(ligne, geom) -> list[list[float]]:
    """Intervalles [d0,d1] où la ligne (LineString, d=distance depuis son origine) traverse `geom`."""
    if geom is None or geom.is_empty:
        return []
    try:
        inter = ligne.intersection(geom)
    except Exception:  # noqa: BLE001
        return []
    if inter.is_empty:
        return []
    parts = list(inter.geoms) if inter.geom_type.startswith("Multi") or inter.geom_type == "GeometryCollection" else [inter]
    out = []
    for part in parts:
        if part.geom_type != "LineString" or part.is_empty:
            continue
        cs = list(part.coords)
        ds = [ligne.project(_pt(c)) for c in (cs[0], cs[-1])]
        out.append([round(min(ds), 2), round(max(ds), 2)])
    return sorted(out)


def _pt(c):
    from shapely.geometry import Point
    return Point(c[0], c[1])


def _construire_coupe(axe: dict, assiette, zone, batis_2975: list[dict], label: str,
                      titre: str, voie_nom: Optional[str]) -> dict:
    """Profil au pas 1 m le long de l'axe + annotations (limites, zone, bâtiments coupés, cotes)."""
    from shapely.geometry import LineString
    ox, oy, ux, uy, L = axe["ox"], axe["oy"], axe["ux"], axe["uy"], axe["L"]
    n = max(2, int(round(L)) + 1)
    pts = [(ox + ux * (L * i / (n - 1)), oy + uy * (L * i / (n - 1))) for i in range(n)]
    zs = sample_points(pts)
    profil = [{"d": round(L * i / (n - 1), 2), "z": zs[i]} for i in range(n)]
    ligne = LineString([(ox, oy), (ox + ux * L, oy + uy * L)])
    # bâtiments coupés : intervalle traversé + hauteur + provenance + altitude de base
    batis_coupes = []
    for b in batis_2975:
        sp = _spans(ligne, b["geom"])
        for d0, d1 in sp:
            batis_coupes.append({"d0": d0, "d1": d1, "hauteur_m": b["hauteur_m"],
                                 "provenance": b["provenance"], "base_alt_m": b["base_alt_m"]})
    return {
        "label": label, "titre": titre, "voie": voie_nom,
        "longueur_m": round(L, 2),
        "origine_2975": [round(ox, 2), round(oy, 2)],
        "direction": [round(ux, 6), round(uy, 6)],
        "profil": profil,
        "limites_parcelle_d": _spans(ligne, assiette),
        "zone_implantation_d": _spans(ligne, zone),
        "batiments": batis_coupes,
        "cotes": _stats_coupe(profil),
    }


# ── Scène ─────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class Scene:
    idu: str
    scene_id: str
    disponible: bool
    origine_2975: list[float] = field(default_factory=list)
    crs: str = "EPSG:2975"
    parcelle: list = field(default_factory=list)
    zone_implantation: list = field(default_factory=list)
    reculs: list = field(default_factory=list)
    exclusions: list = field(default_factory=list)
    batiments: list = field(default_factory=list)
    terrain: dict = field(default_factory=dict)
    regles: dict = field(default_factory=dict)
    coupes: list = field(default_factory=list)
    axes_plan: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    message: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def _fond_meta() -> dict:
    p = get_settings().mnt1m_cog_file
    mp = p.with_suffix(".meta.json")
    base = {"produit": "LiDAR HD MNT 1 m (IGN)", "resolution_m": 1.0,
            "referentiel_plani": "RGR92 / UTM 40 Sud (EPSG:2975)",
            "referentiel_alti": "REUN89 (IGN 1989)", "nodata": _NODATA,
            "disponible": p.exists()}
    if mp.exists():
        try:
            d = json.loads(mp.read_text())
            base.update({"acquisition": d.get("fenetres"), "octets": d.get("taille_octets"),
                         "couche_wms": d.get("couche_wms")})
        except Exception:  # noqa: BLE001
            pass
    return base


def _batiments(gr, ox: float, oy: float) -> list[dict]:
    """Bâtiments existants → empreinte locale + hauteur + provenance (mesurée/estimée) + altitude de base."""
    fc = getattr(gr, "batiExistantGeoJSON", None)
    out = []
    if not isinstance(fc, dict):
        return out
    for f in fc.get("features", []):
        g2975 = _geom_2975(f.get("geometry"))
        if g2975 is None:
            continue
        props = f.get("properties") or {}
        h = props.get("hauteur_m")
        src = props.get("h_source")
        prov = "mesurée" if src == "lidar" else ("estimée" if src == "bdtopo" else "inconnue")
        c = g2975.centroid
        base = sample_points([(c.x, c.y)])[0]
        out.append({
            "geom": g2975,   # shapely 2975 (interne, retiré avant JSON)
            "empreinte": _rings_local(g2975, ox, oy),
            "hauteur_m": float(h) if isinstance(h, (int, float)) else None,
            "provenance": prov,
            "base_alt_m": base,
        })
    return out


def _regles_servies(gr) -> dict:
    """Valeurs réglementaires EN DONNÉES — reprises telles quelles du moteur (aucun chiffre changé)."""
    def src(s):
        if s is None:
            return None
        return {k: getattr(s, k, None) for k in ("document", "zone", "article", "versionDate", "provider")}
    return {
        "surfaceParcelleM2": gr.surfaceParcelleM2,
        "zoneImplantationM2": gr.zoneImplantationM2,
        "batiDeduitM2": gr.batiDeduitM2,
        "plafondEmpriseM2": gr.plafondEmpriseM2,
        "plafondEmpriseStatus": gr.plafondEmpriseStatus,
        "hauteurReglementaireM": gr.hauteurReglementaireM,
        "hauteurBase": gr.hauteurBase,
        "hauteurEstimee": gr.hauteurEstimee,
        "hauteurStatus": gr.hauteurStatus,
        "appliquees": [{"label": r.label, "value": r.value, "unit": r.unit,
                        "detail": r.detail, "source": src(r.source)} for r in (gr.appliedRules or [])],
    }


def _scene_id(idu: str, gr, fond_meta: dict) -> str:
    """Identifiant STABLE : parcelle + nombres servis + signature du fond (change si l'un change)."""
    sig = json.dumps({"idu": idu, "r": _regles_servies(gr), "f": fond_meta.get("octets")},
                     sort_keys=True, default=str)
    return hashlib.sha1(sig.encode()).hexdigest()[:12]


def build_scene(db, idu: str) -> Scene:
    """Construit la scène d'une parcelle. Lit le GabaritResult SERVI (chiffres identiques) + le fond 1 m.

    Dégradation : si le gabarit n'est pas calculable (incomplete/inconstructible) ou si le fond ne
    couvre pas la parcelle, la scène le DIT (``disponible``, ``message``) et sert ce qui existe."""
    from ..api.gabarit import gabarit_detail  # lazy — évite l'import circulaire
    gr = gabarit_detail(idu, db)
    fond_meta = _fond_meta()
    sid = _scene_id(idu, gr, fond_meta)

    contour = _geom_2975(getattr(gr, "contourGeoJSON", None))
    if contour is None:
        return Scene(idu=idu, scene_id=sid, disponible=False, meta=fond_meta,
                     message=gr.message or "Parcelle sans contour exploitable.")
    minx, miny, maxx, maxy = contour.bounds
    ox, oy = math.floor(minx), math.floor(miny)
    centroid = contour.centroid

    zone = _geom_2975(getattr(gr, "zoneImplantationGeoJSON", None))
    reculs = _geom_2975(getattr(gr, "retraitsGeoJSON", None))
    excl = _geom_2975(getattr(gr, "exclusionsGeoJSON", None))
    batis = _batiments(gr, ox, oy)

    # terrain : 1 m sur parcelle+accès (bbox élargie 20 m), 2 m sur le voisinage ~150 m
    g_parcelle = sample_grid(minx - 20, miny - 20, maxx + 20, maxy + 20, 1.0)
    g_voisinage = sample_grid(centroid.x - 150, centroid.y - 150, centroid.x + 150, centroid.y + 150, 2.0)
    for g in (g_parcelle, g_voisinage):   # origine en repère local
        g["ox"] = round(g["ox"] - ox, 2); g["oy"] = round(g["oy"] - oy, 2)

    # axes + coupes (si le fond couvre la parcelle)
    ds = _cog()
    coupes, axes_plan = [], {}
    if ds is not None:
        ax_pente = _axe_plus_grande_pente(ds, contour, centroid)
        voie_nom, ax_acces = _axe_acces(db, idu, contour)
        if ax_pente:
            coupes.append(_construire_coupe(ax_pente, contour, zone, batis, "A",
                                            "Coupe A-A' — plus grande pente", None))
            axes_plan["A"] = _axe_plan(ax_pente, ox, oy)
        if ax_acces:
            coupes.append(_construire_coupe(ax_acces, contour, zone, batis, "B",
                                            "Coupe B-B' — voie vers parcelle (accès)", voie_nom))
            axes_plan["B"] = _axe_plan(ax_acces, ox, oy)

    for b in batis:   # retire la géométrie shapely interne avant sérialisation
        b.pop("geom", None)

    return Scene(
        idu=idu, scene_id=sid, disponible=True, origine_2975=[ox, oy],
        parcelle=_rings_local(contour, ox, oy),
        zone_implantation=_rings_local(zone, ox, oy),
        reculs=_rings_local(reculs, ox, oy),
        exclusions=_rings_local(excl, ox, oy),
        batiments=batis,
        terrain={"parcelle_1m": g_parcelle, "voisinage_2m": g_voisinage},
        regles=_regles_servies(gr),
        coupes=coupes,
        axes_plan=axes_plan,
        meta=fond_meta,
    )


def _axe_plan(axe: dict, ox: float, oy: float) -> dict:
    """Trace de l'axe en repère local (pour le reporter sur le plan)."""
    a = (axe["ox"] - ox, axe["oy"] - oy)
    b = (axe["ox"] + axe["ux"] * axe["L"] - ox, axe["oy"] + axe["uy"] * axe["L"] - oy)
    return {"p0": [round(a[0], 2), round(a[1], 2)], "p1": [round(b[0], 2), round(b[1], 2)]}
