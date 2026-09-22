"""Journal minimal des deltas d'ingestion (SCORING-6 lot F).

Pièce manquante identifiée par SCORING-5-RAPPORT §8.3 : pour recalculer la cascade / le Score EN
DELTA plutôt qu'en entier, il faut savoir QUEL objet a changé QUAND. Ce journal enregistre, à
chaque ingestion, la source, la date, et les parcelles touchées — de quoi préparer un recalcul
ciblé (jointure spatiale par kind/bbox reste au consommateur ; ici on trace le fait brut).

Table `ingestion_delta` (append-only). Aucune écriture dans une table de service.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import text


def ensure_schema(conn) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ingestion_delta (
          id bigserial PRIMARY KEY,
          source text NOT NULL,               -- kind de couche / nom de source ingérée
          survenu_le timestamptz NOT NULL DEFAULT now(),
          n_parcelles integer NOT NULL DEFAULT 0,
          parcel_ids jsonb,                   -- échantillon/liste des parcelles touchées (nullable si volumineux)
          note text)"""))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ingestion_delta_source_date "
                      "ON ingestion_delta (source, survenu_le)"))


@dataclass
class Delta:
    source: str
    survenu_le: str
    n_parcelles: int
    note: str | None


def record_delta(conn, source: str, parcel_ids: list[int] | None = None, *,
                 note: str | None = None, echantillon_max: int = 5000) -> int:
    """Enregistre un delta d'ingestion. `parcel_ids` = parcelles touchées (stockées jusqu'à
    `echantillon_max` ; au-delà seul le compte est gardé). Renvoie n_parcelles."""
    ids = list(parcel_ids or [])
    n = len(ids)
    stored = ids if n <= echantillon_max else None
    conn.execute(text("""
        INSERT INTO ingestion_delta (source, n_parcelles, parcel_ids, note)
        VALUES (:s, :n, :p, :note)"""),
        {"s": source, "n": n,
         "p": json.dumps(stored) if stored is not None else None, "note": note})
    return n


def deltas_depuis(conn, depuis=None, source: str | None = None) -> list[Delta]:
    """Liste des deltas (source, date, n) depuis une date, éventuellement filtrés par source —
    l'entrée d'un recalcul ciblé (le consommateur fait la jointure spatiale)."""
    q = "SELECT source, survenu_le, n_parcelles, note FROM ingestion_delta WHERE TRUE"
    params: dict = {}
    if depuis is not None:
        q += " AND survenu_le >= :d"; params["d"] = depuis
    if source is not None:
        q += " AND source = :s"; params["s"] = source
    q += " ORDER BY survenu_le DESC"
    return [Delta(r.source, str(r.survenu_le), int(r.n_parcelles), r.note)
            for r in conn.execute(text(q), params)]


def parcelles_a_recalculer(conn, depuis) -> list[int]:
    """Union des parcelles touchées depuis `depuis` (celles dont `parcel_ids` est stocké) —
    la liste d'entrée d'un recalcul Score/cascade en delta."""
    rows = conn.execute(text(
        "SELECT parcel_ids FROM ingestion_delta WHERE survenu_le >= :d AND parcel_ids IS NOT NULL"),
        {"d": depuis})
    out: set[int] = set()
    for (pids,) in rows:
        if pids:
            out.update(int(x) for x in pids)
    return sorted(out)
