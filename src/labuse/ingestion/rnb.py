"""REPARATIONS-1 lot 4 — RNB, L'IDENTITÉ DES BÂTIMENTS (Référentiel National des Bâtiments).

API OFFICIELLE `rnb-api.beta.gouv.fr` (Licence Ouverte 2.0 — beta.gouv/ADEME/IGN), jamais de
scraping. Filtrage 974 AU PLUS TÔT : le paramètre `insee_code` de l'API (une passe par commune,
24 codes du référentiel). CRS INSPECTÉ, pas supposé : l'API sert du GeoJSON WGS84 et le flux
diff écrit `SRID=4326` explicitement (constaté sur la réponse du 13/09/2026) → stocké en 4326,
+ `shape_2975` transformée (UTM 40S) pour le rattachement métrique.

CE QU'ON PREND : `rnb_id`, statut, actif, géométries (point + emprise), adresses BAN liées,
`ext_ids` BD TOPO/BDNB (traçabilité). RIEN d'énergétique (le DPE reste à l'ADEME), rien que
BD TOPO ou le LiDAR servent déjà (hauteurs, usages).

CE QU'IL REND (`rattacher()`) : chaque bâtiment BD TOPO servi (spatial_layers kind='batiment')
et chaque hauteur LiDAR (batiment_hauteur_lidar, à la parcelle) rattachés à un RNB ID — taux
mesurés, non-rattachés PAR CAUSE (aucun RNB intersectant / recouvrement insuffisant). C'est la
pièce qui manquait pour que trois sources parlent du même bâtiment.

SENTINELLE : `GET /buildings/diff/?since=<date>` (flux CSV national des changements) — la
version amont bouge à chaque changement ; l'incrémental filtrera le 974 par géométrie.
"""
from __future__ import annotations

import logging
import time as _time

import httpx
from sqlalchemy import text

log = logging.getLogger("labuse.ingestion.rnb")

API = "https://rnb-api.beta.gouv.fr/api/alpha/buildings/"
DIFF = "https://rnb-api.beta.gouv.fr/api/alpha/buildings/diff/"
FICHE_PUBLIQUE = "https://rnb.beta.gouv.fr/batiments/{rnb_id}"

DDL = """
CREATE TABLE IF NOT EXISTS rnb_batiments (
  rnb_id varchar(16) PRIMARY KEY,
  statut varchar(32),
  is_active boolean,
  insee varchar(5) NOT NULL,
  point geometry(Point, 4326),
  shape geometry(Geometry, 4326),
  shape_2975 geometry(Geometry, 2975),
  ext_bdtopo text[],
  adresses jsonb,
  ingere_le timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_rnb_batiments_insee ON rnb_batiments (insee);
CREATE INDEX IF NOT EXISTS ix_rnb_batiments_shape_2975 ON rnb_batiments USING gist (shape_2975);
CREATE TABLE IF NOT EXISTS rnb_rattachement_bdtopo (
  layer_id bigint PRIMARY KEY,
  rnb_id varchar(16),
  recouvrement_pct real,
  cause varchar(40),               -- NULL si rattaché · aucun_rnb_intersectant · recouvrement_insuffisant
  calcule_le timestamptz NOT NULL DEFAULT now()
)
"""


def ensure_tables(engine_or_session) -> None:
    from ..db import sql_statements
    ex = engine_or_session.execute if hasattr(engine_or_session, "execute") else None
    if ex is None:
        with engine_or_session.begin() as c:
            for stmt in sql_statements(DDL):
                c.execute(text(stmt))
    else:
        for stmt in sql_statements(DDL):
            ex(text(stmt))


def _page(client: httpx.Client, url: str, params: dict | None) -> dict:
    for attente in (0, 2, 8):        # 3 essais — l'API publique peut souffler
        if attente:
            _time.sleep(attente)
        try:
            r = client.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            log.warning("RNB %s → %s", url, r.status_code)
        except httpx.HTTPError as exc:  # noqa: PERF203
            log.warning("RNB %s → %s", url, type(exc).__name__)
    raise RuntimeError(f"RNB injoignable après 3 essais : {url}")


def ingest_rnb(session, *, insee_list: list[str] | None = None, limit: int = 100,
               log_fn=print) -> dict:
    """Ingestion par commune (filtrage 974 côté API — au plus tôt), paginée par curseur,
    idempotente (upsert rnb_id). Reprend une commune interrompue en la rejouant entière."""
    ensure_tables(session)
    if insee_list is None:
        insee_list = [i for (i,) in session.execute(text(
            "SELECT insee FROM communes_referentiel ORDER BY insee")).all()]
    total, par_commune = 0, {}
    with httpx.Client(headers={"User-Agent": "labuse (kampusreunion@gmail.com)"}) as client:
        for insee in insee_list:
            n, url, params = 0, API, {"insee_code": insee, "limit": limit}
            while url:
                d = _page(client, url, params)
                params = None            # le curseur `next` porte déjà tout
                rows = d.get("results") or []
                for b in rows:
                    ext = [x["id"] for x in (b.get("ext_ids") or []) if x.get("source") == "bdtopo"]
                    session.execute(text(
                        "INSERT INTO rnb_batiments (rnb_id, statut, is_active, insee, point, shape,"
                        " shape_2975, ext_bdtopo, adresses) VALUES (:r, :s, :a, :i,"
                        " ST_SetSRID(ST_GeomFromGeoJSON(:pt), 4326),"
                        " ST_SetSRID(ST_GeomFromGeoJSON(:sh), 4326),"
                        " ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:sh), 4326), 2975),"
                        " :ext, CAST(:ad AS jsonb)) "
                        "ON CONFLICT (rnb_id) DO UPDATE SET statut = EXCLUDED.statut,"
                        " is_active = EXCLUDED.is_active, insee = EXCLUDED.insee,"
                        " point = EXCLUDED.point, shape = EXCLUDED.shape,"
                        " shape_2975 = EXCLUDED.shape_2975, ext_bdtopo = EXCLUDED.ext_bdtopo,"
                        " adresses = EXCLUDED.adresses, ingere_le = now()"),
                        {"r": b["rnb_id"], "s": b.get("status"), "a": b.get("is_active"),
                         "i": insee,
                         "pt": _json_dumps(b.get("point")), "sh": _json_dumps(b.get("shape")),
                         "ext": ext or None, "ad": _json_dumps(b.get("addresses") or [])})
                    n += 1
                session.commit()
                url = d.get("next")
            par_commune[insee] = n
            total += n
            log_fn(f"  {insee}: {n} bâtiments RNB")
    return {"total": total, "par_commune": par_commune}


def _json_dumps(o) -> str | None:
    import json
    return json.dumps(o) if o is not None else None


def rattacher(session, *, seuil_pct: float = 30.0, log_fn=print) -> dict:
    """LE RATTACHEMENT — spatial (recouvrement d'emprises en 2975), car nos bâtiments BD TOPO
    locaux ne portent pas leur cleabs (l'`ext_id` RNB reste stocké pour une passe exacte future).

    · BD TOPO : pour chaque spatial_layers kind='batiment', le RNB actif au meilleur
      recouvrement ; rattaché si recouvrement ≥ `seuil_pct` % de l'emprise du bâtiment,
      sinon cause `recouvrement_insuffisant` ; aucun candidat → `aucun_rnb_intersectant`.
    · LiDAR : batiment_hauteur_lidar (une ligne par PARCELLE — faîtage/égout du bâti principal)
      → le RNB du bâtiment principal de la parcelle (plus grande emprise RNB ∩ parcelle).
    Idempotent : tout est recalculé (DELETE + INSERT / UPDATE en masse)."""
    ensure_tables(session)
    session.execute(text("DELETE FROM rnb_rattachement_bdtopo"))
    session.execute(text("""
        INSERT INTO rnb_rattachement_bdtopo (layer_id, rnb_id, recouvrement_pct, cause)
        SELECT b.id,
               CASE WHEN m.pct >= :seuil THEN m.rnb_id END,
               m.pct,
               CASE WHEN m.rnb_id IS NULL THEN 'aucun_rnb_intersectant'
                    WHEN m.pct < :seuil THEN 'recouvrement_insuffisant' END
        FROM spatial_layers b
        LEFT JOIN LATERAL (
            SELECT r.rnb_id,
                   (100.0 * ST_Area(ST_Intersection(r.shape_2975, b.geom_2975))
                    / NULLIF(ST_Area(b.geom_2975), 0))::real AS pct
            FROM rnb_batiments r
            WHERE r.is_active AND r.shape_2975 && b.geom_2975
              AND ST_Intersects(r.shape_2975, b.geom_2975)
            ORDER BY ST_Area(ST_Intersection(r.shape_2975, b.geom_2975)) DESC
            LIMIT 1) m ON true
        WHERE b.kind = 'batiment' AND b.geom_2975 IS NOT NULL"""),
        {"seuil": seuil_pct})
    session.commit()
    if not session.execute(text("SELECT to_regclass('batiment_hauteur_lidar')")).scalar():
        session.commit()          # base sans LiDAR (test, base partielle) : le volet LiDAR est sauté
        return mesurer(session, log_fn=log_fn)
    session.execute(text(
        "ALTER TABLE batiment_hauteur_lidar ADD COLUMN IF NOT EXISTS rnb_id varchar(16)"))
    session.execute(text(
        "ALTER TABLE batiment_hauteur_lidar ADD COLUMN IF NOT EXISTS rnb_cause varchar(40)"))
    session.execute(text("""
        UPDATE batiment_hauteur_lidar h SET
          rnb_id = m.rnb_id,
          rnb_cause = CASE WHEN m.rnb_id IS NULL THEN 'aucun_bati_rnb_sur_parcelle' END
        FROM parcels p
        LEFT JOIN LATERAL (
            SELECT r.rnb_id FROM rnb_batiments r
            WHERE r.is_active AND r.shape_2975 && p.geom_2975
              AND ST_Intersects(r.shape_2975, p.geom_2975)
            ORDER BY ST_Area(ST_Intersection(r.shape_2975, p.geom_2975)) DESC
            LIMIT 1) m ON true
        WHERE p.idu = h.idu"""))
    session.commit()
    return mesurer(session, log_fn=log_fn)


def mesurer(session, log_fn=print) -> dict:
    """Les taux de rattachement MESURÉS + les non-rattachés par cause (jamais un taux nu)."""
    bd = {r["cause"] or "rattache": r["n"] for r in session.execute(text(
        "SELECT cause, count(*) AS n FROM rnb_rattachement_bdtopo GROUP BY cause")).mappings()}
    li: dict[str, int] = {}
    if session.execute(text("SELECT to_regclass('batiment_hauteur_lidar')")).scalar() and \
            session.execute(text(
                "SELECT 1 FROM information_schema.columns WHERE table_name='batiment_hauteur_lidar' "
                "AND column_name='rnb_id'")).first():
        li = {r["cause"] or "rattache": r["n"] for r in session.execute(text(
            "SELECT rnb_cause AS cause, count(*) AS n FROM batiment_hauteur_lidar GROUP BY rnb_cause")).mappings()}
    n_rnb = session.execute(text("SELECT count(*) FROM rnb_batiments")).scalar() or 0
    tot_bd = sum(bd.values()) or 1
    tot_li = sum(li.values()) or 1
    res = {
        "rnb_batiments": n_rnb,
        "bdtopo": {"total": sum(bd.values()), "rattaches": bd.get("rattache", 0),
                   "taux_pct": round(100.0 * bd.get("rattache", 0) / tot_bd, 1),
                   "par_cause": {k: v for k, v in bd.items() if k != "rattache"}},
        "lidar": {"total": sum(li.values()), "rattaches": li.get("rattache", 0),
                  "taux_pct": round(100.0 * li.get("rattache", 0) / tot_li, 1),
                  "par_cause": {k: v for k, v in li.items() if k != "rattache"}},
    }
    log_fn(f"RNB : {n_rnb} bâtiments · BD TOPO {res['bdtopo']['taux_pct']} % rattachés "
           f"({res['bdtopo']['par_cause']}) · LiDAR {res['lidar']['taux_pct']} % "
           f"({res['lidar']['par_cause']})")
    return res


def version_diff(since: str) -> dict:
    """SENTINELLE — le flux de changements officiel : nombre de lignes publiées depuis `since`
    (CSV national ; la présence de mouvement = nouvelle version amont)."""
    with httpx.Client() as client:
        r = client.get(DIFF, params={"since": since}, timeout=120)
        r.raise_for_status()
        lignes = r.text.count("\n")
    return {"since": since, "changements": max(0, lignes - 1)}
