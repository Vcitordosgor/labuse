"""PLU-CALIBRAGE-7 — APPLIQUE aux YAML plu_destinations les deux formes de règle ajoutées au schéma.

Lit `/tmp/plu7_out/form1.json` (recul « à l'alignement ») et `/tmp/plu7_out/form2.json` (pleine terre
composée), écrit pour chaque feuille retenue :
  · forme 1 `validee_alignement` : `retraits.<feuille> = {min_m: 0, forme: alignement, article, page,
    citation, statut: valide}` — recul 0 EXPLICITE, ≠ absent ;
  · forme 2 `validee_composee` : `pleine_terre.pct = {espaces_verts_pct: X, pleine_terre_part: Y,
    article, page, citation, statut: valide}` — le `pct` dérivé n'est PAS stocké (le moteur calcule) ;
  · `absent` : retire la valeur, `absent: true`, valide ; `propose` : NON appliqué.

GARDE ANTI-INVENTION : forme 1 → « alignement »/« limite séparative » littéral dans la citation ;
forme 2 → X ET Y littéraux dans la citation. Sinon REFUS + liste.

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage7_appliquer.py [--dry]
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from labuse.plu import destinations as D
from labuse.plu import extraction as X
from labuse.plu import revue as R

_VAL_KEYS = ("m", "r_plus", "pct", "m2", "min_m", "places", "par_m2",
             "espaces_verts_pct", "pleine_terre_part", "forme")


def _num_litteral(val, preuve: str) -> bool:
    preuve = preuve or ""
    s = str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
    cands = {s} | ({s.replace(".", ",")} if "." in s else set())
    return any(re.search(rf"(?<!\d){re.escape(c)}(?!\d)", preuve) for c in cands)


def main() -> int:
    dry = "--dry" in sys.argv
    form1 = json.loads(Path("/tmp/plu7_out/form1.json").read_text(encoding="utf-8"))
    form2 = json.loads(Path("/tmp/plu7_out/form2.json").read_text(encoding="utf-8"))
    counts: Counter = Counter()
    refuses: list[str] = []
    applied: list[dict] = []
    par_ins: dict[str, list] = defaultdict(list)
    for d in form1 + form2:
        par_ins[d["id"].split("|")[0]].append(d)
        counts[d["decision"]] += 1

    for insee, decs in sorted(par_ins.items()):
        path = D._fichier_commune(insee)
        if path is None:
            print(f"!! {insee} non calibrée"); continue
        appl = [d for d in decs if d["decision"] in ("validee_alignement", "validee_composee", "absent")]
        zones = {d["zone"] for d in appl}
        regles_par_zone = {z: r for z, r in R._zones_avec_regles(insee, list(zones))}
        ecrire: dict[str, dict] = {}
        for d in appl:
            zone, champ, dec = d["zone"], d["champ"], d["decision"]
            regles = regles_par_zone.get(zone)
            if regles is None:
                refuses.append(f"{insee} {zone} {champ} : zone introuvable"); counts["REFUS"] += 1; continue
            parts = champ.split(".")
            leaf = (regles.get(parts[0]) or {}).get(parts[1]) if len(parts) == 2 else regles.get(parts[0])
            if not isinstance(leaf, dict):
                refuses.append(f"{insee} {zone} {champ} : feuille introuvable"); counts["REFUS"] += 1; continue
            cit = d.get("citation") or ""
            if dec == "validee_alignement":
                if not re.search(r"alignement|limite séparative", cit, re.I):
                    refuses.append(f"{insee} {zone} {champ} : « alignement/limite » absent de la citation")
                    counts["REFUS"] += 1; continue
                for k in _VAL_KEYS:
                    leaf.pop(k, None)
                leaf["min_m"] = 0
                leaf["forme"] = "alignement"
            elif dec == "validee_composee":
                Xv, Yv = d.get("espaces_verts_pct"), d.get("pleine_terre_part")
                if not (isinstance(Xv, (int, float)) and isinstance(Yv, (int, float))):
                    refuses.append(f"{insee} {zone} {champ} : X/Y non numériques"); counts["REFUS"] += 1; continue
                if not (_num_litteral(Xv, cit) and _num_litteral(Yv, cit)):
                    refuses.append(f"{insee} {zone} {champ} : X={Xv} ou Y={Yv} absent de la citation")
                    counts["REFUS"] += 1; continue
                for k in _VAL_KEYS:
                    leaf.pop(k, None)
                leaf["espaces_verts_pct"] = int(Xv) if float(Xv).is_integer() else Xv
                leaf["pleine_terre_part"] = int(Yv) if float(Yv).is_integer() else Yv
            elif dec == "absent":
                for k in _VAL_KEYS:
                    leaf.pop(k, None)
                leaf["absent"] = True
            if d.get("article"):
                leaf["article"] = d["article"]
            if d.get("page_pdf"):
                leaf["page_pdf"] = d["page_pdf"]
            leaf["citation"] = cit
            leaf.pop("raison", None)
            leaf["statut"] = "valide"
            ecrire[zone] = regles
            applied.append({"insee": insee, "zone": zone, "champ": champ, "decision": dec})
        if ecrire and not dry:
            X._ecrire_regles(path, ecrire)

    print(f"décisions lues : {dict(counts)}")
    print(f"appliquées : {len(applied)}" + (" (DRY-RUN, rien écrit)" if dry else ""))
    if refuses:
        print(f"REFUSÉES : {len(refuses)}")
        for r in refuses:
            print("  ✗", r)
    Path("captures/plu-calibrage7").mkdir(parents=True, exist_ok=True)
    Path("captures/plu-calibrage7/applied_log.json").write_text(
        json.dumps(applied, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
