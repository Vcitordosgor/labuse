"""GABARIT-3D-1 (pilote) — SCÈNE commune du Gabarit : le terrain réel, le bâti, deux coupes.

Révision Astra (étape 1 bis). Une SCÈNE rassemble, en MÈTRES autour d'une origine locale (coin SW de
la bbox du contour, EPSG:2975), tout ce que la vue 3D ET le PDF liront — ILS LISENT LA MÊME SCÈNE :

  - TROIS contours DISTINCTS, trous et parties multiples conservés : cadastral, contour étudié par le
    Gabarit, zone d'implantation ; plus reculs et exclusions ;
  - UNE SEULE surface de référence (bilinéaire sur le MNT LiDAR 1 m = triangulation par maille ;
    raccords 1 m/2 m et lacunes définis). Les profils sont calculés PAR INTERSECTION avec elle — une
    coupe oblique, décalée des centres de pixels, rend la pente constante d'un plan ;
  - les BÂTIMENTS : hauteur COTÉE et dite « mesurée » seulement si rattachée à l'emprise (LiDAR) ;
    sinon volume schématique sans cote. PIED aux DEUX rencontres de la coupe (amont et aval) ;
  - les VALEURS DES RÈGLES en données (reprises telles quelles du moteur — AUCUN chiffre changé) ;
  - deux COUPES : A « pente dominante » ; B orientée par la voie (identité + intersection vérifiée +
    statut d'accès ; sans intersection établie : « orientée vers la voie », sans voie dessinée) ;
  - l'ÉTAT exposé SÉPARÉMENT (couverture du terrain, état du Gabarit, disponibilité des coupes ;
    jamais « disponible » avec des grilles vides) + un IDENTIFIANT calculé sur le contenu et les
    sources versionnées. La scène est DÉTERMINISTE : l'export se reproduit après purge du cache.

Doctrine LABUSE : la scène n'INVENTE aucun chiffre réglementaire — elle lit le GabaritResult servi par
``api.gabarit.gabarit_detail``. Le relief vient du fond LiDAR, un FAIT mesuré. AUCUN plafond de hauteur
n'est dessiné (mandat suivant).
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

_NODATA = -9999.0
_PENTE_FENETRE_M = 5.0   # fenêtre glissante de la pente maximale (CDC 12)


# ── Surface de référence (bilinéaire sur le MNT 1 m) ──────────────────────────────────────────────

@lru_cache(maxsize=4)
def _open_cog(path: str, mtime: float):
    """Ouvre le COG (cache par chemin+mtime). None si absent/illisible (dégradation gracieuse)."""
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


class SurfaceReference:
    """Surface de référence = patchs BILINÉAIRES sur le MNT 1 m (équivalent d'une triangulation par
    maille). ``altitude(x, y)`` interpole les 4 appuis entourant le point ; LACUNE (None) dès qu'un
    appui manque. Reproduit EXACTEMENT un plan → une coupe oblique rend une pente constante."""

    def __init__(self, arr, ox: float, oy: float, pas: float):
        import numpy as np
        self.a = np.asarray(arr, dtype="float64")
        self.a[(self.a <= -1000.0) | ~np.isfinite(self.a)] = np.nan   # sentinelles → lacune
        self.ox, self.oy, self.pas = ox, oy, pas          # (ox,oy) = coin HAUT-GAUCHE du raster lu
        self.ny, self.nx = self.a.shape

    def altitude(self, x: float, y: float) -> Optional[float]:
        import numpy as np
        fc = (x - self.ox) / self.pas - 0.5               # colonne fractionnaire (centres de pixels)
        fr = (self.oy - y) / self.pas - 0.5
        c0, r0 = math.floor(fc), math.floor(fr)
        if r0 < 0 or c0 < 0 or r0 + 1 >= self.ny or c0 + 1 >= self.nx:
            return None
        tc, tr = fc - c0, fr - r0
        z = self.a[r0:r0 + 2, c0:c0 + 2]
        if np.isnan(z).any():                             # un appui manquant → lacune (pas d'invention)
            return None
        top = z[0, 0] * (1 - tc) + z[0, 1] * tc
        bot = z[1, 0] * (1 - tc) + z[1, 1] * tc
        return float(top * (1 - tr) + bot * tr)   # NON arrondi (bilinéaire exact) ; arrondi en sortie

    @staticmethod
    def _r(z):
        return round(z, 2) if z is not None else None

    def ligne(self, ox: float, oy: float, ux: float, uy: float, L: float, pas: float = 1.0) -> list[dict]:
        n = max(2, int(round(L / pas)) + 1)
        out = []
        for i in range(n):
            d = L * i / (n - 1)
            out.append({"d": round(d, 2), "z": self._r(self.altitude(ox + ux * d, oy + uy * d))})
        return out

    def grille(self, minx: float, miny: float, maxx: float, maxy: float, pas: float) -> dict:
        nx = max(1, int(round((maxx - minx) / pas)))
        ny = max(1, int(round((maxy - miny) / pas)))
        z = [self._r(self.altitude(minx + (i + 0.5) * pas, maxy - (j + 0.5) * pas))
             for j in range(ny) for i in range(nx)]
        n_val = sum(1 for v in z if v is not None)
        return {"pas": pas, "ox": minx, "oy": maxy, "nx": nx, "ny": ny, "z": z,
                "couverture": round(n_val / (nx * ny), 3) if nx * ny else 0.0}


def charger_surface(minx: float, miny: float, maxx: float, maxy: float,
                    marge: float = 170.0) -> Optional[SurfaceReference]:
    """Charge la fenêtre du MNT couvrant [minx,maxx]×[miny,maxy] + marge, en une lecture."""
    ds = _cog()
    if ds is None:
        return None
    from rasterio.windows import from_bounds
    try:
        win = from_bounds(minx - marge, miny - marge, maxx + marge, maxy + marge, ds.transform)
        arr = ds.read(1, window=win, boundless=True, fill_value=_NODATA)
        tr = ds.window_transform(win)
        return SurfaceReference(arr, tr.c, tr.f, tr.a)
    except Exception:  # noqa: BLE001
        return None


def sample_points(pts_2975: list[tuple[float, float]]) -> list[Optional[float]]:
    """Altitude ponctuelle (plus proche pixel) — utilisée pour des contrôles/cotes isolées."""
    ds = _cog()
    if ds is None or not pts_2975:
        return [None] * len(pts_2975)
    out = []
    for v in ds.sample(pts_2975):
        z = _valide(v[0])
        out.append(round(z, 2) if z is not None else None)
    return out


# ── Géométrie (→ 2975, repère local, trous + parties multiples conservés) ─────────────────────────

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
    """(Multi)Polygon → liste de polygones {ext, trous} en repère local (trous + multipart CONSERVÉS)."""
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
    """Contour CADASTRAL (parcels.geom_2975) — distinct du contour étudié par le Gabarit."""
    from sqlalchemy import text
    from shapely import wkt as shp_wkt
    try:
        w = db.execute(text("SELECT ST_AsText(geom_2975) FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        g = shp_wkt.loads(w) if w else None
        return g if (g is not None and not g.is_empty) else None
    except Exception:  # noqa: BLE001
        return None


# ── Axes de coupe ─────────────────────────────────────────────────────────────────────────────────

def _axe_pente_dominante(surf: SurfaceReference, assiette, centroid) -> Optional[dict]:
    """Axe A : PENTE DOMINANTE. Ajuste un plan z=a·x+b·y+c aux appuis du MNT SOUS la parcelle ; la
    descente la plus raide est -(a,b). None si le fond ne couvre pas assez la parcelle."""
    import numpy as np
    from shapely.geometry import Point
    minx, miny, maxx, maxy = assiette.bounds
    xs, ys, zs = [], [], []
    y = miny + 0.5
    while y < maxy:
        x = minx + 0.5
        while x < maxx:
            z = surf.altitude(x, y)
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
        n2 = math.hypot(vx, vy) or 1.0
        ux, uy = vx / n2, vy / n2
    else:
        ux, uy = -a / n, -b / n
    proj = [((x - centroid.x) * ux + (y - centroid.y) * uy) for x, y in assiette.exterior.coords]
    dmin, dmax = min(proj), max(proj)
    return {"ox": centroid.x + ux * dmin, "oy": centroid.y + uy * dmin, "ux": ux, "uy": uy,
            "L": dmax - dmin, "pente_plan_pct": round(n * 100, 1)}


def _axe_voie(db, idu: str, assiette):
    """Axe B : orienté par la voie. Renvoie (axe, voie) où voie = {nom, etablie, intersection_d,
    statut, geom}. L'axe part de 25 m avant le bord « voie » (chaussée). Si aucune intersection de
    voie n'est établie : statut « orientée vers la voie », voie non dessinée (geom None)."""
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
    # intersection VÉRIFIÉE de l'axe avec la géométrie de voie
    ligne = LineString([(axe["ox"], axe["oy"]),
                        (axe["ox"] + axe["ux"] * axe["L"], axe["oy"] + axe["uy"] * axe["L"])])
    inter_d, voie_geom, voie_nom = None, None, (voies[0].nom if voies else None)
    for v in voies:
        try:
            it = ligne.intersection(v.geom_2975)
        except Exception:  # noqa: BLE001
            continue
        if it.is_empty:
            continue
        pt = it if it.geom_type == "Point" else (list(it.geoms)[0] if hasattr(it, "geoms") else it.centroid)
        inter_d = round(ligne.project(pt), 2)
        voie_geom, voie_nom = v.geom_2975, v.nom
        break
    if inter_d is not None:
        voie = {"nom": voie_nom, "etablie": True, "intersection_d": inter_d,
                "statut": "accès présumé (intersection de voie vérifiée)", "geom": voie_geom}
    else:
        voie = {"nom": None, "etablie": False, "intersection_d": None,
                "statut": "coupe orientée vers la voie (intersection non établie)", "geom": None}
    return axe, voie


# ── Profil, bâtiments, intervalles, indicateurs ───────────────────────────────────────────────────

def _runs(profil: list[dict]) -> list[list[dict]]:
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
    """Intervalles [d0,d1] où la ligne traverse `geom` (par tronçons, triés)."""
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


def _z_interp(profil: list[dict], d: float) -> Optional[float]:
    """Altitude du profil à la distance d (interpolée dans un run ; None si lacune locale)."""
    for run in _runs(profil):
        if run[0]["d"] - 1e-6 <= d <= run[-1]["d"] + 1e-6:
            for a, b in zip(run, run[1:]):
                if a["d"] <= d <= b["d"] and b["d"] > a["d"]:
                    t = (d - a["d"]) / (b["d"] - a["d"])
                    return round(a["z"] + t * (b["z"] - a["z"]), 2)
            return run[min(range(len(run)), key=lambda i: abs(run[i]["d"] - d))]["z"]
    return None


def _batiment_coupe(surf, ligne, axe, b) -> list[dict]:
    """Un bâtiment traversé → un segment par tronçon, avec PIED aux deux rencontres (amont/aval)."""
    out = []
    for d0, d1 in _spans(ligne, b["geom"]):
        pa = surf.altitude(axe["ox"] + axe["ux"] * d0, axe["oy"] + axe["uy"] * d0)
        pv = surf.altitude(axe["ox"] + axe["ux"] * d1, axe["oy"] + axe["uy"] * d1)
        out.append({"d0": d0, "d1": d1, "hauteur_m": b["hauteur_m"], "provenance": b["provenance"],
                    "cotee": b["cotee"], "schematique": b.get("schematique", not b["cotee"]),
                    "pied_amont_m": pa, "pied_aval_m": pv})
    return out


def _indicateurs(profil, parcelle_spans, bati_spans, voie) -> dict:
    """Indicateurs PAR TRAVERSÉE CONTINUE (CDC 12) : pente entre limites (signée) et amplitude,
    SÉPARÉMENT ; pente max sur 5 m (fenêtre entièrement valable, DANS la parcelle, HORS bâti), avec
    son emplacement ; pente d'accès seulement si une voie est établie."""
    # traversées continues = valides ∩ parcelle
    traversees = []
    for d0, d1 in parcelle_spans:
        dans_span = [{"d": p["d"], "z": p["z"]} for p in profil if d0 - 1e-6 <= p["d"] <= d1 + 1e-6]
        for run in _runs(dans_span):   # coupé aux lacunes internes
            if len(run) < 2:
                continue
            dz = run[-1]["z"] - run[0]["z"]
            dd = run[-1]["d"] - run[0]["d"]
            alts = [p["z"] for p in run]
            traversees.append({
                "d0": round(run[0]["d"], 2), "d1": round(run[-1]["d"], 2),
                "pente_pct": round(100 * dz / dd, 1) if dd > 0 else None,
                "sens": "montée" if dz > 0.05 else ("descente" if dz < -0.05 else "plat"),
                "amplitude_m": round(max(alts) - min(alts), 2),
            })
    # pente max sur 5 m : fenêtre glissante entièrement valable, dans la parcelle, hors bâti
    def _dans(d, spans):
        return any(a - 1e-6 <= d <= b + 1e-6 for a, b in spans)
    pmax = {"disponible": False}
    pas = (profil[1]["d"] - profil[0]["d"]) if len(profil) > 1 else 1.0
    w = max(1, int(round(_PENTE_FENETRE_M / pas)))
    for i in range(len(profil) - w):
        f = profil[i:i + w + 1]
        if any(p["z"] is None for p in f):
            continue
        dc = (f[0]["d"] + f[-1]["d"]) / 2
        if not _dans(dc, parcelle_spans) or _dans(dc, bati_spans):
            continue
        dd = f[-1]["d"] - f[0]["d"]
        s = abs(f[-1]["z"] - f[0]["z"]) / dd if dd > 0 else 0.0
        if not pmax.get("disponible") or s > pmax["pente_pct"] / 100:
            pmax = {"disponible": True, "pente_pct": round(s * 100, 1), "d": round(dc, 2),
                    "fenetre_m": round(dd, 1)}
    # pente d'accès : le long de l'accès établi (voie → entrée parcelle)
    pente_acces = None
    if voie and voie.get("etablie") and parcelle_spans:
        d_voie = voie["intersection_d"]
        d_entree = min(s[0] for s in parcelle_spans)
        za, zb = _z_interp(profil, d_voie), _z_interp(profil, d_entree)
        if za is not None and zb is not None and abs(d_entree - d_voie) > 1e-6:
            pente_acces = round(100 * (zb - za) / (d_entree - d_voie), 1)
    return {"traversees": traversees, "pente_max_5m": pmax, "pente_acces_pct": pente_acces}


def _cotes_points(profil, parcelle_spans, batiments, voie) -> dict:
    """Points VÉRIFIÉS à coter (CDC 11) : voie si établie, chaque limite, haut/bas de chaque traversée,
    pieds amont/aval des bâtiments. Une cote au support incertain (lacune locale) est OMISE (None)."""
    pts = []

    def add(d, role):
        z = _z_interp(profil, d)
        if z is not None:
            pts.append({"d": round(d, 2), "z": z, "role": role})
    if voie and voie.get("etablie"):
        add(voie["intersection_d"], "voie")
    for d0, d1 in parcelle_spans:
        add(d0, "limite"); add(d1, "limite")
    # haut / bas sur l'ensemble des points dans la parcelle
    dans = [p for p in profil if p["z"] is not None and any(a - 1e-6 <= p["d"] <= b + 1e-6 for a, b in parcelle_spans)]
    if dans:
        hi = max(dans, key=lambda p: p["z"]); lo = min(dans, key=lambda p: p["z"])
        pts.append({"d": hi["d"], "z": hi["z"], "role": "haut"})
        pts.append({"d": lo["d"], "z": lo["z"], "role": "bas"})
    for b in batiments:
        if b.get("pied_amont_m") is not None:
            pts.append({"d": b["d0"], "z": b["pied_amont_m"], "role": "pied"})
        if b.get("pied_aval_m") is not None:
            pts.append({"d": b["d1"], "z": b["pied_aval_m"], "role": "pied"})
    return {"points": pts}


def _stats_coupe(profil: list[dict]) -> dict:
    """Résumé robuste : altitudes extrêmes + nombre de lacunes (indicateurs détaillés : _indicateurs)."""
    alts = [p["z"] for p in profil if p["z"] is not None]
    if not alts:
        return {"disponible": False}
    return {"disponible": True, "altitude_min_m": round(min(alts), 2),
            "altitude_max_m": round(max(alts), 2), "amplitude_m": round(max(alts) - min(alts), 2),
            "n_lacune": sum(1 for p in profil if p["z"] is None),
            "couverture": round(len(alts) / len(profil), 3)}


def _construire_coupe(surf, axe, cadastre, zone, batis, label, titre, voie) -> dict:
    """Profil par intersection avec la surface + annotations (limites cadastrales, zone, bâti, cotes)."""
    from shapely.geometry import LineString
    ox, oy, ux, uy, L = axe["ox"], axe["oy"], axe["ux"], axe["uy"], axe["L"]
    profil = surf.ligne(ox, oy, ux, uy, L, pas=1.0)
    ligne = LineString([(ox, oy), (ox + ux * L, oy + uy * L)])
    parcelle_spans = _spans(ligne, cadastre)
    bati_coupes = [c for b in batis for c in _batiment_coupe(surf, ligne, axe, b)]
    bati_spans = [[c["d0"], c["d1"]] for c in bati_coupes]
    return {
        "label": label, "titre": titre,
        "voie": {k: v for k, v in (voie or {}).items() if k != "geom"} if voie else None,
        "longueur_m": round(L, 2), "origine_2975": [round(ox, 2), round(oy, 2)],
        "direction": [round(ux, 6), round(uy, 6)],
        "profil": profil,
        "limites_parcelle_d": parcelle_spans,
        "zone_implantation_d": _spans(ligne, zone),
        "batiments": bati_coupes,
        "indicateurs": _indicateurs(profil, parcelle_spans, bati_spans, voie),
        "cotes": _stats_coupe(profil),
        "cotes_points": _cotes_points(profil, parcelle_spans, bati_coupes, voie),
    }


# ── Scène ─────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class Scene:
    idu: str
    scene_id: str
    etat: dict = field(default_factory=dict)        # couverture terrain / gabarit / coupes (séparés)
    disponible: bool = False
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
            "referentiel_alti": "REUN89 (IGN 1989)", "nodata": _NODATA, "disponible": p.exists()}
    if mp.exists():
        try:
            d = json.loads(mp.read_text())
            base.update({"acquisition": d.get("fenetres"), "octets": d.get("taille_octets"),
                         "couche_wms": d.get("couche_wms"), "version_fond": d.get("taille_octets")})
        except Exception:  # noqa: BLE001
            pass
    return base


def _batiments(gr, surf, ox: float, oy: float) -> list[dict]:
    """Bâtiments existants. La hauteur LiDAR est un FAÎTAGE PAR PARCELLE (pas par emprise) : elle n'est
    attribuable — et donc cotée « mesurée (LiDAR) » — que si la parcelle ne porte QU'UN SEUL bâtiment.
    Si elle en porte plusieurs, AUCUN n'est coté : volume schématique, mention « hauteur non attribuée ».
    BD TOPO (hauteur par bâtiment) → « estimée », volume schématique non coté."""
    fc = getattr(gr, "batiExistantGeoJSON", None)
    out = []
    if not isinstance(fc, dict):
        return out
    feats = fc.get("features", [])
    n_bati = len(feats)                      # nombre de bâtiments PORTÉS par la parcelle
    for f in feats:
        g2975 = _geom_2975(f.get("geometry"))
        if g2975 is None:
            continue
        props = f.get("properties") or {}
        h = props.get("hauteur_m")
        src = props.get("h_source")
        hauteur = float(h) if isinstance(h, (int, float)) and h > 0 else None
        if src == "lidar" and n_bati == 1 and hauteur:
            prov, cotee, haut = "mesurée (LiDAR)", True, hauteur      # un seul bâti → attribuable
        elif src == "lidar":
            prov, cotee, haut = "hauteur non attribuée", False, 3.0   # plusieurs → faîtage non attribuable
        elif src == "bdtopo" and hauteur:
            prov, cotee, haut = "estimée (BD TOPO)", False, hauteur   # par bâtiment, mais non cotée
        else:
            prov, cotee, haut = "hauteur non attribuée", False, 3.0
        out.append({
            "geom": g2975,
            "empreinte": _polys_local(g2975, ox, oy),
            "hauteur_m": haut,              # schématique (3 m) quand non attribuée
            "provenance": prov,
            "cotee": cotee,
            "schematique": not cotee,       # volume schématique (hauteur non cotée)
        })
    return out


def _regles_servies(gr) -> dict:
    def src(s):
        if s is None:
            return None
        return {k: getattr(s, k, None) for k in ("document", "zone", "article", "versionDate", "provider")}
    return {
        "surfaceParcelleM2": gr.surfaceParcelleM2, "zoneImplantationM2": gr.zoneImplantationM2,
        "batiDeduitM2": gr.batiDeduitM2, "plafondEmpriseM2": gr.plafondEmpriseM2,
        "plafondEmpriseStatus": gr.plafondEmpriseStatus, "hauteurReglementaireM": gr.hauteurReglementaireM,
        "hauteurBase": gr.hauteurBase, "hauteurEstimee": gr.hauteurEstimee, "hauteurStatus": gr.hauteurStatus,
        "appliquees": [{"label": r.label, "value": r.value, "unit": r.unit, "detail": r.detail,
                        "source": src(r.source)} for r in (gr.appliedRules or [])],
    }


def _sources_versionnees(gr, fond_meta: dict) -> list:
    """Sources VERSIONNÉES entrant dans l'identifiant (versionDate des règles + version du fond)."""
    out = [{"fond": fond_meta.get("version_fond"), "produit": fond_meta.get("produit")}]
    for r in (gr.appliedRules or []):
        s = getattr(r, "source", None)
        if s is not None:
            out.append({"doc": getattr(s, "document", None), "version": getattr(s, "versionDate", None)})
    return out


def _scene_id(idu: str, gr, fond_meta: dict, contenu: dict) -> str:
    """Identifiant calculé sur le CONTENU (géométries, grilles, coupes) ET les SOURCES VERSIONNÉES."""
    sig = json.dumps({"idu": idu, "regles": _regles_servies(gr),
                      "sources": _sources_versionnees(gr, fond_meta), "contenu": contenu},
                     sort_keys=True, default=str)
    return hashlib.sha1(sig.encode()).hexdigest()[:12]


def build_scene(db, idu: str) -> Scene:
    """Construit la scène (déterministe). Lit le GabaritResult SERVI (chiffres identiques) + le MNT 1 m.

    ÉTAT exposé séparément : couverture du terrain, état du Gabarit, disponibilité des coupes.
    Jamais « disponible » avec des grilles vides."""
    from ..api.gabarit import gabarit_detail  # lazy — évite l'import circulaire
    gr = gabarit_detail(idu, db)
    fond_meta = _fond_meta()

    contour = _geom_2975(getattr(gr, "contourGeoJSON", None))
    cadastre = _cadastre_2975(db, idu)
    ref = contour or cadastre
    if ref is None:
        sid = _scene_id(idu, gr, fond_meta, {"vide": True})
        return Scene(idu=idu, scene_id=sid, disponible=False, meta=fond_meta,
                     etat={"gabarit": gr.status, "terrain_couverture": 0.0, "coupes": []},
                     message=gr.message or "Parcelle sans contour exploitable.")
    minx, miny, maxx, maxy = ref.bounds
    ox, oy = math.floor(minx), math.floor(miny)
    centroid = ref.centroid

    zone = _geom_2975(getattr(gr, "zoneImplantationGeoJSON", None))
    reculs = _geom_2975(getattr(gr, "retraitsGeoJSON", None))
    excl = _geom_2975(getattr(gr, "exclusionsGeoJSON", None))

    # UNE seule surface de référence (une lecture) → grilles ET profils
    surf = charger_surface(min(minx, centroid.x - 150), min(miny, centroid.y - 150),
                           max(maxx, centroid.x + 150), max(maxy, centroid.y + 150))
    batis = _batiments(gr, surf, ox, oy) if surf else _batiments(gr, None, ox, oy)

    terrain, coupes, axes_plan = {}, [], []
    coupes_etat = []
    couverture = 0.0
    if surf is not None:
        g_parcelle = surf.grille(minx - 20, miny - 20, maxx + 20, maxy + 20, 1.0)
        g_voisinage = surf.grille(centroid.x - 150, centroid.y - 150, centroid.x + 150, centroid.y + 150, 2.0)
        for g in (g_parcelle, g_voisinage):
            g["ox"] = round(g["ox"] - ox, 2); g["oy"] = round(g["oy"] - oy, 2)
        terrain = {"parcelle_1m": g_parcelle, "voisinage_2m": g_voisinage}
        couverture = g_parcelle["couverture"]

        ax_pente = _axe_pente_dominante(surf, ref, centroid)
        ax_voie, voie = _axe_voie(db, idu, ref)
        if ax_pente:
            c = _construire_coupe(surf, ax_pente, cadastre or ref, zone, batis, "A",
                                  "Coupe A-A′ — pente dominante", None)
            coupes.append(c); axes_plan.append(_axe_plan("A", ax_pente, ox, oy))
            coupes_etat.append({"axe": "A", "disponible": c["cotes"]["disponible"]})
        if ax_voie:
            titre = ("Coupe B-B′ — orientée par la voie" if voie and voie.get("etablie")
                     else "Coupe B-B′ — orientée vers la voie")
            c = _construire_coupe(surf, ax_voie, cadastre or ref, zone, batis, "B", titre, voie)
            coupes.append(c); axes_plan.append(_axe_plan("B", ax_voie, ox, oy))
            coupes_etat.append({"axe": "B", "disponible": c["cotes"]["disponible"]})

    for b in batis:
        b.pop("geom", None)

    etat = {"gabarit": gr.status, "terrain_couverture": couverture,
            "fond_disponible": surf is not None, "coupes": coupes_etat}
    # « disponible » = le fond couvre réellement le terrain (jamais vrai avec des grilles vides)
    disponible = surf is not None and couverture > 0.0

    contenu = {"cad": _polys_local(cadastre, ox, oy), "gab": _polys_local(contour, ox, oy),
               "zone": _polys_local(zone, ox, oy),
               "coupes": [[p["z"] for p in c["profil"]] for c in coupes],
               "couverture": couverture}
    sid = _scene_id(idu, gr, fond_meta, contenu)

    return Scene(
        idu=idu, scene_id=sid, etat=etat, disponible=disponible, origine_2975=[ox, oy],
        contour_cadastral=_polys_local(cadastre, ox, oy),
        contour_gabarit=_polys_local(contour, ox, oy),
        zone_implantation=_polys_local(zone, ox, oy),
        reculs=_polys_local(reculs, ox, oy),
        exclusions=_polys_local(excl, ox, oy),
        batiments=batis, terrain=terrain, regles=_regles_servies(gr),
        coupes=coupes, axes_plan={a["label"]: a for a in axes_plan}, meta=fond_meta,
        message=None if disponible else "Fond d'altitudes absent sur cette emprise (terrain en lacune).",
    )


def _axe_plan(label: str, axe: dict, ox: float, oy: float) -> dict:
    a = (axe["ox"] - ox, axe["oy"] - oy)
    b = (axe["ox"] + axe["ux"] * axe["L"] - ox, axe["oy"] + axe["uy"] * axe["L"] - oy)
    return {"label": label, "p0": [round(a[0], 2), round(a[1], 2)], "p1": [round(b[0], 2), round(b[1], 2)],
            "sens": [round(axe["ux"], 4), round(axe["uy"], 4)]}
