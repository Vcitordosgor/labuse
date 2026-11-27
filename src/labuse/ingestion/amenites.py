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
# catégories d'AFFICHAGE (mandat contexte-commune, liste promotrice) — la couche carte les
# montre, le scoring ne les lit PAS (câblage = dette G3 au backlog). Séparées de CATEGORIES :
# on n'y touche pas pour ne pas purger/dériver les POI qui alimentent parcel_amenites.
CATEGORIES_AFFICHAGE = {
    "mairie": '["amenity"="townhall"]',
    "police": '["amenity"~"^(police)$"]',           # gendarmerie taguée amenity=police en OSM
    "sport": '["leisure"~"^(sports_centre|stadium|pitch|swimming_pool)$"]',
    # M55-A (10/08) : élargissement BORNÉ validé Vic — marché forain, crèche, collège/lycée.
    # Rien d'autre. Affichage seul (le scoring ne les lit pas).
    "marche": '["amenity"="marketplace"]',
    "creche": '["amenity"="childcare"]',
    # collège & lycée : en France ils sont tagués amenity=school (comme le primaire) ; OSM ne les
    # sépare pas proprement — on les distingue par le nom (« Collège … » / « Lycée … »), best-effort
    # d'affichage. Le « . » couvre le caractère accentué (è / é) ; `,i` = insensible à la casse.
    "college_lycee": '["amenity"="school"]["name"~"coll.ge|lyc.e",i]',
}
DIST_COL = {"ecole": "dist_ecole_m", "sante": "dist_sante_m",
            "commerce": "dist_commerce_m", "tcsp": "dist_tcsp_m"}


def _query(selector: str, bbox: tuple[float, float, float, float]) -> str:
    minlon, minlat, maxlon, maxlat = bbox
    b = f"{minlat},{minlon},{maxlat},{maxlon}"
    return (f"[out:json][timeout:90];("
            f"node{selector}({b});way{selector}({b}););out center;")


def _points(data: dict, *, identifiants: bool = False):
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
        point = (float(lon), float(lat), nom)
        if identifiants:
            attrs = {"osm_type": el["type"], "osm_id": el["id"]} if el.get("id") is not None else {}
            yield (*point, attrs)
        else:
            yield point


def _remplacer_poi(session: Session, commune: str, bbox, categories: dict, *, affichage: bool) -> dict:
    sid = session.execute(text("SELECT id FROM data_sources WHERE name='OpenStreetMap / Overpass'")).scalar()
    lots = {}
    for cat, selecteur in categories.items():
        data = _overpass(_query(selecteur, bbox))
        if not isinstance(data.get("elements"), list) or data.get("remark"):
            raise ValueError(f"Réponse Overpass incomplète pour {commune} ({cat})")
        lots[cat] = list(_points(data, identifiants=True))
    params = {"commune": commune, "categories": list(categories)}
    session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:cle), :groupe)"),
                    {"cle": "amenites/" + commune, "groupe": int(affichage)})
    filtre = "kind='amenite' AND commune=:commune AND subtype=ANY(:categories)"
    session.execute(text(f"DELETE FROM spatial_layers WHERE {filtre}"), params)
    for cat, points in lots.items():
        for lon, lat, nom, identite in points:
            attrs = {"categorie": cat, "name": nom, **identite}
            if affichage:
                attrs["affichage_seul"] = True
            _insert_layer(session, "amenite", cat, nom, {"type": "Point", "coordinates": [lon, lat]},
                          sid, commune, None, attrs)
    if session.execute(text("SELECT to_regclass('tuyau_subdivise') IS NOT NULL")).scalar_one():
        session.execute(text(f"DELETE FROM tuyau_subdivise WHERE {filtre}"), params)
        session.execute(text(f"""INSERT INTO tuyau_subdivise(kind,subtype,name,commune,attrs,data_source_id,geom_2975)
            SELECT kind,subtype,name,commune,attrs,data_source_id,geom_2975 FROM spatial_layers
            WHERE {filtre}"""), params)
        if session.execute(text("SELECT to_regclass('mvt_meta') IS NOT NULL")).scalar_one():
            session.execute(text("""INSERT INTO mvt_meta(key,value,updated_at)
                VALUES('tuyau_rev',to_char(clock_timestamp(),'YYYYMMDDHH24MISSUS'),now())
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at"""))
    session.flush()
    return {cat: len(points) for cat, points in lots.items()}


def ingest_poi_commune(session: Session, commune: str,
                       bbox: tuple[float, float, float, float]) -> dict:
    """Remplace les quatre catégories de proximité d'une commune et les points correspondants de la carte."""
    counts = _remplacer_poi(session, commune, bbox, CATEGORIES, affichage=False)
    session.execute(text("UPDATE data_sources SET last_sync_at=now() WHERE name='OpenStreetMap / Overpass'"))
    return counts


def ingest_poi_affichage(session: Session, commune: str,
                         bbox: tuple[float, float, float, float]) -> dict:
    """Remplace les six catégories d’affichage d'une commune dans la source et sur la carte."""
    return _remplacer_poi(session, commune, bbox, CATEGORIES_AFFICHAGE, affichage=True)


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
