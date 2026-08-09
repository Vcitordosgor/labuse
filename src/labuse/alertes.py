"""3.C — Alertes intelligentes (« nouveautés »).

Le SCOPE est défini par l'utilisateur — on n'inonde pas avec les 3 000 parcelles :
- **ZONES DE VEILLE** : polygones dessinés sur la carte (`watch_zones`).

Au RAFRAÎCHISSEMENT (`compute_alertes`), on détecte les faits qui touchent ce scope :
- une vente **DVF** tombant dans une zone de veille dessinée      → alerte `dvf_in_zone`

M54-EXPO-2 (arbitrage Vic 10/08) : le kind `permit_near_followed` (permis SITADEL près d'une
parcelle suivie) est RETIRÉ — la cloche (events M-T, kind='permis') couvre déjà ce fait. Un
signal, un canal. Ce module ne garde que sa valeur UNIQUE : les ventes DVF en zone dessinée.

**Idempotent** : un même fait-source ne déclenche qu'UNE alerte (index unique partiel +
`ON CONFLICT DO NOTHING`). Re-rafraîchir sans donnée neuve n'ajoute rien ; une donnée
nouvellement ingérée apparaît exactement une fois. v1 = détection + liste de nouveautés
(pas de notification push — hors scope, cf. brief 3.C).

Ce module ne fabrique aucune donnée : il croise des faits RÉELS déjà ingérés (DVF) avec un
scope choisi par l'utilisateur.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# ───────────────────────────── Zones de veille ─────────────────────────────

def create_watch_zone(session: Session, name: str, commune: str, polygon_geojson: dict,
                      cid: int | None) -> dict[str, Any]:
    """Crée une zone de veille à partir d'un polygone GeoJSON (EPSG:4326). `cid` = compte
    propriétaire (cloison M-K, hérité à l'insert ; None = bucket pilote)."""
    gid = session.execute(
        text("INSERT INTO watch_zones (name, commune, compte_id, geom) "
             "VALUES (:n, :c, :cid, ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)) RETURNING id"),
        {"n": name.strip()[:120] or "Zone de veille", "c": commune, "cid": cid,
         "g": json.dumps(polygon_geojson)},
    ).scalar()
    session.flush()
    return {"id": gid, "name": name, "commune": commune}


def list_watch_zones(session: Session, commune: str | None, cid: int | None) -> list[dict[str, Any]]:
    """Zones de veille DU COMPTE `cid` (cloison M-K : jamais celles d'un autre compte)."""
    rows = session.execute(
        text("""SELECT z.id, z.name, z.commune, z.created_at,
                       ST_AsGeoJSON(z.geom) AS geojson,
                       round(ST_Area(ST_Transform(z.geom, 2975))::numeric) AS area_m2,
                       (SELECT count(*) FROM alertes a WHERE a.zone_id = z.id) AS n_alertes
                FROM watch_zones z
                WHERE z.compte_id IS NOT DISTINCT FROM :cid
                  AND (CAST(:c AS text) IS NULL OR z.commune = :c)
                ORDER BY z.created_at DESC"""),
        {"c": commune, "cid": cid},
    ).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        d["geojson"] = json.loads(d["geojson"]) if d.get("geojson") else None
        d["area_m2"] = int(d["area_m2"]) if d.get("area_m2") is not None else None
        out.append(d)
    return out


def rename_watch_zone(session: Session, zone_id: int, name: str, cid: int | None) -> bool:
    """M54-EXPO-3 — renomme une zone du compte `cid` (SEC-IDOR : rowcount 0 → 404). Nom borné."""
    n = session.execute(
        text("UPDATE watch_zones SET name = :n WHERE id = :i AND compte_id IS NOT DISTINCT FROM :cid"),
        {"n": name.strip()[:120] or "Zone de veille", "i": zone_id, "cid": cid}).rowcount
    session.flush()
    return n > 0


def delete_watch_zone(session: Session, zone_id: int, cid: int | None) -> bool:
    """SEC-IDOR (M-K) : ne supprime QUE si la zone appartient au compte `cid` (sinon rowcount
    0 → l'endpoint répond 404, jamais 403)."""
    n = session.execute(
        text("DELETE FROM watch_zones WHERE id = :i AND compte_id IS NOT DISTINCT FROM :cid"),
        {"i": zone_id, "cid": cid}).rowcount
    session.flush()
    return n > 0


# ───────────────────────────── Détection ─────────────────────────────

def compute_alertes(session: Session, commune: str, cid: int | None) -> dict[str, int]:
    """Détecte les nouveautés du scope DU COMPTE `cid`. Renvoie le nb de NOUVELLES alertes par
    type (les faits déjà vus sont ignorés par les index uniques).

    Cloison M-K (P1-9) : ne croise QUE les zones de veille du compte `cid` ; l'alerte hérite du
    compte propriétaire (z.compte_id = :cid) — jamais la zone d'un compte n'alimente un autre.

    M54-EXPO-2 (arbitrage Vic 10/08) : le kind `permit_near_followed` est RETIRÉ. Les permis près
    d'une parcelle suivie sont DÉJÀ servis par la cloche (events M-T, kind='permis') — un signal,
    un canal. Ce canal ne garde que sa valeur UNIQUE : les ventes DVF dans une zone DESSINÉE."""
    n_dvf = session.execute(
        text("""INSERT INTO alertes (kind, zone_id, compte_id, source_ref, label, payload, detected_at)
                SELECT 'dvf_in_zone', z.id, z.compte_id, d.id::text,
                       'Vente DVF dans « ' || z.name || ' »',
                       jsonb_build_object('date', d.date_mutation, 'valeur_fonciere', d.valeur_fonciere,
                                          'nature', d.nature_mutation, 'type_local', d.type_local,
                                          'surface_terrain', d.surface_terrain, 'zone', z.name),
                       now()
                FROM watch_zones z
                JOIN dvf_mutations d ON d.geom IS NOT NULL AND ST_Contains(z.geom, d.geom)
                WHERE z.commune = :c AND z.compte_id IS NOT DISTINCT FROM :cid
                ON CONFLICT DO NOTHING
                RETURNING 1"""),
        {"c": commune, "cid": cid},
    ).rowcount

    session.execute(
        text("UPDATE watch_zones SET last_run_at = now() "
             "WHERE commune = :c AND compte_id IS NOT DISTINCT FROM :cid"),
        {"c": commune, "cid": cid})
    session.flush()
    return {"dvf_in_zone": n_dvf, "total": n_dvf}


# ───────────────────────────── Liste / accusé ─────────────────────────────

def list_alertes(session: Session, commune: str | None, cid: int | None, *,
                 only_new: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    """Nouveautés DU COMPTE `cid` (cloison M-K), non-lues d'abord puis par date décroissante."""
    rows = session.execute(
        text("""SELECT a.id, a.kind, a.label, a.payload, a.acknowledged, a.detected_at,
                       z.name AS zone_name, p.idu AS parcel_idu
                FROM alertes a
                LEFT JOIN watch_zones z ON z.id = a.zone_id
                LEFT JOIN parcels p ON p.id = a.parcel_id
                WHERE a.compte_id IS NOT DISTINCT FROM :cid
                  AND (CAST(:c AS text) IS NULL OR z.commune = :c OR p.commune = :c)
                  AND (:onlynew = false OR a.acknowledged = false)
                ORDER BY a.acknowledged ASC, a.detected_at DESC
                LIMIT :lim"""),
        {"c": commune, "cid": cid, "onlynew": only_new, "lim": limit},
    ).mappings().all()
    return [dict(r) for r in rows]


def acknowledge(session: Session, cid: int | None, *,
                alerte_id: int | None = None, commune: str | None = None) -> int:
    """Marque comme lue une alerte (par id) ou toutes celles d'une commune, DU COMPTE `cid`.
    SEC-IDOR (M-K) : on n'accuse jamais réception d'une alerte d'un autre compte."""
    if alerte_id is not None:
        n = session.execute(
            text("UPDATE alertes SET acknowledged = true WHERE id = :i AND acknowledged = false"
                 " AND compte_id IS NOT DISTINCT FROM :cid"),
            {"i": alerte_id, "cid": cid},
        ).rowcount
    else:
        n = session.execute(
            text("""UPDATE alertes SET acknowledged = true
                    WHERE acknowledged = false AND compte_id IS NOT DISTINCT FROM :cid AND id IN (
                       SELECT a.id FROM alertes a
                       LEFT JOIN watch_zones z ON z.id = a.zone_id
                       LEFT JOIN parcels p ON p.id = a.parcel_id
                       WHERE (CAST(:c AS text) IS NULL OR z.commune = :c OR p.commune = :c))"""),
            {"c": commune, "cid": cid},
        ).rowcount
    session.flush()
    return n
