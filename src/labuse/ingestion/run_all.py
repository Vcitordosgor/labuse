"""Ingestion + évaluation MULTI-COMMUNES (974), en série et REPRENABLE.

Robustesse (brief montée en charge) :
- une commune = une unité de travail COMMITTÉE indépendamment → un arrêt ne reperd
  pas les communes déjà faites ;
- reprise via `ingestion_runs.status` : `ok` (sauté), `ingested` (parcelles là →
  ré-évaluation seule), sinon (absent / `error` / `ingesting`) → purge + ingestion ;
- couches isolées par SAVEPOINT (déjà dans layers_ingest) : une couche en échec
  n'empêche pas les autres ni la commune ;
- bbox des couches = bbox de LA commune (pas l'emprise globale).

Aucune logique de cascade/scoring touchée : on orchestre l'existant.
"""
from __future__ import annotations

import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.cadastre import ingest_parcels
from ..models import IngestionRun
from . import cadastre_bulk, layers_ingest

# Les 24 communes de La Réunion — source : geo.api.gouv.fr/departements/974/communes.
REUNION_COMMUNES: list[tuple[str, str]] = [
    ("97401", "Les Avirons"),         ("97402", "Bras-Panon"),
    ("97403", "Entre-Deux"),          ("97404", "L'Étang-Salé"),
    ("97405", "Petite-Île"),          ("97406", "La Plaine-des-Palmistes"),
    ("97407", "Le Port"),             ("97408", "La Possession"),
    ("97409", "Saint-André"),         ("97410", "Saint-Benoît"),
    ("97411", "Saint-Denis"),         ("97412", "Saint-Joseph"),
    ("97413", "Saint-Leu"),           ("97414", "Saint-Louis"),
    ("97415", "Saint-Paul"),          ("97416", "Saint-Pierre"),
    ("97417", "Saint-Philippe"),      ("97418", "Sainte-Marie"),
    ("97419", "Sainte-Rose"),         ("97420", "Sainte-Suzanne"),
    ("97421", "Salazie"),             ("97422", "Le Tampon"),
    ("97423", "Les Trois-Bassins"),   ("97424", "Cilaos"),
]


def run_status(session: Session, name: str) -> str | None:
    """Dernier statut d'ingestion connu pour la commune (None si jamais tentée)."""
    return session.execute(
        text("SELECT status FROM ingestion_runs WHERE commune = :c ORDER BY id DESC LIMIT 1"),
        {"c": name},
    ).scalar()


def _commune_bbox(session: Session, name: str) -> tuple[float, float, float, float] | None:
    row = session.execute(
        text("SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) "
             "FROM (SELECT ST_Extent(geom) AS e FROM parcels WHERE commune = :c) t"),
        {"c": name},
    ).one()
    return None if row[0] is None else (float(row[0]), float(row[1]), float(row[2]), float(row[3]))


def purge_commune(session: Session, name: str) -> None:
    """Efface les données d'une commune (reprise propre, idempotence). Atomique avec l'ingestion."""
    session.execute(text("DELETE FROM spatial_layers WHERE commune = :c"), {"c": name})
    session.execute(text("DELETE FROM dvf_mutations WHERE commune = :c"), {"c": name})
    # parcels : ON DELETE CASCADE → cascade_results / parcel_evaluations / parcel_source_results
    session.execute(text("DELETE FROM parcels WHERE commune = :c"), {"c": name})
    session.execute(text("DELETE FROM ingestion_runs WHERE commune = :c"), {"c": name})


def _download_with_retry(insee: str, tries: int = 4):
    """Téléchargement cadastre résilient (backoff exponentiel sur erreur réseau)."""
    last = None
    for attempt in range(tries):
        try:
            return cadastre_bulk.download_parcelles(insee)
        except Exception as exc:  # noqa: BLE001 - on retente puis on relaie
            last = exc
            if attempt < tries - 1:
                time.sleep(2 ** attempt)
    raise last  # type: ignore[misc]


def ingest_commune(session: Session, insee: str, name: str, *, limit: int | None = None) -> dict:
    """PHASE INGESTION : purge + cadastre bulk + parcelles + couches (bbox commune).

    Statut du run → 'ingested' (parcelles & couches persistées). La cascade vient après.
    """
    purge_commune(session, name)
    run = IngestionRun(commune=name, status="ingesting", parcels_count=0)
    session.add(run)
    session.flush()

    parcels = cadastre_bulk.parse_etalab(_download_with_retry(insee))
    total = len(parcels)
    if limit:
        parcels = parcels[:limit]
    n = ingest_parcels(session, parcels, name, run.id)

    bbox = _commune_bbox(session, name)
    counts = layers_ingest.ingest_layers(session, insee, name, bbox, run.id) if bbox else {}

    run.parcels_count = n
    run.status = "ingested"
    return {"total": total, "parcels": n, "layers": counts, "run_id": run.id}


def evaluate_commune(session: Session, name: str, ai_provider=None) -> int:
    """PHASE ÉVALUATION : cascade + scoring sur les parcelles de la commune. Run → 'ok'."""
    from ..cascade import evaluate_parcels

    ids = [r[0] for r in session.execute(
        text("SELECT id FROM parcels WHERE commune = :c ORDER BY idu"), {"c": name}).all()]
    if ids:
        evaluate_parcels(ids, session, persist=True, ai_provider=ai_provider)
    session.execute(text("UPDATE ingestion_runs SET status = 'ok' WHERE commune = :c"), {"c": name})
    return len(ids)
