"""Ingestion Cartofriches (Vague C1) → spatial_layers kind='friche'  [data pure].

Friches (terrains à reconvertir) de l'inventaire national Cerema, rattachées aux parcelles de
façon EXACTE via `unite_fonciere_refcad` (liste d'IDU), fallback polygone `ST_Intersects`.
Stockage : spatial_layers (géométrie /geofriches + attrs jsonb résumé & détail curé) — validé Vic.

La donnée d'abord, le scoring ensuite : signal promoteur (mutabilité) branché PLUS TARD
(# TODO étage 1/2). Ce module N'ALIMENTE PAS le score.
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.cartofriches import DETAIL_FIELDS, CartofrichesConnector
from .layers_ingest import _insert_layer

SOURCE_NAME = "Cartofriches (Cerema)"

# Champs de résumé (properties /geofriches) conservés tels quels dans attrs.
SUMMARY_FIELDS = (
    "site_nom", "site_type", "site_adresse", "site_statut", "comm_insee",
    "proprio_personne", "unite_fonciere_surface", "source_nom", "nature", "urba_zone_type",
)


def _refcad(props: dict) -> list[str]:
    """`unite_fonciere_refcad` normalisé en liste d'IDU (l'API le sert en liste ; parfois chaîne)."""
    v = props.get("unite_fonciere_refcad")
    if isinstance(v, list):
        return [str(x) for x in v if x]
    if isinstance(v, str) and v:
        try:
            return [str(x) for x in json.loads(v.replace("'", '"')) if x]
        except (ValueError, TypeError):
            return [v]
    return []


def parse_friche(feature: dict, detail: dict | None = None) -> dict | None:
    """Feature GeoJSON /geofriches (+ détail optionnel) → dict couche. None si pas de géométrie."""
    geom = feature.get("geometry")
    if not isinstance(geom, dict) or not geom.get("coordinates"):
        return None
    props = feature.get("properties") or {}
    refcad = _refcad(props)
    attrs = {k: props.get(k) for k in SUMMARY_FIELDS}
    attrs["site_id"] = feature.get("id")
    attrs["refcad"] = refcad
    if detail:
        attrs["detail"] = {k: detail.get(k) for k in DETAIL_FIELDS}
    return {
        "kind": "friche",
        "subtype": props.get("site_statut"),        # « friche avec projet » / « sans projet »
        "name": props.get("site_nom"),
        "geometry": geom,
        "attrs": attrs,
    }


def _source_id(session: Session) -> int | None:
    return session.execute(
        text("SELECT id FROM data_sources WHERE name = :n"), {"n": SOURCE_NAME}).scalar()


def ingest_commune(session: Session, insee: str, commune: str, run_id: int | None = None,
                   connector: CartofrichesConnector | None = None, with_detail: bool = True) -> int:
    """Ingère les friches d'une commune dans spatial_layers (kind='friche'). Retourne le compte.

    Idempotent : purge les friches de la commune AVANT réinsertion (rejouable sans doublon).
    ⚠ ÉCRIT + APPELS RÉSEAU. `with_detail` : enrichit chaque friche des 78 champs (1 appel/friche).
    """
    connector = connector or CartofrichesConnector()
    sid = _source_id(session)
    session.execute(text("DELETE FROM spatial_layers WHERE commune = :c AND kind = 'friche'"),
                    {"c": commune})
    n = 0
    for feat in connector.geofriches(insee):
        detail = connector.detail(feat.get("id")) if with_detail else None
        p = parse_friche(feat, detail)
        if not p:
            continue
        _insert_layer(session, "friche", p["subtype"], p["name"], p["geometry"],
                      sid, commune, run_id, p["attrs"])
        n += 1
    _touch_source(session)
    session.flush()
    return n


def parcelles_croisees(session: Session, commune: str) -> dict:
    """Parcelles rattachées aux friches d'une commune : EXACT (idu ∈ refcad) + fallback polygone."""
    exact = session.execute(text(
        "SELECT count(DISTINCT p.id) FROM parcels p "
        "WHERE p.commune = :c AND EXISTS ("
        "  SELECT 1 FROM spatial_layers l, jsonb_array_elements_text(l.attrs->'refcad') AS ref(idu) "
        "  WHERE l.kind='friche' AND l.commune = :c AND ref.idu = p.idu)"),
        {"c": commune}).scalar()
    poly = session.execute(text(
        "SELECT count(DISTINCT p.id) FROM parcels p "
        "WHERE p.commune = :c AND EXISTS ("
        "  SELECT 1 FROM spatial_layers l WHERE l.kind='friche' AND l.commune = :c "
        "  AND ST_Intersects(p.geom_2975, l.geom_2975))"),
        {"c": commune}).scalar()
    return {"exact_refcad": int(exact or 0), "polygone": int(poly or 0)}


def sample_report(session: Session, commune: str, n_examples: int = 5) -> dict:
    n_friches = int(session.execute(text(
        "SELECT count(*) FROM spatial_layers WHERE kind='friche' AND commune=:c"),
        {"c": commune}).scalar() or 0)
    ex = [dict(r) for r in session.execute(text(
        "SELECT name, subtype, attrs->>'site_id' AS site_id, "
        "       attrs->>'unite_fonciere_surface' AS surface, "
        "       jsonb_array_length(COALESCE(attrs->'refcad','[]'::jsonb)) AS n_parcelles "
        "FROM spatial_layers WHERE kind='friche' AND commune=:c AND name IS NOT NULL "
        "ORDER BY (attrs->>'unite_fonciere_surface')::float DESC NULLS LAST LIMIT :n"),
        {"c": commune, "n": n_examples}).mappings().all()]
    return {"commune": commune, "friches": n_friches,
            "parcelles_croisees": parcelles_croisees(session, commune), "exemples": ex}


def _touch_source(session: Session) -> None:
    session.execute(
        text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})
