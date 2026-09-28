#!/usr/bin/env python
"""PLU-VERIF-1 Lot C — applique les corrections de statut/référence/note aux YAML calibrés.

Édition CHIRURGICALE (préserve commentaires, ordre, citations) : on localise la feuille
(zone → regles → rubrique[.sous]) par indentation et on ne touche qu'aux champs visés.

  FAUSSE     → statut: propose  + note (valeur lue au PDF, pour la recalibration)
  MAUV_REF   → page_pdf corrigée + note de traçabilité
  EXCEPTION  → note (texte de l'exception à afficher sous le « i » de la fiche)

Ne CHANGE JAMAIS une valeur chiffrée (m/pct/places). Usage :
  python appliquer_lotC.py <insee>        # applique pour une commune
  python appliquer_lotC.py --tous         # toutes
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEST = REPO / "config" / "plu_destinations"
COR = REPO / "docs/audit-2026-09/PLU-VERIF-1/corrections_lotC.json"

FILES = {p.name[:5]: p for p in DEST.glob("974??_*.yaml")}


def _q(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip()).replace('"', "'")
    return '"' + s + '"'


def _leaf_range(lines, zone, chemin):
    """(début_champs, fin_champs, indent_champs) de la feuille, ou None."""
    parts = chemin.split(".")
    def find_key(key, indent, lo, hi):
        pat = re.compile(r"^" + " " * indent + re.escape(key) + r":\s*$")
        for i in range(lo, hi):
            if pat.match(lines[i]):
                return i
        return None
    def block_end(start, indent, hi):
        for j in range(start + 1, hi):
            if lines[j].strip() and (len(lines[j]) - len(lines[j].lstrip())) <= indent \
                    and not lines[j].lstrip().startswith("#"):
                return j
        return hi
    n = len(lines)
    zi = find_key(zone, 2, 0, n)
    if zi is None:
        return None
    ze = block_end(zi, 2, n)
    ri = find_key("regles", 4, zi + 1, ze)
    if ri is None:
        return None
    re_end = block_end(ri, 4, ze)
    rub_i = find_key(parts[0], 6, ri + 1, re_end)
    if rub_i is None:
        return None
    if len(parts) == 1:  # rubrique plate (mixite) : feuille = rubrique, champs à 8
        return rub_i + 1, block_end(rub_i, 6, re_end), 8
    rub_end = block_end(rub_i, 6, re_end)
    sous_i = find_key(parts[1], 8, rub_i + 1, rub_end)
    if sous_i is None:
        return None
    return sous_i + 1, block_end(sous_i, 8, rub_end), 10


def _set_field(lines, lo, hi, indent, field, value):
    pat = re.compile(r"^(" + " " * indent + re.escape(field) + r"):\s*.*$")
    for i in range(lo, hi):
        if pat.match(lines[i]):
            lines[i] = " " * indent + f"{field}: {value}"
            return 0  # remplacé, delta lignes = 0
    lines.insert(hi, " " * indent + f"{field}: {value}")
    return 1  # inséré


def appliquer(insee, cors, dry=False):
    path = FILES[insee]
    lines = path.read_text(encoding="utf-8").split("\n")
    faits = {"FAUSSE": 0, "MAUV_REF": 0, "EXCEPTION": 0, "RATE": 0}
    detail = []
    for c in cors:
        rng = _leaf_range(lines, c["zone"], c["regle"])
        if rng is None:
            faits["RATE"] += 1
            detail.append(f"RATÉ {c['zone']} {c['regle']} (feuille introuvable)")
            continue
        lo, hi, ind = rng
        act = c["action"]
        if act == "FAUSSE":
            _set_field(lines, lo, hi, ind, "statut", "propose")
            rng = _leaf_range(lines, c["zone"], c["regle"]); lo, hi, ind = rng
            note = (f"PLU-VERIF-1 : valeur passée en propose (non servie) — lue au PDF : "
                    f"{c.get('valeur_lue') or '?'}. {c.get('preuve') or ''}")
            _set_field(lines, lo, hi, ind, "note", _q(note))
            faits["FAUSSE"] += 1
        elif act == "MAUV_REF":
            m = re.search(r"\d+", str(c.get("page_correcte") or ""))
            if not m:
                faits["RATE"] += 1; continue
            newp = int(m.group())
            _set_field(lines, lo, hi, ind, "page_pdf", newp)
            rng = _leaf_range(lines, c["zone"], c["regle"]); lo, hi, ind = rng
            note = (f"PLU-VERIF-1 : page corrigée {c.get('page')}→{newp} "
                    f"(art. {c.get('article_correct') or c.get('article')}).")
            _set_field(lines, lo, hi, ind, "note", _q(note))
            faits["MAUV_REF"] += 1
        elif act == "EXCEPTION":
            note = "PLU-VERIF-1 (exception à afficher) : " + (c.get("exception") or "")
            _set_field(lines, lo, hi, ind, "note", _q(note))
            faits["EXCEPTION"] += 1
    if not dry:
        path.write_text("\n".join(lines), encoding="utf-8")
    return faits, detail


def main():
    cor = json.load(open(COR))
    dry = "--dry" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--tous" in sys.argv:
        communes = sorted(FILES)
    else:
        communes = args
    par_ins = {}
    for c in cor:
        par_ins.setdefault(c["insee"], []).append(c)
    tot = {"FAUSSE": 0, "MAUV_REF": 0, "EXCEPTION": 0, "RATE": 0}
    for insee in communes:
        cors = par_ins.get(insee, [])
        if not cors:
            continue
        faits, detail = appliquer(insee, cors, dry=dry)
        for k in tot:
            tot[k] += faits[k]
        print(f"{insee} {FILES[insee].name:35} {faits}")
        for d in detail:
            print("   ", d)
    print("TOTAL", tot, "(dry-run)" if dry else "")


if __name__ == "__main__":
    main()
