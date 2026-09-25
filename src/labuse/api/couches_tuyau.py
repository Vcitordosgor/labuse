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

import functools
import re
import threading
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
    # COUCHES-RECETTE-2 (retour) : la couche « Équipements OSM » ne montre QUE les aménités typées
    # (couleur + icône) ; les sous-types tcsp/sport (12 000 points, doublons de Transport/Sport) sont
    # EXCLUS — sinon la vue rue est un tapis de points gris sans icône. Filtre à la source (le verrou
    # lit la même résolution → cohérent).
    "amenite": [("amenite", ("mairie", "ecole", "sante", "commerce", "police", "marche", "creche", "college_lycee"))],
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


@functools.lru_cache(maxsize=1)
def _charger_hors_registre() -> list[dict]:
    """retour §2 : les couches déclarées HORS spatial_layers (leur propre source), lues du YAML
    `declarations/couches/tuyau_hors_registre.yaml`. Une couche n'a pas besoin d'être dans
    spatial_layers pour être au panneau.
    CARTE-VITESSE-2 lot D (R4) — MÉMOÏSÉ : YAML statique relu à chaque `/map/tuyau/couches` avant
    ce cache ; appelé en lecture seule (registre() + tuyau_couches construisent des dicts neufs)."""
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
                # COUCHES-RECETTE-1 (Lot B) : piscines dédoublonnées + niveau → repointées sur
                # tuyau_piscines (l'attribut `niveau` y est en attrs, la résolution kind='piscine_cosia'
                # tient). Additif : spatial_layers.piscine_cosia reste intacte.
                if s.execute(text("SELECT to_regclass('tuyau_piscines')")).scalar() and "piscine_cosia" in reg:
                    reg["piscine_cosia"] = _replace(reg["piscine_cosia"], table="tuyau_piscines")
                # COUCHES-RECETTE-2 Lot D : telepherique = Papang servi + ligne Payanké (projet) →
                # repointé sur tuyau_telepherique (additif ; spatial_layers.telepherique intacte).
                if s.execute(text("SELECT to_regclass('tuyau_telepherique')")).scalar() and "telepherique" in reg:
                    reg["telepherique"] = _replace(reg["telepherique"], table="tuyau_telepherique")
                # COUCHES-RECETTE-2 (retour) : SUP dissoute par famille (opacité uniforme au zoom) →
                # repointée sur tuyau_sup (override la substitution subdivise ci-dessus).
                if s.execute(text("SELECT to_regclass('tuyau_sup')")).scalar() and "sup" in reg:
                    reg["sup"] = _replace(reg["sup"], table="tuyau_sup")
        except Exception:  # noqa: BLE001 — pas de base au chargement : défaut spatial_layers
            pass
        _REGISTRE = reg
    return _REGISTRE


# ───────────────────────── cache HTTP par run servi ─────────────────────────
_CACHE: OrderedDict[tuple, bytes] = OrderedDict()
_CACHE_MAX = 4096
_HEADERS = {"Cache-Control": "public, max-age=3600, stale-while-revalidate=86400"}
_VER: dict = {"v": "", "at": -1e9}
_VER_TTL_S = 60.0            # COUCHES-RECETTE-1 : rafraîchie au plus toutes les 60 s
_VER_LOCK = threading.Lock()


def _version(db: Session) -> str:
    """Version des tuiles = run servi + empreinte de fraîcheur de spatial_layers. Entre dans la
    clé du cache LRU ET l'ETag : un changement de run OU une réingestion invalide sans redémarrage.

    COUCHES-RECETTE-1 — la version est calculée UNE FOIS et gardée en mémoire (TTL 60 s), JAMAIS par
    tuile. Un viewport charge des dizaines de tuiles d'un coup : sans garde, à l'expiration du TTL
    elles lançaient TOUTES le `max(created_at)` en même temps (stampede) → saturation du pool
    (QueuePool 5+10). Verrou SINGLE-FLIGHT non bloquant : un seul thread rafraîchit, les autres
    servent la version en cache (au plus 60 s de retard, cohérente) sans frapper la DB. La requête
    elle-même est désormais instantanée (index `ix_spatial_layers_created_at` → Index Only Scan)."""
    now = time.monotonic()
    if now - _VER["at"] <= _VER_TTL_S:
        return _VER["v"]
    # périmée : un seul thread refait la requête. `blocking` uniquement au tout premier calcul
    # (pas encore de valeur) — ensuite jamais d'attente, on sert la valeur en cache.
    if not _VER_LOCK.acquire(blocking=_VER["at"] < 0):
        return _VER["v"]
    try:
        if time.monotonic() - _VER["at"] > _VER_TTL_S:
            try:
                run = runs.current()
            except Exception:  # noqa: BLE001
                run = ""
            mx = db.execute(text(
                "SELECT to_char(max(created_at), 'YYYYMMDDHH24MISS') FROM spatial_layers")).scalar() or ""
            _VER["v"] = f"{run}.{mx}"
            _VER["at"] = time.monotonic()
    finally:
        _VER_LOCK.release()
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


def build_tuyau_piscines(db: Session) -> int:
    """COUCHES-RECETTE-1 (Lot B) — piscines : UNE piscine = UN point, le niveau de confiance en
    ATTRIBUT (avant : la couche servait CoSIA seule, `subtype='Piscine'` partout → aucun des 3
    niveaux, et des doublons de détection).

    On construit une table dérivée `tuyau_piscines` (n'affecte NI spatial_layers NI :8020) :
      1. DÉDOUBLONNAGE : les points CoSIA sont regroupés par ST_ClusterDBSCAN (1,5 m) — un
         représentant par grappe → une piscine = un point.
      2. NIVEAU (attribut `niveau`) selon les deux détecteurs :
         · confirmee — CoSIA ∩ détection ortho interne (les deux d'accord, < 2 m) ;
         · probable  — CoSIA seule ;
         · rare      — détection ortho interne seule (aucune CoSIA à < 2 m).
    La couche `piscine_cosia` est repointée sur cette table (cf. registre())."""
    db.execute(text("DROP TABLE IF EXISTS tuyau_piscines"))
    # tables temporaires INDEXÉES (GIST) → les jointures spatiales (EXISTS/NOT EXISTS à 2 m) sont
    # rapides et bornées (sinon O(n²) contre un CTE non indexé). On ne touche PAS les tables partagées.
    db.execute(text("""
        CREATE TEMP TABLE _cosia_dedup ON COMMIT DROP AS
        WITH cosia AS (
            SELECT geom_2975, commune, (attrs->>'surface_m2')::float AS surf,
                   ST_ClusterDBSCAN(geom_2975, eps := 1.5, minpoints := 1) OVER () AS cid
            FROM spatial_layers WHERE kind = 'piscine_cosia'
        )
        SELECT DISTINCT ON (cid) geom_2975, commune, surf
        FROM cosia ORDER BY cid, surf DESC NULLS LAST"""))
    db.execute(text("CREATE INDEX ON _cosia_dedup USING GIST (geom_2975)"))
    db.execute(text("""
        CREATE TEMP TABLE _ortho_pisc ON COMMIT DROP AS
        SELECT geom_2975, surface_m2 FROM ortho_detections
        WHERE type ILIKE 'piscine' AND confiance >= 0.8"""))
    db.execute(text("CREATE INDEX ON _ortho_pisc USING GIST (geom_2975)"))
    db.execute(text("ANALYZE _cosia_dedup"))
    db.execute(text("ANALYZE _ortho_pisc"))
    db.execute(text("""
        CREATE TABLE tuyau_piscines AS
        -- COUCHES-RECETTE-2 Lot A : une piscine = UN POINT (ST_PointOnSurface) — la donnée CoSIA est
        -- un POLYGONE (l'empreinte du bassin) ; servie telle quelle, le calque cercle posait un rond
        -- par sommet (« 5 points par piscine »). On sert le point représentatif → un rond par piscine.
        SELECT 'piscine_cosia'::text AS kind, u.niveau AS subtype, NULL::text AS name, u.commune,
               jsonb_build_object('niveau', u.niveau, 'surface_m2', u.surf) AS attrs,
               ST_PointOnSurface(u.geom_2975) AS geom_2975
        FROM (
            SELECT c.geom_2975, c.commune, c.surf,
                   CASE WHEN EXISTS (SELECT 1 FROM _ortho_pisc o
                                     WHERE ST_DWithin(c.geom_2975, o.geom_2975, 2.0))
                        THEN 'confirmee' ELSE 'probable' END AS niveau
            FROM _cosia_dedup c
            UNION ALL
            SELECT o.geom_2975, NULL::text, o.surface_m2, 'rare'
            FROM _ortho_pisc o
            WHERE NOT EXISTS (SELECT 1 FROM _cosia_dedup c
                              WHERE ST_DWithin(o.geom_2975, c.geom_2975, 2.0))
        ) u"""))
    db.execute(text("CREATE INDEX tuyau_piscines_gix ON tuyau_piscines USING GIST (geom_2975)"))
    db.execute(text("CREATE INDEX tuyau_piscines_kind ON tuyau_piscines (kind, subtype)"))
    db.execute(text("ANALYZE tuyau_piscines"))
    n = db.execute(text("SELECT count(*) FROM tuyau_piscines")).scalar() or 0
    db.commit()
    _CACHE.clear()
    return int(n)


def build_tuyau_sup(db: Session) -> int:
    """COUCHES-RECETTE-2 (retour) — SUP : couleur qui CHANGE avec le zoom. Cause : les assiettes d'une
    même famille se RECOUVRENT (pm1 : 45 assiettes, 1,7 M points) ; servies telles quelles et découpées,
    chaque pixel empile N morceaux semi-transparents → à z10 (le pixel couvre plus d'assiettes) la teinte
    est bien plus foncée qu'à z16. Correctif : DISSOUDRE chaque famille (ST_Union par sous-type) — le
    footprint couvert est IDENTIQUE (ce n'est pas une simplification de géométrie, c'est l'union exacte),
    mais sans recouvrement interne → opacité UNIFORME à tous les zooms, teinte constante. Puis subdivisé
    (≤ 256 sommets) pour la performance des tuiles, comme les autres méga-polygones.

    Additif : spatial_layers intacte (:8020 inchangé). Popup au niveau FAMILLE (code de servitude) — le
    détail par assiette (acte/règlement) n'est plus servi par CETTE couche après dissolution, assumé."""
    db.execute(text("DROP TABLE IF EXISTS tuyau_sup"))
    db.execute(text("""
        CREATE TEMP TABLE _sup_dissous ON COMMIT DROP AS
        SELECT subtype, ST_Union(geom_2975) AS geom_2975
        FROM spatial_layers WHERE kind = 'sup' GROUP BY subtype"""))
    db.execute(text("""
        CREATE TABLE tuyau_sup AS
        SELECT 'sup'::text AS kind, d.subtype, NULL::text AS name, NULL::text AS commune,
               jsonb_build_object('subtype', d.subtype) AS attrs, p.geom AS geom_2975
        FROM _sup_dissous d, LATERAL ST_Subdivide(d.geom_2975, 256) AS p(geom)"""))
    db.execute(text("CREATE INDEX tuyau_sup_gix ON tuyau_sup USING GIST (geom_2975)"))
    db.execute(text("CREATE INDEX tuyau_sup_kind ON tuyau_sup (kind, subtype)"))
    db.execute(text("ANALYZE tuyau_sup"))
    n = db.execute(text("SELECT count(*) FROM tuyau_sup")).scalar() or 0
    db.commit()
    _CACHE.clear()
    return int(n)


def build_tuyau_telepherique(db: Session) -> int:
    """COUCHES-RECETTE-2 Lot D — ajoute le 2e téléphérique EN PROJET « Payanké » (CINOR, ligne
    Bellepierre ↔ La Montagne, mise en service annoncée ~2029) à la couche telepherique, SANS toucher
    spatial_layers (donc :8020 intact) : table dérivée = telepherique servi + la ligne projet.

    Le TRACÉ officiel (câble au-dessus de la Ravine du Butor) n'est pas publié en GIS. Les deux
    STATIONS, elles, sont publiées : station haute « Belvédère - La Vigie » à La Montagne (nœud OSM,
    55.4330/-20.8848) et station basse à Bellepierre (bas, intersection rue Bertin, près du CHU Félix
    Guyon, ~55.4448/-20.8918). On sert donc un SEGMENT INDICATIF entre les deux stations annoncées,
    étiqueté « Projet — tracé indicatif » (subtype=ligne_projet), source CINOR citée. Rien inventé
    au-delà des stations publiées ; la précision du câble n'est pas revendiquée."""
    db.execute(text("DROP TABLE IF EXISTS tuyau_telepherique"))
    db.execute(text("""
        CREATE TABLE tuyau_telepherique AS
        SELECT kind, subtype, name, commune, attrs, geom_2975
        FROM spatial_layers WHERE kind = 'telepherique'
        UNION ALL
        SELECT 'telepherique'::text, 'ligne_projet'::text, 'Payanké (projet)'::text, 'Saint-Denis'::text,
               jsonb_build_object(
                 'reseau', 'CINOR',
                 'statut', 'en projet (mise en service annoncée ~2029)',
                 'source', 'CINOR — ligne Bellepierre ↔ La Montagne ; tracé INDICATIF entre les deux stations annoncées'),
               ST_Transform(ST_SetSRID(
                 ST_MakeLine(ARRAY[ST_MakePoint(55.4448, -20.8918), ST_MakePoint(55.4330, -20.8848)]),
                 4326), 2975)"""))
    db.execute(text("CREATE INDEX tuyau_telepherique_gix ON tuyau_telepherique USING GIST (geom_2975)"))
    db.execute(text("CREATE INDEX tuyau_telepherique_kind ON tuyau_telepherique (kind, subtype)"))
    db.execute(text("ANALYZE tuyau_telepherique"))
    n = db.execute(text("SELECT count(*) FROM tuyau_telepherique")).scalar() or 0
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


# COUCHES-RECETTE-1 : mémoïse les tables déjà VUES existantes → plus de `to_regclass` par tuile
# (une table dérivée reconstruite l'est en DROP+CREATE dans UNE transaction : les autres connexions
# voient toujours l'ancienne jusqu'au commit — « existe » ne devient jamais faux à tort).
_TABLES_OK: set[str] = set()


def _table_manquante(db: Session, table: str) -> bool:
    if table in _TABLES_OK:
        return False
    existe = db.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is not None
    if existe:
        _TABLES_OK.add(table)
    return not existe


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
            # de couches en un toggle), etiquette (calque symbole d'étiquettes), icones (emoji par
            # sous-type) — tous rendus côté front.
            "centroide": bool(c.get("centroide", False)),
            "groupe": c.get("groupe"),
            "etiquette": c.get("etiquette"),
            "icones": c.get("icones"),
            "note": c.get("note"),
            # COUCHES-RECETTE-2 (retour) : clic PRÉCIS sur une couche affichée dissoute — `detail_kind`
            # dit au front d'interroger l'endpoint /map/couche-detail/{detail_kind} (table d'origine, non
            # dissoute) au point cliqué, et `popup_detail` les champs à afficher.
            "detail_kind": c.get("detail_kind"),
            "popup_detail": c.get("popup_detail"),
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


# SUP-GESTIONNAIRE-1 — le champ « gestionnaire » d'une SUP était DÉDUIT de la catégorie (subtype),
# pas présent dans la donnée source (le jeu GPU des assiettes ne porte AUCUN champ d'autorité :
# attrs = generateur_type/nom, nomass, urlreg, typeass…). Un libellé standardisé par famille n'est
# pas la donnée : il est retiré du détail au clic (endpoint + popup_detail). Le générateur de la
# servitude (generateur_type → « Servitude », generateur_nom → « Acte / périmètre ») reste, lui, réel.
@router.get("/map/couche-detail/{kind}")
def couche_detail(kind: str, lon: float, lat: float, db: Session = Depends(get_db)) -> dict:
    """COUCHES-RECETTE-2 (retour) — clic PRÉCIS sur une couche affichée dissoute : interroge la table
    D'ORIGINE (assiettes NON dissoutes) au point cliqué et renvoie le détail de la (des) servitude(s)
    concernée(s). Seuls les kinds explicitement autorisés (avec un `detail_kind` déclaré) sont servis."""
    from ..registre.declarations import couches_carte
    autorises = {c.get("detail_kind") for c in couches_carte() if c.get("detail_kind")}
    if kind not in autorises:
        return Response(status_code=404)  # type: ignore[return-value]
    # point cliqué (WGS84) → SRID de spatial_layers (2975). Assiettes contenant le point.
    sql = text("""
        SELECT DISTINCT subtype,
               attrs->>'generateur_type' AS libelle,
               attrs->>'generateur_nom'  AS acte,
               attrs->>'nomass'          AS assiette,
               attrs->>'urlreg'          AS urlreg
        FROM spatial_layers
        WHERE kind = :k
          AND ST_Contains(geom_2975, ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 2975))
        LIMIT 12""")
    rows = db.execute(sql, {"k": kind, "lon": lon, "lat": lat}).mappings().all()
    servitudes = []
    for r in rows:
        servitudes.append({
            "code": (r["subtype"] or "").upper(),
            "libelle": r["libelle"] or "",
            "acte": r["acte"] or "",
            "assiette": r["assiette"] or "",
            "urlreg": r["urlreg"] or "",
        })
    return {"servitudes": servitudes}
