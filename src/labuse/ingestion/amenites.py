"""Ingestion aménités (Vague C bonus) — POI OSM → spatial_layers kind='amenite' + signal distance.

Réutilise la machinerie Overpass existante (_overpass). 4 catégories validées : école, santé,
commerce, tcsp (bus). Pour chaque parcelle, distance (m, en 2975) au plus proche POI de chaque
catégorie → table parcel_amenites.

Signal CALCULÉ par parcelle (distances brutes), PAS des couches d'icônes. L'agrégation pondérée
en « score d'aménités » est # TODO étage 1 (poids au calibrage). NE touche PAS au score.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .layers_ingest import _insert_layer, _overpass

# catégorie → sélecteur Overpass (sur node ET way, centroïde via `out center`).
CATEGORIES = {
    "ecole": '["amenity"~"^(school|kindergarten|college)$"]',
    "sante": '["amenity"~"^(pharmacy|hospital|clinic|doctors)$"]',
    "commerce": '["shop"~"^(supermarket|convenience|bakery|mall)$"]',
    "tcsp": '["highway"="bus_stop"]',
}
DIST_COL = {"ecole": "dist_ecole_m", "sante": "dist_sante_m",
            "commerce": "dist_commerce_m", "tcsp": "dist_tcsp_m"}


def _query(selector: str, bbox: tuple[float, float, float, float]) -> str:
    minlon, minlat, maxlon, maxlat = bbox
    b = f"{minlat},{minlon},{maxlat},{maxlon}"
    return (f"[out:json][timeout:90];("
            f"node{selector}({b});way{selector}({b}););out center;")


def _points(data: dict):
    """Éléments Overpass → (lon, lat, nom). node : lat/lon ; way : center."""
    for el in (data or {}).get("elements") or []:
        if el.get("type") == "node":
            lon, lat = el.get("lon"), el.get("lat")
        else:
            ctr = el.get("center") or {}
            lon, lat = ctr.get("lon"), ctr.get("lat")
        if lon is None or lat is None:
            continue
        nom = (el.get("tags") or {}).get("name")
        yield float(lon), float(lat), nom


def ingest_poi_commune(session: Session, commune: str,
                       bbox: tuple[float, float, float, float]) -> dict:
    """Ingère les POI OSM des 4 catégories pour une commune → spatial_layers kind='amenite'.
    Idempotent (purge kind='amenite' de la commune avant réinsertion). ⚠ APPELS RÉSEAU (Overpass)."""
    sid = session.execute(
        text("SELECT id FROM data_sources WHERE name='OpenStreetMap / Overpass'")).scalar()
    session.execute(text("DELETE FROM spatial_layers WHERE commune=:c AND kind='amenite'"), {"c": commune})
    counts: dict[str, int] = {}
    for cat, sel in CATEGORIES.items():
        data = _overpass(_query(sel, bbox))
        n = 0
        for lon, lat, nom in _points(data):
            _insert_layer(session, "amenite", cat, nom, {"type": "Point", "coordinates": [lon, lat]},
                          sid, commune, None, {"categorie": cat, "name": nom})
            n += 1
        counts[cat] = n
    session.execute(text("UPDATE data_sources SET last_sync_at=now() WHERE name='OpenStreetMap / Overpass'"))
    session.flush()
    return counts


def compute_amenites_commune(session: Session, commune: str) -> int:
    """Calcule, pour chaque parcelle de la commune, la distance (2975) au plus proche POI de chaque
    catégorie (parmi TOUS les POI de l'île) → parcel_amenites. Idempotent (upsert par parcel_id)."""
    dist = ", ".join(
        f"(SELECT ST_Distance(p.geom_2975, a.geom_2975) FROM spatial_layers a "
        f" WHERE a.kind='amenite' AND a.subtype='{cat}' "
        f" ORDER BY p.geom_2975 <-> a.geom_2975 LIMIT 1) AS {col}"
        for cat, col in DIST_COL.items())
    n = session.execute(text(
        f"INSERT INTO parcel_amenites (parcel_id, dist_ecole_m, dist_sante_m, dist_commerce_m, dist_tcsp_m) "
        f"SELECT p.id, {dist} FROM parcels p WHERE p.commune=:c AND p.geom_2975 IS NOT NULL "
        f"ON CONFLICT (parcel_id) DO UPDATE SET "
        f"  dist_ecole_m=EXCLUDED.dist_ecole_m, dist_sante_m=EXCLUDED.dist_sante_m, "
        f"  dist_commerce_m=EXCLUDED.dist_commerce_m, dist_tcsp_m=EXCLUDED.dist_tcsp_m, computed_at=now()"),
        {"c": commune}).rowcount
    session.flush()
    return n


def sample_report(session: Session, commune: str) -> dict:
    poi = {r[0]: r[1] for r in session.execute(text(
        "SELECT subtype, count(*) FROM spatial_layers WHERE kind='amenite' AND commune=:c GROUP BY 1"),
        {"c": commune}).all()}
    med = session.execute(text(
        "SELECT count(*) AS parcelles, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY dist_ecole_m)::int AS med_ecole, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY dist_sante_m)::int AS med_sante, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY dist_commerce_m)::int AS med_commerce, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY dist_tcsp_m)::int AS med_tcsp "
        "FROM parcel_amenites a JOIN parcels p ON p.id=a.parcel_id WHERE p.commune=:c"),
        {"c": commune}).mappings().first()
    return {"commune": commune, "poi": poi, "distances_medianes_m": dict(med) if med else {}}
