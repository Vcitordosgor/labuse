"""MOTEUR-VERITE-FIX-4 LOT 3 — injection des FORMULES de retrait relatif manquantes.

Pour TOUTES les zones dont la citation `retraits.limites_separatives` contient un retrait
relatif (H/2, L=H, moitié de la hauteur/différence) SANS `formule` résolue, la formule est
écrite au YAML — le moteur l'exécute alors : référence à l'ÉGOUT prouvée → niveau par niveau ;
sinon référence PRUDENTE faîtage (builder FIX-3 LOT 1). Erreur déjà présente dans MAIN :
Sainte-Marie UAz servait 5 321 m² avec 3 m de retrait pour un R+8 de 27 m (AS1397).

Exclusions motivées :
· 97413 AUe — la citation (mur coupe-feu) n'est PAS un retrait relatif : rien à injecter ;
· 97408 AUAv — classement FAUX (relecture FIX-4) : la règle PROPRE p.68 prescrit 3 m (seuls les
  îlots 10C/8D/5B permettent la limite sous condition de profondeur 10 m) → h_reference égout
  RETIRÉ, aucune formule (le minimum fixe est la règle).

Sortie : docs/audit-2026-11/moteur-verite-fix-1/FORMULES-FIX4.csv (liste complète + décision).

    python docs/audit-2026-11/moteur-verite-fix-1/scripts/injecter_formules_fix4.py
"""
from __future__ import annotations

import csv
import glob
import re
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[4]
OUT = RACINE / "docs" / "audit-2026-11" / "moteur-verite-fix-1" / "FORMULES-FIX4.csv"

PAT_REL = re.compile(
    r"h\s*/\s*2|moiti[ée] de la (hauteur|diff[ée]rence)|L\s*=\s*1?/?2?\s*H|[ée]gale? [àa] la "
    r"moiti[ée]|diff[ée]rence d'altitude|correspondant [àa] la hauteur", re.I)
PAT_LH = re.compile(r"L\s*=\s*H\b|correspondant [àa] la hauteur maximale", re.I)

SKIP = {("97413", "AUe"): "citation « mur coupe-feu » : pas un retrait relatif",
        ("97408", "AUAv"): "règle PROPRE 3 m (p.68) — renvoi faux, h_reference retiré à part"}


def main() -> None:
    rows = []
    for f in sorted(glob.glob(str(RACINE / "config" / "plu_destinations" / "*.yaml"))):
        insee = Path(f).name[:5]
        doc = yaml.safe_load(open(f))
        cibles = []
        for z, zd in ((doc or {}).get("zones") or {}).items():
            leaf = (((zd or {}).get("regles") or {}).get("retraits") or {}).get("limites_separatives")
            if not isinstance(leaf, dict) or leaf.get("statut") != "valide":
                continue
            cit = str(leaf.get("citation") or "")
            for sub in ("implantation_laterales", "implantation_fond"):
                s = leaf.get(sub)
                if isinstance(s, dict):
                    cit += " " + str(s.get("citation") or "")
            if not PAT_REL.search(cit) or str(leaf.get("formule") or "").strip():
                continue
            minm = leaf.get("min_m")
            if (insee, z) in SKIP:
                rows.append({"insee": insee, "zone": z, "decision": "exclue",
                             "formule": "", "motif": SKIP[(insee, z)]})
                continue
            if not isinstance(minm, (int, float)):
                rows.append({"insee": insee, "zone": z, "decision": "exclue",
                             "formule": "", "motif": "min_m absent — formule non chiffrable"})
                continue
            if PAT_LH.search(cit):
                formule = f"L = H, minimum {minm:g} m"
            else:
                formule = f"H/2, minimum {minm:g} m"
            cibles.append((z, formule))
            rows.append({"insee": insee, "zone": z, "decision": "injectee",
                         "formule": formule, "motif": "citation à retrait relatif, formule absente"})
        if not cibles:
            continue
        # insertion TEXTUELLE : `formule:` juste après la ligne `limites_separatives:` du bloc zone
        lines = open(f).readlines()
        out, zone_cur, injected = [], None, set()
        for ln in lines:
            m = re.match(r"^  (\S[^:]*):\s*$", ln)
            if m:
                zone_cur = m.group(1)
            out.append(ln)
            if re.match(r"^        limites_separatives:\s*$", ln):
                for z, formule in cibles:
                    if z == zone_cur and z not in injected:
                        out.append(f"          formule: '{formule}'\n")
                        out.append("          note_fix4: 'MOTEUR-VERITE-FIX-4 LOT 3 : citation à "
                                   "retrait relatif SANS formule résolue (le moteur gardait le "
                                   "minimum) — formule injectée, exécutée à l''égout prouvé ou en "
                                   "référence prudente faîtage.'\n")
                        injected.add(z)
        assert injected == {z for z, _ in cibles}, (f, injected, cibles)
        open(f, "w").writelines(out)
        print(f"{insee} : {sorted(injected)}")
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["insee", "zone", "decision", "formule", "motif"],
                           delimiter=";")
        w.writeheader()
        w.writerows(rows)
    print(f"→ {OUT.name} : {sum(1 for r in rows if r['decision'] == 'injectee')} injectées, "
          f"{sum(1 for r in rows if r['decision'] == 'exclue')} exclues")


if __name__ == "__main__":
    main()
