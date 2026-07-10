"""Signal CATNAT (Lot 3) — arrêtés de catastrophe naturelle GASPAR (Géorisques).

Constat d'inventaire : la wave Géorisques existante ingère les ZONAGES (PPR, aléas,
cavités, ICPE… → spatial_layers) mais PAS les arrêtés CATNAT — aucune ligne
kind='catnat' en base. On les ingère donc ICI, via l'endpoint /gaspar/catnat déjà
présent dans le connecteur (`GeorisquesConnector.catnat`), filtré 974 (les 24
communes du référentiel). Refresh : job mensuel (deploy/cron.d/catnat).

Effet produit : les presets `boost_catnat` (couvreurs, étanchéité, menuiseries)
affichent le bandeau « communes récemment en état de catastrophe naturelle : X, Y »
et proposent le filtre `catnat_recent` pré-coché. Fenêtre/périls : config/segments.yaml.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import text

from .. import config
from ..ingestion.run_all import REUNION_COMMUNES

log = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS catnat_arretes (
  id serial PRIMARY KEY,
  insee varchar(5) NOT NULL,
  commune varchar(80),
  type_peril text,
  date_arrete date,
  date_debut date,
  date_fin date,
  raw jsonb,
  ingested_at timestamptz DEFAULT now(),
  UNIQUE (insee, type_peril, date_arrete, date_debut)
);
CREATE INDEX IF NOT EXISTS ix_catnat_commune_date ON catnat_arretes (commune, date_arrete)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


def _parse_date(v) -> date | None:
    """GASPAR livre du JJ/MM/AAAA (vérifié live 2026-07) ; on tolère aussi l'ISO."""
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%d/%m/%Y",):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def ingest_catnat(session, *, connector=None, insee_list: list[str] | None = None) -> dict:
    """Ingestion idempotente (upsert sur (insee, type_peril, date_arrete, date_debut)).

    Champs GASPAR : libelle_risque_jo (péril), date_publication_arrete (l'arrêté),
    date_debut_evt / date_fin_evt (l'événement). `raw` conserve l'objet complet.
    """
    import json as _json

    if connector is None:
        from ..connectors.georisques import GeorisquesConnector
        connector = GeorisquesConnector()
    by_insee = dict(REUNION_COMMUNES)
    targets = insee_list or [i for i, _ in REUNION_COMMUNES]
    total, communes_ok, erreurs = 0, 0, {}
    for insee in targets:
        try:
            data = connector.catnat(insee)
        except Exception as exc:  # noqa: BLE001 — une commune en panne n'arrête pas le lot
            erreurs[insee] = f"{type(exc).__name__}: {exc}"
            continue
        items = (data or {}).get("data") or []
        for it in items:
            session.execute(text("""
                INSERT INTO catnat_arretes (insee, commune, type_peril, date_arrete,
                                            date_debut, date_fin, raw)
                VALUES (:insee, :commune, :peril, :arrete, :debut, :fin, CAST(:raw AS jsonb))
                ON CONFLICT (insee, type_peril, date_arrete, date_debut) DO UPDATE SET
                  date_fin = EXCLUDED.date_fin, raw = EXCLUDED.raw"""), {
                "insee": insee,
                "commune": by_insee.get(insee) or it.get("libelle_commune"),
                "peril": it.get("libelle_risque_jo"),
                "arrete": _parse_date(it.get("date_publication_arrete")),
                "debut": _parse_date(it.get("date_debut_evt")),
                "fin": _parse_date(it.get("date_fin_evt")),
                "raw": _json.dumps(it, ensure_ascii=False),
            })
            total += 1
        communes_ok += 1
    session.flush()
    return {"communes_ok": communes_ok, "arretes": total, "erreurs": erreurs}


def catnat_config() -> dict:
    try:
        cfg = (config.load_yaml_config("segments") or {}).get("catnat", {})
    except FileNotFoundError:
        cfg = {}
    return {"fenetre_mois": int(cfg.get("fenetre_mois", 6)),
            "perils": cfg.get("perils") or ["vent", "cyclon", "inondation"]}


def communes_recentes(session) -> dict:
    """Bandeau des presets boost_catnat : communes sous arrêté CATNAT récent
    (fenêtre + périls de config/segments.yaml)."""
    cfg = catnat_config()
    try:
        rows = session.execute(text("""
            SELECT DISTINCT commune, max(date_arrete) AS dernier_arrete,
                   string_agg(DISTINCT type_peril, ' · ') AS perils
            FROM catnat_arretes
            WHERE date_arrete >= (CURRENT_DATE - make_interval(months => :m))
              AND type_peril ILIKE ANY(:p)
            GROUP BY commune ORDER BY commune"""),
            {"m": cfg["fenetre_mois"], "p": [f"%{x}%" for x in cfg["perils"]]}).mappings().all()
    except Exception:  # noqa: BLE001 — table absente (base partielle) → signal éteint, jamais d'erreur
        session.rollback()
        rows = []
    return {"fenetre_mois": cfg["fenetre_mois"],
            "communes": [{"commune": r["commune"],
                          "dernier_arrete": r["dernier_arrete"].isoformat()
                          if r["dernier_arrete"] else None,
                          "perils": r["perils"]} for r in rows]}
