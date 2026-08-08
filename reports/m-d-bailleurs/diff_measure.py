"""M-D — mesure du diff avant/après resserrement du pattern bailleur.

Rejoue la NOUVELLE classify_owner (constantes resserrées) sur toutes les parcelles de
personne morale et compare au owner_type STOCKÉ (ancien) dans parcel_v_score. Aucune
écriture — mesure pure. Le run V réel persistera ensuite le même résultat.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict

from sqlalchemy import create_engine, text

from labuse.scoring.score_v import classify_owner
from labuse.connectors.recherche_entreprises import parse_result

url = os.environ["LABUSE_DATABASE_URL"]
eng = create_engine(url)

with eng.connect() as c:
    # fiches d'enrichissement par siren (nature_juridique sert au repli public/copro)
    fiches: dict[str, dict] = {}
    for siren, payload in c.execute(text("SELECT siren, payload FROM owner_enrichment")):
        if payload:
            fiches[siren] = parse_result(payload if isinstance(payload, dict) else json.loads(payload))

    # toutes les parcelles PM avec leur type stocké (= ancien classement) et le siren résolu stocké
    rows = c.execute(text(
        """SELECT pm.idu, pm.groupe, pm.denomination, v.owner_siren, v.owner_type
             FROM parcelle_personne_morale pm
             JOIN parcel_v_score v ON v.parcelle_id = pm.idu""")).all()

transitions = Counter()               # (old, new) -> n
moved_denoms = defaultdict(Counter)   # denomination -> Counter((old,new))
old_dist, new_dist = Counter(), Counter()

for idu, groupe, denom, siren, old_type in rows:
    link = {"groupe": groupe, "denomination": denom}
    fiche = fiches.get(siren) if siren else None
    new_type = classify_owner(link, siren, fiche)
    old_dist[old_type] += 1
    new_dist[new_type] += 1
    if new_type != old_type:
        transitions[(old_type, new_type)] += 1
        moved_denoms[denom][(old_type, new_type)] += 1

print("=== Parcelles PM analysées :", len(rows), "===\n")
print("--- Distribution owner_type (PM uniquement) : AVANT -> APRÈS ---")
for t in sorted(set(old_dist) | set(new_dist)):
    print(f"  {t:10s} {old_dist[t]:7d} -> {new_dist[t]:7d}  ({new_dist[t]-old_dist[t]:+d})")

print("\n--- Transitions (old -> new) : total rows déplacées ---")
if not transitions:
    print("  AUCUNE")
for (o, n), k in transitions.most_common():
    print(f"  {o:10s} -> {n:10s} : {k}")

print("\n--- Détail par dénomination déplacée ---")
for denom, ctr in sorted(moved_denoms.items(), key=lambda kv: -sum(kv[1].values())):
    for (o, n), k in ctr.items():
        print(f"  {k:4d}  {o} -> {n}   « {denom} »")
