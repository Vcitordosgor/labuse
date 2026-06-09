"""Worker isolé : évalue OU ingère UNE seule commune, dans un process frais
(engine SQLAlchemy propre). Reprenable : vérifie le statut avant d'agir.

Usage :
  python scripts/_commune_worker.py eval   "Saint-Denis"
  python scripts/_commune_worker.py ingest 97418 "Sainte-Marie"
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permet l'exécution même si le package n'est pas installé (fallback src/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from labuse.db import session_scope  # noqa: E402
from labuse.ingestion import run_all  # noqa: E402


def main() -> None:
    action = sys.argv[1]
    if action == "eval":
        name = sys.argv[2]
        with session_scope() as s:
            if run_all.run_status(s, name) == "ok":
                print(f"skip-ok {name}", flush=True)
                return
        with session_scope() as s:
            n = run_all.evaluate_commune(s, name)
        print(f"evaluated {name} {n}", flush=True)
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
