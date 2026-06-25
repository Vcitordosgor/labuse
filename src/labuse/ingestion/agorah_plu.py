"""Connecteur PLU AGORAH (repli / fallback) — « Base permanente des PLU de La Réunion ».

Source : AGORAH (agence d'urbanisme de La Réunion) via Open Data Réunion (OpenDataSoft).
Utilisé UNIQUEMENT en repli quand le Géoportail de l'Urbanisme (API Carto / WFS) ne sert
AUCUNE zone propre `DU_<INSEE>` pour une commune EXPLICITEMENT allowlistée (couverture
parcellaire ≥ 99 % validée au préalable en pré-vol lecture seule).

Le mapping vise le MÊME schéma que `plu_gpu_zone` (kind/subtype=typezone/name=libellé) ;
`attrs.source` distingue la provenance (AGORAH vs API Carto GPU). Module ISOLÉ : aucune
logique ad hoc dans le pipeline ; `layers_ingest.ingest_gpu_zones` n'appelle le repli que
si `should_use_agorah_fallback(...)` est vrai.
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

log = logging.getLogger("labuse")

ODS_BASE = "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets"
AGORAH_PLU_DATASET = "base-permanente-des-plu-de-la-reunion"
AGORAH_SOURCE = "AGORAH_BASE_PERMANENTE_PLU_REUNION"
_ODS_SELECT = "typezone,libelle,libelong,idurba,datappro,geo_shape"

# Communes dont la couverture AGORAH a été VALIDÉE ≥ 99 % en pré-vol lecture seule.
#   - Saint-André 97409 : 100,00 % (PLU 2019, récent/stable) → activée.
#   - Saint-Leu  97413 : 99,12 % — repli PROVISOIRE sur le PLU 2007 (idurba 97413_20070226).
#     Décision produit 2026-06-25 : commune à fort enjeu commercial (DVF 2470) ; révision PLU
#     enlisée (avis Région défavorable, approbation 2e sem. 2026 non stabilisée, géométrie révisée
#     non publiée en SIG) → analyse PROVISOIRE autorisée mais NON-GOLD. Saint-Leu RESTE non-gold
#     tant que le PLU révisé n'est pas approuvé + publié en géométrie exploitable ; le run devra
#     afficher un disclaimer fort. À réviser/retirer quand le nouveau PLU est disponible.
AGORAH_PLU_ALLOWLIST: frozenset[str] = frozenset({"97409", "97413"})


def agorah_partition(insee: str) -> str:
    """Partition canonique d'un document d'urbanisme (alignée GPU) : `DU_<INSEE>`."""
    return f"DU_{insee}"


def should_use_agorah_fallback(insee: str, gpu_propre_count: int) -> bool:
    """Repli AGORAH ssi le GPU n'a AUCUNE zone propre ET la commune est allowlistée.

    Jamais de repli si le GPU sert déjà des zones propres (`gpu_propre_count > 0`), ni
    pour une commune non allowlistée.
    """
    return gpu_propre_count == 0 and insee in AGORAH_PLU_ALLOWLIST


def _geo_shape_geometry(geo_shape: object) -> dict | None:
    """Extrait la géométrie GeoJSON d'un champ ODS `geo_shape` (Feature OU geometry)."""
    if not isinstance(geo_shape, dict):
        return None
    if geo_shape.get("type") == "Feature":
        g = geo_shape.get("geometry")
        return g if isinstance(g, dict) and g.get("type") else None
    if geo_shape.get("type") in ("Polygon", "MultiPolygon", "GeometryCollection"):
        return geo_shape
    return None


def agorah_zone_mapping(rec: dict, insee: str) -> dict | None:
    """PURE : un enregistrement AGORAH → dict prêt pour `spatial_layers` (kind=plu_gpu_zone).

    Renvoie None si la géométrie est absente/inexploitable. Conserve les attributs utiles
    dans `attrs` (source/insee/typezone/libelle/libelong/idurba/datappro/partition/url).
    """
    geom = _geo_shape_geometry(rec.get("geo_shape"))
    if not geom:
        return None
    typezone = (rec.get("typezone") or "").strip() or None
    libelle = rec.get("libelle")
    libelong = rec.get("libelong")
    return {
        "kind": "plu_gpu_zone",
        "subtype": typezone,
        "name": libelong or libelle,
        "geometry": geom,
        "attrs": {
            "source": AGORAH_SOURCE,
            "insee": insee,
            "typezone": typezone,
            "libelle": libelle,
            "libelong": libelong,
            "idurba": rec.get("idurba"),
            "datappro": rec.get("datappro"),
            "partition": agorah_partition(insee),
            "dataset_url": f"{ODS_BASE}/{AGORAH_PLU_DATASET}",
        },
    }


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=max(get_settings().http_timeout_s, 60.0),
        headers={"User-Agent": constants.USER_AGENT},
        follow_redirects=True,
    )


def fetch_agorah_zones(insee: str, *, client: httpx.Client | None = None, cap: int = 5000) -> list[dict]:
    """Récupère les enregistrements AGORAH (records ODS) d'une commune. LECTURE SEULE réseau."""
    own = client or _client()
    try:
        out: list[dict] = []
        offset, page = 0, 100
        while offset < cap:
            r = own.get(
                f"{ODS_BASE}/{AGORAH_PLU_DATASET}/records",
                params={"where": f"insee='{insee}'", "limit": page, "offset": offset, "select": _ODS_SELECT},
            )
            r.raise_for_status()
            res = r.json().get("results", []) or []
            out.extend(res)
            if len(res) < page:
                break
            offset += page
        return out
    finally:
        if client is None:
            own.close()


def ingest_agorah_plu_zones(session: Session, insee: str, commune: str,
                            run_id: int | None, source_id: int | None) -> int:
    """Insère les zones PLU AGORAH (repli) dans `spatial_layers` (kind='plu_gpu_zone')."""
    from .layers_ingest import _insert_layer  # import paresseux : évite tout cycle d'import
    n = 0
    for rec in fetch_agorah_zones(insee):
        m = agorah_zone_mapping(rec, insee)
        if not m:
            continue
        _insert_layer(session, m["kind"], m["subtype"], m["name"], m["geometry"],
                      source_id, commune, run_id, m["attrs"])
        n += 1
    log.warning("AGORAH PLU fallback[%s/%s] : %d zones insérées (source=%s)", commune, insee, n, AGORAH_SOURCE)
    return n


def agorah_plu_preflight(insee: str, parcel_points: list[tuple[float, float]] | None = None) -> dict:
    """Pré-vol LECTURE SEULE : récupère + valide les géométries AGORAH, résume, et (si
    `parcel_points` = liste de (lon, lat)) estime la couverture parcellaire.

    AUCUN accès base, AUCUN insert. Renvoie un dict résumé (zones, typezones, idurba,
    datappro, invalid_repaired, et coverage_pct si points fournis).
    """
    from collections import Counter

    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree

    zones: list = []
    tz: Counter = Counter()
    idu: Counter = Counter()
    dat: Counter = Counter()
    invalid = 0
    for rec in fetch_agorah_zones(insee):
        m = agorah_zone_mapping(rec, insee)
        if not m:
            invalid += 1
            continue
        try:
            g = shape(m["geometry"])
            if not g.is_valid:
                g = g.buffer(0)
                invalid += 1
            if g.is_empty:
                continue
            zones.append(g)
            tz[m["subtype"]] += 1
            idu[rec.get("idurba")] += 1
            dat[(rec.get("datappro") or "")[:10]] += 1
        except Exception:  # noqa: BLE001 — une géométrie cassée ne stoppe pas le pré-vol
            invalid += 1
    out: dict = {
        "insee": insee, "partition": agorah_partition(insee), "zones": len(zones),
        "typezones": dict(tz), "idurba": dict(idu), "datappro": dict(dat), "invalid_repaired": invalid,
    }
    if parcel_points and zones:
        tree = STRtree(zones)
        covered = 0
        for x, y in parcel_points:
            pt = Point(x, y)
            if any(zones[int(i)].covers(pt) for i in tree.query(pt)):
                covered += 1
        out["parcels"] = len(parcel_points)
        out["covered"] = covered
        out["coverage_pct"] = round(100.0 * covered / len(parcel_points), 2)
    return out
