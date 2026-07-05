"""Ingestion QPV 2024 (Vague C bonus) → spatial_layers kind='qpv'  [data pure].

Quartiers prioritaires (ANCT 2024) → couche géographique + intersection parcelles. Sert le
BILAN PROMOTEUR (dispositifs/abattements/TVA en QPV), PAS le score. # TODO bilan (non branché).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.qpv import QpvConnector
from .layers_ingest import _insert_layer

SOURCE_NAME = "QPV 2024 (ANCT)"


def parse_feature(feat: dict) -> dict | None:
    """Feature QPV → dict couche. None si pas de géométrie."""
    geom = feat.get("geometry")
    if not isinstance(geom, dict) or not geom.get("coordinates"):
        return None
    p = feat.get("properties") or {}
    return {
        "kind": "qpv",
        "subtype": p.get("insee_dep"),
        "name": p.get("lib_qp"),
        "geometry": geom,
        "attrs": {
            "code_qp": p.get("code_qp"), "lib_qp": p.get("lib_qp"),
            "insee_com": p.get("insee_com"), "lib_com": p.get("lib_com"),
            "insee_dep": p.get("insee_dep"), "siren_epci": p.get("siren_epci"),
            "generation": "2024",
        },
        "commune": p.get("lib_com"),
    }


def ingest(session: Session, connector: QpvConnector | None = None, dep: str = "974") -> dict:
    """Ingère les QPV du département dans spatial_layers (kind='qpv'). Idempotent (purge d'abord).
    ⚠ ÉCRIT + APPEL RÉSEAU (un téléchargement). Ne touche PAS au score (# TODO bilan)."""
    connector = connector or QpvConnector()
    sid = session.execute(text("SELECT id FROM data_sources WHERE name=:n"), {"n": SOURCE_NAME}).scalar()
    session.execute(text("DELETE FROM spatial_layers WHERE kind='qpv'"))
    n = 0
    for feat in connector.fetch_dep(dep):
        p = parse_feature(feat)
        if not p:
            continue
        _insert_layer(session, "qpv", p["subtype"], p["name"], p["geometry"],
                      sid, p["commune"], None, p["attrs"])
        n += 1
    session.execute(text("UPDATE data_sources SET last_sync_at=now() WHERE name=:n"), {"n": SOURCE_NAME})
    session.flush()
    return {"qpv": n}


def parcelles_en_qpv(session: Session) -> int:
    """Parcelles dont le centroïde/emprise intersecte un QPV (intersection géométrique)."""
    return int(session.execute(text(
        "SELECT count(DISTINCT p.id) FROM parcels p "
        "WHERE EXISTS (SELECT 1 FROM spatial_layers l WHERE l.kind='qpv' "
        "  AND ST_Intersects(p.geom_2975, l.geom_2975))")).scalar() or 0)


def bilan(session: Session) -> dict:
    total = int(session.execute(text("SELECT count(*) FROM spatial_layers WHERE kind='qpv'")).scalar() or 0)
    communes = int(session.execute(text(
        "SELECT count(DISTINCT commune) FROM spatial_layers WHERE kind='qpv'")).scalar() or 0)
    return {"qpv": total, "communes": communes, "parcelles_en_qpv": parcelles_en_qpv(session)}
