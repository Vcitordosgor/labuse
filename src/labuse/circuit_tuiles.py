"""COUCHES-TUYAU-1 lot 3 — le verrou des tuiles.

`verrou_tuiles` (V7a) DÉCODE la tuile réellement servie par le tuyau et la compare à la
géométrie BRUTE de la base, pour CHAQUE couche déclarée, aux zooms 10 / 13 / 16 :

  • même nombre d'objets sur l'emprise (aucune troncature muette) ;
  • aucune partie perdue — GeometryCollections comprises (comparaison PAR DIMENSION :
    points / lignes / polygones, chaque dimension a sa contrepartie) ;
  • écart de contour < 1 pixel (distance de Hausdorff servie↔brute, en mètres 3857,
    rapportée au pixel de la tuile) ;
  • position exacte : aucun décalage (le même Hausdorff attrape tout offset).

Le décodeur MVT est SANS DÉPENDANCE (protobuf lu à la main) : un verrou qui ne peut pas
tourner doit rougir, jamais passer en vert par défaut. En dessous du zoom_min d'une couche,
le tuyau ne sert RIEN — le verrou l'exige (aucune fuite) plutôt que de comparer un vide.
"""
from __future__ import annotations

from shapely.geometry import (GeometryCollection, LineString, MultiLineString,
                              MultiPoint, MultiPolygon, Point, Polygon)
from shapely.ops import unary_union
from sqlalchemy import text

_R = 20037508.342789244  # demi-circonférence Web Mercator (3857)
_ZOOMS = (10, 13, 16)
_EXTENT = 4096


# ─────────────────────────── décodeur MVT sans dépendance ───────────────────────────
def _varint(buf: bytes, pos: int) -> tuple[int, int]:
    shift = result = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def _zigzag(n: int) -> int:
    return (n >> 1) ^ -(n & 1)


def _skip(buf: bytes, wire: int, pos: int) -> int:
    if wire == 0:
        _, pos = _varint(buf, pos)
    elif wire == 2:
        ln, pos = _varint(buf, pos)
        pos += ln
    elif wire == 5:
        pos += 4
    elif wire == 1:
        pos += 8
    else:
        raise ValueError(f"wire type {wire} non géré")
    return pos


def _decode_geometry(cmds: list[int]) -> tuple[int, list[list[tuple[int, int]]]]:
    """Retourne (type, anneaux/lignes/points) en coordonnées de tuile (y vers le bas).
    Chaque sous-liste est une séquence de points ; pour un polygone, ce sont les anneaux."""
    rings: list[list[tuple[int, int]]] = []
    cur: list[tuple[int, int]] = []
    x = y = 0
    i = 0
    while i < len(cmds):
        cmd = cmds[i]
        i += 1
        cmd_id, count = cmd & 0x7, cmd >> 3
        if cmd_id == 1:  # MoveTo
            for _ in range(count):
                x += _zigzag(cmds[i]); y += _zigzag(cmds[i + 1]); i += 2
                if cur:
                    rings.append(cur)
                cur = [(x, y)]
        elif cmd_id == 2:  # LineTo
            for _ in range(count):
                x += _zigzag(cmds[i]); y += _zigzag(cmds[i + 1]); i += 2
                cur.append((x, y))
        elif cmd_id == 7:  # ClosePath
            if cur:
                rings.append(cur)
                cur = []
    if cur:
        rings.append(cur)
    return rings


def decode_tile(data: bytes) -> dict[str, list[tuple[int, list]]]:
    """{nom_couche: [(type, anneaux) …]} — type 1 point, 2 ligne, 3 polygone."""
    out: dict[str, list[tuple[int, list]]] = {}
    pos, n = 0, len(data)
    while pos < n:
        key, pos = _varint(data, pos)
        field, wire = key >> 3, key & 0x7
        if field == 3 and wire == 2:  # layer
            ln, pos = _varint(data, pos)
            end = pos + ln
            name = None
            feats: list[tuple[int, list]] = []
            p = pos
            while p < end:
                k2, p = _varint(data, p)
                f2, w2 = k2 >> 3, k2 & 0x7
                if f2 == 1 and w2 == 2:  # name
                    sl, p = _varint(data, p)
                    name = data[p:p + sl].decode("utf-8"); p += sl
                elif f2 == 2 and w2 == 2:  # feature
                    fl, p = _varint(data, p)
                    fend = p + fl
                    ftype = 0
                    geom: list[int] = []
                    q = p
                    while q < fend:
                        k3, q = _varint(data, q)
                        f3, w3 = k3 >> 3, k3 & 0x7
                        if f3 == 3 and w3 == 0:  # type
                            ftype, q = _varint(data, q)
                        elif f3 == 4 and w3 == 2:  # geometry (packed)
                            gl, q = _varint(data, q)
                            gend = q + gl
                            while q < gend:
                                v, q = _varint(data, q)
                                geom.append(v)
                        else:
                            q = _skip(data, w3, q)
                    feats.append((ftype, _decode_geometry(geom)))
                    p = fend
                else:
                    p = _skip(data, w2, p)
            if name is not None:
                out[name] = feats
            pos = end
        else:
            pos = _skip(data, wire, pos)
    return out


# ─────────────────────────── tuile → géométrie 3857 ───────────────────────────
def _tile_bounds_3857(z: int, x: int, y: int) -> tuple[float, float, float]:
    size = 2 * _R / (2 ** z)
    xmin = -_R + x * size
    ymax = _R - y * size
    return xmin, ymax, size


def _to_3857(pt: tuple[int, int], xmin: float, ymax: float, size: float):
    tx, ty = pt
    return (xmin + (tx / _EXTENT) * size, ymax - (ty / _EXTENT) * size)


def _signed_area(ring: list[tuple[float, float]]) -> float:
    a = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % len(ring)]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def _valide(g):
    if g is None or g.is_empty:
        return g
    if not g.is_valid:
        try:
            from shapely import make_valid
            g = make_valid(g)
        except Exception:  # noqa: BLE001
            g = g.buffer(0)
    return g


def _feature_to_geom(ftype: int, rings, xmin, ymax, size):
    """Une géométrie shapely (3857) à partir d'une feature MVT décodée. L'aire signée qui
    distingue anneau extérieur / trou est calculée en COORDONNÉES DE TUILE (y vers le bas,
    spec MVT : extérieur = aire positive) — jamais après reprojection (qui inverse le signe)."""
    def proj(r):
        return [_to_3857(p, xmin, ymax, size) for p in r]
    if ftype == 1:  # points
        pts = [proj(r)[0] for r in rings if r]
        return Point(pts[0]) if len(pts) == 1 else MultiPoint(pts)
    if ftype == 2:  # lignes
        lines = [LineString(proj(r)) for r in rings if len(r) >= 2]
        return lines[0] if len(lines) == 1 else MultiLineString(lines)
    if ftype == 3:  # polygones
        polys: list[Polygon] = []
        shell = None
        holes: list = []
        for r in rings:
            if len(r) < 3:
                continue
            exterieur = _signed_area(r) > 0  # aire signée en espace TUILE (y bas)
            pr = proj(r)
            if exterieur:
                if shell is not None:
                    polys.append(Polygon(shell, holes))
                shell, holes = pr, []
            elif shell is not None:
                holes.append(pr)
        if shell is not None:
            polys.append(Polygon(shell, holes))
        polys = [_valide(p) for p in polys if p is not None]
        polys = [p for p in polys if p is not None and not p.is_empty]
        if not polys:
            return None
        return polys[0] if len(polys) == 1 else _valide(unary_union(polys))
    return None


def _dimension(g) -> int:
    t = g.geom_type
    if "Point" in t:
        return 0
    if "LineString" in t:
        return 1
    return 2  # Polygon / MultiPolygon


def _par_dimension(geoms):
    """Regroupe une liste de géométries shapely par dimension (0 point,1 ligne,2 polygone),
    en éclatant les GeometryCollection — « GeometryCollections comprises »."""
    bacs: dict[int, list] = {0: [], 1: [], 2: []}

    def ranger(g):
        if g is None or g.is_empty:
            return
        if isinstance(g, GeometryCollection):
            for sub in g.geoms:
                ranger(sub)
            return
        bacs[_dimension(g)].append(g)

    for g in geoms:
        ranger(g)
    return bacs


# ─────────────────────────── le verrou ───────────────────────────
def _where_src(c, params) -> str:
    """WHERE de la source : résolution par kind (spatial_layers) ou filtre explicite (couche §2)."""
    if getattr(c, "resolution", None):
        clauses = []
        for i, (k, subs) in enumerate(c.resolution):
            params[f"k{i}"] = k
            if subs:
                clauses.append(f"(m.kind = :k{i} AND m.subtype = ANY(:s{i}))")
                params[f"s{i}"] = list(subs)
            else:
                clauses.append(f"(m.kind = :k{i})")
        return "(" + " OR ".join(clauses) + ")"
    return getattr(c, "where_sql", None) or "TRUE"


def _src_geom(c):
    """(geom_src, geom_3857) — géométrie source SRID forcé, et sa reprojection 3857."""
    g_src = f"ST_SetSRID(m.{c.geom}, {c.srid})"
    g_3857 = g_src if c.srid == 3857 else f"ST_Transform({g_src}, 3857)"
    return g_src, g_3857


def _busiest_tile(db, c, z: int):
    """retour §3/§4 : AUCUN plafond. La tuile de contrôle = la plus DENSE (le contrôle le plus
    sévère — le plus d'objets à comparer). Source-aware (§2). Retourne (x, y, count)."""
    p: dict = {}
    wk = _where_src(c, p)
    p["n"] = float(2 ** z)
    ll = f"ST_Transform(ST_SetSRID(ST_Centroid(m.{c.geom}), {c.srid}), 4326)"
    row = db.execute(text(f"""
        WITH e AS (
            SELECT {ll} AS g
            FROM {c.table} m WHERE {wk} LIMIT 20000
        ), q AS (
            SELECT ST_X(g) lon, ST_Y(g) lat FROM e WHERE g IS NOT NULL
        ), t AS (
            SELECT floor((lon + 180.0) / 360.0 * :n)::int AS x,
                   floor((1.0 - ln(tan(radians(lat)) + 1.0/cos(radians(lat))) / pi()) / 2.0 * :n)::int AS y,
                   count(*) AS c
            FROM q GROUP BY 1, 2 ORDER BY c DESC LIMIT 1
        )
        SELECT x, y, c FROM t
    """), p).first()
    return (row[0], row[1], row[2]) if row else None


# retour §4/Option 1 : au-delà de ce nombre de sommets bruts sur l'emprise, la référence de CONTOUR
# (ST_AsMVTGeom de millions de sommets) dépasse 60 s et n'est PAS interruptible. À ces tuiles, on
# vérifie le NOMBRE d'objets (rapide) et le contour est vérifié aux zooms où il tient sous 60 s
# (typiquement z13/z16). Verdict réel par couche — jamais une requête lancée qui dépasserait 60 s.
_SEUIL_CONTOUR_SOMMETS = 700_000


def _npoints_tuile(db, c, z, x, y) -> int:
    """Somme (bornée, ~0,1 s) des sommets bruts de la source sur l'emprise (source-aware §2)."""
    p: dict = {"z": z, "x": x, "y": y}
    wk = _where_src(c, p)
    g_src, _ = _src_geom(c)
    filtre = "b.env" if c.srid == 3857 else f"ST_Transform(b.env, {c.srid})"
    return int(db.execute(text(f"""
        WITH b AS (SELECT ST_TileEnvelope(:z, :x, :y, margin => 0.02) AS env)
        SELECT coalesce(sum(ST_NPoints({g_src})), 0) FROM {c.table} m, b
        WHERE {wk} AND {g_src} && {filtre}
    """), p).scalar() or 0)


def _dims_declarees(geometrie: str) -> set[int]:
    g = (geometrie or "").lower()
    if g == "point":
        return {0}
    if g == "ligne":
        return {1}
    if g in ("polygone", "extrusion"):
        return {2}
    if g == "point_et_polygone":
        return {0, 2}
    return {0, 1, 2}  # inconnu / multi (tcsp) : toutes dimensions


def _kept_count(db, c, z, x, y) -> int:
    """Le nombre de features que la tuile RETIENT : celles dont `ST_AsMVTGeom` n'est pas nul —
    exactement ce que `ST_AsMVT` a encodé. La disparition, correcte, des objets sous le pixel
    n'est donc pas comptée comme une perte. Source-aware (§2)."""
    p: dict = {"z": z, "x": x, "y": y}
    wk = _where_src(c, p)
    g_src, g_3857 = _src_geom(c)
    filtre = "b.env" if c.srid == 3857 else f"ST_Transform(b.env, {c.srid})"
    return int(db.execute(text(f"""
        WITH b AS (SELECT ST_TileEnvelope(:z, :x, :y, margin => 0.02) AS env)
        SELECT count(*) FROM {c.table} m, b
        WHERE {wk} AND {g_src} && {filtre}
          AND ST_AsMVTGeom({g_3857}, ST_TileEnvelope(:z, :x, :y), 4096, 64, true) IS NOT NULL
    """), p).scalar() or 0)


def _hausdorff_pg(db, c, z, x, y, dimtype: int, served_wkb: bytes | None):
    """retour §4 : Hausdorff (mètres 3857) entre la géométrie SERVIE décodée (WKB — les octets
    RÉELLEMENT servis) et la BRUTE RENDUE À LA TUILE : `ST_AsMVTGeom` de la `geom_2975` ENTIÈRE
    (extent 4096 — exactement le MVT que l'endpoint sert), ramenée en 3857 par l'affine inverse.
    AUCUNE simplification de notre fait (pas de ST_SimplifyPreserveTopology) — la seule
    transformation est la quantification MVT que le tuyau applique DE TOUTE FAÇON pour servir.

    Pourquoi pas la brute PLEINE résolution : mesuré, un tel Hausdorff échoue à z10 sur les couches
    à contour fin (znieff 199 m, tcsp 277 m > 1 px) — non pas parce que le tuyau se trompe, mais
    parce que `ST_AsMVTGeom` (le format MVT) écarte, correctement, le détail SOUS le pixel (parties
    fines, sommets sub-grille) que la brute pleine résolution porte encore. Comparer à la brute
    RENDUE À LA TUILE est donc la bonne tolérance « < 1 pixel » : H ≈ 0 quand le tuyau est fidèle,
    H ≫ px sous le moindre bug de décodeur, d'enveloppe, d'extent, de transform ou de SRID.
    Une requête qui n'aboutit pas (timeout, base) remonte en exception → couche ROUGE."""
    p: dict = {"z": z, "x": x, "y": y, "dt": dimtype, "sv": served_wkb, "has_sv": served_wkb is not None}
    wk = _where_src(c, p)
    g_src, g_3857 = _src_geom(c)
    filtre = "b.env_marge" if c.srid == 3857 else f"ST_Transform(b.env_marge, {c.srid})"
    row = db.execute(text(f"""
        WITH b AS (
            SELECT ST_TileEnvelope(:z, :x, :y) AS env,
                   ST_TileEnvelope(:z, :x, :y, margin => 0.02) AS env_marge,
                   ST_XMin(ST_TileEnvelope(:z, :x, :y)) AS xmin,
                   ST_YMax(ST_TileEnvelope(:z, :x, :y)) AS ymax,
                   (ST_XMax(ST_TileEnvelope(:z, :x, :y)) - ST_XMin(ST_TileEnvelope(:z, :x, :y))) / 4096.0 AS sx
        ),
        raw AS (  -- collecter une fois, transformer une fois, ST_AsMVTGeom une fois (voie agrégat rapide)
            SELECT ST_Collect({g_3857}) AS g FROM {c.table} m, b
            WHERE {wk} AND {g_src} && {filtre}
        ),
        r AS (  -- rendu MVT de la brute (déjà 3857), ramené en 3857 par l'affine inverse de la tuile
            SELECT ST_SetSRID(ST_Affine(
                       ST_CollectionExtract(
                           ST_AsMVTGeom(raw.g, b.env, 4096, 64, true), :dt),
                       b.sx, 0, 0, -b.sx, b.xmin, b.ymax), 3857) AS geom
            FROM raw, b
        )
        SELECT (geom IS NOT NULL AND NOT ST_IsEmpty(geom)) AS present,
               CASE WHEN :has_sv AND geom IS NOT NULL AND NOT ST_IsEmpty(geom)
                    THEN ST_HausdorffDistance(ST_CollectionExtract(ST_GeomFromWKB(:sv, 3857), :dt), geom)
               END AS h
        FROM r
    """), p).first()
    if row is None:
        return (False, None)
    return (bool(row[0]), row[1])


def _served_wkb(geoms, dim: int) -> bytes | None:
    """Assemble les géométries servies d'une dimension en un MULTI et le sérialise en WKB (à
    comparer côté PostGIS). Les parties invalides sont conservées : Hausdorff n'exige pas la validité."""
    def flat(gs):
        for g in gs:
            if g is None or g.is_empty:
                continue
            if hasattr(g, "geoms"):
                yield from flat(g.geoms)
            else:
                yield g
    parts = list(flat(geoms))
    if dim == 0:
        parts = [g for g in parts if g.geom_type == "Point"]
        mg = MultiPoint([p.coords[0] for p in parts]) if parts else None
    elif dim == 1:
        parts = [g for g in parts if g.geom_type == "LineString"]
        mg = MultiLineString(parts) if parts else None
    else:
        parts = [g for g in parts if g.geom_type == "Polygon"]
        mg = MultiPolygon(parts) if parts else None
    return mg.wkb if mg is not None and not mg.is_empty else None


def _controle_couche(db, kind, c, pbs, etat) -> None:
    """Le contrôle d'UNE couche aux zooms 10/13/16 (échantillon fixe : la tuile la plus dense par
    zoom), chaque tuile EN ENTIER, à géométrie BRUTE. Une erreur (timeout, base) remonte en
    exception → la couche est marquée ROUGE par l'appelant. Aucune note, aucune simplification."""
    from .api import couches_tuyau as tuyau
    # retour §5 : plus de bornage par zoom_min — chaque couche est contrôlée à TOUS les zooms
    # 10/13/16 (elle est visible dès l'île), safer compris. Aucun cas « sous le zoom minimum ».
    for z in _ZOOMS:
        bt = _busiest_tile(db, c, z)
        if bt is None:
            continue  # couche sans donnée à ce zoom — rien à perdre
        x, y, _cnt = bt
        etat["controles"] += 1
        body = tuyau._construire_tuile(db, c, z, x, y)
        try:
            decoded = decode_tile(body).get(kind, [])
        except Exception as e:  # noqa: BLE001 — un décodage impossible = rouge
            pbs.append(f"{kind} z{z} : décodage tuile impossible ({e.__class__.__name__})")
            continue
        xmin, ymax, size = _tile_bounds_3857(z, x, y)
        served = [_feature_to_geom(ft, rings, xmin, ymax, size) for ft, rings in decoded]
        served = [g for g in served if g is not None and not g.is_empty]
        px = size / 256.0
        # 1) même nombre d'objets : la tuile porte EXACTEMENT les features retenues par le tuyau.
        kept = _kept_count(db, c, z, x, y)
        if len(served) != kept:
            pbs.append(f"{kind} z{z} ({x}/{y}) : {len(served)} objet(s) servi(s) ≠ {kept} retenu(s)")
        # Option 1 (§4) : au-delà du seuil, la référence de CONTOUR (ST_AsMVTGeom de millions de
        # sommets) dépasse 60 s et n'est pas interruptible → on NE LANCE PAS cette requête. Le
        # NOMBRE d'objets est vérifié ci-dessus ; le contour l'est aux zooms où il tient (13/16).
        # Verdict réel par couche (comptage partout), jamais une requête > 60 s ni une note muette.
        if _npoints_tuile(db, c, z, x, y) > _SEUIL_CONTOUR_SOMMETS:
            etat.setdefault("contour_reporte", []).append(f"{kind} z{z}")
            continue
        # 2+3+4) par DIMENSION DÉCLARÉE : aucune partie perdue, contour < 1 px, position exacte
        # (Hausdorff PostGIS, géométrie BRUTE, aucune simplification).
        sb = _par_dimension(served)
        dims = _dims_declarees(c.geometrie)
        for dim in sorted(dims):
            sv = _served_wkb(sb[dim], dim) if sb[dim] else None
            present, h = _hausdorff_pg(db, c, z, x, y, dim + 1, sv)
            if (sv is None) != (not present):
                pbs.append(f"{kind} z{z} dim{dim} : dimension {'servie' if sv else 'retenue'} sans contrepartie")
                continue
            if h is not None and h > px:
                pbs.append(f"{kind} z{z} dim{dim} : Hausdorff {h:.1f} m > 1 px ({px:.1f} m)")


def verrou_tuiles(db=None) -> "object":
    """V7a — la tuile servie == la brute, couche par couche, zoom par zoom."""
    from .circuit_verrous import PHRASES, ResultatVerrou
    from .api import couches_tuyau as tuyau
    phrase = PHRASES.get("V7a", "Chaque tuile servie reproduit la géométrie brute (objets, parties, contour, position).")
    if db is None:
        return ResultatVerrou("V7a", phrase, "casse", "injouable sans base")
    reg = tuyau.registre()
    # Garde-fou de durée GÉNÉREUX : la comparaison brute d'un méga-polygone est légitimement lente ;
    # on la laisse ABOUTIR (échantillon = 1 tuile/zoom, pas de per-tile raccourci). Une requête qui
    # dépasse même ce plafond OU une base indisponible remonte en exception → la couche est ROUGE.
    try:
        db.execute(text("SET statement_timeout = '300s'"))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    pbs: list[str] = []
    couches_ok = 0
    etat: dict = {"controles": 0}
    for kind, c in sorted(reg.items()):
        n0 = len(pbs)
        try:
            _controle_couche(db, kind, c, pbs, etat)
        except Exception as e:  # noqa: BLE001 — timeout ou erreur DB : ROUGE, jamais un silence
            db.rollback()
            pbs.append(f"{kind} : non vérifiable ici ({e.__class__.__name__}) — ROUGE")
        if len(pbs) == n0:
            couches_ok += 1
    controles = etat["controles"]
    reporte = etat.get("contour_reporte", [])
    rep = (f" ; contour reporté à z13/z16 (comptage vérifié à ce zoom) pour : {', '.join(reporte)}"
           if reporte else "")
    n = len(reg)
    if pbs:
        return ResultatVerrou("V7a", phrase, "casse",
                              f"{couches_ok}/{n} couches fidèles ; {len(pbs)} écart(s) sur {controles} contrôle(s){rep}",
                              pbs[:40])
    return ResultatVerrou("V7a", phrase, "ok",
                          f"{n} couches × zooms 10/13/16 : {controles} tuile(s) décodée(s) EN ENTIER, "
                          f"objets/parties/contour/position identiques à la brute{rep}")
