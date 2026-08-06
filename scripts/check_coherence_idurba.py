"""M40 — vérification AUTONOME de la garde de cohérence idurba GPU-vs-mairie (dette confrontation).

Confronte l'idurba mairie (config/plu_millesimes.yaml) à l'idurba GPU ingéré (spatial_layers).
Bruyante NON bloquante : sort toujours 0 (comme check_fraicheur — elle alerte, elle ne bloque pas).
La MÊME garde (`labuse.bascule_gardes.check_coherence_idurba`) tourne au geste de bascule groupé.

Usage : PYTHONPATH=src python scripts/check_coherence_idurba.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from labuse.bascule_gardes import check_coherence_idurba  # noqa: E402


def main() -> None:
    res = check_coherence_idurba()
    print("\n— CONFRONTATION IDURBA GPU vs MAIRIE —")
    print(f"  divergences : {res['n']} (MANQUANT={res['n_manquant']}, RESIDU={res['n_residu']})")
    if res["divergences"]:
        print(f"  {'commune':22s} {'type':9s} {'idurba mairie':22s} {'idurba GPU':22s} ampleur")
        for d in res["divergences"]:
            amp = f"{d['ampleur_jours']} j" if d.get("ampleur_jours") is not None else "—"
            print(f"  {(d['commune'] or ''):22s} {d['type']:9s} {d['idurba_mairie']:22s} "
                  f"{d['idurba_gpu']:22s} {amp}")
        if res["n_manquant"]:
            print("  ⚠ MANQUANT = document mairie ABSENT du GPU = vrai retard GPU-derrière-mairie.")
        if res["n_residu"]:
            print("  ⚠ RESIDU = document superseded conservé au GPU (hygiène — à archiver).")
    else:
        print("  ✓ GPU = mairie pour toutes les communes outillées.")
    # NON bloquant : toujours exit 0 (régime check_fraicheur).


if __name__ == "__main__":
    main()
