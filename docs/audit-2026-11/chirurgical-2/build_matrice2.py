#!/usr/bin/env python3
"""Assemble MATRICE-2.csv (idu × fait × document × valeur) à partir de :
 - ref_faits.csv            → colonne document=FICHE (vérité servie)
 - matrice_parts/*.csv      → les faits extraits de CHAQUE document par les sous-agents
Puis DIVERGENCES_auto2.csv : pour un même (idu, fait normalisé), des valeurs différentes
entre documents (un fait présent ici et absent là dans une même rubrique = divergence)."""
import csv, glob, re
from pathlib import Path

HERE = Path(__file__).parent
rows = []  # dicts idu,fait,document,valeur

# 1) FICHE (ground truth)
for r in csv.DictReader((HERE / "ref_faits.csv").open()):
    rows.append({"idu": r["idu"], "fait": r["fait"], "document": "FICHE", "valeur": r["valeur"]})

# 2) document fragments
for f in sorted(glob.glob(str(HERE / "matrice_parts" / "*.csv"))):
    for r in csv.DictReader(open(f)):
        if not r.get("idu"):
            continue
        rows.append({"idu": r["idu"], "fait": r.get("fait", ""),
                     "document": r.get("document", Path(f).stem), "valeur": r.get("valeur", "")})

out = HERE / "MATRICE-2.csv"
with out.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["idu", "fait", "document", "valeur"])
    w.writeheader(); w.writerows(sorted(rows, key=lambda x: (x["idu"], x["fait"], x["document"])))
print(f"MATRICE-2.csv → {len(rows)} lignes")

# 3) auto-divergences: normalise numbers, compare across documents per (idu, fait)
def norm(v):
    s = str(v).strip().lower().replace(" ", "").replace("\xa0", "").replace(" ", "")
    m = re.findall(r"-?\d+[.,]?\d*", s.replace(",", "."))
    if m:
        try: return round(float(m[0]), 1)
        except ValueError: return s
    return s

from collections import defaultdict
by = defaultdict(dict)   # (idu,fait) -> {document: set(norm values)}
for r in rows:
    by[(r["idu"], r["fait"])].setdefault(r["document"], set()).add(norm(r["valeur"]))

div = []
for (idu, fait), docs in by.items():
    if len(docs) < 2:
        continue
    # collect the union of normalised scalar values seen across documents
    allvals = set()
    for s in docs.values():
        allvals |= {x for x in s if x not in ("", "none", "—", "-")}
    if len({v for v in allvals if isinstance(v, (int, float))}) > 1 or len(allvals) > 1:
        div.append({"idu": idu, "fait": fait,
                    "valeurs": " | ".join(f"{d}={sorted(map(str,v))}" for d, v in sorted(docs.items()))})

dout = HERE / "DIVERGENCES_auto2.csv"
with dout.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["idu", "fait", "valeurs"])
    w.writeheader(); w.writerows(div)
print(f"DIVERGENCES_auto2.csv → {len(div)} lignes (à trier à la main : méthodes ≠ vs vraies divergences)")
