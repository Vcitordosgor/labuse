"""Worker isolé : évalue OU ingère UNE seule commune, dans un process frais
(engine SQLAlchemy propre). Reprenable AU NIVEAU PARCELLE : l'évaluation ne
traite que les parcelles SANS verdict et committe par petits lots — la
progression s'accumule donc entre deux interruptions (conteneur recyclé, etc.),
au lieu de repartir de zéro à chaque fois.

Usage :
  python scripts/_commune_worker.py eval   "Saint-Denis"
  python scripts/_commune_worker.py ingest 97418 "Sainte-Marie"
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permet l'exécution même si le package n'est pas installé (fallback src/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.ingestion import run_all  # noqa: E402

CHUNK = 1000  # petit lot = commits fréquents = peu de travail reperdu si interruption


def _evaluate_resumable(name: str) -> None:
    """Évalue les parcelles SANS verdict de la commune, lot par lot (commit après
    chacun), puis marque la commune « ok ». Rejouable : reprend là où ça s'est
    arrêté. Verdicts identiques (cascade inchangée)."""
    from labuse.cascade import evaluate_parcels

    done_total = 0
    while True:
        with session_scope() as s:
            ids = [r[0] for r in s.execute(text(
                "SELECT p.id FROM parcels p "
                "WHERE p.commune = :c "
                "  AND NOT EXISTS (SELECT 1 FROM parcel_evaluations e WHERE e.parcel_id = p.id) "
                "ORDER BY p.idu LIMIT :lim"), {"c": name, "lim": CHUNK}).all()]
            if not ids:
                s.execute(text("UPDATE ingestion_runs SET status = 'ok' WHERE commune = :c"),
                          {"c": name})
                break
            evaluate_parcels(ids, s, persist=True)
            s.commit()
        done_total += len(ids)
        print(f"      … {name} +{len(ids)} (cumul session {done_total})", flush=True)


def main() -> None:
    action = sys.argv[1]
    if action == "eval":
        name = sys.argv[2]
        with session_scope() as s:
            if run_all.run_status(s, name) == "ok":
                print(f"skip-ok {name}", flush=True)
                return
        _evaluate_resumable(name)
        print(f"evaluated {name}", flush=True)
    elif action == "ingest":
        insee, name = sys.argv[2], sys.argv[3]
        with session_scope() as s:
            st = run_all.run_status(s, name)
        if st in ("ok", "ingested"):
            print(f"skip-{st} {name}", flush=True)
            return
        with session_scope() as s:
            info = run_all.ingest_commune(s, insee, name)
        print(f"ingested {name} {info['parcels']}", flush=True)
    else:  # pragma: no cover - garde-fou CLI
        raise SystemExit(f"action inconnue: {action!r} (eval|ingest)")


if __name__ == "__main__":
    main()
