"""M113 - Phase 5 - le chrono du maire, PAR LEVIER. On distingue :
  - BASE           : texte libre, routeur sur SONNET (ni A ni B1) = base Phase 0 (~15-16 s attendu)
  - B1 seul        : texte libre, routeur sur HAIKU (B1) - gagne le delta du routage
  - A (+B1) chip web : chip « web » -> classify COURT-CIRCUITE -> web seul (~5 s attendu)

NB : pour le maire (web), le chip saute classify ENTIEREMENT, donc B1 (haiku vs sonnet du routeur)
n'ajoute rien AU CHIP web ; le gain du chip est le meme avec ou sans B1. B1 se voit sur la voie
LIBRE et sur les chips NON-web. On le dit explicitement dans le rapport.

Usage : .venv/bin/python qa/m113/chrono_leviers.py
"""
from __future__ import annotations

import time

from labuse.ai import core
from labuse.copilote_v2 import answering
from labuse.db import session_scope

MSG = "Qui est le maire de La Possession ?"
HAIKU = core.MODEL_FACTUAL
SONNET = core.MODEL_REASONING


def _mesure(db, scenario, forcer_sonnet):
    # forcer_sonnet : la voie LIBRE mesuree avec le routeur sur sonnet (base pre-B1).
    orig = core.MODEL_FACTUAL
    if forcer_sonnet:
        core.MODEL_FACTUAL = SONNET          # le routeur (MODEL_FACTUAL) redevient sonnet
    try:
        t0 = time.perf_counter()
        r = answering.answer(db, MSG, scenario=scenario)
        ms = round((time.perf_counter() - t0) * 1000)
    finally:
        core.MODEL_FACTUAL = orig
    return ms, r.get("degraded"), r.get("scenario")


def main() -> int:
    leviers = [
        ("BASE (libre, routeur SONNET)", None, True),
        ("B1 seul (libre, routeur HAIKU)", None, False),
        ("A+B1 (chip web)", "web", False),
    ]
    with session_scope() as db:
        for label, scen, sonnet in leviers:
            passes = []
            for _ in (1, 2):
                ms, deg, sc = _mesure(db, scen, sonnet)
                passes.append(ms)
                if deg:
                    print(f"  {label}: DEGRADED (quota) - non mesurable")
                    break
            else:
                print(f"  {label}: {passes[0]} ms / {passes[1]} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
