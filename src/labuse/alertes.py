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

#: M104 — dedup event_log d'une alerte de secteur : UN producteur, UN registre, des consommateurs.
_DEDUP = "secteur:{kind}:{zone_id}:{ref}"


def _ensure_secteur_schema(session: Session) -> None:
    """Index d'unicité des nouveaux kinds + table d'empreinte zonage (photo par zone).
    Idempotent — appelé au point de détection, jamais ailleurs."""
    session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_alertes_zone_kind_ref ON alertes (zone_id, kind, source_ref) "
        "WHERE kind IN ('permis_in_zone', 'bodacc_in_zone', 'zonage_in_zone')"))
    session.execute(text(
        "CREATE TABLE IF NOT EXISTS watch_zone_zonage_snap ("
        "  zone_id int NOT NULL, idu varchar(14) NOT NULL, zone_lib text,"
        "  PRIMARY KEY (zone_id, idu))"))
    # le REGISTRE doit exister avant de notifier (bases de test / fraîches) — DDL idempotente,
    # dans LA MÊME transaction que la détection (jamais un engine.begin() parallèle).
    from .api import events as _events
    for stmt in _events.DDL.split(";"):
        if stmt.strip():
            session.execute(text(stmt))
    _events._ensure_cols(session)


def _notifier_secteur(session: Session, rows, zones: dict[int, dict]) -> int:
    """M104 — RACCORDEMENT au registre : chaque NOUVELLE alerte de secteur devient une
    notification event_log (kind `veille_zone` — préférences par type/canal M85 déjà en place).

    RATTRAPAGE DIT (arbitrage) : on REPART DU PRÉSENT — seuls les faits datés d'APRÈS la
    création de la zone notifient. L'historique (dont les 5 776 alertes antérieures au
    raccordement, et le stock rétrospectif qu'une zone neuve détecte à sa création) reste
    visible dans le panneau Surveillance mais n'inonde JAMAIS la cloche ni le digest.
    Nuance assumée : un fait ancien ingéré tardivement (DVF ~6 mois) ne notifie pas non plus."""
    from .api.events import creer_notification
    n = 0
    for r in rows:
        z = zones.get(r["zone_id"]) or {}
        fait = r["payload"].get("fait_date") if r.get("payload") else None
        cree = z.get("created_at")
        if fait is not None and cree is not None and str(fait) < str(cree.date()):
            continue   # fait antérieur à la zone → panneau seulement, pas de notification
        n += 1 if creer_notification(
            session, kind="veille_zone", compte_id=r["compte_id"],
            source=f"Secteur · {z.get('name', '?')}", titre=r["label"],
            detail=(r["payload"] or {}).get("detail") or r["label"],
            lien="/socle/#surveillance=secteurs",
            dedup=_DEDUP.format(kind=r["kind"], zone_id=r["zone_id"], ref=r["source_ref"])) else 0
    return n


def compute_alertes(session: Session, commune: str, cid: int | None) -> dict[str, int]:
    """Détecte les nouveautés du scope DU COMPTE `cid`. Renvoie le nb de NOUVELLES alertes par
    type (les faits déjà vus sont ignorés par les index uniques).

    Cloison M-K (P1-9) : ne croise QUE les zones de veille du compte `cid` ; l'alerte hérite du
    compte propriétaire (z.compte_id = :cid) — jamais la zone d'un compte n'alimente un autre.

    M104 (arbitrage 17/08/2026) : QUATRE faits détectés par secteur — vente DVF (historique),
    permis déposé, procédure BODACC (propriétaire d'une parcelle du secteur), changement de
    zonage (diff d'empreinte, photo silencieuse à la première rencontre). Chaque NOUVELLE
    alerte est raccordée à event_log (`_notifier_secteur`) — fini le tuyau parallèle qui
    n'atteignait ni la cloche ni le digest (double tuyau démasqué à l'audit M104)."""
    _ensure_secteur_schema(session)
    zrows = session.execute(text(
        "SELECT id, name, created_at FROM watch_zones "
        "WHERE commune = :c AND compte_id IS NOT DISTINCT FROM :cid"),
        {"c": commune, "cid": cid}).mappings().all()
    zones = {r["id"]: dict(r) for r in zrows}
    out = {"dvf_in_zone": 0, "permis_in_zone": 0, "bodacc_in_zone": 0,
           "zonage_in_zone": 0, "notifications": 0, "total": 0}
    if not zones:
        return out
    ret = "RETURNING id, kind, zone_id, compte_id, source_ref, label, payload"

    # 1 · VENTES DVF dans le secteur (kind historique, index uq_alertes_zone_dvf inchangé)
    dvf = session.execute(
        text(f"""INSERT INTO alertes (kind, zone_id, compte_id, source_ref, label, payload, detected_at)
                SELECT 'dvf_in_zone', z.id, z.compte_id, d.id::text,
                       'Vente DVF dans « ' || z.name || ' »',
                       jsonb_build_object('date', d.date_mutation, 'fait_date', d.date_mutation,
                                          'valeur_fonciere', d.valeur_fonciere,
                                          'nature', d.nature_mutation, 'type_local', d.type_local,
                                          'surface_terrain', d.surface_terrain, 'zone', z.name,
                                          'detail', 'Mutation du ' || d.date_mutation ||
                                                    coalesce(' — ' || round(d.valeur_fonciere)::text || ' €', '')),
                       now()
                FROM watch_zones z
                JOIN dvf_mutations d ON d.geom IS NOT NULL AND ST_Contains(z.geom, d.geom)
                WHERE z.commune = :c AND z.compte_id IS NOT DISTINCT FROM :cid
                ON CONFLICT DO NOTHING
                {ret}"""),
        {"c": commune, "cid": cid}).mappings().all()

    # 2 · PERMIS déposés dans le secteur (géocodage SITADEL direct — symétrique du suivi parcelle)
    permis = session.execute(
        text(f"""INSERT INTO alertes (kind, zone_id, compte_id, source_ref, label, payload, detected_at)
                SELECT 'permis_in_zone', z.id, z.compte_id, sp.permit_id,
                       'Permis déposé dans « ' || z.name || ' »',
                       jsonb_build_object('fait_date', sp.date_depot, 'type', sp.type, 'zone', z.name,
                                          'detail', coalesce(sp.type, 'Permis') || ' ' || sp.permit_id ||
                                                    ' déposé le ' || sp.date_depot),
                       now()
                FROM watch_zones z
                JOIN sitadel_permits sp ON sp.geom IS NOT NULL AND ST_Contains(z.geom, sp.geom)
                WHERE z.commune = :c AND z.compte_id IS NOT DISTINCT FROM :cid
                  AND sp.permit_id IS NOT NULL AND sp.date_depot IS NOT NULL
                ON CONFLICT DO NOTHING
                {ret}"""),
        {"c": commune, "cid": cid}).mappings().all()

    # 3 · PROCÉDURES BODACC sur le propriétaire (personne morale) d'une parcelle du secteur
    bodacc = session.execute(
        text(f"""INSERT INTO alertes (kind, zone_id, compte_id, source_ref, label, payload, detected_at)
                SELECT DISTINCT ON (z.id, bp.annonce_id)
                       'bodacc_in_zone', z.id, z.compte_id, bp.annonce_id::text,
                       'Procédure BODACC dans « ' || z.name || ' »',
                       jsonb_build_object('fait_date', bp.date_annonce, 'zone', z.name,
                                          'detail', bp.type_procedure || ' publiée le ' || bp.date_annonce ||
                                                    ' — ' || coalesce(pm.denomination, 'propriétaire') ||
                                                    ' (parcelle ' || pm.idu || ')'),
                       now()
                FROM watch_zones z
                JOIN parcels p ON ST_Intersects(z.geom, p.geom)
                JOIN parcelle_personne_morale pm ON pm.idu = p.idu AND pm.siren IS NOT NULL
                JOIN bodacc_procedures bp ON bp.siren = pm.siren
                WHERE z.commune = :c AND z.compte_id IS NOT DISTINCT FROM :cid
                ON CONFLICT DO NOTHING
                {ret}"""),
        {"c": commune, "cid": cid}).mappings().all()

    # 4 · CHANGEMENT DE ZONAGE — diff d'empreinte par zone. Première rencontre d'une zone :
    # PHOTO silencieuse (repartir du présent) ; ensuite, tout écart devient une alerte.
    session.execute(text(
        """INSERT INTO watch_zone_zonage_snap (zone_id, idu, zone_lib)
           SELECT z.id, p.idu, pz.zone_lib
           FROM watch_zones z
           JOIN parcels p ON ST_Intersects(z.geom, p.geom)
           JOIN parcel_zone_plu pz ON pz.idu = p.idu
           WHERE z.commune = :c AND z.compte_id IS NOT DISTINCT FROM :cid
             AND NOT EXISTS (SELECT 1 FROM watch_zone_zonage_snap s WHERE s.zone_id = z.id)
           ON CONFLICT DO NOTHING"""), {"c": commune, "cid": cid})
    zonage = session.execute(
        text(f"""INSERT INTO alertes (kind, zone_id, compte_id, source_ref, label, payload, detected_at)
                SELECT 'zonage_in_zone', s.zone_id, z.compte_id,
                       s.idu || ':' || coalesce(pz.zone_lib, '∅'),
                       'Changement de zonage dans « ' || z.name || ' »',
                       jsonb_build_object('zone', z.name,
                                          'detail', 'Parcelle ' || s.idu || ' : zonage passé de « ' ||
                                                    coalesce(s.zone_lib, '∅') || ' » à « ' ||
                                                    coalesce(pz.zone_lib, '∅') || ' ».'),
                       now()
                FROM watch_zone_zonage_snap s
                JOIN watch_zones z ON z.id = s.zone_id
                LEFT JOIN parcel_zone_plu pz ON pz.idu = s.idu
                WHERE z.commune = :c AND z.compte_id IS NOT DISTINCT FROM :cid
                  AND pz.zone_lib IS DISTINCT FROM s.zone_lib
                ON CONFLICT DO NOTHING
                {ret}"""),
        {"c": commune, "cid": cid}).mappings().all()
    if zonage:
        session.execute(text(
            """UPDATE watch_zone_zonage_snap s SET zone_lib = pz.zone_lib
               FROM parcel_zone_plu pz, watch_zones z
               WHERE pz.idu = s.idu AND z.id = s.zone_id
                 AND z.commune = :c AND z.compte_id IS NOT DISTINCT FROM :cid"""),
            {"c": commune, "cid": cid})

    out["dvf_in_zone"], out["permis_in_zone"] = len(dvf), len(permis)
    out["bodacc_in_zone"], out["zonage_in_zone"] = len(bodacc), len(zonage)
    out["notifications"] = _notifier_secteur(session, [*dvf, *permis, *bodacc, *zonage], zones)
    out["total"] = len(dvf) + len(permis) + len(bodacc) + len(zonage)

    session.execute(
        text("UPDATE watch_zones SET last_run_at = now() "
             "WHERE commune = :c AND compte_id IS NOT DISTINCT FROM :cid"),
        {"c": commune, "cid": cid})
    session.flush()
    return out


def evaluer_tous_secteurs(session: Session) -> dict[str, int]:
    """M104 — le job CRONABLE (après ingestion, comme evaluer_suivis/evaluer_toutes) : évalue
    les secteurs de TOUS les comptes. Un producteur, un registre, des consommateurs."""
    couples = session.execute(text(
        "SELECT DISTINCT commune, compte_id FROM watch_zones")).all()
    agg = {"scopes": 0, "alertes": 0, "notifications": 0}
    for commune, cid in couples:
        r = compute_alertes(session, commune, cid)
        agg["scopes"] += 1
        agg["alertes"] += r["total"]
        agg["notifications"] += r["notifications"]
    return agg


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
