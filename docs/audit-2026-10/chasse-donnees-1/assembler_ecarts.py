#!/usr/bin/env python3
"""Assemble ECARTS.md depuis ecarts-parts/*.csv (c*=lot C, d*=lot D, e*=lot E).

Usage : python assembler_ecarts.py  (depuis docs/audit-2026-10/chasse-donnees-1/)
"""
import csv
import glob
import collections

ORDER = {'FAUX-CLIENT': 0, 'DIVERGENT': 1, 'LATENT': 2, 'ETIQUETTE': 3, 'ABSENCE': 4, 'FRAICHEUR': 5}
LOTS = {'c': 'Lot C — même donnée, même valeur partout',
        'd': 'Lot D — la vérité face à la source',
        'e': 'Lot E — étiquettes et absences'}


def key_grav(g):
    return ORDER.get(g.strip().upper().replace('É', 'E').replace('Î', 'I'), 9)


def esc(s):
    return ' '.join(s.replace('|', '¦').split())


def main():
    by_lot = collections.defaultdict(list)
    for f in sorted(glob.glob('ecarts-parts/*.csv')):
        name = f.split('/')[-1]
        lot, part = name[0], name.split('-')[0]
        with open(f, encoding='utf-8') as fh:
            r = csv.reader(fh, delimiter=';')
            next(r)
            for row in r:
                if not row or not any(c.strip() for c in row):
                    continue
                if len(row) > 9:
                    row = row[:8] + [' ; '.join(row[8:])]
                assert len(row) == 9, (f, row)
                by_lot[lot].append([part] + row)

    total = collections.Counter()
    for rows in by_lot.values():
        for r in rows:
            total[r[2].strip().upper()] += 1

    with open('ECARTS.md', 'w', encoding='utf-8') as fh:
        fh.write("# CHASSE-DONNEES-1 — ECARTS\n\n")
        fh.write("Relevé des 12/10/2026 sur le local q_v18 (API 8740). Une ligne par écart ; "
                 "reproduction rejouable (détail dans `ecarts-parts/*.csv`, matrices dans `lotC/`, "
                 "confrontations dans `lotD/`).\n\n")
        fh.write("Bilan : " + " · ".join(
            f"**{k} {v}**" for k, v in sorted(total.items(), key=lambda kv: key_grav(kv[0])))
            + f" — {sum(total.values())} écarts.\n\n")
        n = 0
        for lot in sorted(by_lot):
            rows = sorted(by_lot[lot], key=lambda r: (key_grav(r[2]), r[0]))
            cnt = collections.Counter(r[2].strip().upper() for r in rows)
            fh.write(f"## {LOTS.get(lot, lot)}\n\n")
            fh.write(" · ".join(f"{k} {v}" for k, v in sorted(cnt.items(), key=lambda kv: key_grav(kv[0])))
                     + f" — {len(rows)} écarts.\n\n")
            fh.write("| # | part | notion | gravité | témoin | valeur A | valeur B | source | cause | fichier:ligne | reproduction |\n")
            fh.write("|---|------|--------|---------|--------|----------|----------|--------|-------|---------------|---------------|\n")
            for r in rows:
                n += 1
                fh.write("| %s-%02d | %s |\n" % (lot.upper(), n, " | ".join(esc(c) for c in r)))
            fh.write("\n")
    print(f"{sum(total.values())} écarts — " + ", ".join(
        f"{k}:{v}" for k, v in sorted(total.items(), key=lambda kv: key_grav(kv[0]))))


if __name__ == '__main__':
    main()
