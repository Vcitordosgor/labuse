"""Contexte d'évaluation : accès PostGIS partagé par les couches.

Centralise les requêtes spatiales (intersection en 2975, voisinage par rayon)
pour qu'aucune couche ne réécrive de SQL — et que la discipline CRS reste tenue.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config


@dataclass
class ParcelRef:
    id: int
    idu: str
    commune: str | None = None
    surface_m2: float | None = None


@dataclass
class Intersection:
    subtype: str | None
    name: str | None
    coverage: float            # part (0..1) de la parcelle couverte, calculée en 2975
    attrs: dict[str, Any]
    source_name: str | None


class EvalContext:
    def __init__(self, session: Session, rules: dict | None = None):
        self.session = session
        self.rules = rules or config.cascade_rules()
        self._source_ids: dict[str, int | None] = {}
        self._kind_present: dict[str, bool] = {}

    # ───────────────────────── requêtes spatiales ─────────────────────────

    def intersections(self, parcel_id: int, kind: str) -> list[Intersection]:
        """Entités `spatial_layers` de ce `kind` qui intersectent la parcelle.

        ST_Intersects (test topologique, CRS-agnostique) pour le filtre ;
        couverture mesurée en 2975 (jamais en degrés).
        """
        sql = text(
            """
            SELECT sl.subtype, sl.name, sl.attrs,
                   ST_Area(ST_Intersection(ST_Transform(p.geom, 2975), ST_Transform(sl.geom, 2975)))
                     / NULLIF(ST_Area(ST_Transform(p.geom, 2975)), 0) AS coverage,
                   ds.name AS source_name
            FROM parcels p
            JOIN spatial_layers sl
              ON sl.kind = :kind AND ST_Intersects(p.geom, sl.geom)
            LEFT JOIN data_sources ds ON ds.id = sl.data_source_id
            WHERE p.id = :pid
            """
        )
        rows = self.session.execute(sql, {"kind": kind, "pid": parcel_id}).mappings().all()
        return [
            Intersection(r["subtype"], r["name"], float(r["coverage"] or 0.0), r["attrs"] or {}, r["source_name"])
            for r in rows
        ]

    def kind_present(self, kind: str) -> bool:
        """Une couche `spatial_layers` de ce `kind` est-elle ingérée ? (→ UNKNOWN sinon).

        Distingue « donnée absente » (UNKNOWN, impacte la complétude) de « donnée
        présente mais parcelle non contrainte » (PASS). Mis en cache par kind.
        """
        if kind not in self._kind_present:
            self._kind_present[kind] = bool(
                self.session.execute(
                    text("SELECT EXISTS(SELECT 1 FROM spatial_layers WHERE kind = :k)"), {"k": kind}
                ).scalar()
            )
        return self._kind_present[kind]

    def table_has_commune(self, table: str, commune: str | None) -> bool:
        """Y a-t-il des lignes ingérées pour la commune dans dvf_mutations/sitadel_permits."""
        if table not in {"dvf_mutations", "sitadel_permits"}:
            raise ValueError(table)
        sql = text(f"SELECT EXISTS(SELECT 1 FROM {table} WHERE CAST(:c AS text) IS NULL OR commune = :c)")
        return bool(self.session.execute(sql, {"c": commune}).scalar())

    def centroid_in(self, parcel_id: int, kind: str) -> bool:
        """Le centroïde de la parcelle tombe-t-il dans une entité de ce `kind` ?"""
        sql = text(
            """
            SELECT EXISTS(
              SELECT 1 FROM parcels p
              JOIN spatial_layers sl ON sl.kind = :kind AND ST_Contains(sl.geom, p.centroid)
              WHERE p.id = :pid
            )
            """
        )
        return bool(self.session.execute(sql, {"kind": kind, "pid": parcel_id}).scalar())

    def dvf_stats(self, parcel_id: int, radius_m: float, years: int) -> dict[str, Any]:
        """Stats DVF agrégées dans un rayon (m) autour du centroïde, sur N années.

        Médiane robuste ; jamais de mutation nominative exposée (R112 A-3 LPF).
        """
        sql = text(
            """
            SELECT count(*) AS n,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY d.valeur_fonciere) AS median_value
            FROM parcels p
            JOIN dvf_mutations d
              ON ST_DWithin(ST_Transform(p.centroid, 2975), ST_Transform(d.geom, 2975), :r)
            WHERE p.id = :pid
              AND (d.date_mutation IS NULL OR d.date_mutation >= now() - (:yrs || ' years')::interval)
            """
        )
        r = self.session.execute(sql, {"pid": parcel_id, "r": radius_m, "yrs": years}).mappings().one()
        return {"count": int(r["n"] or 0), "median_value": float(r["median_value"]) if r["median_value"] else None}

    def sitadel_near(self, parcel_id: int, radius_m: float, months: int) -> dict[str, Any]:
        """Permis SITADEL rattachés (IDU) ou à proximité (rayon = signal de zone, §7bis)."""
        sql = text(
            """
            WITH p AS (SELECT id, idu, centroid FROM parcels WHERE id = :pid)
            SELECT
              count(*) FILTER (WHERE jsonb_exists(s.idu_codes, p.idu)) AS matched_idu,
              count(*) FILTER (
                WHERE s.geom IS NOT NULL
                  AND ST_DWithin(ST_Transform(p.centroid, 2975), ST_Transform(s.geom, 2975), :r)
              ) AS nearby
            FROM p
            LEFT JOIN sitadel_permits s
              ON (s.date IS NULL OR s.date >= now() - (:mo || ' months')::interval)
            GROUP BY p.id
            """
        )
        r = self.session.execute(sql, {"pid": parcel_id, "r": radius_m, "mo": months}).mappings().first()
        if not r:
            return {"matched_idu": 0, "nearby": 0}
        return {"matched_idu": int(r["matched_idu"] or 0), "nearby": int(r["nearby"] or 0)}

    def latest_source_result(self, parcel_id: int, source_name: str) -> dict[str, Any] | None:
        """Dernier résultat d'une source pour la parcelle (ex. propriétaire manuel/mock)."""
        sql = text(
            """
            SELECT psr.status, psr.raw_payload, psr.summary
            FROM parcel_source_results psr
            JOIN data_sources ds ON ds.id = psr.data_source_id
            WHERE psr.parcel_id = :pid AND ds.name = :sname
            ORDER BY psr.fetched_at DESC
            LIMIT 1
            """
        )
        r = self.session.execute(sql, {"pid": parcel_id, "sname": source_name}).mappings().first()
        return dict(r) if r else None

    # ───────────────────────── sources ─────────────────────────

    def source_id(self, name: str | None) -> int | None:
        if not name:
            return None
        if name not in self._source_ids:
            sid = self.session.execute(
                text("SELECT id FROM data_sources WHERE name = :n"), {"n": name}
            ).scalar()
            self._source_ids[name] = sid
        return self._source_ids[name]
