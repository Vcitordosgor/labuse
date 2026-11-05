"""ZONE-DONNÉES · LOT 5 — INGESTION du TRAFIC MOYEN JOURNALIER ANNUEL sur les ROUTES NATIONALES (974).

Notre substitut au flux piéton que vendent MyTraffic/Geoblink (et qu'ils ne couvrent pas à La Réunion).
Source : Région Réunion, Système d'Information Routier — open data ODS `trafic-mja-rn-lareunion`
(tronçons LineString WGS84, `route`/`annee`/`tmja` véhicules/jour). Table dédiée `trafic_rn`.

STRICTEMENT : trafic VÉHICULES sur ROUTES NATIONALES (pas de flux piéton, pas de réseau départemental/
communal). L'équivalent départemental/communal n'est pas ouvert (cf. compte-rendu) — on n'extrapole pas.
Idempotent : purge avant réinsertion. CLI `ingest-trafic-rn`.
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE_NAME = "Trafic RN (Région Réunion — SIR)"
EXPORT_URL = ("https://data.regionreunion.com/api/explore/v2.1/catalog/datasets/"
              "trafic-mja-rn-lareunion/exports/geojson")

DDL = """
CREATE TABLE IF NOT EXISTS trafic_rn (
  id     serial PRIMARY KEY,
  route  varchar(12),                 -- ex. N1, N2, N3
  annee  integer,                     -- millésime du comptage (fraîcheur amont)
  tmja   integer,                     -- trafic moyen journalier annuel (véhicules/jour)
  nb_pl  integer,                     -- poids lourds (NULL si non renseigné)
  geom   geometry(LineString, 4326),
  data_source_id integer
);
CREATE INDEX IF NOT EXISTS ix_trafic_rn_geom ON trafic_rn USING gist (geom);
"""


def ensure_tables(session: Session) -> None:
    from ..db import sql_statements
    for stmt in sql_statements(DDL):
        session.execute(text(stmt))
    session.flush()


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def build_trafic_rn(session: Session, *, url: str = EXPORT_URL, log=lambda *_: None) -> dict:
    """Télécharge l'export GeoJSON de la Région et ingère les tronçons de comptage RN.

    INJECTION-SOLIDE-2 — passe par `remplacer_servie` : le GeoJSON est chargé dans une STAGING,
    contrôlé (non vide, géométries valides, dans La Réunion, écart sous seuil) puis échangé
    ATOMIQUEMENT. Une livraison vide/à moitié/hors territoire est REFUSÉE et la version servie est
    conservée (`InjectionRefusee`). Plus de `DELETE FROM trafic_rn` à vif."""
    from . import injection_sure
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": SOURCE_NAME}).scalar()
    with httpx.Client(timeout=120.0, headers={"User-Agent": "labuse/zone-donnees"}) as c:
        r = c.get(url)
        r.raise_for_status()
        fc = r.json()
    feats = fc.get("features", [])
    annees: set[int] = set()

    def charger(conn, staging):
        for f in feats:
            geom = f.get("geometry")
            if not geom or geom.get("type") != "LineString":
                continue
            pr = f.get("properties", {})
            annee = _int(pr.get("annee"))
            if annee:
                annees.add(annee)
            conn.execute(text(
                f'INSERT INTO "{staging}" (route, annee, tmja, nb_pl, geom, data_source_id) VALUES '
                "(:rt, :an, :tm, :pl, ST_SetSRID(ST_GeomFromGeoJSON(:g),4326), :sid)"),
                {"rt": (pr.get("route") or None), "an": annee, "tm": _int(pr.get("tmja")),
                 "pl": _int(pr.get("nb_pl")), "g": json.dumps(geom), "sid": sid})

    res = injection_sure.remplacer_servie(
        session, table="trafic_rn", preparer=ensure_tables, charger_staging=charger,
        a_geometrie=True, geom_col="geom", couverture_974_min=0, delta_max_pct=60.0,
        alerter=injection_sure.alerte_injection("trafic_rn", SOURCE_NAME), log=log)
    n = res["mesures"]["comptes_apres"]
    mill = f"comptages {min(annees)}–{max(annees)}" if annees else "millésime non renseigné"
    session.execute(text(
        "UPDATE data_sources SET last_sync_at = now(), source_millesime = :m WHERE name = :n"),
        {"m": f"Trafic RN Région — {mill}", "n": SOURCE_NAME})
    session.flush()
    log(f"Trafic RN : {n} tronçons ingérés ({mill})")
    return {"n": n, "annees": sorted(annees)}
