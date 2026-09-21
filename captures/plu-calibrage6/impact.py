"""PLU-CALIBRAGE-6 §4 — MESURE D'IMPACT (lecture seule, aucune écriture).

Compare, parcelle par parcelle sur un échantillon REPRODUCTIBLE, la capacité résiduelle calculée :
  · ÉTAT A (avant) : `_val` lit les valeurs `propose` (comportement d'origine, sans garde) ;
  · ÉTAT C (après) : garde PLU-CALIBRAGE-6 (validées-only + zone à règle SDP propose → non
    calculable) + les 72 validations déjà appliquées au YAML.

Les deux états sont calculés dans le MÊME process (monkeypatch pour l'état A), sur le YAML final.
On isole ainsi l'effet de la GARDE : quelles parcelles passent NON CALCULABLES (« règle PLU non
validée »), lesquelles changent de valeur (corrections), lesquelles sont inchangées.

Usage : LABUSE_DATABASE_URL=postgresql+psycopg:///labuse \
        PYTHONPATH=src .venv/bin/python captures/plu-calibrage6/impact.py [--par-zone N]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite import zonage as Z
from labuse.faisabilite.residuel import compute_residuel

PAR_ZONE = 40
if "--par-zone" in sys.argv:
    PAR_ZONE = int(sys.argv[sys.argv.index("--par-zone") + 1])

AFF = json.load(open("/tmp/plu6_affected_zones.json"))
NC_ZONES = {tuple(x) for x in AFF["nc_zones"]}
CORR_ZONES = {tuple(x) for x in AFF["corriger_sdp_zones"]}
ZONES = NC_ZONES | CORR_ZONES


# ── comportement d'ORIGINE (état A) ─────────────────────────────────────────────────────────────
def _val_old(reg, rub, feuille, cle):
    leaf = (reg.get(rub) or {}).get(feuille) if rub in reg else None
    if not isinstance(leaf, dict) or leaf.get("absent") or leaf.get("plage"):
        return None
    v = leaf.get(cle)
    if v is None:
        return Z.A_VERIFIER if leaf.get("statut") == "propose" else None
    return float(v) if isinstance(v, (int, float)) else v


import re as _re


def _stat_old(reg):
    leaf = (reg.get("stationnement") or {}).get("par_logement")
    if not isinstance(leaf, dict) or leaf.get("absent"):
        return None
    p = leaf.get("places")
    if isinstance(p, (int, float)):
        p = int(p) if float(p).is_integer() else p
        return f"{p} place / logement" if p == 1 else f"{p} places / logement"
    if _re.search(r"exempt|aucune place", leaf.get("raison") or "", _re.I):
        return "exempté : aucune place imposée"
    return Z.A_VERIFIER if leaf.get("statut") == "propose" else None


def _patch_old():
    Z._val = _val_old
    Z._stat_from_regles = _stat_old
    Z._regles_sdp_non_validees = lambda reg: []      # pas de routage « non calculable »
    Z._calibrage_overlay.cache_clear()


def _restore_new(orig):
    Z._val, Z._stat_from_regles, Z._regles_sdp_non_validees = orig
    Z._calibrage_overlay.cache_clear()


def _etat(session, pid):
    d = compute_residuel(session, pid)
    if d.get("disponible"):
        return ("compute", d.get("sdp_residuelle_m2"))
    return ("nc", d.get("cause"))


def main():
    orig = (Z._val, Z._stat_from_regles, Z._regles_sdp_non_validees)
    par_commune = defaultdict(lambda: defaultdict(int))   # commune -> transition -> n (échantillon)
    detail_cause = defaultdict(int)
    # extrapolation : par commune, somme sur zones de (taux newly_nc du sample) × (taille zone)
    extrap = defaultdict(lambda: {"newly_nc_est": 0.0, "total_zone": 0})
    n_total = 0
    NEWLY = "A_calc → C_non_calculable (règle non validée)"
    with session_scope() as s:
        for (commune, zone) in sorted(ZONES):
            rows = s.execute(text(
                """SELECT p.id FROM parcel_zone_plu zp JOIN parcels p ON p.idu = zp.idu
                   WHERE p.commune = :c AND zp.zone_lib = :z ORDER BY p.id"""),
                {"c": commune, "z": zone}).scalars().all()
            if not rows:
                continue
            step = max(1, len(rows) // PAR_ZONE)
            sample = rows[::step][:PAR_ZONE]              # échantillon déterministe (id-ordonné)
            newly = 0
            for pid in sample:
                n_total += 1
                cC = _etat(s, pid)                         # état C (nouveau) — fonctions en place
                _patch_old()
                cA = _etat(s, pid)                         # état A (ancien)
                _restore_new(orig)

                if cA[0] == "compute" and cC[0] == "nc" and cC[1] and cC[1].startswith("regle_plu_non_validee"):
                    par_commune[commune][NEWLY] += 1; newly += 1
                elif cA[0] == "compute" and cC[0] == "compute" and cA[1] != cC[1]:
                    par_commune[commune]["capacité changée (valeur corrigée)"] += 1
                elif cA[0] == "compute" and cC[0] == "compute":
                    par_commune[commune]["inchangée (calculée)"] += 1
                elif cA[0] == "nc" and cC[0] == "nc":
                    par_commune[commune]["déjà non calculable (autre cause)"] += 1
                    detail_cause[f"{cA[1]} → {cC[1]}"] += 1
                else:
                    par_commune[commune][f"autre ({cA[0]}:{cA[1]} → {cC[0]}:{cC[1]})"] += 1
            # extrapolation de zone : taux echantillon × taille réelle de la zone
            if zone_is_nc := ((commune, zone) in NC_ZONES):
                extrap[commune]["newly_nc_est"] += (newly / len(sample)) * len(rows)
                extrap[commune]["total_zone"] += len(rows)

    print(f"Échantillon : {n_total} parcelles ({len(ZONES)} zones affectées, "
          f"≤{PAR_ZONE}/zone, id-ordonné déterministe)\n")
    grand = defaultdict(int)
    for commune in sorted(par_commune):
        print(f"## {commune}")
        for trans, n in sorted(par_commune[commune].items(), key=lambda x: -x[1]):
            print(f"   {n:4}  {trans}")
            grand[trans] += n
        print()
    print("## TOTAL échantillon")
    for trans, n in sorted(grand.items(), key=lambda x: -x[1]):
        print(f"   {n:4}  {trans}")
    print("\n## EXTRAPOLATION île (parcelles dominantes des 22 zones NC → « règle non validée »)")
    tot_est = 0
    for commune in sorted(extrap):
        e = extrap[commune]; tot_est += e["newly_nc_est"]
        print(f"   {commune:14} ~{round(e['newly_nc_est']):5} / {e['total_zone']:5} parcelles de zones NC")
    print(f"   {'TOTAL':14} ~{round(tot_est):5} parcelles nouvellement non calculables (estimé)")
    out = {"n_total": n_total, "par_zone": PAR_ZONE,
           "par_commune": {k: dict(v) for k, v in par_commune.items()},
           "total": dict(grand), "transitions_nc": dict(detail_cause),
           "extrapolation": {k: {"newly_nc_est": round(v["newly_nc_est"]),
                                 "total_zone": v["total_zone"]} for k, v in extrap.items()},
           "extrapolation_total": round(tot_est)}
    json.dump(out, open("captures/plu-calibrage6/impact_resultat.json", "w"),
              ensure_ascii=False, indent=1)
    print("\n→ captures/plu-calibrage6/impact_resultat.json")


if __name__ == "__main__":
    main()
