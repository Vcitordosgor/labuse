#!/usr/bin/env python
"""DASHBOARD-FIX-1 (point 3) — RATTRAPAGE du journal des bascules.

La bascule q_v16 du 05/10 a été posée HORS du chemin `basculer()` (pointeurs édités/commités à la
main) : elle n'a jamais écrit `run_bascule_journal`, dont la dernière ligne restait le 05/09
(q_v12 → q_v11_m137). L'indicateur « dernière bascule » de /admin/flux mentait donc d'un mois.

Ce script écrit UNE ligne, datée du vrai moment de la promotion (lu dans le manifeste), motif
« rattrapage ». IDEMPOTENT : si une ligne q_v11_m137 → q_v16 datée du 05/10 existe déjà, il ne fait
rien. Aucune requête lourde (un SELECT de contrôle + un INSERT).

Usage :  PYTHONPATH=src python scripts/dashboard-fix/rattrapage_bascule.py
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from labuse import bascule_flux
from labuse.db import engine, session_scope

_MANIFESTE = Path(__file__).resolve().parents[2] / "config" / "served_manifest.json"


def main() -> int:
    m = json.loads(_MANIFESTE.read_text(encoding="utf-8"))
    nouveau = m["scoring_run"]                              # q_v16
    ancien = (m.get("precedent") or {}).get("scoring_run")  # q_v11_m137
    ts = m["promoted_at"]                                   # 2026-10-05T11:35:…+00:00
    bascule_flux.ensure_tables(engine())
    with session_scope() as s:
        deja = s.execute(text(
            "SELECT count(*) FROM run_bascule_journal WHERE nouveau = :n AND ts::date = :d"),
            {"n": nouveau, "d": ts[:10]}).scalar() or 0
        if deja:
            print(f"✓ déjà au journal : bascule {ancien} → {nouveau} du {ts[:10]} ({deja} ligne(s)) — rien à faire")
            return 0
        s.execute(text(
            "INSERT INTO run_bascule_journal (ts, ancien, nouveau, par, sens, caches_purges, coherence) "
            "VALUES (:ts, :a, :n, :par, 'avant', '[]'::jsonb, :co)"),
            {"ts": ts, "a": ancien, "n": nouveau, "par": "rattrapage",
             "co": json.dumps({"motif": "rattrapage",
                               "note": "DASHBOARD-FIX-1 — bascule q_v16 posée hors basculer() le 05/10, "
                                       "rattrapée au journal (une ligne, datée du manifeste)."})})
        s.commit()
    print(f"✓ rattrapage écrit : bascule {ancien} → {nouveau} datée {ts} (motif « rattrapage »)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
