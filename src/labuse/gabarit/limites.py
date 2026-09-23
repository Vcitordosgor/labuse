"""Classification des limites de parcelle v2 (GABARIT-2).

GABARIT-1 a mesuré que « voisin cadastré à 0,5 m = séparative » se trompe en centre-ville,
où les rues sont elles-mêmes des parcelles cadastrées : la façade sur rue était classée
« séparative ». v2 inverse l'ordre — **la route d'abord** :

  1. VOIE si un tronçon BD TOPO carrossable passe à ≤ largeur/2 + 1,5 m de l'arête
     (attribut `largeur` ; à défaut 4 m). Priorité absolue.
  2. VOIE si le voisin cadastré collé à l'arête est une **parcelle de voirie**
     (traversée par un axe BD TOPO ET sans bâti).
  3. SÉPARATIVE si voisin cadastré ≤ 0,5 m et rien de ce qui précède.
  4. NON CLASSÉE (bloquant, motif nommé) : ni voie ni voisin (ravine, littoral, domaine
     public non routier), ou arête résiduelle < 1 m.
  5. side / rear : rear = séparative sans point commun avec une arête voie ;
     parcelle sans aucune arête voie (enclave / drapeau) → bloquant.

Le cœur `classify_edges` est PUR (géométries en entrée, EPSG:2975, aucune DB) et testable ;
`classify_parcel_limits` fait les requêtes PostGIS puis appelle le cœur.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry

# natures BD TOPO carrossables qui qualifient une « voie » (recul voie). Sentier/Escalier exclus.
ROAD_NATURES_EXCLUES = {"Sentier", "Escalier"}

SEP_TOL_M = 0.5        # voisin cadastré collé à l'arête
# marge au-delà de la demi-chaussée (axe BD TOPO → bord de parcelle). Mandat GABARIT-2 : 1,5 m ;
# A0-2 : calibré 3,5 m (axe à demi-chaussée + trottoir). GABARIT-3 lot D : 4,0 m — capte les frontages
# légèrement en retrait (~5,6 m de l'axe, ex. AE0256) ; audité 0 faux-voie sur les 70 (A0-3-MESURE.md).
# La surface de route BD TOPO (qui trancherait sans marge) n'est pas en base → GABARIT-4.
ROAD_EXTRA_M = 4.0
DEFAULT_WIDTH_M = 4.0  # largeur de tronçon par défaut si l'attribut manque
SIMPLIFY_M = 0.05      # ne retire que le bruit GPS sub-décimétrique (jamais un vrai chanfrein)
CHUNK_M = 3.0          # densification : on classe des tronçons ≤ 3 m par leur MILIEU (évite l'artefact
                       # de coin où un segment ne touche un voisin qu'à son sommet)
MIN_EDGE_M = 1.0       # run non classé sous ce cumul = négligeable (n'affiche ni ne bloque)
# GABARIT-6 lot A : une arête « non classée » qui est un simple artefact de numérisation (< MIN_EDGE_M
# ET < RESIDUAL_MAX_PERIM_FRAC du périmètre de la parcelle) est rattachée à l'arête adjacente la plus
# longue (héritage type + source), tracée, et cesse de bloquer. Au-delà de 2 % du périmètre (parcelle
# minuscule), une arête < 1 m reste significative → bloque comme avant.
RESIDUAL_MAX_PERIM_FRAC = 0.02

MOTIF_NON_QUALIFIEE = "arête sans voie ni voisin cadastré (ravine, littoral ou domaine public non routier)"
MOTIF_ARETE_COURTE = "arête résiduelle < 1 m, non classable"
MOTIF_SANS_FACADE = "parcelle sans façade sur voie (enclave ou accès en drapeau)"
MOTIF_VOIE_PRIVEE = "desservie par une voie privée : le règlement ne précise pas le recul"

# --- parcelle de voie privée (GABARIT-5, E2) : trois critères OBLIGATOIRES, aucun seul ne suffit.
PRIVATE_ROAD_MIN_ELONGATION = 5.0   # allongement L/l de l'enveloppe orientée (chemin, pas un lot)
PRIVATE_ROAD_MAX_WIDTH_M = 6.0      # largeur (petit côté OBB) d'une voie privée : au-delà = lot, pas un chemin
# « touche une voie BD TOPO à une extrémité » : la BD TOPO donne l'AXE (centre de chaussée) ; le débouché
# d'un chemin est donc à ~ demi-chaussée + accotement de l'axe. On aligne ce seuil sur la portée-façade de
# la classification voie (demi-chaussée par défaut 2 m + marge 4 m = 6 m), sinon un débouché réel est manqué.
PRIVATE_ROAD_TOUCH_M = 6.0
PRIVATE_ROAD_AXIS_MAX_M = 3.0       # un axe BD TOPO courant DANS la parcelle sur > 3 m = voirie (pas privée)


def obb_dims(perimeter: Optional[float], area: Optional[float]) -> Optional[tuple[float, float]]:
    """(longueur, largeur) d'un rectangle (enveloppe orientée ST_OrientedEnvelope) depuis son périmètre
    et son aire : L+l = P/2, L·l = A → L,l racines de t² − (P/2)t + A. None si non calculable."""
    if not perimeter or not area or area <= 0:
        return None
    s = perimeter / 2.0
    disc = s * s - 4.0 * area
    root = math.sqrt(disc) if disc > 0 else 0.0
    L = (s + root) / 2.0
    w = (s - root) / 2.0
    if w <= 0:
        return None
    return (L, w)


def elongation_from_obb(perimeter: Optional[float], area: Optional[float]) -> Optional[float]:
    """Allongement L/l de l'enveloppe orientée. None si non calculable."""
    d = obb_dims(perimeter, area)
    return None if d is None else d[0] / d[1]


def is_private_road_parcel(*, has_bati: bool, elongation: Optional[float], width_m: Optional[float],
                           touches_road: bool, axis_len_inside_m: Optional[float]) -> bool:
    """Une parcelle voisine est-elle une VOIE PRIVÉE cadastrée (E2) ? Critères obligatoires, aucun seul
    ne suffit : (1) sans bâti, (2) allongée ET étroite — L/l ≥ 5 et largeur ≤ 6 m (un chemin, pas un lot
    allongé), (3) raccordée au réseau BD TOPO à une extrémité SANS être elle-même une voie BD TOPO (aucun
    axe carrossable ne la traverse sur plus de 3 m — sinon c'est une parcelle-voirie, déjà traitée)."""
    if has_bati:
        return False
    if elongation is None or elongation < PRIVATE_ROAD_MIN_ELONGATION:
        return False
    if width_m is None or width_m > PRIVATE_ROAD_MAX_WIDTH_M:
        return False
    if not touches_road:
        return False
    if axis_len_inside_m is not None and axis_len_inside_m > PRIVATE_ROAD_AXIS_MAX_M:
        return False
    return True


@dataclass
class Edge:
    """Une arête classée du contour (géométrie en 2975)."""
    geom: LineString
    type: str                 # 'voie' | 'side' | 'rear' | 'nonclass'
    length_m: float
    motif: Optional[str] = None
    source_kind: Optional[str] = None   # pour 'voie' : 'bdtopo' | 'emprise_publique'
    ring: Optional[int] = None          # index de l'anneau extérieur (adjacence cyclique par anneau)
    attached: bool = False              # GABARIT-6 : micro-arête résiduelle rattachée à sa voisine


@dataclass
class Road:
    line: LineString          # axe BD TOPO (2975)
    largeur_m: Optional[float]


def _segments(ring_coords) -> list[LineString]:
    return [LineString([ring_coords[i], ring_coords[i + 1]]) for i in range(len(ring_coords) - 1)]


def _chunks(ring_coords, chunk: float) -> list[LineString]:
    """Densifie le contour en tronçons ≤ `chunk` m (pour classer par le milieu)."""
    out: list[LineString] = []
    for seg in _segments(ring_coords):
        L = seg.length
        if L <= chunk:
            out.append(seg)
            continue
        n = int(L // chunk) + 1
        pts = [seg.interpolate(i / n, normalized=True) for i in range(n + 1)]
        for i in range(n):
            out.append(LineString([pts[i], pts[i + 1]]))
    return out


def _key(pt) -> tuple:
    return (round(pt[0], 3), round(pt[1], 3))


def classify_edges(
    parcel_2975: BaseGeometry,
    neighbors: list[tuple[BaseGeometry, bool]],   # (geom, is_road_parcel)
    roads: list[Road],
    *,
    sep_tol: float = SEP_TOL_M,
    road_extra: float = ROAD_EXTRA_M,
    default_width: float = DEFAULT_WIDTH_M,
    simplify: float = SIMPLIFY_M,
    chunk: float = CHUNK_M,
    min_edge: float = MIN_EDGE_M,
    emprises_publiques: bool = False,
    private_roads: Optional[list[BaseGeometry]] = None,
    voies_privees: bool = False,
) -> list[Edge]:
    """Cœur PUR. Classe CHAQUE segment brut du contour (route d'abord), puis fusionne les
    segments CONSÉCUTIFS de même type en arêtes logiques. Une même « face » cadastrale peut
    être en partie sur voie, en partie sur voisin (segments distincts) — on ne les mélange pas."""
    poly = parcel_2975.simplify(simplify, preserve_topology=True)  # bruit GPS seulement
    # tous les anneaux extérieurs (un morceau constructible à cheval peut être un MultiPolygon)
    polys = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
    rings = [list(g.exterior.coords) for g in polys if g.geom_type == "Polygon" and not g.is_empty]

    # (ring_idx, seg, type, motif, source_kind)
    seg_types: list[tuple[int, LineString, str, Optional[str], Optional[str]]] = []
    for ri, coords in enumerate(rings):
        for seg in _chunks(coords, chunk):
            L = seg.length
            mid = seg.interpolate(0.5, normalized=True)   # milieu : évite l'artefact de coin
            near = [(g, is_road) for (g, is_road) in neighbors if mid.distance(g) <= sep_tol]
            near_road = any(is_road for (_g, is_road) in near)
            near_real = any(not is_road for (_g, is_road) in near)
            near_private = any(mid.distance(g) <= sep_tol for g in (private_roads or []))
            # deux portées de route : sur la chaussée (≤ largeur/2) vs à portée de façade (+ marge).
            road_on = road_near = False
            for r in roads:
                w = r.largeur_m if r.largeur_m and r.largeur_m > 0 else default_width
                d = mid.distance(r.line)
                if d <= w / 2.0:
                    road_on = road_near = True
                    break
                if d <= w / 2.0 + road_extra:
                    road_near = True
            # Priorité : voisin-voirie / axe dans l'emprise → voie (même avec voisin réel) ; voisin réel
            # → séparative ; arête ouverte à portée façade → voie ; arête ouverte + emprises publiques → voie.
            if near_road or road_on or road_near:
                if near_real and not (near_road or road_on):
                    seg_types.append((ri, seg, "sep", None, None))
                else:
                    seg_types.append((ri, seg, "voie", None, "bdtopo"))
            elif near_private:
                # arête collée à une parcelle de voie privée : résolue APRÈS la boucle, selon que la
                # parcelle a (ou non) une façade sur voie PUBLIQUE — cf. bloc « résolution priv » plus bas.
                seg_types.append((ri, seg, "priv", None, None))
            elif near_real:
                seg_types.append((ri, seg, "sep", None, None))
            elif emprises_publiques and L >= min_edge:
                seg_types.append((ri, seg, "voie", None, "emprise_publique"))
            else:
                motif = MOTIF_ARETE_COURTE if L < min_edge else MOTIF_NON_QUALIFIEE
                seg_types.append((ri, seg, "nonclass", motif, None))

    # résolution des arêtes « priv » (collées à une voie privée cadastrée). Portée aux ENCLAVES seules :
    # si la parcelle a une façade sur voie PUBLIQUE (bdtopo / emprise publique), le chemin privé n'est
    # qu'une limite → séparative (aucune régression sur les parcelles desservies). Sinon (enclave E2) :
    # voie si la citation PLU vise les voies privées, sinon arête non qualifiée motivée (bloc honnête).
    has_public_voie = any(t == "voie" for (_ri, _s, t, _m, _sk) in seg_types)
    resolved_priv: list[tuple[int, LineString, str, Optional[str], Optional[str]]] = []
    for (ri, seg, t, m, sk) in seg_types:
        if t == "priv":
            if has_public_voie:
                resolved_priv.append((ri, seg, "sep", None, None))
            elif voies_privees:
                resolved_priv.append((ri, seg, "voie", None, "voie_privee"))
            else:
                resolved_priv.append((ri, seg, "nonclass", MOTIF_VOIE_PRIVEE, None))
        else:
            resolved_priv.append((ri, seg, t, m, sk))
    seg_types = resolved_priv

    # side / rear : rear = séparative ne partageant aucun sommet avec un segment voie
    voie_pts: set[tuple] = set()
    for _ri, seg, t, _m, _sk in seg_types:
        if t == "voie":
            for c in seg.coords:
                voie_pts.add(_key(c))
    resolved: list[tuple[int, LineString, str, Optional[str], Optional[str]]] = []
    for ri, seg, t, m, sk in seg_types:
        if t == "sep":
            touche = any(_key(c) in voie_pts for c in seg.coords)
            resolved.append((ri, seg, "side" if touche else "rear", None, None))
        else:
            resolved.append((ri, seg, t, m, sk))

    # fusion des segments consécutifs de même (anneau, type, source_kind) en arêtes logiques
    edges: list[Edge] = []
    run_pts: list = []
    run_type: Optional[str] = None
    run_motif: Optional[str] = None
    run_sk: Optional[str] = None
    run_ring: Optional[int] = None

    def _flush():
        nonlocal run_pts, run_type, run_motif, run_sk, run_ring
        if run_type and len(run_pts) >= 2:
            line = LineString(run_pts)
            edges.append(Edge(line, run_type, line.length, run_motif, run_sk, ring=run_ring))
        run_pts, run_type, run_motif, run_sk, run_ring = [], None, None, None, None

    for ri, seg, t, m, sk in resolved:
        if t != run_type or sk != run_sk or ri != run_ring:
            _flush()
            run_type, run_motif, run_sk, run_ring = t, m, sk, ri
            run_pts = list(seg.coords)
        else:
            run_pts.append(seg.coords[-1])
            run_motif = run_motif or m
    _flush()

    # GABARIT-6 lot A — rattachement des micro-arêtes résiduelles (artefacts de numérisation).
    _attach_residual_microedges(edges, rings, min_edge=min_edge)
    return edges


def _attach_residual_microedges(edges: list[Edge], rings: list, *, min_edge: float,
                                max_perim_frac: float = RESIDUAL_MAX_PERIM_FRAC) -> int:
    """Rattache chaque arête « non classée » qui n'est qu'un artefact de numérisation à l'arête
    ADJACENTE la plus longue du MÊME anneau (adjacence cyclique) : l'arête en hérite le type ET la
    source, `attached=True` la trace, et elle cesse de bloquer.

    Rattachée SI ET SEULEMENT SI : type == 'nonclass' ET longueur < `min_edge` ET longueur
    < `max_perim_frac` du périmètre de la parcelle. Une arête < min_edge mais ≥ 2 % du périmètre
    (parcelle minuscule, l'arête pèse) reste bloquante ; une arête longue non qualifiable aussi.
    Renvoie le nombre d'arêtes rattachées."""
    perim = sum(LineString(coords).length for coords in rings) if rings else 0.0
    if perim <= 0:
        return 0
    thr = max_perim_frac * perim
    by_ring: dict[Optional[int], list[int]] = {}
    for i, e in enumerate(edges):
        by_ring.setdefault(e.ring, []).append(i)
    n_attached = 0
    for _ring, idxs in by_ring.items():
        n = len(idxs)
        if n < 2:               # anneau à une seule arête : rien à quoi rattacher (et length == perim)
            continue
        for pos, i in enumerate(idxs):
            e = edges[i]
            if e.type != "nonclass" or e.length_m >= min_edge or e.length_m >= thr:
                continue
            prev_e = edges[idxs[(pos - 1) % n]]
            next_e = edges[idxs[(pos + 1) % n]]
            donor = prev_e if prev_e.length_m >= next_e.length_m else next_e
            e.type = donor.type
            e.source_kind = donor.source_kind
            e.motif = None
            e.attached = True
            n_attached += 1
    return n_attached


# --------------------------------------------------------------------------- couche DB

@dataclass
class LimitesResult:
    edges: list[Edge]                 # arêtes classées (géométrie 2975)
    has_voie: bool
    non_classees: list[str]           # motifs des arêtes non classées (dédupliqués)
    blocking: Optional[str]           # motif de blocage parcelle, sinon None
    private_road: bool = False        # une parcelle de voie privée collée a été détectée (E2)
    residual_attached: int = 0        # GABARIT-6 : nb de micro-arêtes résiduelles rattachées


def summarize_edges(edges: list[Edge]) -> LimitesResult:
    """PUR — verdict parcelle : façade présente ? arêtes non qualifiées ? blocage motivé ?"""
    has_voie = any(e.type == "voie" for e in edges)
    non_cl: list[str] = []
    for e in edges:
        if e.type == "nonclass" and e.motif and e.motif not in non_cl:
            non_cl.append(e.motif)
    blocking: Optional[str] = None
    if non_cl:
        blocking = "Limites de la parcelle non qualifiées (voie / limite séparative) — " + " ; ".join(non_cl)
    elif not has_voie:
        blocking = MOTIF_SANS_FACADE
    return LimitesResult(edges=edges, has_voie=has_voie, non_classees=non_cl, blocking=blocking,
                         residual_attached=sum(1 for e in edges if e.attached))


def classify_parcel_limits(session, parcel_id: int, *, emprises_publiques: bool = False,
                           voies_privees: bool = False,
                           sub_geom_wkt: Optional[str] = None,
                           extra_neighbors_wkt: Optional[list[str]] = None) -> Optional[LimitesResult]:
    """Requêtes PostGIS (2975) puis cœur pur. Renvoie None si parcelle introuvable.

    `sub_geom_wkt` : classe cette géométrie (morceau constructible d'une parcelle à cheval) au lieu de
    la parcelle entière. `extra_neighbors_wkt` : voisins additionnels non-voirie (ex. la partie A/N
    complémentaire) → la coupure interne entre zones devient une séparative, pas une arête non classée."""
    from shapely import wkt as shp_wkt
    from sqlalchemy import text

    if sub_geom_wkt is not None:
        parcel = shp_wkt.loads(sub_geom_wkt)
        geom_expr = "ST_GeomFromText(:g, 2975)"
        geom_param = {"g": sub_geom_wkt}
    else:
        row = session.execute(text("SELECT ST_AsText(geom_2975) g FROM parcels WHERE id = :pid"),
                              {"pid": parcel_id}).first()
        if not row or not row[0]:
            return None
        parcel = shp_wkt.loads(row[0])
        geom_expr = "(SELECT geom_2975 FROM parcels WHERE id=:pid)"
        geom_param = {}

    # voisins cadastrés à ≤ 0,5 m, avec drapeau « parcelle de voirie » (axe voirie + aucun bâti).
    nb_rows = session.execute(text(
        f"""
        SELECT ST_AsText(o.geom_2975) AS g,
               EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie'
                        AND v.subtype NOT IN ('Sentier','Escalier')
                        AND ST_Intersects(v.geom_2975, o.geom_2975))
               AND NOT EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment'
                        AND ST_Intersects(b.geom_2975, o.geom_2975)) AS is_road_parcel
        FROM parcels o
        WHERE o.id <> :pid AND ST_DWithin(o.geom_2975, {geom_expr}, 0.5)
        """
    ), {"pid": parcel_id, **geom_param}).fetchall()
    neighbors = [(shp_wkt.loads(r[0]), bool(r[1])) for r in nb_rows if r[0]]
    for wkt_n in (extra_neighbors_wkt or []):   # parties A/N complémentaires : voisins non-voirie
        neighbors.append((shp_wkt.loads(wkt_n), False))

    # parcelles de voie privée collées (E2) : sans bâti, allongées, raccordées au réseau BD TOPO à une
    # extrémité mais NON traversées par un axe (donc absentes de BD TOPO comme voie). Détectées ici,
    # servies dans le cœur seulement si la citation PLU vise les voies privées (arg voies_privees).
    pr_rows = session.execute(text(
        f"""
        SELECT ST_AsText(o.geom_2975) AS g,
               ST_Perimeter(ST_OrientedEnvelope(o.geom_2975)) AS obb_perim,
               ST_Area(ST_OrientedEnvelope(o.geom_2975)) AS obb_area,
               EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment'
                        AND ST_Intersects(b.geom_2975, o.geom_2975)) AS has_bati,
               EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie'
                        AND v.subtype NOT IN ('Sentier','Escalier')
                        AND ST_DWithin(v.geom_2975, o.geom_2975, :touch)) AS touches_road,
               COALESCE((SELECT SUM(ST_Length(ST_Intersection(v.geom_2975, o.geom_2975)))
                         FROM spatial_layers v WHERE v.kind='voirie'
                           AND v.subtype NOT IN ('Sentier','Escalier')
                           AND ST_Intersects(v.geom_2975, o.geom_2975)), 0) AS axis_len_inside
        FROM parcels o
        WHERE o.id <> :pid AND ST_DWithin(o.geom_2975, {geom_expr}, 0.5)
        """
    ), {"pid": parcel_id, "touch": PRIVATE_ROAD_TOUCH_M, **geom_param}).fetchall()
    def _is_priv(r):
        d = obb_dims(r[1], r[2])
        return d is not None and is_private_road_parcel(
            has_bati=bool(r[3]), elongation=d[0] / d[1], width_m=d[1],
            touches_road=bool(r[4]), axis_len_inside_m=float(r[5] or 0))

    private_roads = [shp_wkt.loads(r[0]) for r in pr_rows if r[0] and _is_priv(r)]

    # tronçons carrossables proches (rayon = max demi-chaussée + marge)
    rd_rows = session.execute(text(
        f"""
        SELECT ST_AsText(v.geom_2975) AS g, (v.attrs->>'largeur')::float AS largeur
        FROM spatial_layers v
        WHERE v.kind='voirie' AND v.subtype NOT IN ('Sentier','Escalier')
          AND ST_DWithin(v.geom_2975, {geom_expr}, 12)
        """
    ), {"pid": parcel_id, **geom_param}).fetchall()
    roads = [Road(shp_wkt.loads(r[0]), r[1]) for r in rd_rows if r[0]]

    res = summarize_edges(classify_edges(parcel, neighbors, roads, emprises_publiques=emprises_publiques,
                                         private_roads=private_roads, voies_privees=voies_privees))
    res.private_road = bool(private_roads)
    return res
