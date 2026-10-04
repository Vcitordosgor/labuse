"""CHASSE-1 angle 1 — face-à-face des lecteurs sur l'échantillon CHASSE (607 parcelles).

    python -m scripts.chasse.face_a_face   # → docs/audit-2026-10/CHASSE-1/ECARTS-LECTEURS.csv

Réutilise TELLE QUELLE la machinerie du banc V6b (scripts/coherence : CHECKS_P/CHECKS_C,
tuiles MVT décodées, croisements parcelle↔commune, déterminisme) mais sur l'ÉCHANTILLON
CHASSE-1 (stratifié + pièges + témoins ORACLE-1) au lieu des 120 parcelles historiques.
Mode en-process (TestClient FastAPI) : ni quota, ni DEV_MODE. Lecture seule.
"""
from __future__ import annotations

import csv
import json
import pathlib
import time

from scripts.coherence import banc
from scripts.coherence.lib import Contexte, Ecarts, client_en_process

RACINE = pathlib.Path(__file__).resolve().parents[2]
ECHANTILLON = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "ECHANTILLON.csv"
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "ECARTS-LECTEURS.csv"


def charger() -> list[dict]:
    with open(ECHANTILLON, newline="") as f:
        return [r for r in csv.DictReader(f) if r["idu"]]


def main() -> None:
    parcelles = charger()
    communes = sorted({r["commune"] for r in parcelles if r["commune"]})
    print(f"face-à-face lecteurs — {len(parcelles)} parcelles, {len(communes)} communes")
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
    grav = Counter(l["gravite"] for l in ec.lignes)
    print(f"\n{ec.n_comparaisons} comparaisons · {len(ec.lignes)} écarts : {dict(grav)}")
    print(f"→ {SORTIE} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
