"""3.C — Alertes intelligentes (« nouveautés »).

Le SCOPE est défini par l'utilisateur — on n'inonde pas avec les 3 000 parcelles :
- **ZONES DE VEILLE** : polygones dessinés sur la carte (`watch_zones`).
- **PARCELLES SUIVIES** : les parcelles du pipeline de prospection (`pipeline_entries`).

Au RAFRAÎCHISSEMENT (`compute_alertes`), on détecte les faits qui touchent ce scope :
- une vente **DVF** tombant dans une zone de veille            → alerte `dvf_in_zone`
- un **permis** (SITADEL géocodé, 1.B) à ≤ R d'une parcelle suivie → `permit_near_followed`

**Idempotent** : un même fait-source ne déclenche qu'UNE alerte (index unique partiel +
`ON CONFLICT DO NOTHING`). Re-rafraîchir sans donnée neuve n'ajoute rien ; une donnée
nouvellement ingérée apparaît exactement une fois. v1 = détection + liste de nouveautés
(pas de notification push — hors scope, cf. brief 3.C).

Ce module ne fabrique aucune donnée : il croise des faits RÉELS déjà ingérés (DVF, SITADEL)
avec un scope choisi par l'utilisateur.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# ───────────────────────────── Zones de veille ─────────────────────────────

def create_watch_zone(session: Session, name: str, commune: str, polygon_geojson: dict) -> dict[str, Any]:
    """Crée une zone de veille à partir d'un polygone GeoJSON (EPSG:4326)."""
    gid = session.execute(
        text("INSERT INTO watch_zones (name, commune, geom) "
             "VALUES (:n, :c, ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)) RETURNING id"),
        {"n": name.strip()[:120] or "Zone de veille", "c": commune, "g": json.dumps(polygon_geojson)},
    ).scalar()
    session.flush()
    return {"id": gid, "name": name, "commune": commune}


def list_watch_zones(session: Session, commune: str | None = None) -> list[dict[str, Any]]:
    rows = session.execute(
        text("""SELECT z.id, z.name, z.commune, z.created_at,
                       ST_AsGeoJSON(z.geom) AS geojson,
                       round(ST_Area(ST_Transform(z.geom, 2975))::numeric) AS area_m2,
                       (SELECT count(*) FROM alertes a WHERE a.zone_id = z.id) AS n_alertes
                FROM watch_zones z
                WHERE (CAST(:c AS text) IS NULL OR z.commune = :c)
                ORDER BY z.created_at DESC"""),
        {"c": commune},
    ).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        d["geojson"] = json.loads(d["geojson"]) if d.get("geojson") else None
        d["area_m2"] = int(d["area_m2"]) if d.get("area_m2") is not None else None
        out.append(d)
    return out


def delete_watch_zone(session: Session, zone_id: int) -> bool:
    n = session.execute(text("DELETE FROM watch_zones WHERE id = :i"), {"i": zone_id}).rowcount
    session.flush()
    return n > 0


# ───────────────────────────── Détection ─────────────────────────────

def compute_alertes(session: Session, commune: str, *, permit_radius_m: int = 200) -> dict[str, int]:
    """Détecte les nouveautés du scope (zones + parcelles suivies). Renvoie le nb de NOUVELLES
    alertes par type (les faits déjà vus sont ignorés par les index uniques)."""
    n_dvf = session.execute(
        text("""INSERT INTO alertes (kind, zone_id, source_ref, label, payload, detected_at)
                SELECT 'dvf_in_zone', z.id, d.id::text,
                       'Vente DVF dans « ' || z.name || ' »',
                       jsonb_build_object('date', d.date_mutation, 'valeur_fonciere', d.valeur_fonciere,
                                          'nature', d.nature_mutation, 'type_local', d.type_local,
                                          'surface_terrain', d.surface_terrain, 'zone', z.name),
                       now()
                FROM watch_zones z
                JOIN dvf_mutations d ON d.geom IS NOT NULL AND ST_Contains(z.geom, d.geom)
                WHERE z.commune = :c
                ON CONFLICT DO NOTHING
                RETURNING 1"""),
        {"c": commune},
    ).rowcount

    n_permit = session.execute(
        text("""INSERT INTO alertes (kind, parcel_id, source_ref, label, payload, detected_at)
                SELECT 'permit_near_followed', p.id, s.id::text,
                       'Permis ' || COALESCE(s.type, '') || ' près de ' || p.idu,
                       jsonb_build_object('date', s.date, 'type', s.type, 'idu', p.idu,
                          'within_m', round(ST_Distance(ST_Transform(p.centroid, 2975),
                                                        ST_Transform(s.geom, 2975))::numeric)),
                       now()
                FROM pipeline_entries pe
                JOIN parcels p ON p.id = pe.parcel_id
                JOIN sitadel_permits s ON s.geom IS NOT NULL
                     AND ST_DWithin(ST_Transform(p.centroid, 2975), ST_Transform(s.geom, 2975), :r)
                WHERE p.commune = :c
                ON CONFLICT DO NOTHING
                RETURNING 1"""),
        {"c": commune, "r": permit_radius_m},
    ).rowcount

    session.execute(text("UPDATE watch_zones SET last_run_at = now() WHERE commune = :c"), {"c": commune})
    session.flush()
    return {"dvf_in_zone": n_dvf, "permit_near_followed": n_permit, "total": n_dvf + n_permit}


# ───────────────────────────── Liste / accusé ─────────────────────────────

def list_alertes(session: Session, commune: str | None = None, *,
                 only_new: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    """Nouveautés, non-lues d'abord puis par date décroissante."""
    rows = session.execute(
        text("""SELECT a.id, a.kind, a.label, a.payload, a.acknowledged, a.detected_at,
                       z.name AS zone_name, p.idu AS parcel_idu
                FROM alertes a
                LEFT JOIN watch_zones z ON z.id = a.zone_id
                LEFT JOIN parcels p ON p.id = a.parcel_id
                WHERE (CAST(:c AS text) IS NULL OR z.commune = :c OR p.commune = :c)
                  AND (:onlynew = false OR a.acknowledged = false)
                ORDER BY a.acknowledged ASC, a.detected_at DESC
                LIMIT :lim"""),
        {"c": commune, "onlynew": only_new, "lim": limit},
    ).mappings().all()
    return [dict(r) for r in rows]


def acknowledge(session: Session, *, alerte_id: int | None = None, commune: str | None = None) -> int:
    """Marque comme lue une alerte (par id) ou toutes celles d'une commune. Renvoie le nb modifié."""
    if alerte_id is not None:
        n = session.execute(
            text("UPDATE alertes SET acknowledged = true WHERE id = :i AND acknowledged = false"),
            {"i": alerte_id},
        ).rowcount
    else:
        n = session.execute(
            text("""UPDATE alertes SET acknowledged = true
                    WHERE acknowledged = false AND id IN (
                       SELECT a.id FROM alertes a
                       LEFT JOIN watch_zones z ON z.id = a.zone_id
                       LEFT JOIN parcels p ON p.id = a.parcel_id
                       WHERE (CAST(:c AS text) IS NULL OR z.commune = :c OR p.commune = :c))"""),
            {"c": commune},
        ).rowcount
    session.flush()
    return n
