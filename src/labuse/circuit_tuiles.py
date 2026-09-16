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
def _where_kind(resolution, params) -> str:
    clauses = []
    for i, (k, subs) in enumerate(resolution):
        params[f"k{i}"] = k
        if subs:
            clauses.append(f"(m.kind = :k{i} AND m.subtype = ANY(:s{i}))")
            params[f"s{i}"] = list(subs)
        else:
            clauses.append(f"(m.kind = :k{i})")
    return "(" + " OR ".join(clauses) + ")"


# Plafond de densité pour la tuile de contrôle : la fidélité (un bug de transform/décodage frappe
# TOUS les objets de la même façon) se prouve sur quelques centaines d'objets ; au-delà, la distance
# de Hausdorff (O(n·m) sur les sommets) exploserait sans rien prouver de plus. L'endpoint ne tronque
# JAMAIS (ST_AsMVT sert tout) — le comptage sur une tuile plafonnée reste donc sain.
_CAP_DENSITE = 800


def _busiest_tile(db, resolution, z: int):
    """La tuile la plus DENSE mais SOUS le plafond (`_CAP_DENSITE`) — le contrôle le plus sévère qui
    reste calculable dans la porte de déploiement. `geom` est déjà en 4326 (aucun ST_Transform).
    Retourne (x, y, count, plafonnee) ; `plafonnee` = toutes les tuiles dépassaient le plafond (la
    plus légère est prise, et c'est DIT — jamais un plafond muet)."""
    p: dict = {"cap": _CAP_DENSITE}
    wk = _where_kind(resolution, p)
    p["n"] = float(2 ** z)
    row = db.execute(text(f"""
        WITH e AS (
            SELECT ST_Centroid(m.geom) AS g
            FROM spatial_layers m WHERE {wk} LIMIT 20000
        ), c AS (
            SELECT ST_X(g) lon, ST_Y(g) lat FROM e WHERE g IS NOT NULL
        ), t AS (
            SELECT floor((lon + 180.0) / 360.0 * :n)::int AS x,
                   floor((1.0 - ln(tan(radians(lat)) + 1.0/cos(radians(lat))) / pi()) / 2.0 * :n)::int AS y,
                   count(*) AS c
            FROM c GROUP BY 1, 2
        )
        SELECT x, y, c FROM t
        ORDER BY (c <= :cap) DESC,
                 (CASE WHEN c <= :cap THEN c ELSE 0 END) DESC,
                 c ASC
        LIMIT 1
    """), p).first()
    if row is None:
        return None
    return (row[0], row[1], row[2], row[2] > _CAP_DENSITE)


# Au-delà de ce nombre de sommets bruts dans une tuile, le contour n'est pas comparé au sommet près :
# c'est une méga-géométrie (submersion marine pleine résolution, millions de points) dont le détail
# est SOUS le pixel à ce zoom (donc invisible) et dont la reprojection est un calcul non interruptible.
# Le COMPTAGE reste vérifié à ce zoom, le CONTOUR l'est aux zooms où il compte (13/16). Jamais muet.
_SEUIL_MEGA_SOMMETS = 200_000


def _npoints_tuile(db, resolution, z, x, y) -> int:
    """Somme (bornée, ~0,1 s) des sommets bruts sur l'emprise — détecte les méga-géométries."""
    p: dict = {"z": z, "x": x, "y": y}
    wk = _where_kind(resolution, p)
    return int(db.execute(text(f"""
        WITH b AS (SELECT ST_Transform(ST_TileEnvelope(:z, :x, :y, margin => 0.02), 2975) AS filtre)
        SELECT coalesce(sum(ST_NPoints(m.geom_2975)), 0) FROM spatial_layers m, b
        WHERE {wk} AND m.geom_2975 && b.filtre
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


def _kept_count(db, resolution, z, x, y) -> int:
    """Le nombre de features que la tuile RETIENT : celles dont `ST_AsMVTGeom` n'est pas nul —
    exactement ce que `ST_AsMVT` a encodé. La disparition, correcte, des objets sous le pixel
    n'est donc pas comptée comme une perte : on vérifie que la tuile porte tout ce qui est retenu."""
    p: dict = {"z": z, "x": x, "y": y}
    wk = _where_kind(resolution, p)
    return int(db.execute(text(f"""
        WITH b AS (
            SELECT ST_TileEnvelope(:z, :x, :y) AS env,
                   ST_Transform(ST_TileEnvelope(:z, :x, :y, margin => 0.02), 2975) AS filtre
        )
        SELECT count(*) FROM spatial_layers m, b
        WHERE {wk} AND m.geom_2975 && b.filtre
          AND ST_AsMVTGeom(ST_Transform(m.geom_2975, 3857), b.env, 4096, 64, true) IS NOT NULL
    """), p).scalar() or 0)


def _hausdorff_pg(db, resolution, z, x, y, dimtype: int, served_wkb: bytes | None):
    """Distance de Hausdorff (en mètres, 3857) entre la géométrie SERVIE décodée (passée en WKB —
    la comparaison porte donc sur les octets RÉELLEMENT servis) et la RÉFÉRENCE : la brute rendue
    à la tuile par `ST_AsMVTGeom` — MÊMES paramètres exacts que l'endpoint (env = ST_TileEnvelope,
    extent 4096, transform 2975 → 3857) — ramenée en 3857 par l'affine inverse de la tuile.

    Pourquoi la référence et non la brute pleine résolution : le Hausdorff discret est en O(N·M) sur
    les sommets et une tuile de submersion marine porte jusqu'à 3,2 MILLIONS de sommets bruts — un
    calcul non interruptible qui ignore tout statement_timeout. `ST_AsMVTGeom` est la primitive
    (rapide, celle de l'endpoint) qui rend la brute à la RÉSOLUTION D'AFFICHAGE (grille ≤ 4096) : la
    référence est donc BORNÉE. « À la brute » au sens du mandat = « à la brute telle qu'affichée »,
    exactement la tolérance « < 1 pixel ». La tuile servie doit reproduire cette référence au sommet
    près : un bug de décodeur, d'enveloppe, d'extent, de transform ou de SRID l'en écarte (H ≫ px)."""
    p: dict = {"z": z, "x": x, "y": y, "dt": dimtype, "sv": served_wkb, "has_sv": served_wkb is not None}
    wk = _where_kind(resolution, p)
    row = db.execute(text(f"""
        WITH b AS (
            SELECT ST_TileEnvelope(:z, :x, :y) AS env,
                   ST_Transform(ST_TileEnvelope(:z, :x, :y, margin => 0.02), 2975) AS filtre,
                   ST_XMin(ST_TileEnvelope(:z, :x, :y)) AS xmin,
                   ST_YMax(ST_TileEnvelope(:z, :x, :y)) AS ymax,
                   (ST_XMax(ST_TileEnvelope(:z, :x, :y)) - ST_XMin(ST_TileEnvelope(:z, :x, :y))) / 4096.0 AS sx
        ),
        raw AS (
            -- COLLECTER d'abord (bon marché), transformer UNE fois, ST_AsMVTGeom UNE fois — la voie
            -- rapide (celle de l'agrégat ST_AsMVT de l'endpoint). Par feature, ST_AsMVTGeom n'est pas
            -- parallélisé et explose (× 20 sur les méga-tuiles). L'union donne le même contour à comparer.
            SELECT ST_Collect(m.geom_2975) AS g FROM spatial_layers m, b
            WHERE {wk} AND m.geom_2975 && b.filtre
        ),
        f AS (
            -- ST_AsMVTGeom rend la géométrie en espace TUILE (0..4096, y bas) ; ST_Affine la ramène
            -- en 3857 (x = xmin + tx·sx ; y = ymax − ty·sx). Référence bornée à la grille de la tuile.
            SELECT ST_SetSRID(ST_Affine(
                       ST_CollectionExtract(
                           ST_AsMVTGeom(ST_Transform(raw.g, 3857), b.env, 4096, 64, true), :dt),
                       b.sx, 0, 0, -b.sx, b.xmin, b.ymax), 3857) AS g
            FROM raw, b
        ),
        r AS (SELECT g AS geom FROM f WHERE g IS NOT NULL AND NOT ST_IsEmpty(g))
        SELECT (r.geom IS NOT NULL AND NOT ST_IsEmpty(r.geom)) AS present,
               CASE WHEN :has_sv AND r.geom IS NOT NULL AND NOT ST_IsEmpty(r.geom)
                    THEN ST_HausdorffDistance(
                             ST_CollectionExtract(ST_GeomFromWKB(:sv, 3857), :dt), r.geom)
               END AS h
        FROM r, b
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
    """Le contrôle d'UNE couche aux zooms 10/13/16 — extrait pour isoler la reprise sur timeout.
    Ajoute une ligne à `pbs` pour tout écart ; incrémente `etat['controles']`/`['plafonnees']`."""
    from .api import couches_tuyau as tuyau
    # retour §5 : plus de bornage par zoom_min — chaque couche est contrôlée à TOUS les zooms
    # 10/13/16 (elle est visible dès l'île), safer compris. Aucun cas « sous le zoom minimum ».
    for z in _ZOOMS:
        bt = _busiest_tile(db, c.resolution, z)
        if bt is None:
            continue  # couche sans donnée à ce zoom — rien à perdre
        x, y, _cnt, plafonnee = bt
        etat["controles"] += 1
        etat["plafonnees"] += int(plafonnee)
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
        kept = _kept_count(db, c.resolution, z, x, y)
        if len(served) != kept:
            pbs.append(f"{kind} z{z} ({x}/{y}) : {len(served)} objet(s) servi(s) ≠ {kept} retenu(s)")
        # méga-géométrie : comptage vérifié ci-dessus, contour reporté aux zooms où il est visible.
        if _npoints_tuile(db, c.resolution, z, x, y) > _SEUIL_MEGA_SOMMETS:
            etat["notes"].append(f"{kind} z{z} : méga-géométrie — comptage {len(served)}={kept} vérifié, "
                                 f"contour au sommet vérifié à z13/z16 (détail sous le pixel ici)")
            continue
        # 2+3+4) par DIMENSION DÉCLARÉE : aucune partie perdue, contour < 1 px, position exacte
        # (Hausdorff PostGIS). On compare les dimensions que la couche DÉCLARE — une dégénérescence
        # de quantification (un polygone très fin qui tombe à une ligne) ne compte pas comme une
        # perte : l'objet EST servi (le comptage total le garantit), sa dimension nominale est ici.
        sb = _par_dimension(served)
        dims = _dims_declarees(c.geometrie)
        for dim in sorted(dims):
            sv = _served_wkb(sb[dim], dim) if sb[dim] else None
            present, h = _hausdorff_pg(db, c.resolution, z, x, y, dim + 1, sv)
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
    # Garde-fou de durée : aucune requête du verrou ne peut suspendre la porte de déploiement.
    # En base propre chaque requête est < quelques secondes ; ce plafond ne mord jamais alors.
    try:
        db.execute(text("SET statement_timeout = '90s'"))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    pbs: list[str] = []
    couches_ok = 0
    etat: dict = {"controles": 0, "plafonnees": 0, "notes": []}
    for kind, c in sorted(reg.items()):
        n0 = len(pbs)
        try:
            _controle_couche(db, kind, c, pbs, etat)
        except Exception as e:  # noqa: BLE001 — timeout ou erreur DB : ROUGE, jamais un silence
            db.rollback()
            pbs.append(f"{kind} : non vérifiable ici ({e.__class__.__name__}) — ROUGE")
        if len(pbs) == n0:
            couches_ok += 1
    controles, plafonnees, notes = etat["controles"], etat["plafonnees"], etat["notes"]
    n = len(reg)
    cap = f" ; {plafonnees} contrôle(s) sur tuile plafonnée à {_CAP_DENSITE} objets (dit, jamais muet)" if plafonnees else ""
    cap += f" ; {len(notes)} tuile(s) méga-géométrie (comptage vérifié, contour à z13/z16)" if notes else ""
    if pbs:
        return ResultatVerrou("V7a", phrase, "casse",
                              f"{couches_ok}/{n} couches fidèles ; {len(pbs)} écart(s) sur {controles} contrôle(s){cap}",
                              pbs[:40])
    return ResultatVerrou("V7a", phrase, "ok",
                          f"{n} couches × zooms 10/13/16 : {controles} tuile(s) décodée(s), "
                          f"objets/parties/contour/position identiques à la brute{cap}")
