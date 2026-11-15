"""VERITE-TERRAIN-3 — LOT 2 (Test 1 : verdict) et LOT 3 (Test 2 : enveloppe) sur la cohorte H.

Consomme : cohortes/H.csv + cache/capacite/<idu>.json (moteur de main, rejeu VT-3)
         + cohortes/SERVI.csv (gate servi — ce que le client voit).

Sorties (dans cohortes/) :
  TEST1-VERDICTS.csv   — un permis H par ligne : verdict direct + servi, zones, motifs ;
  TEST1-NON-60.csv     — l'échantillon de relecture (tous les « non » ≤ 60, sinon tirage md5) ;
  TEST2-ENVELOPPE.csv  — H mono-parcelle : autorisé vs estimation rapide vs enveloppe max ;
  TEST2-DEPASSEMENTS-40.csv — les 40 dépassements d'enveloppe les plus forts.
Les agrégats sont imprimés (effectifs + dénominateurs, jamais un % seul).

    PYTHONPATH=src python docs/audit-2026-11/verite-terrain-3/scripts/lot2_lot3_analyse.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
DOSSIER = RACINE / "docs" / "audit-2026-11" / "verite-terrain-3"
COHORTES = DOSSIER / "cohortes"
CACHE = DOSSIER / "cache" / "capacite"

COEF_PLANCHER = 1.15          # habitable Sit@del → plancher (même coef que VT-2 / score_e)
SEUIL_DEPASSEMENT = 1.10      # enveloppe dépassée de plus de 10 %
GRAINE = "VT3-LOT2-60"


def cache(idu: str) -> dict | None:
    p = CACHE / f"{idu}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main() -> None:
    servi = {}
    with open(COHORTES / "SERVI.csv", newline="") as f:
        for r in csv.DictReader(f):
            servi[r["idu"]] = r

    h = list(csv.DictReader(open(COHORTES / "H.csv", newline="")))
    print(f"H = {len(h)} permis")

    t1_rows, manquants = [], 0
    for p in h:
        idus = [i.strip() for i in p["idus"].split(",") if i.strip()]
        caps = [cache(i) for i in idus]
        if any(c is None for c in caps):
            manquants += 1
            continue
        constr = [bool(c.get("constructible")) for c in caps]
        causes = sorted({str(c.get("cause")) for c in caps if not c.get("constructible")})
        zones = sorted({c.get("zone") or "?" for c in caps})
        fams = sorted({c.get("zone_fam") or "?" for c in caps})
        sv = [servi.get(i) for i in idus]
        sv_ouvert = [s is not None and s.get("gate_ferme") == "f" for s in sv]
        t1_rows.append({
            "permit_id": p["permit_id"], "insee": p["insee"], "commune": p["commune"],
            "d_aut": p["d_aut"], "type_projet": p["type_projet"], "mono": p["mono"],
            "nb_lgt": p["nb_lgt"], "surf_hab": p["surf_hab"],
            "n_parc": len(idus), "idus": " ".join(idus),
            "zones": "|".join(zones), "zone_fam": "|".join(fams),
            "direct_constructible": any(constr),
            "direct_causes_non": " ; ".join(causes)[:160],
            "servi_ouvert": any(sv_ouvert),
            "servi_causes": " ; ".join(sorted({(s.get("resid_cause") or s.get("constr_label")
                                                or s.get("au_classe") or "")
                                               for s in sv if s}))[:160],
        })
    print(f"permis sans cache complet (sautés) : {manquants}")

    with open(COHORTES / "TEST1-VERDICTS.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(t1_rows[0]))
        w.writeheader()
        w.writerows(t1_rows)

    n = len(t1_rows)
    oui = [r for r in t1_rows if r["direct_constructible"]]
    non = [r for r in t1_rows if not r["direct_constructible"]]
    sv_oui = sum(1 for r in t1_rows if r["servi_ouvert"])
    print(f"\nTEST 1 — moteur en direct : constructible {len(oui)}/{n} "
          f"({100*len(oui)/n:.1f} %) ; non {len(non)}")
    print(f"TEST 1 — servi (gate) : ouvert {sv_oui}/{n} ({100*sv_oui/n:.1f} %)")

    def taux(groupe_cle):
        agg = defaultdict(lambda: [0, 0])
        for r in t1_rows:
            k = r[groupe_cle]
            agg[k][1] += 1
            agg[k][0] += bool(r["direct_constructible"])
        return {k: (o, t) for k, (o, t) in sorted(agg.items(), key=lambda kv: -kv[1][1])}

    print("\npar commune (oui/total) :")
    for k, (o, t) in taux("commune").items():
        print(f"  {k:24s} {o:5d}/{t:5d} ({100*o/t:5.1f} %)")
    print("par famille de zone :")
    for k, (o, t) in taux("zone_fam").items():
        print(f"  {k:10s} {o:5d}/{t:5d} ({100*o/t:5.1f} %)")
    print("par type de projet :")
    for k, (o, t) in taux("type_projet").items():
        print(f"  {k:22s} {o:5d}/{t:5d} ({100*o/t:5.1f} %)")
    print("causes des « non » (direct) :")
    for c, v in Counter(r["direct_causes_non"] for r in non).most_common(15):
        print(f"  {v:5d}  {c[:110]}")

    ech = non if len(non) <= 60 else sorted(
        non, key=lambda r: hashlib.md5((r["permit_id"] + GRAINE).encode()).hexdigest())[:60]
    with open(COHORTES / "TEST1-NON-60.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ech[0]) if ech else ["permit_id"])
        w.writeheader()
        w.writerows(ech)
    print(f"échantillon de relecture : {len(ech)} permis → TEST1-NON-60.csv (graine {GRAINE})")

    # ── TEST 2 — H mono-parcelle ────────────────────────────────────────────────────────
    t2 = []
    for p in h:
        if p["mono"] != "t":
            continue
        idu = p["idus"].strip()
        c = cache(idu)
        if c is None:
            continue
        aut = float(p["surf_hab"] or 0) * COEF_PLANCHER
        est = float(c.get("sdp_max_m2") or 0)
        emp = c.get("emprise_constructible_m2")
        niv = c.get("niveaux_max")
        env = (float(emp) * int(niv)) if (emp is not None and niv) else None
        t2.append({
            "permit_id": p["permit_id"], "insee": p["insee"], "commune": p["commune"],
            "d_aut": p["d_aut"], "type_projet": p["type_projet"], "idu": idu,
            "zone": c.get("zone"), "zone_fam": c.get("zone_fam"),
            "constructible_direct": bool(c.get("constructible")),
            "nb_lgt": p["nb_lgt"], "surf_hab": p["surf_hab"],
            "aut_plancher_m2": round(aut), "estimation_m2": round(est),
            "emprise_constructible_m2": emp, "niveaux_max": niv,
            "enveloppe_max_m2": round(env) if env is not None else "",
            "ratio_aut_estimation": round(aut / est, 3) if est > 0 else "",
            "ratio_aut_enveloppe": round(aut / env, 3) if env else "",
        })
    with open(COHORTES / "TEST2-ENVELOPPE.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(t2[0]))
        w.writeheader()
        w.writerows(t2)

    def dist(vals, titre):
        vals = sorted(v for v in vals if v)
        if not vals:
            print(f"{titre} : aucune valeur")
            return
        q = statistics.quantiles(vals, n=20)
        print(f"{titre} : n={len(vals)} méd={statistics.median(vals):.2f} "
              f"Q1={q[4]:.2f} Q3={q[14]:.2f} p90={q[17]:.2f} p95={q[18]:.2f} max={vals[-1]:.2f}")

    mesurables = [r for r in t2 if r["ratio_aut_enveloppe"] != ""]
    print(f"\nTEST 2 — H mono-parcelle : {len(t2)} permis, enveloppe mesurable {len(mesurables)}")
    dist([r["ratio_aut_estimation"] for r in t2 if r["ratio_aut_estimation"] != ""],
         "ratio autorisé / estimation rapide")
    dist([r["ratio_aut_enveloppe"] for r in mesurables], "ratio autorisé / enveloppe max")
    dep = [r for r in mesurables if float(r["ratio_aut_enveloppe"]) > SEUIL_DEPASSEMENT]
    print(f"dépassements de l'enveloppe max (> {SEUIL_DEPASSEMENT}) : {len(dep)}/{len(mesurables)} "
          f"({100*len(dep)/max(1,len(mesurables)):.1f} %)")
    top40 = sorted(dep, key=lambda r: -float(r["ratio_aut_enveloppe"]))[:40]
    with open(COHORTES / "TEST2-DEPASSEMENTS-40.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(t2[0]))
        w.writeheader()
        w.writerows(top40)
    print("→ TEST2-DEPASSEMENTS-40.csv")

    print("\nestimation rapide vs réalisé, par type de projet (ratio aut/est) :")
    for typ in ("individuel", "collectif_ou_groupe"):
        vals = [float(r["ratio_aut_estimation"]) for r in t2
                if r["type_projet"] == typ and r["ratio_aut_estimation"] != ""]
        if vals:
            dist(vals, f"  {typ}")


if __name__ == "__main__":
    main()
