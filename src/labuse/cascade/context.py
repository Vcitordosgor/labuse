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
        # Caches batch (remplis par prime()) : évitent une requête par parcelle×couche.
        self._primed_ids: set[int] = set()
        self._inter: dict[tuple[int, str], list[Intersection]] = {}
        self._centroid: dict[tuple[int, str], bool] = {}
        self._near: dict[tuple[int, str], float] = {}   # min distance (m, 2975) à un kind linéaire
        self._dvf: dict[int, dict[int, dict]] = {}
        self._sitadel: dict[int, dict] = {}
        self._ff: dict[int, dict] = {}
        self._fbz: dict[int, tuple[int, int, int]] = {}

    # ───────────────────────── batch (commune entière) ─────────────────────────

    def _layer_params(self, name: str) -> dict:
        for lc in self.rules.get("layers", []):
            if lc.get("name") == name:
                return lc.get("params", {}) or {}
        return {}

    def prime(self, parcel_ids: list[int]) -> None:
        """Précalcule EN BATCH les requêtes spatiales pour tout l'ensemble de parcelles
        (une requête par famille au lieu d'une par parcelle×couche) — brief §4 : la
        cascade tourne en batch sur toute la commune. Les getters lisent ensuite le cache."""
        ids = list(parcel_ids)
        if not ids:
            return
        self._primed_ids = set(ids)

        # kind='batiment' (>10k polygones BD TOPO par commune) est EXCLU : aucune couche
        # cascade ne le lit — il alimente le DÉCLASSEMENT (compute_declass_signals) et la
        # fiche « Occupation », qui font leurs propres requêtes ciblées. Le garder ici
        # multiplierait le coût d'intersection sans changer aucun verdict.
        for r in self.session.execute(
            text(
                """
                SELECT p.id AS pid, sl.kind, sl.subtype, sl.name, sl.attrs,
                       ST_Area(ST_Intersection(p.geom_2975, sl.geom_2975))
                         / NULLIF(ST_Area(p.geom_2975), 0) AS coverage,
                       ds.name AS source_name
                FROM parcels p
                JOIN spatial_layers sl ON ST_Intersects(p.geom_2975, sl.geom_2975)
                LEFT JOIN data_sources ds ON ds.id = sl.data_source_id
                WHERE p.id = ANY(:ids) AND sl.kind <> 'batiment'
                """
            ), {"ids": ids}
        ).mappings().all():
            self._inter.setdefault((r["pid"], r["kind"]), []).append(
                Intersection(r["subtype"], r["name"], float(r["coverage"] or 0.0), r["attrs"] or {}, r["source_name"]))

        # Centroïde ∈ entité : SEULE la couche « eau » consomme centroid_in (cf. EauLayer).
        # On restreint donc la précomputation au `kind` concerné, sinon on testait
        # ST_Contains sur les 244k entités de TOUS les kinds — requête DOMINANTE du batch
        # (ex. ~7 min pour un lot de 2000 parcelles). Résultat STRICTEMENT IDENTIQUE :
        # centroid_in n'est jamais lu pour les autres kinds (un seul appelant, vérifié).
        centroid_kinds = {k for k in (self._layer_params("eau").get("spatial_kind"),) if k}
        if centroid_kinds:
            for pid, kind in self.session.execute(
                text(
                    """SELECT p.id, sl.kind FROM parcels p
                       JOIN spatial_layers sl ON sl.kind = ANY(:kinds)
                         AND ST_Contains(sl.geom, p.centroid)
                       WHERE p.id = ANY(:ids)"""
                ), {"ids": ids, "kinds": list(centroid_kinds)}
            ).all():
                self._centroid[(pid, kind)] = True

        # Distance min (m, 2975) à des kinds où la PROXIMITÉ compte (ST_Intersects ne la capte
        # pas) : ravine (axe linéaire) + water (surface → BORD/berge, 2.C). Batché sous un rayon
        # de garde, comme centroid_in. Consommé par la couche `ravine`.
        rp = self._layer_params("ravine")
        if rp.get("enabled", True) is not False and rp.get("spatial_kind"):
            near_cap = float(rp.get("search_cap_m", 60))
            near_kinds = [rp["spatial_kind"]] + list(rp.get("berge_kinds", []))
            for k in near_kinds:
                for pid, dist in self.session.execute(
                    text(
                        """SELECT p.id, MIN(ST_Distance(p.geom_2975, sl.geom_2975)) AS d
                           FROM parcels p JOIN spatial_layers sl ON sl.kind = :k
                             AND ST_DWithin(p.geom_2975, sl.geom_2975, :cap)
                           WHERE p.id = ANY(:ids) GROUP BY p.id"""
                    ), {"ids": ids, "k": k, "cap": near_cap}
                ).all():
                    self._near[(pid, k)] = float(dist)

        dp = self._layer_params("dvf")
        years = dp.get("lookback_years", 5)
        for radius in dp.get("radii_m", [250, 500, 1000]):
            self._dvf[radius] = {}
            for r in self.session.execute(
                text(
                    """SELECT p.id AS pid, count(*) AS n,
                              percentile_cont(0.5) WITHIN GROUP (ORDER BY d.valeur_fonciere) AS med,
                              percentile_cont(0.5) WITHIN GROUP (
                                ORDER BY d.valeur_fonciere / NULLIF(d.surface_terrain, 0))
                                FILTER (WHERE d.surface_terrain > 0 AND d.valeur_fonciere > 0) AS med_em2
                       FROM parcels p JOIN dvf_mutations d
                         ON ST_DWithin(ST_Transform(p.centroid, 2975), ST_Transform(d.geom, 2975), :r)
                       WHERE p.id = ANY(:ids)
                         AND (d.date_mutation IS NULL OR d.date_mutation >= now() - (:yrs || ' years')::interval)
                       GROUP BY p.id"""
                ), {"ids": ids, "r": radius, "yrs": years}
            ).mappings().all():
                self._dvf[radius][r["pid"]] = {"count": int(r["n"] or 0),
                                               "median_value": float(r["med"]) if r["med"] else None,
                                               "median_eur_m2": float(r["med_em2"]) if r["med_em2"] else None}

        sp = self._layer_params("sitadel")
        for r in self.session.execute(
            text(
                """WITH pp AS (SELECT id, idu, centroid FROM parcels WHERE id = ANY(:ids))
                   SELECT pp.id AS pid,
                     count(*) FILTER (WHERE jsonb_exists(s.idu_codes, pp.idu)) AS matched,
                     count(*) FILTER (WHERE s.geom IS NOT NULL AND
                        ST_DWithin(ST_Transform(pp.centroid, 2975), ST_Transform(s.geom, 2975), :r)) AS nearby
                   FROM pp LEFT JOIN sitadel_permits s
                     ON (s.date IS NULL OR s.date >= now() - (:mo || ' months')::interval)
                   GROUP BY pp.id"""
            ), {"ids": ids, "r": sp.get("radius_m", 200), "mo": sp.get("lookback_months", 36)}
        ).mappings().all():
            self._sitadel[r["pid"]] = {"matched_idu": int(r["matched"] or 0), "nearby": int(r["nearby"] or 0)}

        for r in self.session.execute(
            text(
                """SELECT DISTINCT ON (psr.parcel_id) psr.parcel_id AS pid, psr.status, psr.raw_payload, psr.summary
                   FROM parcel_source_results psr JOIN data_sources ds ON ds.id = psr.data_source_id
                   WHERE ds.name = :ff AND psr.parcel_id = ANY(:ids)
                   ORDER BY psr.parcel_id, psr.fetched_at DESC"""
            ), {"ids": ids, "ff": "Fichiers fonciers (Cerema)"}
        ).mappings().all():
            self._ff[r["pid"]] = {"status": r["status"], "raw_payload": r["raw_payload"], "summary": r["summary"]}

        radius = config.opportunity_weights().get("feedback", {}).get("zone_radius_m", 300)
        for pid, fp, gl, ni in self.session.execute(
            text(
                """WITH fb AS (SELECT pc.centroid, pf.verdict
                              FROM parcel_feedback pf JOIN parcels pc ON pc.id = pf.parcel_id)
                   SELECT p.id,
                     count(*) FILTER (WHERE fb.verdict = 'false_positive') AS fp,
                     count(*) FILTER (WHERE fb.verdict = 'good_lead') AS gl,
                     count(*) FILTER (WHERE fb.verdict = 'not_interested') AS ni
                   FROM parcels p
                   JOIN fb ON ST_DWithin(ST_Transform(p.centroid,2975), ST_Transform(fb.centroid,2975), :r)
                   WHERE p.id = ANY(:ids) GROUP BY p.id"""
            ), {"ids": ids, "r": radius}
        ).all():
            self._fbz[pid] = (int(fp), int(gl), int(ni))

    def feedback_counts(self, parcel_id: int) -> tuple[int, int, int]:
        """Agrégat du retour terrain dans la zone : (faux_positif, bon_lead, pas_intéressé) (§10)."""
        if parcel_id in self._primed_ids:
            return self._fbz.get(parcel_id, (0, 0, 0))
        radius = config.opportunity_weights().get("feedback", {}).get("zone_radius_m", 300)
        r = self.session.execute(
            text(
                """WITH fb AS (SELECT pc.centroid, pf.verdict
                              FROM parcel_feedback pf JOIN parcels pc ON pc.id = pf.parcel_id)
                   SELECT count(*) FILTER (WHERE fb.verdict = 'false_positive'),
                          count(*) FILTER (WHERE fb.verdict = 'good_lead'),
                          count(*) FILTER (WHERE fb.verdict = 'not_interested')
                   FROM parcels p
                   JOIN fb ON ST_DWithin(ST_Transform(p.centroid,2975), ST_Transform(fb.centroid,2975), :r)
                   WHERE p.id = :pid"""
            ), {"pid": parcel_id, "r": radius}
        ).first()
        return (int(r[0]), int(r[1]), int(r[2])) if r else (0, 0, 0)

    # ───────────────────────── requêtes spatiales ─────────────────────────

    def intersections(self, parcel_id: int, kind: str) -> list[Intersection]:
        """Entités `spatial_layers` de ce `kind` qui intersectent la parcelle.

        ST_Intersects (test topologique, CRS-agnostique) pour le filtre ;
        couverture mesurée en 2975 (jamais en degrés).
        """
        if parcel_id in self._primed_ids:
            return self._inter.get((parcel_id, kind), [])
        sql = text(
            """
            SELECT sl.subtype, sl.name, sl.attrs,
                   ST_Area(ST_Intersection(p.geom_2975, sl.geom_2975))
                     / NULLIF(ST_Area(p.geom_2975), 0) AS coverage,
                   ds.name AS source_name
            FROM parcels p
            JOIN spatial_layers sl
              ON sl.kind = :kind AND ST_Intersects(p.geom_2975, sl.geom_2975)
            LEFT JOIN data_sources ds ON ds.id = sl.data_source_id
            WHERE p.id = :pid
            """
        )
        rows = self.session.execute(sql, {"kind": kind, "pid": parcel_id}).mappings().all()
        return [
            Intersection(r["subtype"], r["name"], float(r["coverage"] or 0.0), r["attrs"] or {}, r["source_name"])
            for r in rows
        ]

    def min_distance_m(self, parcel_id: int, kind: str) -> float | None:
        """Distance min (m, 2975) de la parcelle à une entité de ce `kind`, ou None si au-delà
        du rayon de garde (cf. prime). Pour les couches linéaires (ravine) où la PROXIMITÉ
        compte, pas l'intersection."""
        if parcel_id in self._primed_ids:
            return self._near.get((parcel_id, kind))
        row = self.session.execute(
            text(
                """SELECT MIN(ST_Distance(p.geom_2975, sl.geom_2975))
                   FROM parcels p JOIN spatial_layers sl ON sl.kind = :k
                     AND ST_DWithin(p.geom_2975, sl.geom_2975, :cap)
                   WHERE p.id = :pid"""
            ), {"pid": parcel_id, "k": kind, "cap": 200.0}
        ).scalar()
        return float(row) if row is not None else None

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
        if parcel_id in self._primed_ids:
            return self._centroid.get((parcel_id, kind), False)
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
        if parcel_id in self._primed_ids and radius_m in self._dvf:
            return self._dvf[radius_m].get(parcel_id, {"count": 0, "median_value": None, "median_eur_m2": None})
        sql = text(
            """
            SELECT count(*) AS n,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY d.valeur_fonciere) AS median_value,
                   percentile_cont(0.5) WITHIN GROUP (
                     ORDER BY d.valeur_fonciere / NULLIF(d.surface_terrain, 0))
                     FILTER (WHERE d.surface_terrain > 0 AND d.valeur_fonciere > 0) AS median_eur_m2
            FROM parcels p
            JOIN dvf_mutations d
              ON ST_DWithin(ST_Transform(p.centroid, 2975), ST_Transform(d.geom, 2975), :r)
            WHERE p.id = :pid
              AND (d.date_mutation IS NULL OR d.date_mutation >= now() - (:yrs || ' years')::interval)
            """
        )
        r = self.session.execute(sql, {"pid": parcel_id, "r": radius_m, "yrs": years}).mappings().one()
        return {"count": int(r["n"] or 0),
                "median_value": float(r["median_value"]) if r["median_value"] else None,
                "median_eur_m2": float(r["median_eur_m2"]) if r["median_eur_m2"] else None}

    def sitadel_near(self, parcel_id: int, radius_m: float, months: int) -> dict[str, Any]:
        """Permis SITADEL rattachés (IDU) ou à proximité (rayon = signal de zone, §7bis)."""
        if parcel_id in self._primed_ids:
            return self._sitadel.get(parcel_id, {"matched_idu": 0, "nearby": 0})
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
        if parcel_id in self._primed_ids and source_name == "Fichiers fonciers (Cerema)":
            return self._ff.get(parcel_id)
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
