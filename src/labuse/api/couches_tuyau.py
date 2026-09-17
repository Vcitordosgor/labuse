"""COUCHES-TUYAU-1 — un seul tuyau : tuiles vectorielles pour toutes les couches déclarées.

UN endpoint, UNE requête paramétrique, ZÉRO branche `if kind == …`.

  • La LISTE des couches et, pour chacune, sa géométrie / son style / son popup / sa
    famille / son zoom_min viennent de la DÉCLARATION (`declarations.couches_carte()`).
  • La seule chose qui n'est pas dans la déclaration est la RÉSOLUTION d'un kind-front
    « virtuel » vers le(s) kind(s) STOCKÉ(s) dans `spatial_layers` + un filtre `subtype`
    (ex. `alea_inondation` → `georisque_alea` filtré). C'est une TABLE DE DONNÉES
    (`_RESOLUTION_OVERRIDE`, défaut = identité) — jamais du branchement. Le constructeur
    de requête ne connaît aucun kind en dur : il boucle sur la résolution.
  • Les PROPRIÉTÉS portées par la tuile sont EXACTEMENT celles que la déclaration
    référence (`subtype` colonne, `couleur_propriete`, `niveaux[].propriete`,
    `popup[].champ`, filtre) — promues depuis la colonne ou depuis `attrs` (jsonb).
  • Transformation 2975 → 3857 faite UNE FOIS, ici (le filtre spatial reste en 2975,
    indexé ; seule la géométrie retenue est reprojetée pour le MVT). Extent 4096.
  • Géométrie BRUTE : `geom_2975` telle quelle (pas de geom_simple / geom_ile / palier
    par zoom / centroïde). Le verrou `verrou_tuiles` compare la tuile servie à cette brute.

Le tuyau est ADDITIF : il ne retire ni l'ancien endpoint GeoJSON (`/map/layers.geojson`)
ni aucune couche existante ; il sert les 52 couches déclarées sur un chemin distinct.
"""
from __future__ import annotations

import re
import time
from collections import OrderedDict
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import runs

router = APIRouter(tags=["couches-tuyau"])


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py, comme tiles.py)
    from .app import get_db as _g
    yield from _g()


# ───────────────────────── résolution kind-front → source stockée ─────────────────────────
# DONNÉE, pas du code. Chaque entrée liste les MORCEAUX stockés d'un kind-front virtuel :
# (kind_stocké, subtypes|None). Défaut (absent d'ici) = identité : [(kind, None)]. Ces valeurs
# reproduisent la résolution de l'API (`_VIRTUAL_MAP_KINDS` / TCSP multi) sans la dupliquer en
# logique : le constructeur de requête boucle dessus, il n'a aucun `if kind ==`.
_RESOLUTION_OVERRIDE: dict[str, list[tuple[str, tuple[str, ...] | None]]] = {
    "enp": [("ens", None)],
    "er": [("plu_gpu_prescription", ("05",))],
    "ebc": [("plu_gpu_prescription", ("01",))],
    "sis": [("sol_pollue", ("sis",))],
    "casias": [("sol_pollue", ("casias", "instruction"))],
    "alea_inondation": [("georisque_alea", ("inondation", "submersion_marine", "submersion_marine_cc"))],
    "alea_mvt": [("georisque_alea", ("mouvement_terrain",))],
    # TCSP : une couche-front, trois morceaux stockés (zone + tronçons en site propre + stations).
    "tcsp": [("tcsp_zone", None), ("tcsp_troncon", ("site_propre",)), ("tcsp_station", None)],
}

# colonnes réelles de spatial_layers exposables telles quelles ; tout autre nom référencé par la
# déclaration est lu dans attrs (jsonb). `name`/`commune`/`subtype` sont des colonnes.
_COLONNES = {"subtype", "name", "commune"}
_IDENT = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


@dataclass(frozen=True)
class CoucheTuyau:
    kind: str                                            # kind-front = nom de la couche MVT
    resolution: tuple[tuple[str, tuple[str, ...] | None], ...]
    zoom_min: int
    geometrie: str
    props: tuple[tuple[str, str], ...]                   # (nom_sortie, expression SQL)
    # retour §2 : la SOURCE physique — défaut spatial_layers/geom_2975/2975 (résolution par kind) ;
    # une couche hors registre déclare sa propre table/colonne/srid/filtre (mvt_parcels, mvt_communes…).
    table: str = "spatial_layers"
    geom: str = "geom_2975"
    srid: int = 2975
    where_sql: str | None = None                         # filtre explicite (couches hors spatial_layers)
    # COUCHES-RECETTE-1 (Lot B) : une couche `contour_seul` (bassin versant) ne dessine QUE son bord
    # (pas de remplissage). Elle ne doit JAMAIS passer par la table ST_Subdivide : le front supprime
    # le contour des morceaux (coutures) → contour_seul + subdivisé = ni fond ni bord = RIEN.
    contour_seul: bool = False


_REGISTRE: dict[str, CoucheTuyau] | None = None


def _expr_pour(nom: str) -> str | None:
    """Expression SQL pour une propriété référencée par la déclaration (colonne ou attrs)."""
    if not _IDENT.match(nom):
        return None  # nom non sûr → ignoré (jamais interpolé tel quel)
    if nom in _COLONNES:
        return f"m.{nom}"
    return f"(m.attrs ->> '{nom}')"


def _props_referencees(carte: dict) -> list[str]:
    """Ensemble ORDONNÉ des propriétés que le front lira sur la tuile pour cette couche :
    subtype (toujours), la propriété de coloration, les propriétés des niveaux, le champ du
    filtre, et les champs du popup. Dédupliqué, ordre stable."""
    vus: list[str] = []

    def ajoute(n: str | None) -> None:
        if n and n not in vus:
            vus.append(n)

    ajoute("subtype")
    ajoute("name")
    ajoute("commune")
    style = carte.get("style") or {}
    ajoute(style.get("couleur_propriete"))
    filtre = style.get("filtre")
    if isinstance(filtre, dict):
        ajoute(filtre.get("propriete"))
    for niv in carte.get("niveaux") or []:
        if isinstance(niv, dict):
            ajoute(niv.get("propriete"))
    for champ in carte.get("popup") or []:
        if isinstance(champ, dict):
            ajoute(champ.get("champ"))
    return vus


def _charger_hors_registre() -> list[dict]:
    """retour §2 : les couches déclarées HORS spatial_layers (leur propre source), lues du YAML
    `declarations/couches/tuyau_hors_registre.yaml`. Une couche n'a pas besoin d'être dans
    spatial_layers pour être au panneau."""
    import pathlib
    import yaml as _yaml
    p = pathlib.Path(__file__).resolve().parents[3] / "declarations" / "couches" / "tuyau_hors_registre.yaml"
    if not p.exists():
        return []
    return _yaml.safe_load(p.read_text(encoding="utf-8")) or []


def registre() -> dict[str, CoucheTuyau]:
    """Construit (une fois) le registre du tuyau depuis la déclaration. Lit UNIQUEMENT le YAML."""
    global _REGISTRE
    if _REGISTRE is None:
        from ..registre.declarations import couches_carte
        reg: dict[str, CoucheTuyau] = {}
        for c in couches_carte():
            kind = c["kind"]
            res = _RESOLUTION_OVERRIDE.get(kind, [(kind, None)])
            props: list[tuple[str, str]] = []
            for nom in _props_referencees(c):
                e = _expr_pour(nom)
                if e is not None:
                    props.append((nom, e))
            reg[kind] = CoucheTuyau(
                kind=kind, resolution=tuple(res), zoom_min=int(c.get("zoom_min") or 0),
                geometrie=c.get("geometrie") or "polygone", props=tuple(props),
                contour_seul=bool((c.get("style") or {}).get("contour_seul")),
            )
        # couches hors spatial_layers : source déclarée, propriétés = colonnes réelles de la table.
        for c in _charger_hors_registre():
            src = c.get("source") or {}
            kind = c["kind"]
            props = [(nom, f"m.{nom}") for nom in _props_referencees(c)
                     if _IDENT.match(nom) and nom not in ("subtype", "name")]
            reg[kind] = CoucheTuyau(
                kind=kind, resolution=(), zoom_min=int(c.get("zoom_min") or 0),
                geometrie=c.get("geometrie") or "polygone", props=tuple(props),
                table=str(src.get("table") or "spatial_layers"),
                geom=str(src.get("geom") or "geom_2975"),
                srid=int(src.get("srid") or 2975),
                where_sql=src.get("where"),
            )
        # retour §2 : si la table dérivée existe, servir depuis les MORCEAUX (ST_Subdivide) UNIQUEMENT
        # les couches dont le kind stocké y figure (les méga-polygones). Endpoint ET verrou passent par
        # `registre()` → même source, cohérents. Les autres restent sur spatial_layers (déjà rapides).
        from dataclasses import replace as _replace
        try:
            from ..db import session_scope
            with session_scope() as s:
                if s.execute(text("SELECT to_regclass('tuyau_subdivise')")).scalar():
                    subd = {r[0] for r in s.execute(text("SELECT DISTINCT kind FROM tuyau_subdivise")).all()}
                    for k, v in list(reg.items()):
                        # COUCHES-RECETTE-1 : jamais de subdivise pour une couche contour_seul (sinon
                        # ni fond ni bord — cf. bassin versant). Elle reste sur spatial_layers.
                        if v.table == "spatial_layers" and v.resolution and not v.contour_seul \
                                and all(sk in subd for sk, _ in v.resolution):
                            reg[k] = _replace(v, table="tuyau_subdivise")
        except Exception:  # noqa: BLE001 — pas de base au chargement : défaut spatial_layers
            pass
        _REGISTRE = reg
    return _REGISTRE


# ───────────────────────── cache HTTP par run servi ─────────────────────────
_CACHE: OrderedDict[tuple, bytes] = OrderedDict()
_CACHE_MAX = 4096
_HEADERS = {"Cache-Control": "public, max-age=3600, stale-while-revalidate=86400"}
_VER: dict = {"v": "", "at": -1e9}
_VER_TTL_S = 10.0


def _version(db: Session) -> str:
    """Version des tuiles = run servi + empreinte de fraîcheur de spatial_layers. Entre dans la
    clé du cache LRU ET l'ETag : un changement de run OU une réingestion invalide sans redémarrage."""
    now = time.monotonic()
    if now - _VER["at"] > _VER_TTL_S:
        try:
            run = runs.current()
        except Exception:  # noqa: BLE001
            run = ""
        mx = db.execute(text(
            "SELECT to_char(max(created_at), 'YYYYMMDDHH24MISS') FROM spatial_layers")).scalar() or ""
        _VER["v"] = f"{run}.{mx}"
        _VER["at"] = now
    return _VER["v"]


def build_tuyau_subdivise(db: Session) -> int:
    """retour §2 — le DÉFAUT de prod : servir un méga-polygone (millions de sommets) en vue île lance
    un `ST_AsMVTGeom` NON INTERRUPTIBLE (17 s pour SUP). Correctif : table dérivée où CHAQUE géométrie
    de spatial_layers est découpée par `ST_Subdivide` en morceaux ≤ 256 sommets, indexée (GIST). L'UNION
    des morceaux = la géométrie d'origine → remplissage IDENTIQUE, AUCUNE simplification. L'endpoint lit
    cette table à la place des méga-géométries → `ST_AsMVTGeom` par petit morceau, parallélisable → < 2 s.
    Construite comme les autres tables MVT (une fois, hors requête). Les morceaux gardent kind/subtype/
    attrs pour la résolution et les popups. Le contour se dessine du bord d'origine (cf. front)."""
    db.execute(text("DROP TABLE IF EXISTS tuyau_subdivise"))
    # COUCHES-RECETTE-1 (Lot B) — DÉDOUBLONNAGE (SUP PM1 dupliqués ~4×) : on retire d'abord les
    # doublons EXACTS (même kind, même sous-type, même géométrie) — des artefacts d'ingestion, pas de
    # la géométrie (l'union des doublons = un seul → couverture identique). Fait UNIQUEMENT dans la
    # table dérivée du tuyau : `spatial_layers` (donc `:8020`) reste INTOUCHÉE. SUP : 417 → 123 assiettes.
    # Clé de dédoublonnage PEU COÛTEUSE : les doublons SUP partagent leur `idass` (mesuré : 123 idass
    # = 123 géométries distinctes → chaque idass n'a qu'UNE géométrie, les autres lignes en sont des
    # copies exactes). On dédoublonne par (kind, subtype, idass) ; les lignes sans idass (les autres
    # kinds) retombent sur leur `id` (unique) → aucune dédup, aucune perte. Pas de hash de géométrie.
    db.execute(text("""
        CREATE TABLE tuyau_subdivise AS
        WITH uniques AS (
            SELECT DISTINCT ON (kind, subtype, COALESCE(attrs->>'idass', id::text))
                   kind, subtype, name, commune, attrs, geom_2975
            FROM spatial_layers
            ORDER BY kind, subtype, COALESCE(attrs->>'idass', id::text)
        )
        SELECT m.kind, m.subtype, m.name, m.commune, m.attrs, p.geom AS geom_2975
        FROM uniques m, LATERAL ST_Subdivide(m.geom_2975, 256) AS p(geom)"""))
    db.execute(text("CREATE INDEX tuyau_subdivise_gix ON tuyau_subdivise USING GIST (geom_2975)"))
    db.execute(text("CREATE INDEX tuyau_subdivise_kind ON tuyau_subdivise (kind, subtype)"))
    db.execute(text("ANALYZE tuyau_subdivise"))
    n = db.execute(text("SELECT count(*) FROM tuyau_subdivise")).scalar() or 0
    db.commit()
    _CACHE.clear()
    return int(n)


def build_mvt_communes(db: Session) -> int:
    """COUCHES-RECETTE-1 (Lot B) — limites communes RÉPARÉES.

    Le build précédent dissolvait mvt_parcels par commune (`ST_Boundary(ST_UnaryUnion(...))`). Les
    parcelles portant des micro-slivers/écarts topologiques, l'union ne dissolvait PAS les arêtes
    internes → la « frontière » incluait tout le réseau parcellaire (jusqu'à 667 000 points pour une
    seule commune) : la couche dessinait un réseau, pas les 24 communes.

    On reprend EXACTEMENT la source de l'ancienne couche `communes-bounds` : le GeoJSON officiel
    `frontend/public/communes974.geojson` (contours IGN, 24 communes, WGS84). On stocke le contour net
    (ST_Boundary) en 3857. `commune` et `code` pour le popup. Additif, reconstruit hors requête."""
    import json
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[3] / "frontend" / "public" / "communes974.geojson"
    fc = json.loads(p.read_text(encoding="utf-8"))
    db.execute(text("DROP TABLE IF EXISTS mvt_communes"))
    db.execute(text(
        "CREATE TABLE mvt_communes (commune text, code text, "
        "geom_3857 geometry(MultiLineString, 3857))"))
    ins = text("""
        INSERT INTO mvt_communes (commune, code, geom_3857)
        VALUES (:commune, :code,
            ST_Multi(ST_Boundary(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geo), 4326), 3857))))""")
    n = 0
    for feat in fc.get("features", []):
        props = feat.get("properties") or {}
        db.execute(ins, {"commune": props.get("nom"), "code": props.get("code"),
                         "geo": json.dumps(feat["geometry"])})
        n += 1
    db.execute(text("CREATE INDEX mvt_communes_gix ON mvt_communes USING GIST (geom_3857)"))
    db.execute(text("ANALYZE mvt_communes"))
    db.commit()
    _CACHE.clear()
    return int(n)


def _table_manquante(db: Session, table: str) -> bool:
    return db.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is None


def _construire_tuile(db: Session, c: CoucheTuyau, z: int, x: int, y: int) -> bytes:
    """L'UNIQUE requête. Filtre dans le SRID de la source (indexé), reprojette en 3857 une fois, MVT
    extent 4096. Le nom de couche MVT = le kind-front ; les propriétés = celles déclarées.
    Source-aware (§2) : spatial_layers/geom_2975/2975 par défaut, ou la table/colonne/srid déclarée."""
    params: dict = {"z": z, "x": x, "y": y, "layer": c.kind}
    # WHERE : résolution par kind (spatial_layers) ou filtre explicite (couche hors registre).
    if c.resolution:
        clauses: list[str] = []
        for i, (k, subs) in enumerate(c.resolution):
            params[f"k{i}"] = k
            if subs:
                clauses.append(f"(m.kind = :k{i} AND m.subtype = ANY(:s{i}))")
                params[f"s{i}"] = list(subs)
            else:
                clauses.append(f"(m.kind = :k{i})")
        where = "(" + " OR ".join(clauses) + ")"
    else:
        where = c.where_sql or "TRUE"
    # géométrie source → 3857 (une fois). Le SRID est FORCÉ (mvt_parcels.geom_3857 est en SRID 0).
    g_src = f"ST_SetSRID(m.{c.geom}, {c.srid})"
    g_3857 = g_src if c.srid == 3857 else f"ST_Transform({g_src}, 3857)"
    filtre = "b.env_marge" if c.srid == 3857 else f"ST_Transform(b.env_marge, {c.srid})"
    props_sql = "".join(f', {expr} AS "{nom}"' for nom, expr in c.props)
    sql = text(f"""
        WITH b AS (
            SELECT ST_TileEnvelope(:z, :x, :y) AS env,
                   ST_TileEnvelope(:z, :x, :y, margin => 0.125) AS env_marge
        ),
        mvt AS (
            SELECT ST_AsMVTGeom({g_3857}, b.env, 4096, 64, true) AS geom{props_sql}
            FROM {c.table} m, b
            WHERE {where}
              AND {g_src} && {filtre}
        )
        SELECT ST_AsMVT(mvt.*, :layer, 4096, 'geom') FROM mvt WHERE geom IS NOT NULL
    """)
    data = db.execute(sql, params).scalar()
    return bytes(data) if data else b""


@router.get("/map/tiles/{kind}/{z}/{x}/{y}.pbf")
def couche_tuile(kind: str, z: int, x: int, y: int,
                 request: Request, db: Session = Depends(get_db)) -> Response:
    """Tuile vectorielle MVT d'une couche déclarée. Chemin dédié `/map/tiles/{kind}/…` (4 segments
    — distinct de `/map/tiles/{z}/{x}/{y}.pbf` parcelles et `/map/tiles/ov/…`)."""
    reg = registre()
    c = reg.get(kind)
    if c is None:
        return Response(status_code=404)  # kind non déclaré : jamais servi en silence
    # COUCHES-TUYAU-1 retour §5 : PLUS de bornage par zoom_min — toutes les couches sont visibles
    # dès la vue île (safer compris). Aucune réponse 204 sous un « zoom minimum » : le tuyau sert
    # à tous les zooms valides. (Seuls les z hors plage physique sont refusés.)
    if z < 0 or z > 22:
        return Response(status_code=404)
    version = _version(db)
    etag = f'"{version}:{kind}:{z}:{x}:{y}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={**_HEADERS, "ETag": etag})
    key = (version, kind, z, x, y)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return Response(content=_CACHE[key], media_type="application/x-protobuf",
                        headers={**_HEADERS, "ETag": etag})
    if _table_manquante(db, c.table):
        # source pas encore construite (ex. mvt_communes avant build) — vide gracieux, jamais 500.
        return Response(status_code=204)
    body = _construire_tuile(db, c, z, x, y)
    _CACHE[key] = body
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return Response(content=body, media_type="application/x-protobuf",
                    headers={**_HEADERS, "ETag": etag})


@router.get("/map/tuyau/couches")
def tuyau_couches() -> dict:
    """Le PLAN du tuyau : ce que le front monte en sources vectorielles. Dérivé de la déclaration
    (kind, famille, géométrie, zoom_min, style, niveaux, popup) + l'URL de tuile de CE tuyau."""
    from ..registre.declarations import couches_carte
    reg = registre()
    couches = []
    for c in couches_carte():
        k = c["kind"]
        if k not in reg:
            continue
        couches.append({
            "kind": k,
            "nom": c.get("nom") or c.get("libelle") or k,
            "famille": c.get("famille"),
            "geometrie": c.get("geometrie"),
            "zoom_min": reg[k].zoom_min,
            "rang_carte": c.get("rang_carte"),
            "style": c.get("style"),
            "niveaux": c.get("niveaux"),
            "popup": c.get("popup"),
            "legende": c.get("legende"),
            # COUCHES-RECETTE-1 A8 : le texte du « i » (explication de l'acronyme, source, enjeu) vient
            # du YAML (comment.i) et est transmis au front pour l'info-bulle par couche.
            "i": c.get("i"),
            # COUCHES-RECETTE-1 : centroïde (A2 — point d'île pour un polygone minuscule), groupe (fusion
            # de couches en un toggle), etiquette (calque symbole d'étiquettes) — tous rendus côté front.
            "centroide": bool(c.get("centroide", False)),
            "groupe": c.get("groupe"),
            "etiquette": c.get("etiquette"),
            "note": c.get("note"),
            "statut_juridique": c.get("statut_juridique"),
            "tuiles_url": f"/map/tiles/{k}/{{z}}/{{x}}/{{y}}.pbf",
            # retour §2 : couche servie en MORCEAUX (ST_Subdivide) → le front dessine le remplissage
            # sans contour de morceau (pas de couture) ; le bord visible est celui de l'origine.
            "subdivise": reg[k].table == "tuyau_subdivise",
        })
    # retour §2 : les couches hors registre (Limites parcelles, Zonage par parcelle, Limites communes)
    for c in _charger_hors_registre():
        k = c["kind"]
        couches.append({
            "kind": k, "nom": c.get("nom") or k, "famille": c.get("famille"),
            "geometrie": c.get("geometrie"), "zoom_min": int(c.get("zoom_min") or 0),
            "rang_carte": c.get("rang_carte") or 0, "style": c.get("style"),
            "niveaux": c.get("niveaux"), "popup": c.get("popup"), "legende": c.get("legende"),
            "i": c.get("i"),
            "centroide": bool(c.get("centroide", False)),
            "groupe": c.get("groupe"), "etiquette": c.get("etiquette"),
            "statut_juridique": c.get("statut_juridique"),
            "tuiles_url": f"/map/tiles/{k}/{{z}}/{{x}}/{{y}}.pbf",
        })
    couches.sort(key=lambda d: (d.get("famille") or "", d.get("rang_carte") or 0, d["kind"]))
    return {"couches": couches}
