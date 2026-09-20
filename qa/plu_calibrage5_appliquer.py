"""PLU-CALIBRAGE-5 — APPLIQUE les décisions de relecture (lots 2/4) aux YAML plu_destinations.

Lit les fichiers de décision (un par commune) produits par les agents de relecture et écrit, pour
chaque feuille tranchée, son nouveau statut dans le YAML — SANS jamais toucher à la preuve
(article/page/citation restent la trace) ni au reste du fichier (`X._ecrire_regles`).

Gestes appliqués : `valider` (statut→valide, valeur inchangée) · `corriger` (pose la valeur
corrigée puis valide) · `absent` (retire la valeur, `absent: true`, valide = silence prouvé).
`formule` et `propose` ne sont PAS appliqués ici (formule → lot 3 ; propose → reste propose).

GARDE ANTI-INVENTION : un `valider`/`corriger` n'est appliqué que si le nombre décidé apparaît
LITTÉRALEMENT dans la `preuve` citée par l'agent. Sinon la décision est REFUSÉE et listée.

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage5_appliquer.py <dossier_decisions> [--dry]
"""
from __future__ import annotations

import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path

from labuse.plu import destinations as D
from labuse.plu import extraction as X
from labuse.plu import revue as R

_VAL_KEYS = ("m", "r_plus", "pct", "m2", "min_m", "places", "par_m2", "detail", "formule",
             "seuil_logements", "seuil_m2", "quota_pct", "portee")


def _num_dans_preuve(val, preuve: str) -> bool:
    """Le nombre `val` apparaît-il comme un TOKEN dans la preuve (70 ∈ « 70% », pas ∈ « 170 ») ?"""
    preuve = preuve or ""
    s = str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
    cands = {s}
    if "." in s:
        cands.add(s.replace(".", ","))          # 7.5 → « 7,5 »
    return any(re.search(rf"(?<!\d){re.escape(c)}(?!\d)", preuve) for c in cands)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    dec_dir = Path(args[0]) if args else Path("captures/plu-calibrage5/b_decisions")
    counts: Counter = Counter()
    refuses: list[str] = []
    applied_log: list[dict] = []
    for f in sorted(dec_dir.glob("974??.json")):
        dec = json.loads(f.read_text(encoding="utf-8"))
        insee = dec["insee"]
        path = D._fichier_commune(insee)
        if path is None:
            print(f"!! {insee} non calibrée"); continue
        # zones touchées par un geste applicable
        applicables = [d for d in dec["decisions"] if d["geste"] in ("valider", "corriger", "absent")]
        for d in dec["decisions"]:
            counts[d["geste"]] += 1
        zones_touchees = {d["zone"] for d in applicables}
        regles_par_zone = {z: r for z, r in R._zones_avec_regles(insee, list(zones_touchees))}
        ecrire: dict[str, dict] = {}
        for d in applicables:
            zone, chemin, geste = d["zone"], d["chemin"], d["geste"]
            regles = regles_par_zone.get(zone)
            if regles is None:
                refuses.append(f"{insee} {zone} {chemin} : zone introuvable"); counts["REFUS"] += 1; continue
            parts = chemin.split(".")
            leaf = regles.get(parts[0]) if len(parts) == 1 else (regles.get(parts[0]) or {}).get(parts[1])
            if not isinstance(leaf, dict):
                refuses.append(f"{insee} {zone} {chemin} : feuille introuvable"); counts["REFUS"] += 1; continue
            if geste in ("valider", "corriger"):
                if not d.get("valeur"):
                    refuses.append(f"{insee} {zone} {chemin} : valeur manquante"); counts["REFUS"] += 1; continue
                # garde : TOUTE valeur numérique décidée (min_m, pct, places…) doit être littéralement
                # dans la preuve. La `formule` (texte) n'est pas soumise au contrôle numérique.
                nums = [v for v in d["valeur"].values() if isinstance(v, (int, float))]
                manque = next((v for v in nums if not _num_dans_preuve(v, d.get("preuve", ""))), None)
                if manque is not None:
                    refuses.append(f"{insee} {zone} {chemin} {geste} : « {manque} » absent de la preuve « {str(d.get('preuve'))[:60]} »")
                    counts["REFUS"] += 1; continue
                val = nums[0] if nums else next(iter(d["valeur"].values()))
                # valider ET corriger posent la valeur décidée (pour valider = valeur confirmée,
                # idempotent ; pour une formule = min_m + formule nouvellement encodés).
                for k, v in d["valeur"].items():
                    leaf[k] = v
                # « chaque décision porte sa citation » : si la citation stockée ne contient pas la
                # valeur décidée (cas des renvois 1AU→U lus ailleurs dans le PDF, ou d'un écart
                # harmonisé), on grave la PREUVE vérifiée comme citation — plus jamais un `valide`
                # dont le texte ne porte pas sa valeur. Article + page (locateurs) conservés.
                if not _num_dans_preuve(val, str(leaf.get("citation") or "")) and d.get("preuve"):
                    leaf["citation"] = d["preuve"]
                leaf["statut"] = "valide"
            elif geste == "absent":
                for k in _VAL_KEYS:
                    leaf.pop(k, None)
                leaf["absent"] = True
                if d.get("preuve"):                 # citation = la preuve du SILENCE (« non réglementé »)
                    leaf["citation"] = d["preuve"]
                leaf["statut"] = "valide"
            ecrire[zone] = regles
            applied_log.append({"insee": insee, "zone": zone, "chemin": chemin, "geste": geste,
                                "valeur": d.get("valeur"), "preuve": d.get("preuve")})
        if ecrire and not dry:
            X._ecrire_regles(path, ecrire)
    print(f"décisions lues : {dict(counts)}")
    print(f"appliquées : {len(applied_log)}" + (" (DRY-RUN, rien écrit)" if dry else ""))
    if refuses:
        print(f"REFUSÉES (garde anti-invention) : {len(refuses)}")
        for r in refuses[:30]:
            print("  ✗", r)
    Path("captures/plu-calibrage5/applied_log.json").write_text(
        json.dumps(applied_log, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
