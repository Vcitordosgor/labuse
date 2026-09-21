"""PLU-CALIBRAGE-6 — APPLIQUE aux YAML plu_destinations les décisions de validation des 95 feuilles
`propose` numériques qui nourrissent la SDP (SCORING-5-RETOUR §2).

Lit `/tmp/plu6_decisions_all.json` (sorties des agents + relecture) et écrit, feuille par feuille :
  · `validee` : statut→valide, valeur inchangée, article/page/citation = la preuve retrouvée ;
  · `corriger` : pose la valeur RÉELLE lue au règlement (l'harmonisation était fausse), puis valide,
    article/page/citation = la preuve ;
  · `absent`  : retire la valeur, `absent: true`, valide (silence prouvé), citation = la preuve ;
  · `propose` : NON appliqué (reste propose — citation introuvable/non littérale).

GARDE ANTI-INVENTION (identique PLU-CALIBRAGE-5) : un `validee`/`corriger` n'est écrit que si la
valeur retenue apparaît LITTÉRALEMENT (token) dans la citation. Sinon REFUS + liste.

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage6_appliquer.py [--dry]
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

DECISIONS = Path("/tmp/plu6_decisions_all.json")
_VAL_KEYS = ("m", "r_plus", "pct", "m2", "min_m", "places", "par_m2")
_CLE = {"hauteur.faitage": "m", "hauteur.egout": "m", "emprise_sol.ces": "pct",
        "retraits.voie": "min_m", "retraits.limites_separatives": "min_m",
        "pleine_terre.pct": "pct", "stationnement.par_logement": "places"}


def _num_dans_preuve(val, preuve: str) -> bool:
    preuve = preuve or ""
    s = str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
    cands = {s}
    if "." in s:
        cands.add(s.replace(".", ","))
    return any(re.search(rf"(?<!\d){re.escape(c)}(?!\d)", preuve) for c in cands)


def main() -> int:
    dry = "--dry" in sys.argv
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
    counts: Counter = Counter()
    refuses: list[str] = []
    applied: list[dict] = []
    par_commune: dict[str, list] = defaultdict(list)
    for d in decisions:
        counts[d["decision"]] += 1
        par_commune[d["insee"]].append(d)

    for insee, decs in sorted(par_commune.items()):
        path = D._fichier_commune(insee)
        if path is None:
            print(f"!! {insee} non calibrée"); continue
        applicables = [d for d in decs if d["decision"] in ("validee", "corriger", "absent")]
        zones = {d["zone"] for d in applicables}
        regles_par_zone = {z: r for z, r in R._zones_avec_regles(insee, list(zones))}
        ecrire: dict[str, dict] = {}
        for d in applicables:
            zone, champ, dec = d["zone"], d["champ"], d["decision"]
            regles = regles_par_zone.get(zone)
            if regles is None:
                refuses.append(f"{insee} {zone} {champ} : zone introuvable"); counts["REFUS"] += 1; continue
            parts = champ.split(".")
            leaf = (regles.get(parts[0]) or {}).get(parts[1]) if len(parts) == 2 else regles.get(parts[0])
            if not isinstance(leaf, dict):
                refuses.append(f"{insee} {zone} {champ} : feuille introuvable"); counts["REFUS"] += 1; continue
            if dec in ("validee", "corriger"):
                val = d.get("valeur_retenue")
                if not isinstance(val, (int, float)):
                    refuses.append(f"{insee} {zone} {champ} : valeur_retenue non numérique"); counts["REFUS"] += 1; continue
                if not _num_dans_preuve(val, d.get("citation", "")):
                    refuses.append(f"{insee} {zone} {champ} {dec} : « {val} » absent de la citation")
                    counts["REFUS"] += 1; continue
                leaf[_CLE[champ]] = val
                if d.get("article"):
                    leaf["article"] = d["article"]
                if d.get("page_pdf"):
                    leaf["page_pdf"] = d["page_pdf"]
                if d.get("citation"):
                    leaf["citation"] = d["citation"]
                leaf.pop("raison", None)           # la raison « harmonisation ≠ texte » n'a plus lieu d'être
                leaf["statut"] = "valide"
            elif dec == "absent":
                for k in _VAL_KEYS:
                    leaf.pop(k, None)
                leaf["absent"] = True
                if d.get("citation"):
                    leaf["citation"] = d["citation"]
                if d.get("article"):
                    leaf["article"] = d["article"]
                if d.get("page_pdf"):
                    leaf["page_pdf"] = d["page_pdf"]
                leaf.pop("raison", None)
                leaf["statut"] = "valide"
            ecrire[zone] = regles
            applied.append({"insee": insee, "zone": zone, "champ": champ, "decision": dec,
                            "valeur_retenue": d.get("valeur_retenue")})
        if ecrire and not dry:
            X._ecrire_regles(path, ecrire)

    print(f"décisions lues : {dict(counts)}")
    print(f"appliquées : {len(applied)}" + (" (DRY-RUN, rien écrit)" if dry else ""))
    if refuses:
        print(f"REFUSÉES (garde anti-invention) : {len(refuses)}")
        for r in refuses[:40]:
            print("  ✗", r)
    Path("captures/plu-calibrage6").mkdir(parents=True, exist_ok=True)
    Path("captures/plu-calibrage6/applied_log.json").write_text(
        json.dumps(applied, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
