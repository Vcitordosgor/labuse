#!/usr/bin/env python3
"""ORACLE-1 — agrège les parts par parcelle en VERITE.csv et LECTURE.csv (ordre S01→S20)."""
import csv
import glob
import os
import pathlib

ICI = pathlib.Path(__file__).parent
VER_COLS = ["idu", "slot", "notion", "valeur_labuse", "valeur_source", "service",
            "url", "page", "ecart", "verdict", "pourquoi"]
LEC_COLS = ["idu", "slot", "question", "statut", "preuve"]


def _agr(sous_dossier, cols, cible):
    rows = []
    for f in sorted(glob.glob(str(ICI / sous_dossier / "S*.csv"))):
        with open(f, newline="") as fh:
            r = csv.DictReader(fh, delimiter=";")
            for row in r:
                rows.append({c: (row.get(c) or "") for c in cols})
    rows.sort(key=lambda x: (x["slot"], x["notion"] if "notion" in x else x.get("question", "")))
    with open(ICI / cible, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter=";")
        w.writeheader()
        w.writerows(rows)
    return rows


def main():
    ver = _agr("verite_parts", VER_COLS, "VERITE.csv")
    lec = _agr("lecture_parts", LEC_COLS, "LECTURE.csv")
    nv = {}
    for r in ver:
        nv[r["verdict"]] = nv.get(r["verdict"], 0) + 1
    print(f"VERITE.csv : {len(ver)} lignes — {nv}")
    st = {}
    for r in lec:
        st[r["statut"]] = st.get(r["statut"], 0) + 1
    print(f"LECTURE.csv : {len(lec)} lignes — {st}")
    slots = sorted({r["slot"] for r in ver})
    print(f"slots présents ({len(slots)}) : {' '.join(slots)}")


if __name__ == "__main__":
    main()
