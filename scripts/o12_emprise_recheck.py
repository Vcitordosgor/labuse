#!/usr/bin/env python
"""O12-PARTIEL — RE-CONFRONTATION de l'emprise du lot restant au plafond RÉEL de sa zone.

Le pool a été calculé quand 2 communes seulement (Saint-Paul, Saint-Denis) portaient un PLU
calibré ; les autres passaient par le repli 60 %. Les PLU de la nuit gravent les emprises max
réelles (souvent < 60 %). L'emprise du lot restant est un FAIT géométrique (bâti conservé /
surface restante) qui ne bouge pas ; c'est le PLAFOND qui change. Ce script confronte, pour
chacun des 36, l'emprise restante stockée au plafond de sa zone lu MAINTENANT (LECTURE SEULE,
n'écrit rien) — mêmes règles que le détecteur (_emprise_max_sql) : emprise_sol_pct calibrée
si c'est un nombre, sinon EMPRISE_RESTANTE_MAX (0,60).

À lancer APRÈS le merge de feat/plu-nuit-a ET feat/plu-nuit-b (sinon on lit l'ancien état)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labuse.faisabilite import plu_rules  # noqa: E402
from labuse.ingestion.division_or import EMPRISE_RESTANTE_MAX  # noqa: E402

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")


def plafond(commune: str, zone_lib: str | None) -> tuple[float, str]:
    """(plafond, source) pour la zone d'un candidat. source ∈ {calibré, repli-zone, repli-commune}.
    repli-commune : PLU de la commune absent → 60 %. repli-zone : PLU présent mais la zone n'a
    pas d'emprise chiffrée (null / a_verifier) → 60 %."""
    rules = plu_rules.load_rules(commune)          # {} si commune non outillée
    if not rules:
        return EMPRISE_RESTANTE_MAX, "repli-commune (PLU non calibré)"
    r = rules.get(zone_lib or "")
    if r is not None and isinstance(r.emprise_sol_pct, float):
        return r.emprise_sol_pct / 100.0, "calibré"
    return EMPRISE_RESTANTE_MAX, "repli-zone (emprise non chiffrée au PLU)"


def main() -> None:
    e = create_engine(DB)
    rows = [dict(r) for r in e.connect().execute(text(
        "SELECT idu, commune, type_division, zone_lib, emprise_restante "
        "FROM division_or_candidates ORDER BY commune, idu")).mappings()]
    from labuse.config import get_settings
    calib = sorted(p.name[len("plu_"):-len(".yaml")] for p in
                   get_settings().config_path.glob("plu_*.yaml"))
    print(f"Communes PLU calibrées lues MAINTENANT ({len(calib)}) : {', '.join(calib)}\n")

    passe, tombe, repli = [], [], []
    for r in rows:
        emp = float(r["emprise_restante"]) if r["emprise_restante"] is not None else 0.0
        pl, src = plafond(r["commune"], r["zone_lib"])
        r["plafond"], r["source"], r["emp"] = pl, src, emp
        (tombe if emp > pl + 1e-9 else passe).append(r)
        if src != "calibré":
            repli.append(r)

    print(f"POOL : {len(rows)} candidats — PASSENT : {len(passe)} · TOMBENT : {len(tombe)}\n")
    if tombe:
        print("── TOMBENT (emprise restante > plafond réel de la zone) ──")
        for r in sorted(tombe, key=lambda r: r["emp"] - r["plafond"], reverse=True):
            print(f"  {r['idu']}  {r['commune']:<16} {r['type_division']:<10} zone {r['zone_lib'] or '(RNU)':<6} "
                  f"emprise {r['emp']*100:4.0f}% > plafond {r['plafond']*100:3.0f}% ({r['source']})")
    else:
        print("  aucun candidat ne tombe ✓")

    print(f"\n── Encore au REPLI 60 % (à signaler à part, {len(repli)}) ──")
    for r in sorted(repli, key=lambda r: (r["commune"], r["idu"])):
        print(f"  {r['idu']}  {r['commune']:<16} zone {r['zone_lib'] or '(RNU)':<6} "
              f"emprise {r['emp']*100:4.0f}% / repli 60%  [{r['source']}]  "
              f"{'⚠ dépasserait un vrai plafond < 60%' if r['emp'] > 0.5 else ''}")


if __name__ == "__main__":
    main()
