#!/usr/bin/env python
"""PLU-EXCEPTIONS-1 Lot A — écrit les exceptions verbatim dans les feuilles `regles`.

Pour chaque feuille (zone, regle) JUSTE+exception, insère un bloc `exceptions:` (liste de
{texte, article, page_pdf, porte, modifie_calcul}) et RETIRE la note stopgap PLU-VERIF-1
« (exception à afficher) ». Édition chirurgicale (mêmes repères d'indentation que Lot C).
Le texte est le VERBATIM du règlement, jamais reformulé (garde-fou Lot C).
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEST = REPO / "config" / "plu_destinations"
VB = REPO / "docs/audit-2026-09/PLU-EXCEPTIONS-1/verbatim_agrege.json"
FILES = {p.name[:5]: p for p in DEST.glob("974??_*.yaml")}


def _leaf_range(lines, zone, chemin):
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
    if len(parts) == 1:
        return rub_i + 1, block_end(rub_i, 6, re_end), 8
    rub_end = block_end(rub_i, 6, re_end)
    sous_i = find_key(parts[1], 8, rub_i + 1, rub_end)
    if sous_i is None:
        return None
    return sous_i + 1, block_end(sous_i, 8, rub_end), 10


def _scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return json.dumps(str(v), ensure_ascii=False)  # double-quoted, \" et \\ échappés


def _bloc_exceptions(excs, ind):
    sp = " " * ind
    out = [f"{sp}exceptions:"]
    for e in excs:
        out.append(f"{sp}- texte: {_scalar(e.get('texte'))}")
        out.append(f"{sp}  article: {_scalar(e.get('article'))}")
        out.append(f"{sp}  page_pdf: {_scalar(e.get('page_pdf'))}")
        out.append(f"{sp}  porte: {_scalar(e.get('porte'))}")
        out.append(f"{sp}  modifie_calcul: {_scalar(bool(e.get('modifie_calcul')))}")
    return out


def main():
    dry = "--dry" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    vb = json.load(open(VB))
    groups = {}
    for o in vb:
        groups.setdefault((o["_insee"], o["zone"], o["regle"]), []).append(o)
    par_ins = {}
    for (ins, zone, regle), excs in groups.items():
        par_ins.setdefault(ins, []).append((zone, regle, excs))
    tot = {"leaves": 0, "exceptions": 0, "notes_retirees": 0, "RATE": 0}
    for ins in sorted(par_ins):
        if only and ins not in only:
            continue
        path = FILES[ins]
        lines = path.read_text(encoding="utf-8").split("\n")
        # traiter en ordre inverse de position pour que les insertions ne décalent pas les suivantes
        items = []
        for zone, regle, excs in par_ins[ins]:
            rng = _leaf_range(lines, zone, regle)
            if rng is None:
                tot["RATE"] += 1
                print(f"   RATÉ {ins} {zone} {regle}")
                continue
            items.append((rng[0], zone, regle, excs, rng))
        items.sort(key=lambda x: x[0], reverse=True)
        for _, zone, regle, excs, rng in items:
            lo, hi, ind = rng
            # retirer la note stopgap « (exception à afficher) » de la feuille
            for i in range(lo, hi):
                if re.match(r"^\s*note:\s*\"PLU-VERIF-1 \(exception à afficher\)", lines[i]):
                    del lines[i]
                    hi -= 1
                    tot["notes_retirees"] += 1
                    break
            lines[hi:hi] = _bloc_exceptions(excs, ind)
            tot["leaves"] += 1
            tot["exceptions"] += len(excs)
        if not dry:
            path.write_text("\n".join(lines), encoding="utf-8")
        print(f"{ins} {path.name:35} feuilles+{sum(1 for z,r,e in par_ins[ins])}")
    print("TOTAL", tot, "(dry)" if dry else "")


if __name__ == "__main__":
    main()
