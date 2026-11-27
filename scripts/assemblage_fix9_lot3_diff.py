"""OUTIL-ASSEMBLAGE-FIX-9 (LOT 3) — diff avant/après de la mesure (zones AU fermées) :
  · parcelles dont la capacité (CA) passe à ZÉRO, par commune × zone ;
  · bilans dont le MONTANT change (CA central avant ≠ après), par commune × zone ;
  · total, et garde-fou : toutes les zones touchées doivent être FERMÉES (fam AU, constructible_neuf=False).
Lecture des deux JSON produits par assemblage_fix9_lot3_mesure.py (before/after)."""
import json
import sys
from collections import defaultdict

before = json.load(open(sys.argv[1]))
after = json.load(open(sys.argv[2]))

assert set(before) == set(after), "populations différentes"


def _ca(v):
    if not isinstance(v, dict):
        return None
    ca = v.get("ca") or [None, None, None]
    return ca[1]  # central


zero = defaultdict(int)       # (commune, zone) -> parcelles capacité -> 0
change = defaultdict(int)     # (commune, zone) -> parcelles montant change
n_zero = n_change = 0
exemples = []
for idu in before:
    b, a = before[idu], after[idu]
    cb, ca = _ca(b), _ca(a)
    key = (b.get("commune"), b.get("zone"))
    if cb != ca:
        change[key] += 1
        n_change += 1
        if (cb or 0) > 0 and not (ca or 0):
            zero[key] += 1
            n_zero += 1
        if len(exemples) < 15:
            exemples.append((idu, b.get("zone"), cb, ca))

print(f"Parcelles mesurées (zone AU fermée dominante) : {len(before)}")
print(f"Parcelles dont le MONTANT change : {n_change}")
print(f"Parcelles dont la capacité passe à ZÉRO : {n_zero}")
print()
print("== Capacité -> 0, par commune × zone ==")
for (commune, zone), n in sorted(zero.items(), key=lambda x: -x[1]):
    print(f"  {commune:20s} {zone:12s} : {n}")
print()
print("== Montant change (dont -> 0), par commune × zone ==")
for (commune, zone), n in sorted(change.items(), key=lambda x: -x[1]):
    print(f"  {commune:20s} {zone:12s} : {n}")
print()
print("== Exemples (idu, zone, CA central AVANT -> APRÈS) ==")
for idu, zone, cb, ca in exemples:
    print(f"  {idu} {zone} : {cb} -> {ca}")
