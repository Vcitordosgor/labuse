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
                kind=kind,
                resolution=tuple(res),
                zoom_min=int(c.get("zoom_min") or 0),
                geometrie=c.get("geometrie") or "polygone",
                props=tuple(props),
            )
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


def _construire_tuile(db: Session, c: CoucheTuyau, z: int, x: int, y: int) -> bytes:
    """L'UNIQUE requête. Filtre en 2975 (indexé), reprojette en 3857 une fois, MVT extent 4096.
    Le nom de couche MVT = le kind-front ; les propriétés = celles référencées par la déclaration."""
    clauses: list[str] = []
    params: dict = {"z": z, "x": x, "y": y}
    for i, (k, subs) in enumerate(c.resolution):
        params[f"k{i}"] = k
        if subs:
            clauses.append(f"(m.kind = :k{i} AND m.subtype = ANY(:s{i}))")
            params[f"s{i}"] = list(subs)
        else:
            clauses.append(f"(m.kind = :k{i})")
    where_kind = "(" + " OR ".join(clauses) + ")"
    props_sql = "".join(f'{expr} AS "{nom}", ' for nom, expr in c.props)
    params["layer"] = c.kind
    sql = text(f"""
        WITH b AS (
            SELECT ST_TileEnvelope(:z, :x, :y) AS env,
                   ST_Transform(ST_TileEnvelope(:z, :x, :y, margin => 0.125), 2975) AS filtre_2975
        ),
        mvt AS (
            SELECT ST_AsMVTGeom(ST_Transform(m.geom_2975, 3857), b.env, 4096, 64, true) AS geom,
                   {props_sql}
                   m.id
            FROM spatial_layers m, b
            WHERE {where_kind}
              AND m.geom_2975 && b.filtre_2975
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
            "statut_juridique": c.get("statut_juridique"),
            "tuiles_url": f"/map/tiles/{k}/{{z}}/{{x}}/{{y}}.pbf",
        })
    couches.sort(key=lambda d: (d.get("famille") or "", d.get("rang_carte") or 0, d["kind"]))
    return {"couches": couches}
