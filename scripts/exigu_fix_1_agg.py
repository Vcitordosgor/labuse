#!/usr/bin/env python
"""EXIGU-FIX-1 — agrège les JSONL de mesure en diagnostic + avant/après (lecture seule, stdout)."""
import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
from sqlalchemy import text                                           # noqa: E402
from labuse.db import session_scope                                   # noqa: E402

POP = sys.argv[1] if len(sys.argv) > 1 else "gt1000"
rows = []
for fp in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "reports", "data",
                                         f"exigu_mesure_{POP}_*.jsonl"))):
    with open(fp) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
print(f"# population={POP} — {len(rows)} parcelles terrain_exigu(OFF)\n")

# géométrie (valide / multipolygone) en un coup
pids = [r["pid"] for r in rows]
geo = {}
if pids:
    with session_scope() as s:
        for pid, valid, ng in s.execute(text(
                "SELECT id, ST_IsValid(geom_2975), ST_NumGeometries(geom_2975) "
                "FROM parcels WHERE id = ANY(:ids)"), {"ids": pids}):
            geo[pid] = (bool(valid), int(ng or 1))
for r in rows:
    v, ng = geo.get(r["pid"], (True, 1))
    r["geom_valide"], r["ngeom"] = v, ng

RAISON_FAMILLE = {
    "reculs": "reculs (tous côtés / forme très découpée)",
    "portion_reduite": "portion U/AU réduite",
    "ppr_rouge": "contraintes superposées (PPR rouge)",
    "hors_rouge_trop_petit": "contraintes superposées (hors rouge < 200 m²)",
    "hors_rouge_sans_acces": "contraintes superposées (hors rouge enclavé)",
    "hors_rouge_invalide": "géométrie invalide (découpe hors rouge)",
    "ebc": "contraintes superposées (EBC)",
    "emplacement_reserve": "contraintes superposées (ER)",
    "contraintes": "contraintes superposées (PEB/DPF/ravine/50 pas)",
}


def cat(r):
    if not r["geom_valide"]:
        return "géométrie invalide"
    if r["raison_off"] == "reculs" and r["ngeom"] > 1:
        return "multipolygone (reculs sur morceaux disjoints)"
    return RAISON_FAMILLE.get(r["raison_off"], f"autre ({r['raison_off']})")


def after(r):
    """État APRÈS servi par le moteur (autoritaire) = cause_on. None→régain capacité ;
    terrain_exigu→reste exigu (preuve) ; assiette_a_verifier→à vérifier ; autre→reclassé."""
    c = r["cause_on"]
    if c is None:
        return "regain"
    if c == "terrain_exigu":
        return "exigu"
    if c == "assiette_a_verifier":
        return "verifier"
    return f"autre:{c}"


# ── DIAGNOSTIC : par cause de contour vide, avec décision du fix ──
by = defaultdict(list)
for r in rows:
    by[cat(r)].append(r)
print("## Diagnostic — pourquoi le contour après reculs est vide (+ ce que le fix en fait)\n")
print("| cause du contour vide | n | régain | exigu(preuve) | à vérifier |")
print("|---|--:|--:|--:|--:|")
for c in sorted(by, key=lambda k: -len(by[k])):
    g = by[c]
    d = defaultdict(int)
    for r in g:
        d[after(r)] += 1
    print(f"| {c} | {len(g)} | {d['regain']} | {d['exigu']} | {d['verifier']} |")
print()
for c in sorted(by, key=lambda k: -len(by[k])):
    ex = sorted(by[c], key=lambda r: -r["surf"])[:3]
    print(f"- **{c}** — ex. " + " · ".join(
        f"{r['idu']} ({r['surf']} m²→{after(r)})" for r in ex))
print()

# ── AVANT/APRÈS par tranche de surface ──
TR = [(1000, 2000), (2000, 5000), (5000, 10000), (10000, 10**12)]
print("## Avant / après — par tranche de surface\n")
print("| tranche | n exigu(avant) | régain capacité | reste exigu (preuve) | à vérifier |")
print("|---|--:|--:|--:|--:|")
tot = defaultdict(int)
for lo, hi in TR:
    g = [r for r in rows if lo <= r["surf"] < hi]
    d = defaultdict(int)
    for r in g:
        d[after(r)] += 1
        tot[after(r)] += 1
    lbl = f">{lo}" if hi > 10**11 else f"{lo}–{hi}"
    print(f"| {lbl} m² | {len(g)} | {d['regain']} | {d['exigu']} | {d['verifier']} | ")
print(f"| **total** | **{len(rows)}** | **{tot['regain']}** | **{tot['exigu']}** | "
      f"**{tot['verifier']}** |")
print()

# ── GARANTIE : aucun > 1000 m² « trop étroit » servi sans preuve géométrique ──
# « trop étroit » = cause SERVIE (cause_on) terrain_exigu AVEC raison reculs. Le moteur ne conserve
# terrain_exigu QUE si son ré-examen a renvoyé 'exigu' (régain→cause None, doute→assiette_a_verifier) :
# la conservation EST la preuve. On recoupe néanmoins avec les métriques enregistrées (arrondies).
etroit = [r for r in rows if r["cause_on"] == "terrain_exigu" and r["raison_on"] == "reculs"]
exigu_tot = [r for r in rows if r["cause_on"] == "terrain_exigu"]
# arrondi JSONL : net_larg est arrondi à 0,1 → tolérance au seuil 3,0 (preuve réelle à 2,97 etc.).
sans_preuve = [r for r in etroit if not (r["net_m2"] < 5 or r["net_larg"] <= 3.0
                                         or (not r["has_net"] and 0 < r["parc_larg"] < 7))]
print(f"## Garantie > 1000 m²\n")
print(f"- parcelles restant `terrain_exigu` servi : {len(exigu_tot)} "
      f"(toutes conservées par le ré-examen géométrique du moteur = preuve par construction)")
print(f"- dont libellé « trop étroit » (raison reculs) : {len(etroit)}")
print(f"- dont SANS trace de preuve dans les métriques (arrondi inclus) : **{len(sans_preuve)}** (doit être 0)")
for r in sans_preuve[:10]:
    print(f"  - {r['idu']} {r['surf']} m² net={r['net_m2']} larg={r['net_larg']} parc={r['parc_larg']}")

# ── liste des IDU à recalculer (régain + à vérifier = cause change) ──
change = [r for r in rows if after(r) in ("regain", "verifier")]
outids = os.path.join(os.path.dirname(__file__), "..", "reports", "data", f"exigu_a_recalculer_{POP}.txt")
with open(outids, "w") as fh:
    for r in sorted(rows, key=lambda r: r["idu"]):
        fh.write(r["idu"] + "\n")
print(f"\n## {len(rows)} IDU terrain_exigu à recalculer → {os.path.basename(outids)} "
      f"(dont {len(change)} changent de verdict)")
