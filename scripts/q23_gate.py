"""DEPLOY-GROUPE-3 — rejeu des 7 contrôles de promotion sur q_v23 (lecture seule)."""
from __future__ import annotations
import json
from labuse.db import session_scope
from labuse import jobs_impl, autonomie, runs


def main() -> None:
    with session_scope() as db:
        precedent = runs.current()
        mesures = jobs_impl._mesures_run(db, "q_v23", precedent)
        man = jobs_impl._manifeste_candidat_present("q_v23")
        mesures["manifeste_present"] = man   # injecté comme le fait le calcul-nuit avant controler_run
        v = autonomie.controler_run(mesures, palier_delta_max_pct=3.0)
    print("precedent (servi) =", precedent)
    print("manifeste candidat présent =", man)
    print("mesures =", json.dumps(mesures, default=str, ensure_ascii=False))
    ok = getattr(v, "ok", None)
    echecs = getattr(v, "echecs", None)
    attente = getattr(v, "en_attente", None)
    print(f"VERDICT ok={ok} echecs={echecs} en_attente={attente}")


if __name__ == "__main__":
    main()
