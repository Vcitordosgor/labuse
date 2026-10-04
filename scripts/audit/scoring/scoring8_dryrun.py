"""SCORING-8 · harnais de DRY-RUN du Score LABUSE (lot A) — mesure « qu'est-ce qui bouge ».

Score les 30 parcelles témoins (reports/scoring-5/TEMOINS.csv) + toute la commune de
Saint-Paul, via `score_batch` (fonction pure + lecture des caches), SANS rien écrire dans
une table de service. Deux modes :

  python scoring8_dryrun.py snapshot <fichier.json>   # fige l'état courant
  python scoring8_dryrun.py diff     <fichier.json>   # rejoue et compare au fichier

Usage (worktree) :
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
    ~/Desktop/labuse/.venv/bin/python scripts/audit/scoring/scoring8_dryrun.py snapshot /tmp/s8a_avant.json

Le `cascade_label` (d'où est lu le facteur mineur `acces`) = étage 0 courant du candidat.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

CASCADE_LABEL = os.environ.get("S8_CASCADE", "q_v13_sources1")
TEMOINS = ROOT / "reports" / "scoring-5" / "TEMOINS.csv"
COMMUNE = os.environ.get("S8_COMMUNE", "Saint-Paul")


def _ids(session) -> list[int]:
    from sqlalchemy import text
    idus = [r["idu"] for r in csv.DictReader(TEMOINS.open())]
    temoins = [row[0] for row in session.execute(
        text("SELECT id FROM parcels WHERE idu = ANY(:i)"), {"i": idus})]
    commune = [row[0] for row in session.execute(
        text("SELECT id FROM parcels WHERE commune = :c ORDER BY id"), {"c": COMMUNE})]
    # union déterministe, témoins d'abord, sans doublon
    vus, out = set(), []
    for pid in temoins + commune:
        if pid not in vus:
            vus.add(pid)
            out.append(pid)
    return out


def _scorer(session, ids: list[int]) -> dict[str, dict]:
    from labuse.scoring.score_labuse import score_batch
    res = {}
    for k in range(0, len(ids), 5000):
        for s in score_batch(session, ids[k:k + 5000], "dryrun_s8a", cascade_label=CASCADE_LABEL):
            res[str(s.parcel_id)] = {
                "idu": s.idu, "commune": s.commune, "score": s.score, "bande": s.bande,
                "nc": s.non_calculable, "cause": s.cause,
                "sdp": s.details.get("sdp_residuelle_m2"),
                "coef": s.details.get("coef"), "f_bati": s.details.get("f_bati"),
                "f_acces": s.details.get("f_acces")}
    return res


def main() -> None:
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    mode, dest = sys.argv[1], sys.argv[2]
    from labuse.db import session_scope
    with session_scope() as s:
        ids = _ids(s)
        cur = _scorer(s, ids)
    print(f"[s8a] {len(ids)} parcelles scorées (cascade={CASCADE_LABEL}).", flush=True)
    if mode == "snapshot":
        Path(dest).write_text(json.dumps(cur, ensure_ascii=False, sort_keys=True))
        print(f"[s8a] snapshot écrit → {dest}", flush=True)
        return
    # diff
    avant = json.loads(Path(dest).read_text())
    bougent_score, bougent_bande, bougent_nc = [], [], []
    for pid, now in cur.items():
        was = avant.get(pid)
        if was is None:
            continue
        if was["score"] != now["score"]:
            bougent_score.append((pid, now["idu"], was["score"], now["score"]))
        if was["bande"] != now["bande"]:
            bougent_bande.append((pid, now["idu"], was["bande"], now["bande"]))
        if was["nc"] != now["nc"]:
            bougent_nc.append((pid, now["idu"], was["nc"], now["nc"]))
    disparus = set(avant) ^ set(cur)
    print(f"[s8a] DIFF vs {dest} :", flush=True)
    print(f"  scores qui bougent : {len(bougent_score)}", flush=True)
    print(f"  bandes qui bougent : {len(bougent_bande)}", flush=True)
    print(f"  NC qui bougent     : {len(bougent_nc)}", flush=True)
    print(f"  ensembles différents (parc. en + ou -): {len(disparus)}", flush=True)
    for lst, nom in ((bougent_score, "SCORE"), (bougent_bande, "BANDE"), (bougent_nc, "NC")):
        for row in lst[:40]:
            print(f"    [{nom}] {row}", flush=True)


if __name__ == "__main__":
    main()
