"""Proxy des fonds ORTHO — RETOURS-16 V1 (généralise le proxy Express de RETOURS-15 U1).

Constat Vic (05/09, 4e recette) : au large, des rectangles bleus décalés en escalier avec des
liserés blancs le long des marches. Mesuré (reconstruction GetTile z13 côte nord) : la mer PHOTO
de l'Ortho Express s'arrête par dalles (escalier), d'un bleu différent de la mer de la mosaïque
monde qui affleure dessous — deux sources, deux bleus, et le blanc no-data mal rogné laisse des
liserés. Un fondu local ne suffit pas : la différence de teinte couvre des km².

Doctrine V1 : TOUTES les sources ortho passent ici (aucune tuile brute), et la mer est UN APLAT
D'UNE SEULE COULEUR (``MER_HEX``, posé par le canvas MapLibre sur l'emprise entière — jamais par
tuile). La photo ne garde la mer que sur une BANDE CÔTIÈRE (pleine jusqu'à ``_R1`` m, fondu vers
l'aplat jusqu'à ``_R2`` m) : la transition suit la CÔTE, plus jamais les bords de dalles. Les
jetées et ports restent photographiés (la bande pleine les couvre) — rien n'est découpé au bord
de tuile. Le blanc no-data connecté au bord fond lui aussi (rampe de distance, plus de liseré).

Coût : les tuiles entièrement au large répondent 404 SANS requête IGN (test géométrique, ~0 ms) ;
les tuiles pleines terre sont relayées telles quelles (octets d'origine) ; seules les tuiles
côtières sont décodées/traitées. Un cache disque (``ortho_proxy_cache_dir``) mémorise le verdict
et les tuiles traitées — la première visite paie le traitement, les suivantes lisent le disque.

Chemin /map/tiles/* exprès : régime carto du rate-limit (quota jour), jamais le 60/min.
"""
from __future__ import annotations

import io
import json
import logging
import math
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from ..config import get_settings

router = APIRouter(tags=["map-tiles"])
log = logging.getLogger("labuse")

#: aplat de mer UNIQUE — même valeur que ``MER_ORTHO`` côté front (MapView.applyClairMode) :
#: bleu profond MESURÉ sur la mosaïque monde IGN au large du 974 (moyenne rgb(10,59,89)).
MER_HEX = "#0A3B59"

#: couches servies — slug public → (couche IGN, format WMTS). Liste FERMÉE : le proxy ne relaie
#: jamais une couche arbitraire. Toutes les sources ortho de basemaps.ts sont ici (V1 pt 1).
_COUCHES: dict[str, tuple[str, str]] = {
    "monde":   ("ORTHOIMAGERY.ORTHOPHOTOS", "image/jpeg"),
    "express": ("ORTHOIMAGERY.ORTHOPHOTOS.ORTHO-EXPRESS.2025", "image/jpeg"),
    "1950":    ("ORTHOIMAGERY.ORTHOPHOTOS.1950-1965", "image/png"),
    "2000":    ("ORTHOIMAGERY.ORTHOPHOTOS2000-2005", "image/jpeg"),
    "2006":    ("ORTHOIMAGERY.ORTHOPHOTOS2006-2010", "image/jpeg"),
    "2011":    ("ORTHOIMAGERY.ORTHOPHOTOS2011-2015", "image/jpeg"),
    "2016":    ("ORTHOIMAGERY.ORTHOPHOTOS2016-2020", "image/jpeg"),
    "2021":    ("ORTHOIMAGERY.ORTHOPHOTOS2021-2023", "image/jpeg"),
}
_WMTS = ("https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&STYLE=normal"
         "&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&LAYER={layer}&FORMAT={fmt}")

#: bande côtière (mètres Mercator, ÷1,072 en mètres vrais à la latitude du 974) : photo pleine
#: jusqu'à _R1 (la grande jetée du Port ≈ 700 m reste entière), fondu vers l'aplat jusqu'à _R2.
#: Au-delà de _R2 : aplat seul. Mesuré au prototype (z11/z13/z14) : aucune marche résiduelle.
_R1, _R2 = 700.0, 1600.0
_Z_FONDU_MAX = 15   # au-delà, le viewport est sub-kilométrique : photo pleine, une seule source
_Z_BLANC_MAX = 16   # bande blanche IGN mesurée z13-16 (U1) — au-delà, rien à rogner
_FONDU_BLANC_PX = 48   # rampe du no-data connecté au bord (24 px laissait un liseré, mesuré)
_QR = 4             # le champ de distance se calcule au quart de résolution (fondu doux, px inutile)

_R_MERC = 6378137.0
_CIRC = 2 * math.pi * _R_MERC

_ile_lock = threading.Lock()
_ile_geom = None   # MultiPolygon Mercator de l'île (chargé une fois) ; False = introuvable


def _ile():
    """Polygone de l'île en WebMercator — source : ile974.geojson (le même fichier que la masse
    terrestre du front ; dist/ en service, public/ en dev). Chargé une fois, thread-safe."""
    global _ile_geom
    if _ile_geom is not None:
        return _ile_geom or None
    with _ile_lock:
        if _ile_geom is not None:
            return _ile_geom or None
        from shapely.geometry import shape
        from shapely.ops import transform as sh_transform
        from shapely.ops import unary_union
        racine = Path(__file__).resolve().parents[3] / "frontend"
        for cand in (racine / "dist" / "ile974.geojson", racine / "public" / "ile974.geojson"):
            if cand.exists():
                gj = json.loads(cand.read_text(encoding="utf-8"))
                brut = unary_union([shape(f["geometry"]) for f in gj["features"]])

                def to_merc(lon, lat, _z=None):
                    return (_R_MERC * math.radians(lon),
                            _R_MERC * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))
                _ile_geom = sh_transform(to_merc, brut)
                return _ile_geom
        log.error("ortho-proxy : ile974.geojson introuvable — fondu de côte désactivé")
        _ile_geom = False
        return None


def _tuile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    s = _CIRC / 2 ** z
    mx0 = -_CIRC / 2 + x * s
    my1 = _CIRC / 2 - y * s
    return mx0, my1 - s, mx0 + s, my1


def _alpha_cote(z: int, x: int, y: int):
    """Champ d'alpha « bande côtière » de la tuile (float 256×256 dans [0,1]).

    Retours : ``None`` = tuile entièrement au large (aplat seul → 404 sans requête IGN) ;
    ``"pleine"`` = tuile entièrement dans la bande pleine (photo intacte, relais direct) ;
    sinon le champ (1 sur terre et bande _R1, rampe _R1→_R2, 0 au-delà)."""
    ile = _ile()
    if ile is None:
        return "pleine"     # sans polygone : ne jamais retirer de photo (échec honnête, loggué)
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy.ndimage import distance_transform_edt
    from shapely.geometry import box
    mx0, my0, mx1, my1 = _tuile_bounds(z, x, y)
    if not ile.intersects(box(mx0 - _R2, my0 - _R2, mx1 + _R2, my1 + _R2)):
        return None
    mpp = (mx1 - mx0) / 256.0
    # champ au quart de résolution, avec une marge _R2 pour voir la côte des tuiles voisines
    q = mpp * _QR
    pad = int(math.ceil(_R2 / q)) + 2
    w = 256 // _QR + 2 * pad
    inter = ile.intersection(box(mx0 - pad * q, my0 - pad * q, mx1 + pad * q, my1 + pad * q))
    if inter.is_empty:
        return None
    img = Image.new("L", (w, w), 0)
    d = ImageDraw.Draw(img)
    for g in getattr(inter, "geoms", [inter]):
        if g.geom_type != "Polygon":
            continue
        d.polygon([((mx - mx0) / q + pad, (my1 - my) / q + pad) for mx, my in g.exterior.coords],
                  fill=255)
        for trou in g.interiors:
            d.polygon([((mx - mx0) / q + pad, (my1 - my) / q + pad) for mx, my in trou.coords],
                      fill=0)
    terre = np.asarray(img) > 0
    if not terre.any():
        return None
    dist = distance_transform_edt(~terre) * q
    a = np.clip((_R2 - dist) / (_R2 - _R1), 0.0, 1.0)[pad:pad + 256 // _QR, pad:pad + 256 // _QR]
    if (a <= 0.0).all():
        return None
    if (a >= 1.0).all():
        return "pleine"
    grand = Image.fromarray((a * 255).astype("uint8")).resize((256, 256), Image.BILINEAR)
    return np.asarray(grand).astype("float32") / 255.0


def _traiter(contenu: bytes, alpha, z: int):
    """Applique bande côtière + rognage du blanc no-data. Retours : ``None`` = tuile vide (404),
    ``"relais"`` = rien à changer (octets d'origine), sinon les octets PNG RGBA traités."""
    import numpy as np
    from PIL import Image
    from scipy.ndimage import binary_dilation, distance_transform_edt
    from scipy.ndimage import label as nd_label
    try:
        a = np.asarray(Image.open(io.BytesIO(contenu)).convert("RGB"))
    except Exception:  # noqa: BLE001 — image illisible : on relaie, jamais bloquant
        return "relais"
    champ = np.ones(a.shape[:2], dtype="float32") if isinstance(alpha, str) else alpha.copy()
    if z <= _Z_BLANC_MAX:
        blanc = (a >= 245).all(axis=2)
        if blanc.all():
            return None
        if blanc.any():
            lab, _n = nd_label(blanc)
            bord = (set(lab[0, :].tolist()) | set(lab[-1, :].tolist())
                    | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())) - {0}
            if bord:
                m = np.isin(lab, list(bord))
                # étendre au halo blanchâtre JPEG adjacent, puis fondre sur _FONDU_BLANC_PX
                m = m | (binary_dilation(m, iterations=3) & (a >= 228).all(axis=2))
                if m.all():
                    return None
                champ = champ * np.clip(distance_transform_edt(~m) / _FONDU_BLANC_PX, 0.0, 1.0)
    if (champ <= 1 / 255).all():
        return None
    if (champ >= 254 / 255).all():
        return "relais"
    rgba = np.dstack([a, (champ * 255).astype("uint8")])
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG")
    return buf.getvalue()


def _cache_base(couche: str, z: int, x: int, y: int) -> Path:
    return Path(get_settings().ortho_proxy_cache_dir) / couche / str(z) / f"{x}_{y}"


_MIME = {".png": "image/png", ".jpg": "image/jpeg"}
_HDR = {"Cache-Control": "public, max-age=86400"}


def _cache_lire(base: Path) -> Response | None:
    for ext, mime in _MIME.items():
        p = base.with_suffix(ext)
        if p.exists():
            return Response(p.read_bytes(), media_type=mime, headers=_HDR)
    if base.with_suffix(".mer").exists():
        raise HTTPException(404, "Tuile mer (aplat)")
    return None


def _cache_ecrire(base: Path, ext: str, contenu: bytes) -> None:
    try:
        base.parent.mkdir(parents=True, exist_ok=True)
        tmp = base.with_suffix(ext + ".tmp")
        tmp.write_bytes(contenu)
        tmp.rename(base.with_suffix(ext))
    except OSError as e:   # cache indisponible : on sert quand même, on le dit
        log.warning("ortho-proxy : cache disque inaccessible (%s)", e)


@router.get("/map/tiles/ortho/{couche}/{z}/{x}/{y}")
def ortho_tile(couche: str, z: int, x: int, y: int) -> Response:
    paire = _COUCHES.get(couche)
    if paire is None:
        raise HTTPException(404, "Couche inconnue")
    if not (0 <= z <= 19 and 0 <= x < 2 ** z and 0 <= y < 2 ** z):
        raise HTTPException(404, "Tuile hors grille")
    base = _cache_base(couche, z, x, y)
    servi = _cache_lire(base)
    if servi is not None:
        return servi
    alpha = _alpha_cote(z, x, y) if z <= _Z_FONDU_MAX else "pleine"
    if alpha is None:                          # entièrement au large : jamais de requête IGN
        _cache_ecrire(base, ".mer", b"")
        raise HTTPException(404, "Tuile mer (aplat)")
    layer, fmt = paire
    import requests as _rq
    try:
        r = _rq.get(_WMTS.format(layer=layer, fmt=fmt, z=z, x=x, y=y),
                    headers={"User-Agent": "labuse/1.0"}, timeout=15)
    except Exception as e:  # noqa: BLE001 — WMTS muet : pas de tuile, l'aplat du dessous reste
        log.warning("ortho-proxy %s %s/%s/%s : WMTS muet (%s)", couche, z, x, y, e)
        raise HTTPException(404, "WMTS indisponible") from None
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/"):
        raise HTTPException(404, "Tuile absente")   # transitoire possible : pas mis en cache
    sortie = _traiter(r.content, alpha, z)
    if sortie is None:
        _cache_ecrire(base, ".mer", b"")
        raise HTTPException(404, "Tuile no-data (mer)")
    if sortie == "relais":
        ext = ".png" if r.headers["content-type"].startswith("image/png") else ".jpg"
        _cache_ecrire(base, ext, r.content)
        return Response(r.content, media_type=_MIME[ext], headers=_HDR)
    _cache_ecrire(base, ".png", sortie)
    return Response(sortie, media_type="image/png", headers=_HDR)


# RETOURS-15 U1 — ancien chemin (front en cache navigateur) : même pipeline, couche express.
@router.get("/map/tiles/ortho-express/{z}/{x}/{y}")
def ortho_express_tile(z: int, x: int, y: int) -> Response:
    return ortho_tile("express", z, x, y)
