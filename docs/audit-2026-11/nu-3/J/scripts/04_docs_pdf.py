#!/usr/bin/env python3
"""AUDIT-NU-3-J — surfaces PDF / Docs. Réutilise le harnais maison scripts.docs_coherence
(les 8-9 documents de la page Docs, pdftotext, 18 faits partagés) sur un sous-ensemble
d'1 parcelle/commune (préférence bâti = plus de faits). Écrit un CSV par parcelle et un
agrégat. Confronte AUSSI les valeurs PDF aux cellules fiche JSON (02). Lecture seule."""
import json, os, sys, csv
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "out")
os.environ["LABUSE_DOCS_API"] = "http://127.0.0.1:9310"
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)  # racine (scripts package)
from scripts import docs_coherence as DC

def choisir(sample, n):
    by_comm = {}
    for r in sample: by_comm.setdefault(r["commune"], []).append(r)
    out = []
    for comm in sorted(by_comm):
        cand = sorted(by_comm[comm], key=lambda r: (0 if "bati" in r.get("profils",[]) else 1,
                                                    0 if "copro" in r.get("profils",[]) else 1, r["idu"]))
        out.append(cand[0])
    return out[:n]

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    sample = json.load(open(os.path.join(OUT, "sample120.json")))
    cible = choisir(sample, n)
    os.makedirs(os.path.join(OUT, "docs"), exist_ok=True)
    agg = []  # {idu, donnee, ecart, cells par doc}
    for i, c in enumerate(cible, 1):
        idu = c["idu"]
        print(f"[{i}/{len(cible)}] {idu} {c['commune']} — génération documents…", flush=True)
        try:
            textes = DC.documents(idu)
            lignes = DC.comparer(textes)
        except Exception as e:
            print(f"  !! {idu} ÉCHEC: {e}", flush=True); continue
        DC._csv(idu, lignes, os.path.join(OUT, "docs", f"{idu}.csv"))
        for l in lignes:
            agg.append({"idu": idu, "commune": c["commune"], "donnee": l["donnee"],
                        "ecart": l["ecart"], "valeurs": l["valeurs"],
                        "cells": {d: l["cells"][d] for d in DC.ORDRE_DOCS}})
        ne = sum(1 for l in lignes if l["ecart"])
        print(f"  -> {ne} écart(s) inter-documents", flush=True)
    json.dump(agg, open(os.path.join(OUT, "docs_pdf_agg.json"), "w"), ensure_ascii=False, indent=1)
    # CSV agrégé long
    with open(os.path.join(OUT, "matrix_docs.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["idu","commune","donnee","ecart"]+DC.ORDRE_DOCS)
        for a in agg:
            w.writerow([a["idu"],a["commune"],a["donnee"],"ECART" if a["ecart"] else ""]
                       +[a["cells"][d] or "" for d in DC.ORDRE_DOCS])
    from collections import Counter
    necart = sum(1 for a in agg if a["ecart"])
    print(f"\nPDF/Docs : {len(cible)} parcelles, {len(agg)} lignes fait×parcelle, {necart} avec écart inter-documents")
    byn = Counter(a["donnee"] for a in agg if a["ecart"])
    for n_,k in byn.most_common(): print(f"  {n_:28} {k}")

if __name__ == "__main__":
    main()
