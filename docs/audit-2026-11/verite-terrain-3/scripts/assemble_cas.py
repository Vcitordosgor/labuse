"""VERITE-TERRAIN-3 — CAS.csv : tous les cas relus un par un, avec leur classement.

Fusionne les relectures (TEST1 ×2, TEST2, LOT4, LOT5, VT2-DEFAUTS si présent) en un format
unique : volet;cas;idu;commune;classement;detail. Les tables Markdown de LOT4/LOT5 sont
parsées (colonnes idu / verdict).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

DOSSIER = Path(__file__).resolve().parents[1]
REL = DOSSIER / "relectures"
OUT = DOSSIER / "CAS.csv"

rows = []


def add(volet, cas, idu, commune, classement, detail):
    rows.append({"volet": volet, "cas": cas, "idu": idu, "commune": commune,
                 "classement": classement, "detail": re.sub(r"\s+", " ", detail or "").strip()[:300]})


for fn, volet in (("TEST1-RELECTURE-1.csv", "test1_verdict"),
                  ("TEST1-RELECTURE-2.csv", "test1_verdict"),
                  ("TEST2-RELECTURE-40.csv", "test2_enveloppe")):
    p = REL / fn
    if not p.exists():
        continue
    for r in csv.DictReader(open(p, newline="")):
        add(volet, r["permit_id"], r["idu"], r.get("commune", ""), r["classement"],
            (r.get("sous_type", "") + " — " if r.get("sous_type") else "") + r.get("preuve", ""))

vt2 = REL / "VT2-DEFAUTS-RELECTURE.csv"
if vt2.exists():
    for r in csv.DictReader(open(vt2, newline="")):
        cle = r.get("cas") or r.get("permit_id") or ""
        add("vt2_defauts", cle, r.get("idu", ""), r.get("commune", ""),
            r.get("classement", ""), r.get("preuve") or r.get("preuve_courte", ""))


def parse_md_table(path, volet):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if not line.startswith("|") or line.startswith("|---") or "| idu |" in line:
            continue
        cells = [re.sub(r"[`*]", "", c).strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or not re.search(r"97[0-9]{3}[0-9]{3}[A-Z0-9]{2}[0-9]{4}", cells[0]):
            continue
        verdict = re.sub(r"\*+", "", cells[-1])
        add(volet, cells[0], cells[0], "", verdict.split("—")[0].strip()[:60], " ".join(cells[1:]))


parse_md_table(REL / "LOT4-RELECTURE-30-NOTES.md", "lot4_classement")
parse_md_table(REL / "LOT5-RELECTURE-20-NOTES.md", "lot5_ventes")

with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["volet", "cas", "idu", "commune", "classement", "detail"],
                       delimiter=";")
    w.writeheader()
    w.writerows(rows)
print(f"→ {OUT} ({len(rows)} cas)")
from collections import Counter
print(Counter((r["volet"], r["classement"][:28]) for r in rows).most_common(20))
