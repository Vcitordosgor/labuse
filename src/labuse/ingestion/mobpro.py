"""ÉTUDE DE ZONE · Z1 — INGESTION MOBPRO (mobilités professionnelles domicile-travail, INSEE) →
table `mobpro_commune`, maille COMMUNE du 974.

Sert le « N actifs y travaillent » de l'Étude de zone : le nombre d'emplois AU LIEU DE TRAVAIL dans
la commune (agrégat des flux domicile-travail dont la destination est la commune). Fait sourcé et daté,
jamais une prévision. Maille commune (le fichier MOBPRO est à la commune).

Source : INSEE — fichier détail MOBPRO (mobilités professionnelles, RP), Licence Ouverte. CLI rejouable
avec --file. Idempotent : purge avant réinsertion. On agrège par commune de LIEU DE TRAVAIL (DCLT),
pondéré par IPONDI ; on filtre le 974 (INSEE commençant par 974).
"""
from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE_NAME = "MOBPRO (mobilités domicile-travail, INSEE)"

DDL = """
CREATE TABLE IF NOT EXISTS mobpro_commune (
  insee                 varchar(5) PRIMARY KEY,
  commune               varchar(60),
  emplois_lieu_travail  integer,          -- actifs qui TRAVAILLENT dans la commune (agrégat MOBPRO)
  millesime             varchar(16),
  data_source_id        integer,
  ingested_at           timestamptz NOT NULL DEFAULT now()
);
"""


def ensure_tables(session: Session) -> None:
    session.execute(text(DDL))
    session.flush()


def _col(row: dict, *names: str) -> str | None:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def build_mobpro(session: Session, *, file: str, millesime: str = "MOBPRO INSEE",
                 log=lambda *_: None) -> dict:
    """Agrège les flux MOBPRO par commune de LIEU DE TRAVAIL (974), pondéré IPONDI. `file` = CSV INSEE."""
    path = Path(file)
    if not path.exists():
        raise FileNotFoundError(f"fichier MOBPRO introuvable : {path}")
    ensure_tables(session)
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": SOURCE_NAME}).scalar()
    insee2nom = {i: n for i, n in session.execute(text("SELECT insee, commune FROM commune_conso_enaf")).all()}

    emplois: dict[str, float] = {}
    with path.open(encoding="utf-8", errors="replace", newline="") as fh:
        # le fichier INSEE MOBPRO est en « ; »
        sample = fh.read(4096); fh.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        reader = csv.DictReader(fh, delimiter=delim)
        for row in reader:
            dclt = _col(row, "DCLT", "COMMUNE_LIEU_TRAVAIL", "dclt")   # commune de LIEU DE TRAVAIL
            if not dclt or not str(dclt).startswith("974"):
                continue
            try:
                pond = float(_col(row, "IPONDI", "ipondi") or 1)
            except ValueError:
                pond = 1.0
            emplois[dclt] = emplois.get(dclt, 0.0) + pond

    session.execute(text("DELETE FROM mobpro_commune"))
    for insee, n in emplois.items():
        session.execute(text(
            "INSERT INTO mobpro_commune (insee, commune, emplois_lieu_travail, millesime, data_source_id) "
            "VALUES (:i, :c, :e, :m, :s) ON CONFLICT (insee) DO UPDATE SET "
            "emplois_lieu_travail = EXCLUDED.emplois_lieu_travail, millesime = EXCLUDED.millesime"),
            {"i": insee, "c": insee2nom.get(insee), "e": round(n), "m": millesime, "s": sid})
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})
    session.flush()
    log(f"MOBPRO 974 : {len(emplois)} communes (emplois au lieu de travail)")
    return {"n_communes": len(emplois)}
