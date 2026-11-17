"""VERITE-TERRAIN-3 — LOT 4 : Score LABUSE en DIRECT (moteur de main) sur les cohortes R et T.

Le classement servi (table `score_labuse`, run q_v20) est lu à part en SQL ; ici on rejoue le
calcul du score avec le code de main (scoring.score_labuse_combine.combiner — même chemin que la
fiche : score + cascade v2 → bande HC éventuelle), sur les caches servis du jour.
Sortie : SCORE-LIVE-R-T.csv (idu, cohorte, score, bande, cause, sdp_residuelle).

    PYTHONPATH=src python docs/audit-2026-11/verite-terrain-3/scripts/lot4_score_live.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
COHORTES = RACINE / "docs" / "audit-2026-11" / "verite-terrain-3" / "cohortes"
SORTIE = COHORTES / "SCORE-LIVE-R-T.csv"

CASCADE = json.loads((RACINE / "config" / "served_manifest.json").read_text())["cascade_run"]


def main() -> None:
    from labuse.db import session_factory
    from labuse.scoring.score_labuse_combine import combiner

    idus: dict[str, str] = {}
    with open(COHORTES / "R.csv", newline="") as f:
        for r in csv.DictReader(f):
            idus[r["idu"]] = "R"
    with open(COHORTES / "T.csv", newline="") as f:
        for r in csv.DictReader(f):
            idus.setdefault(r["idu"], "T")

    session = session_factory()()
    from sqlalchemy import text
    rows = session.execute(text("SELECT idu, id FROM parcels WHERE idu = ANY(:i)"),
                           {"i": list(idus)}).all()
    pid_idu = {r.id: r.idu for r in rows}
    pids = list(pid_idu)
    print(f"{len(idus)} idus ({sum(1 for v in idus.values() if v=='R')} R) ; "
          f"{len(pids)} trouvés en base ; cascade={CASCADE}", flush=True)

    out = []
    for i in range(0, len(pids), 500):
        lot = pids[i:i + 500]
        for l in combiner(session, lot, "vt3_live", cascade_label=CASCADE):
            out.append({"idu": l.idu, "cohorte": idus.get(l.idu, "?"), "score": l.score,
                        "bande": l.bande, "cause": l.cause,
                        "sdp_residuelle_m2": l.sdp_residuelle_m2})
        print(f"  {min(i+500, len(pids))}/{len(pids)}", flush=True)

    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["idu", "cohorte", "score", "bande", "cause",
                                          "sdp_residuelle_m2"])
        w.writeheader()
        w.writerows(sorted(out, key=lambda r: (r["cohorte"], r["idu"])))
    print(f"→ {SORTIE} ({len(out)} lignes)")


if __name__ == "__main__":
    main()
