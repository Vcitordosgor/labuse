"""CHASSE-2 angle 1 — face-à-face des lecteurs sur l'échantillon NEUF (718 parcelles).

    python -m scripts.chasse.face_a_face2   # → docs/audit-2026-10/CHASSE-2/ECARTS-LECTEURS2.csv

Même machinerie que CHASSE-1 (banc V6b : CHECKS_P/CHECKS_C, tuiles MVT décodées,
croisements parcelle↔commune, déterminisme) sur l'échantillon CHASSE-2
(stratifié graine 0.77 + pièges + classes run 13). Mode en-process, lecture seule.
"""
from __future__ import annotations

import csv
import pathlib
import time

from scripts.coherence import banc
from scripts.coherence.lib import Contexte, Ecarts, client_en_process

RACINE = pathlib.Path(__file__).resolve().parents[2]
ECHANTILLON = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "ECHANTILLON.csv"
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "ECARTS-LECTEURS2.csv"


def charger() -> list[dict]:
    with open(ECHANTILLON, newline="") as f:
        return [r for r in csv.DictReader(f) if r["idu"]]


def main() -> None:
    parcelles = charger()
    communes = sorted({r["commune"] for r in parcelles if r["commune"]})
    print(f"face-à-face lecteurs CHASSE-2 — {len(parcelles)} parcelles, {len(communes)} communes")
    client, fetch = client_en_process()
    ctx = Contexte(fetch=fetch, client=client)
    ec = Ecarts()
    t0 = time.time()
    banc.passe_parcelles(ctx, ec, parcelles)
    print(f"parcelles faites ({time.time()-t0:.0f}s) ; communes…")
    banc.passe_communes(ctx, ec, communes, ile=False)
    banc.passe_croisements(ctx, ec, parcelles)
    banc.passe_determinisme(ctx, ec, parcelles, communes, refetch=fetch)

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["notion", "objet", "lecteur_a", "valeur_a",
                                          "lecteur_b", "valeur_b", "ecart", "cause", "gravite"])
        w.writeheader()
        w.writerows(ec.lignes)
    from collections import Counter
    print(f"{sum(ec.compte.values()) if hasattr(ec, 'compte') else ''}")
    print(f"{len(ec.lignes)} écarts : {Counter(l['gravite'] for l in ec.lignes)}")
    print(f"→ {SORTIE} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
