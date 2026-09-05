"""CIRCUIT-3 lot 6.1 — INGESTION DES ARRÊTÉS CatNat (GASPAR / Géorisques).

Réparation d'une fuite : `catnat_n` (arrêtés de catastrophe naturelle par commune, fiche commune)
était FAUX — l'ancienne ingestion lisait UNE page (`connector.catnat`, page_size par défaut) et
tronquait à ~10 arrêtés par commune ; la commande d'ingestion avait ensuite été retirée (spin-off
« Vues » M12). On réingère ici via `connector.catnat_arretes` (paginé) → tous les arrêtés.

Idempotent : upsert sur (insee, type_peril, date_arrete, date_debut). `raw` garde l'objet GASPAR.
"""
from __future__ import annotations

import json as _json
import logging
from datetime import date, datetime

from sqlalchemy import text

from .run_all import REUNION_COMMUNES

log = logging.getLogger("labuse.ingestion.catnat")

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
    """GASPAR livre du JJ/MM/AAAA ; on tolère l'ISO."""
    if not v:
        return None
    s = str(v).strip()
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def ingest_catnat(session, *, connector=None, insee_list: list[str] | None = None,
                  remplacer: bool = False) -> dict:
    """Réingère les arrêtés CatNat des 24 communes (paginé — plus de troncature à 10).

    `remplacer=True` vide la table d'abord (pour solder proprement une version tronquée)."""
    if connector is None:
        from ..connectors.georisques import GeorisquesConnector
        connector = GeorisquesConnector()
    by_insee = dict(REUNION_COMMUNES)
    targets = insee_list or [i for i, _ in REUNION_COMMUNES]
    if remplacer:
        session.execute(text("DELETE FROM catnat_arretes"))
    total, communes_ok, erreurs, par_commune = 0, 0, {}, {}
    for insee in targets:
        try:
            items = list(connector.catnat_arretes(insee))
        except Exception as exc:  # noqa: BLE001 — une commune en panne n'arrête pas le lot
            erreurs[insee] = f"{type(exc).__name__}: {exc}"
            continue
        n_commune = 0
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
            n_commune += 1
        par_commune[insee] = n_commune
        communes_ok += 1
    session.flush()
    return {"communes_ok": communes_ok, "arretes": total, "erreurs": erreurs,
            "par_commune": par_commune}
