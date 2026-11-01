#!/usr/bin/env python3
"""AUDIT-NU-3-J — agrégation : couples comparés, écarts par fait et par surface,
top écarts. Combine matrice JSON (02) + vérité (03) + PDF/Docs (04) + externe (05)."""
import json, os, csv, itertools
from collections import defaultdict, Counter
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "out")

def load(n):
    p = os.path.join(OUT, n)
    return json.load(open(p)) if os.path.exists(p) else None

def main():
    # ── matrice JSON : reconstruire cellules par (idu, notion) ──
    cells = defaultdict(dict)  # (idu,notion) -> {surface: val}
    with open(os.path.join(OUT, "matrix_json.csv")) as fh:
        for r in csv.DictReader(fh):
            if r["valeur"] != "":
                cells[(r["idu"], r["notion"])][r["surface"]] = r["valeur"]
    couples = 0; couples_ecart = 0
    ecart_by_notion = Counter(); couple_by_notion = Counter()
    ecart_by_surface = Counter(); presence_by_surface = Counter()
    for (idu, notion), surf in cells.items():
        for s in surf: presence_by_surface[s] += 1
        for a, b in itertools.combinations(sorted(surf), 2):
            couples += 1; couple_by_notion[notion] += 1
            if surf[a] != surf[b]:
                couples_ecart += 1; ecart_by_notion[notion] += 1
                ecart_by_surface[a] += 1; ecart_by_surface[b] += 1
    # ── PDF/Docs (04) ──
    docs = load("docs_pdf_agg.json") or []
    docs_couples = 0; docs_ecart_rows = 0; docs_ecart_by_fait = Counter()
    docs_parcelles = len({d["idu"] for d in docs})
    for d in docs:
        present = [v for v in d["cells"].values() if v]
        k = len(present)
        docs_couples += k*(k-1)//2
        if d["ecart"]:
            docs_ecart_rows += 1; docs_ecart_by_fait[d["donnee"]] += 1
    # ── externe (05) ──
    ext = load("external20.json") or []
    ext_couples = sum((1 if x.get("ext_contenance") is not None else 0)
                      + (1 if x.get("ext_zone") else 0)
                      + (1 if x.get("ext_vente") else 0) for x in ext)
    ext_ecart = sum((1 if x["ecart_surface"] else 0)+(1 if x["ecart_zone"] else 0)
                    +(1 if x["ecart_vente"] else 0) for x in ext)
    # ── vérité interne (03) : comparer fiche vs vérité pour faits recalculables ──
    truth = load("truth.json") or {}
    # (déjà exploité ailleurs ; ici on ne recompte pas)

    rep = {
      "json": {"cellules_non_vides": sum(len(s) for s in cells.values()),
               "lignes_fait_parcelle": len(cells),
               "couples_compares": couples, "couples_en_ecart": couples_ecart,
               "ecart_par_notion": dict(ecart_by_notion.most_common()),
               "couples_par_notion": dict(couple_by_notion),
               "ecart_par_surface": dict(ecart_by_surface.most_common()),
               "presence_par_surface": dict(presence_by_surface.most_common())},
      "docs": {"parcelles": docs_parcelles, "couples_compares": docs_couples,
               "lignes_fait_avec_ecart": docs_ecart_rows,
               "ecart_par_fait": dict(docs_ecart_by_fait.most_common())},
      "externe": {"parcelles": len(ext), "couples_compares": ext_couples, "ecarts": ext_ecart},
    }
    rep["TOTAL_couples"] = couples + docs_couples + ext_couples
    rep["TOTAL_ecarts"]  = couples_ecart + docs_ecart_rows + ext_ecart
    json.dump(rep, open(os.path.join(OUT, "stats.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
