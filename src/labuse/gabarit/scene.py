"""GABARIT-3D-1 (pilote) — SCÈNE commune du Gabarit : le terrain réel, le bâti, deux coupes.

Verrous Astra (étape 1 ter) :
  - LECTURE DU FOND calée sur ses PIXELS NATIFS (``charger_surface`` snappe la fenêtre sur la grille
    native) → une même cote est identique entre deux cadrages.
  - UN SEUL MAILLAGE triangulé côté serveur (``terrain_mesh.TerrainMesh``, 1 m sur la parcelle / 2 m sur
    le voisinage). Les coupes sont l'INTERSECTION avec ces faces — celles que la visionneuse affiche.
  - Scène construite UNE FOIS (mémo), lue par la visionneuse, les coupes et l'export ; l'identifiant
    change dès qu'un contenu change ; une coupe impossible laisse le plan et le terrain accessibles ;
    « disponible » seulement si la PARCELLE elle-même est couverte.
  - BÂTI : hauteur null quand non attribuée (plus de défaut arbitraire) ; volume schématique de
    contexte (pied conventionnel = médiane des altitudes valides hors façades, dessus horizontal), sans
    cote de toiture. La règle « une seule emprise » est retirée.

Doctrine LABUSE : la scène n'invente aucun chiffre réglementaire — elle lit le GabaritResult servi par
``api.gabarit.gabarit_detail``. AUCUN plafond de hauteur n'est dessiné.
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
from .terrain_mesh import TerrainMesh

_NODATA = -9999.0
_PENTE_FENETRE_M = 5.0
_MARGE_FACES_1M = 25.0          # rayon des faces 1 m autour de la parcelle (le reste en 2 m)


# ── Fond : lecture calée sur les pixels natifs ────────────────────────────────────────────────────

@lru_cache(maxsize=4)
def _open_cog(path: str, mtime: float):
    import rasterio
    try:
        return rasterio.open(path)
    except Exception:  # noqa: BLE001
        return None


def _cog():
    p: Path = get_settings().mnt1m_cog_file
    if not p.exists():
        return None
    return _open_cog(str(p), p.stat().st_mtime)


def _valide(f) -> Optional[float]:
    try:
        f = float(f)
    except Exception:  # noqa: BLE001
        return None
    return None if (not math.isfinite(f) or f <= -1000.0) else f


class _Surface:
    """Fenêtre NATIVE du MNT (tableau + géoréférence), source du maillage et de la couverture."""

    def __init__(self, arr, ox: float, oy: float, pas: float):
        import numpy as np
        self.a = np.asarray(arr, dtype="float64")
        self.a[(self.a <= -1000.0) | ~np.isfinite(self.a)] = np.nan
        self.ox, self.oy, self.pas = ox, oy, pas
        self.ny, self.nx = self.a.shape


def charger_surface(minx: float, miny: float, maxx: float, maxy: float,
                    marge: float = 170.0) -> Optional[_Surface]:
    """Lit la fenêtre du MNT couvrant [minx,maxx]×[miny,maxy] + marge, SNAPPÉE sur les pixels natifs
    (décalages entiers) → l'altitude en un point ne dépend PAS du cadrage de la fenêtre."""
    ds = _cog()
    if ds is None:
        return None
    from rasterio.windows import Window
    try:
        r0, c0 = ds.index(minx - marge, maxy + marge, op=math.floor)   # coin haut-gauche (pixel entier)
        r1, c1 = ds.index(maxx + marge, miny - marge, op=math.ceil)    # coin bas-droit
        row_off, col_off = min(r0, r1), min(c0, c1)
        h, w = abs(r1 - r0) + 1, abs(c1 - c0) + 1
        win = Window(col_off, row_off, w, h)
        arr = ds.read(1, window=win, boundless=True, fill_value=_NODATA)
        tr = ds.window_transform(win)                                  # aligné sur la grille native
        return _Surface(arr, tr.c, tr.f, tr.a)
    except Exception:  # noqa: BLE001
        return None


def sample_points(pts_2975: list[tuple[float, float]]) -> list[Optional[float]]:
    """Altitude ponctuelle (plus proche pixel) — contrôles/cotes isolées."""
    ds = _cog()
    if ds is None or not pts_2975:
        return [None] * len(pts_2975)
    out = []
    for v in ds.sample(pts_2975):
        z = _valide(v[0])
        out.append(round(z, 2) if z is not None else None)
    return out


class _Sampler:
    """Échantillonne le maillage UNIQUE à 1 m, borné à `bounds` (parcelle + abords). C'est EXACTEMENT
    la surface servie à la visionneuse (plus de maillage 2 m : aucune surface superposée)."""

    def __init__(self, surf: _Surface, bounds):
        self.m = TerrainMesh(surf.a, surf.ox, surf.oy, surf.pas, step=1)
        self.b = bounds

    def altitude(self, x: float, y: float) -> Optional[float]:
        if not (self.b[0] <= x <= self.b[2] and self.b[1] <= y <= self.b[3]):
            return None
        return self.m.altitude(x, y)

    def profil(self, ox, oy, ux, uy, L) -> list[dict]:
        """Profil par FRANCHISSEMENT des faces (pas d'échantillonnage au mètre), borné. z NON arrondi
        (arrondi à l'affichage seulement) : une crête de 40,00 m ressort à 40,00 m."""
        return [{"d": p["d"], "z": self.altitude(ox + ux * p["d"], oy + uy * p["d"])}
                for p in self.m.profil(ox, oy, ux, uy, L)]


# ── Géométrie ─────────────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _tf_4326_2975():
    from pyproj import Transformer
    return Transformer.from_crs(4326, 2975, always_xy=True)


def _geom_2975(geojson: Optional[dict]):
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


def _polys_local(geom, ox: float, oy: float) -> list[dict]:
    """(Multi)Polygon → polygones {ext, trous} en repère local (trous + parties multiples CONSERVÉS)."""
    if geom is None or geom.is_empty:
        return []
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    out = []
    for p in polys:
        if p.is_empty or p.geom_type != "Polygon":
            continue
        ext = [[round(x - ox, 2), round(y - oy, 2)] for x, y in p.exterior.coords]
        trous = [[[round(x - ox, 2), round(y - oy, 2)] for x, y in r.coords] for r in p.interiors]
        out.append({"ext": ext, "trous": trous})
    return out


def _cadastre_2975(db, idu: str):
    from sqlalchemy import text
    from shapely import wkt as shp_wkt
    try:
        w = db.execute(text("SELECT ST_AsText(geom_2975) FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        g = shp_wkt.loads(w) if w else None
        return g if (g is not None and not g.is_empty) else None
    except Exception:  # noqa: BLE001
        return None


def _couverture_parcelle(sampler, assiette) -> float:
    """Fraction de points INTÉRIEURS à la parcelle (y compris multi-morceaux) couverts par le fond."""
    from shapely.geometry import Point
    minx, miny, maxx, maxy = assiette.bounds
    pas = 2.0
    tot = ok = 0
    y = miny + pas / 2
    while y < maxy:
        x = minx + pas / 2
        while x < maxx:
            if assiette.covers(Point(x, y)):
                tot += 1
                if sampler.altitude(x, y) is not None:
                    ok += 1
            x += pas
        y += pas
    return round(ok / tot, 3) if tot else 0.0


# ── Axes ──────────────────────────────────────────────────────────────────────────────────────────

def _axe_pente_dominante(sampler, assiette, centroid) -> Optional[dict]:
    import numpy as np
    from shapely.geometry import Point
    minx, miny, maxx, maxy = assiette.bounds
    xs, ys, zs = [], [], []
    y = miny + 0.5
    while y < maxy:
        x = minx + 0.5
        while x < maxx:
            z = sampler.altitude(x, y)
            if z is not None and assiette.covers(Point(x, y)):
                xs.append(x); ys.append(y); zs.append(z)
            x += 1.0
        y += 1.0
    if len(zs) < 8:
        return None
    A = np.column_stack([np.array(xs) - centroid.x, np.array(ys) - centroid.y, np.ones(len(xs))])
    coef, *_ = np.linalg.lstsq(A, np.array(zs), rcond=None)
    a, b = float(coef[0]), float(coef[1])
    n = math.hypot(a, b)
    if n < 1e-6:
        mrr = list(assiette.minimum_rotated_rectangle.exterior.coords)[:4]
        vx, vy = mrr[1][0] - mrr[0][0], mrr[1][1] - mrr[0][1]
        nn = math.hypot(vx, vy) or 1.0
        ux, uy = vx / nn, vy / nn
    else:
        ux, uy = -a / n, -b / n
    proj = [((x - centroid.x) * ux + (y - centroid.y) * uy) for x, y in assiette.exterior.coords]
    return {"ox": centroid.x + ux * min(proj), "oy": centroid.y + uy * min(proj), "ux": ux, "uy": uy,
            "L": max(proj) - min(proj), "pente_plan_pct": round(n * 100, 1)}


def _axe_voie(db, idu: str, assiette):
    from shapely.geometry import LineString
    from ..implantation import contexte as ctx
    voies = ctx._voies(db, assiette.wkt)
    voie_edges = [v.geom_2975 for v in voies] or None
    axe = ctx._axe_coupe(assiette, voie_edges)
    if axe is None:
        return None, None
    recul = 25.0
    axe = {**axe, "ox": axe["ox"] - axe["ux"] * recul, "oy": axe["oy"] - axe["uy"] * recul,
           "L": axe["L"] + recul}
    ligne = LineString([(axe["ox"], axe["oy"]),
                        (axe["ox"] + axe["ux"] * axe["L"], axe["oy"] + axe["uy"] * axe["L"])])
    inter_d, voie_geom, voie_nom = None, None, None
    for v in voies:
        try:
            it = ligne.intersection(v.geom_2975)
        except Exception:  # noqa: BLE001
            continue
        if it.is_empty:
            continue
        pt = it if it.geom_type == "Point" else (list(it.geoms)[0] if hasattr(it, "geoms") else it.centroid)
        inter_d, voie_geom, voie_nom = round(ligne.project(pt), 2), v.geom_2975, v.nom
        break
    if inter_d is not None:
        voie = {"nom": voie_nom, "etablie": True, "intersection_d": inter_d,
                "statut": "accès présumé (intersection de voie vérifiée)", "geom": voie_geom,
                "point_local": None}   # rempli plus tard
    else:
        voie = {"nom": None, "etablie": False, "intersection_d": None,
                "statut": "coupe orientée vers la voie (intersection non établie)", "geom": None,
                "point_local": None}
    return axe, voie


# ── Bâti (modèle de contexte) ─────────────────────────────────────────────────────────────────────

def _pied_conventionnel(sampler, geom) -> Optional[float]:
    """Pied conventionnel = médiane des altitudes valides juste HORS des façades (anneau à ~1 m)."""
    try:
        anneau = geom.buffer(1.0).exterior
    except Exception:  # noqa: BLE001
        return None
    import numpy as np
    L = anneau.length
    n = max(8, int(L / 2))
    zs = []
    for i in range(n):
        p = anneau.interpolate(i / n, normalized=True)
        z = sampler.altitude(p.x, p.y)
        if z is not None:
            zs.append(z)
    return round(float(np.median(zs)), 2) if zs else None


def _batiments(gr, sampler, ox: float, oy: float) -> list[dict]:
    """Bâti existant (étape 2 bis). La hauteur du VOLUME est PROPRE au bâtiment (BD TOPO) si elle existe ;
    sinon CONTOUR seul. Plus de hauteur de PARCELLE (faîtage LiDAR) recopiée sur chaque emprise. Le volume
    n'est dessiné que si pied ET hauteur sont connus (sinon emprise seule). Trous conservés ; la même
    transformation sert l'emprise (plan) et le volume (3D)."""
    fc = getattr(gr, "batiExistantGeoJSON", None)
    out = []
    if not isinstance(fc, dict):
        return out
    for f in fc.get("features", []):
        g2975 = _geom_2975(f.get("geometry"))
        if g2975 is None:
            continue
        props = f.get("properties") or {}
        hb = props.get("hauteur_bdtopo_m")
        hauteur = float(hb) if isinstance(hb, (int, float)) and hb > 0 else None   # BD TOPO, par bâtiment
        pied = _pied_conventionnel(sampler, g2975) if sampler else None
        volume = hauteur is not None and pied is not None
        out.append({
            "geom": g2975,
            "empreinte": _polys_local(g2975, ox, oy),     # trous conservés
            "pied_m": pied,
            "hauteur_m": hauteur if volume else None,     # hauteur propre au bâtiment, sinon null → contour seul
            "attribution": "bdtopo" if volume else None,
            "volume": volume,
        })
    return out


# ── Coupe ─────────────────────────────────────────────────────────────────────────────────────────

def _runs(profil):
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


def _pt(c):
    from shapely.geometry import Point
    return Point(c[0], c[1])


def _spans(ligne, geom) -> list[list[float]]:
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


def _z_interp(profil, d) -> Optional[float]:
    for run in _runs(profil):
        if run[0]["d"] - 1e-6 <= d <= run[-1]["d"] + 1e-6:
            for a, b in zip(run, run[1:]):
                if a["d"] <= d <= b["d"] and b["d"] > a["d"]:
                    t = (d - a["d"]) / (b["d"] - a["d"])
                    return round(a["z"] + t * (b["z"] - a["z"]), 2)
            return run[min(range(len(run)), key=lambda i: abs(run[i]["d"] - d))]["z"]
    return None


def _continu(profil, d0: float, d1: float) -> bool:
    """Le profil est-il continu (aucune lacune) entre d0 et d1 ?"""
    lo, hi = min(d0, d1), max(d0, d1)
    return all(p["z"] is not None for p in profil if lo - 1e-6 <= p["d"] <= hi + 1e-6)


def _batiment_coupe(sampler, ligne, axe, b) -> list[dict]:
    """Un bâtiment traversé → segments ; terrain coté aux DEUX façades (amont/aval) si dispo. Au pied
    du bâti, on compare DEUX coupes parallèles légèrement décalées (±1,5 m perpendiculaire) : `supporte`
    = les appuis existent des deux côtés sur toute l'emprise (sinon la portion sera interrompue)."""
    ox, oy, ux, uy = axe["ox"], axe["oy"], axe["ux"], axe["uy"]
    px, py = -uy, ux                                       # perpendiculaire à l'axe
    out = []
    for d0, d1 in _spans(ligne, b["geom"]):
        fa = sampler.altitude(ox + ux * d0, oy + uy * d0)
        fv = sampler.altitude(ox + ux * d1, oy + uy * d1)
        appuis = True
        for off in (-1.5, 1.5):
            for k in range(5):
                d = d0 + (d1 - d0) * k / 4
                if sampler.altitude(ox + ux * d + px * off, oy + uy * d + py * off) is None:
                    appuis = False
        out.append({"d0": d0, "d1": d1, "facade_amont_m": None if fa is None else round(fa, 2),
                    "facade_aval_m": None if fv is None else round(fv, 2),
                    "pied_m": b["pied_m"], "hauteur_m": b["hauteur_m"], "attribution": b["attribution"],
                    "appuis": appuis})
    return out


def _indicateurs(profil, parcelle_spans, bati_spans, voie) -> dict:
    """Pente entre limites (signée) + amplitude séparément ; pente max sur 5 m ENTIERS dans un seul
    tronçon valide, dans la parcelle, HORS emprise bâtie élargie de 1 m, deux bornes exposées ;
    pente d'accès seulement si le profil est continu de la voie à la limite."""
    traversees = []
    for d0, d1 in parcelle_spans:
        dans = [{"d": p["d"], "z": p["z"]} for p in profil if d0 - 1e-6 <= p["d"] <= d1 + 1e-6]
        for run in _runs(dans):
            if len(run) < 2:
                continue
            dz, dd = run[-1]["z"] - run[0]["z"], run[-1]["d"] - run[0]["d"]
            alts = [p["z"] for p in run]
            traversees.append({"d0": round(run[0]["d"], 2), "d1": round(run[-1]["d"], 2),
                               "pente_pct": round(100 * dz / dd, 1) if dd > 0 else None,
                               "sens": "montée" if dz > 0.05 else ("descente" if dz < -0.05 else "plat"),
                               "amplitude_m": round(max(alts) - min(alts), 2)})
    # pente max sur 5 m ENTIERS (fenêtre en DISTANCE ; profil à pas irrégulier après franchissement)
    def _dans(d, spans):
        return any(a - 1e-6 <= d <= b + 1e-6 for a, b in spans)
    bati_elargi = [[a - 1.0, b + 1.0] for a, b in bati_spans]
    W = _PENTE_FENETRE_M
    runs = [(r[0]["d"], r[-1]["d"]) for r in _runs(profil)]   # tronçons continus couverts
    pmax = {"disponible": False}
    for i, pi in enumerate(profil):
        d0, zi = pi["d"], pi["z"]
        d1 = d0 + W
        if zi is None or d1 > profil[-1]["d"] + 1e-6:
            continue
        if not any(a - 1e-6 <= d0 and d1 <= b + 1e-6 for a, b in runs):   # ENTIÈREMENT dans UN tronçon
            continue
        fenetre = [p for p in profil if d0 - 1e-6 <= p["d"] <= d1 + 1e-6]
        if any(p["z"] is None for p in fenetre):          # 5 m entiers valides
            continue
        if not (_dans(d0, parcelle_spans) and _dans(d1, parcelle_spans)):
            continue
        if any(_dans(p["d"], bati_elargi) for p in fenetre):   # hors emprise bâtie ±1 m
            continue
        z1 = _z_interp(profil, d1)
        if z1 is None:
            continue
        s = abs(z1 - zi) / W
        if not pmax.get("disponible") or s > pmax["pente_pct"] / 100:
            pmax = {"disponible": True, "pente_pct": round(s * 100, 1),
                    "d0": round(d0, 2), "d1": round(d1, 2)}
    pente_acces = None
    if voie and voie.get("etablie") and parcelle_spans:
        d_voie = voie["intersection_d"]
        d_entree = min(s[0] for s in parcelle_spans)
        if _continu(profil, d_voie, d_entree):            # profil continu sur tout le trajet
            za, zb = _z_interp(profil, d_voie), _z_interp(profil, d_entree)
            if za is not None and zb is not None and abs(d_entree - d_voie) > 1e-6:
                pente_acces = round(100 * (zb - za) / (d_entree - d_voie), 1)
    return {"traversees": traversees, "pente_max_5m": pmax, "pente_acces_pct": pente_acces}


def _cotes_points(profil, parcelle_spans, batiments, voie) -> dict:
    """Points VÉRIFIÉS (décimètre) : voie si établie, chaque limite, haut/bas, façades amont/aval.
    UNE SEULE cote par point (dédupliquée au décimètre de distance)."""
    pts = []

    def add(d, role):
        z = _z_interp(profil, d)
        if z is not None:
            pts.append({"d": round(d, 1), "z": z, "role": role})
    if voie and voie.get("etablie"):
        add(voie["intersection_d"], "voie")
    for d0, d1 in parcelle_spans:
        add(d0, "limite"); add(d1, "limite")
    dans = [p for p in profil if p["z"] is not None
            and any(a - 1e-6 <= p["d"] <= b + 1e-6 for a, b in parcelle_spans)]
    if dans:
        hi, lo = max(dans, key=lambda p: p["z"]), min(dans, key=lambda p: p["z"])
        pts.append({"d": round(hi["d"], 1), "z": hi["z"], "role": "haut"})
        pts.append({"d": round(lo["d"], 1), "z": lo["z"], "role": "bas"})
    for b in batiments:
        if b.get("facade_amont_m") is not None:
            pts.append({"d": round(b["d0"], 1), "z": b["facade_amont_m"], "role": "facade"})
        if b.get("facade_aval_m") is not None:
            pts.append({"d": round(b["d1"], 1), "z": b["facade_aval_m"], "role": "facade"})
    # une seule cote par point (priorité : voie > limite > façade > haut/bas)
    rang = {"voie": 0, "limite": 1, "facade": 2, "haut": 3, "bas": 3}
    best = {}
    for p in pts:
        k = p["d"]
        if k not in best or rang[p["role"]] < rang[best[k]["role"]]:
            best[k] = p
    return {"points": sorted(best.values(), key=lambda p: p["d"])}


def _stats_coupe(profil) -> dict:
    alts = [p["z"] for p in profil if p["z"] is not None]
    if not alts:
        return {"disponible": False}
    return {"disponible": True, "altitude_min_m": round(min(alts), 2), "altitude_max_m": round(max(alts), 2),
            "amplitude_m": round(max(alts) - min(alts), 2),
            "n_lacune": sum(1 for p in profil if p["z"] is None),
            "couverture": round(len(alts) / len(profil), 3)}


def _construire_coupe(sampler, axe, cadastre, zone, batis, label, titre, voie) -> dict:
    from shapely.geometry import LineString
    ox, oy, ux, uy, L = axe["ox"], axe["oy"], axe["ux"], axe["uy"], axe["L"]
    profil = sampler.profil(ox, oy, ux, uy, L)   # franchissement des faces (A2)
    ligne = LineString([(ox, oy), (ox + ux * L, oy + uy * L)])
    parcelle_spans = _spans(ligne, cadastre)
    bati_coupes = [c for b in batis for c in _batiment_coupe(sampler, ligne, axe, b)]
    bati_spans = [[c["d0"], c["d1"]] for c in bati_coupes]
    return {
        "label": label, "titre": titre,
        "voie": {k: v for k, v in (voie or {}).items() if k != "geom"} if voie else None,
        "longueur_m": round(L, 2), "origine_2975": [round(ox, 2), round(oy, 2)],
        "direction": [round(ux, 6), round(uy, 6)],
        "profil": profil, "limites_parcelle_d": parcelle_spans, "zone_implantation_d": _spans(ligne, zone),
        "batiments": bati_coupes,
        "indicateurs": _indicateurs(profil, parcelle_spans, bati_spans, voie),
        "cotes": _stats_coupe(profil),
        "cotes_points": _cotes_points(profil, parcelle_spans, bati_coupes, voie),
        "zone_presente": bool(zone is not None and not zone.is_empty),
    }


# ── Scène ─────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class Scene:
    idu: str
    scene_id: str
    etat: dict = field(default_factory=dict)
    disponible: bool = False
    adresse: Optional[str] = None
    origine_2975: list[float] = field(default_factory=list)
    crs: str = "EPSG:2975"
    contour_cadastral: list = field(default_factory=list)
    contour_gabarit: list = field(default_factory=list)
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
            "referentiel_alti": "REUN89 (IGN 1989)", "nodata": _NODATA, "disponible": p.exists(),
            "acquisition_date": None}
    if mp.exists():
        try:
            d = json.loads(mp.read_text())
            base.update({"acquisition": d.get("fenetres"), "octets": d.get("taille_octets"),
                         "couche_wms": d.get("couche_wms"), "version_fond": d.get("taille_octets")})
            miss = [m for w in (d.get("fenetres") or []) for m in (w.get("missions") or [])]
            if miss:
                base["acquisition_date"] = miss[0].get("fin") or miss[0].get("debut")
        except Exception:  # noqa: BLE001
            pass
    return base


def _adresse(db, idu: str) -> Optional[str]:
    from sqlalchemy import text
    try:
        r = db.execute(text(
            "SELECT numero, voie FROM adresses WHERE idu=:i AND voie IS NOT NULL "
            "ORDER BY (numero ~ '^[0-9]') DESC LIMIT 1"), {"i": idu}).first()
        if r:
            return " ".join(x for x in (str(r[0] or "").strip(), str(r[1] or "").strip()) if x) or None
    except Exception:  # noqa: BLE001
        return None
    return None


def _regles_servies(gr) -> dict:
    def src(s):
        return None if s is None else {k: getattr(s, k, None)
                                       for k in ("document", "zone", "article", "versionDate", "provider")}
    return {"surfaceParcelleM2": gr.surfaceParcelleM2, "zoneImplantationM2": gr.zoneImplantationM2,
            "batiDeduitM2": gr.batiDeduitM2, "plafondEmpriseM2": gr.plafondEmpriseM2,
            "plafondEmpriseStatus": gr.plafondEmpriseStatus, "hauteurReglementaireM": gr.hauteurReglementaireM,
            "hauteurBase": gr.hauteurBase, "hauteurEstimee": gr.hauteurEstimee, "hauteurStatus": gr.hauteurStatus,
            "appliquees": [{"label": r.label, "value": r.value, "unit": r.unit, "detail": r.detail,
                            "source": src(r.source)} for r in (gr.appliedRules or [])]}


def _hash_scene(scene: "Scene") -> str:
    """Identifiant = hachage de la scène RÉELLEMENT SÉRIALISÉE (tout sauf l'identifiant lui-même) :
    adresse, contours, reculs, exclusions, bâti, terrain (sommets), règles, coupes, métadonnées."""
    payload = {k: v for k, v in scene.to_dict().items() if k != "scene_id"}
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]


_MEMO: dict = {}        # scène construite UNE FOIS (clé : idu + signature du fond), lue par tous


def build_scene(db, idu: str, use_cache: bool = True) -> Scene:
    """Construit la scène (déterministe, mémoïsée). Lit le GabaritResult SERVI + le MNT 1 m."""
    p = get_settings().mnt1m_cog_file
    sig = (idu, str(p), p.stat().st_mtime if p.exists() else 0)
    if use_cache and sig in _MEMO:
        return _MEMO[sig]
    scene = _build_scene(db, idu)
    if use_cache:
        if len(_MEMO) > 32:
            _MEMO.clear()
        _MEMO[sig] = scene
    return scene


def _build_scene(db, idu: str) -> Scene:
    from ..api.gabarit import gabarit_detail
    gr = gabarit_detail(idu, db)
    fond_meta = _fond_meta()
    adresse = _adresse(db, idu)
    try:                                   # commune (en-tête de la visionneuse)
        from sqlalchemy import text as _t
        fond_meta = {**fond_meta, "commune": db.execute(_t("SELECT commune FROM parcels WHERE idu=:i"), {"i": idu}).scalar()}
    except Exception:  # noqa: BLE001
        pass

    contour = _geom_2975(getattr(gr, "contourGeoJSON", None))
    cadastre = _cadastre_2975(db, idu)
    ref = cadastre or contour
    if ref is None:
        vide = Scene(idu=idu, scene_id="", disponible=False, adresse=adresse, meta=fond_meta,
                     etat={"gabarit": gr.status, "terrain_couverture": 0.0, "fond_disponible": False, "coupes": []},
                     message=gr.message or "Parcelle sans contour exploitable.")
        vide.scene_id = _hash_scene(vide)
        return vide
    minx, miny, maxx, maxy = ref.bounds
    ox, oy = math.floor(minx), math.floor(miny)
    centroid = ref.centroid
    zone = _geom_2975(getattr(gr, "zoneImplantationGeoJSON", None))
    reculs = _geom_2975(getattr(gr, "retraitsGeoJSON", None))
    excl = _geom_2975(getattr(gr, "exclusionsGeoJSON", None))

    # UN SEUL maillage à 1 m, borné à la parcelle + abords (plus de fenêtre 150 m ni de maillage 2 m)
    bounds_1m = (minx - _MARGE_FACES_1M, miny - _MARGE_FACES_1M, maxx + _MARGE_FACES_1M, maxy + _MARGE_FACES_1M)
    surf = charger_surface(minx, miny, maxx, maxy, marge=_MARGE_FACES_1M + 10)
    sampler = _Sampler(surf, bounds_1m) if surf else None

    terrain, coupes, axes_plan, coupes_etat = {}, [], [], []
    couverture = 0.0
    faces_1m = {}
    batis = _batiments(gr, sampler, ox, oy) if sampler else []
    if sampler is not None:
        couverture = _couverture_parcelle(sampler, ref)
        faces_1m = sampler.m.faces(ox, oy, bounds=bounds_1m)   # faces SERVIES = affichées par la visionneuse
        terrain = {"faces_parcelle": faces_1m, "couverture_parcelle": couverture}

        # chaque coupe est protégée : un échec la rend indisponible, PLAN et TERRAIN restent accessibles
        try:
            ax_p = _axe_pente_dominante(sampler, ref, centroid)
        except Exception:  # noqa: BLE001
            ax_p = None
        try:
            ax_v, voie = _axe_voie(db, idu, ref)
        except Exception:  # noqa: BLE001
            ax_v, voie = None, None
        if voie and voie.get("etablie") and voie.get("intersection_d") is not None:
            voie["point_local"] = [round(ax_v["ox"] + ax_v["ux"] * voie["intersection_d"] - ox, 2),
                                   round(ax_v["oy"] + ax_v["uy"] * voie["intersection_d"] - oy, 2)]
        if ax_p:
            try:
                c = _construire_coupe(sampler, ax_p, cadastre or ref, zone, batis, "A",
                                      "Coupe A-A′ — pente dominante", None)
                coupes.append(c); axes_plan.append(_axe_plan("A", ax_p, ox, oy))
                coupes_etat.append({"axe": "A", "disponible": c["cotes"]["disponible"]})
            except Exception:  # noqa: BLE001
                coupes_etat.append({"axe": "A", "disponible": False})
        if ax_v:
            try:
                titre = ("Coupe B-B′ — orientée par la voie" if voie and voie.get("etablie")
                         else "Coupe B-B′ — orientée vers la voie")
                c = _construire_coupe(sampler, ax_v, cadastre or ref, zone, batis, "B", titre, voie)
                coupes.append(c); axes_plan.append(_axe_plan("B", ax_v, ox, oy))
                coupes_etat.append({"axe": "B", "disponible": c["cotes"]["disponible"]})
            except Exception:  # noqa: BLE001
                coupes_etat.append({"axe": "B", "disponible": False})

    for b in batis:
        b.pop("geom", None)

    etat = {"gabarit": gr.status, "terrain_couverture": couverture, "fond_disponible": sampler is not None,
            "coupes": coupes_etat}
    disponible = sampler is not None and couverture > 0.5   # la PARCELLE elle-même doit être couverte

    scene = Scene(
        idu=idu, scene_id="", etat=etat, disponible=disponible, adresse=adresse, origine_2975=[ox, oy],
        contour_cadastral=_polys_local(cadastre, ox, oy), contour_gabarit=_polys_local(contour, ox, oy),
        zone_implantation=_polys_local(zone, ox, oy), reculs=_polys_local(reculs, ox, oy),
        exclusions=_polys_local(excl, ox, oy), batiments=batis, terrain=terrain,
        regles=_regles_servies(gr), coupes=coupes, axes_plan={a["label"]: a for a in axes_plan},
        meta=fond_meta,
        message=None if disponible else "Fond d'altitudes absent/insuffisant sur la parcelle (terrain en lacune).")
    # identifiant = hachage de la scène réellement sérialisée (A3 : adresse/reculs/sommets compris)
    scene.scene_id = _hash_scene(scene)
    return scene


def _axe_plan(label, axe, ox, oy) -> dict:
    a = (axe["ox"] - ox, axe["oy"] - oy)
    b = (axe["ox"] + axe["ux"] * axe["L"] - ox, axe["oy"] + axe["uy"] * axe["L"] - oy)
    return {"label": label, "p0": [round(a[0], 2), round(a[1], 2)], "p1": [round(b[0], 2), round(b[1], 2)],
            "sens": [round(axe["ux"], 4), round(axe["uy"], 4)]}
