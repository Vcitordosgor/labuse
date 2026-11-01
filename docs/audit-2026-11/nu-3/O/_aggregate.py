#!/usr/bin/env python3
"""Agrège les résultats des sous-auditeurs lot O, bâtit FAITS-verifies.csv et des stats."""
import csv, json, glob, os, sys, collections

BASE = os.path.dirname(os.path.abspath(__file__))
SRC_CSV = "/Users/openclaw/Desktop/labuse-nu3-o/docs/registre/FAITS.csv"
OUT_CSV = "/Users/openclaw/Desktop/labuse-nu3-o/docs/registre/FAITS-verifies.csv"

def load_results():
    res = {}
    dup = collections.Counter()
    for f in sorted(glob.glob(os.path.join(BASE, "resultats", "*.json"))):
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print(f"!! illisible {os.path.basename(f)}: {e}", file=sys.stderr); continue
        items = data if isinstance(data, list) else data.get("faits", data.get("results", []))
        for it in items:
            if not isinstance(it, dict): continue
            fid = it.get("id")
            if not fid: continue
            dup[fid]+=1
            # garde la version avec le verdict le plus informatif (ecart>impossible>juste si conflit? non:
            # on garde la 1re non vide, mais si une dit 'ecart' on la privilégie)
            if fid not in res or (it.get("verdict")=="ecart" and res[fid].get("verdict")!="ecart"):
                res[fid] = it
    return res, dup

def main():
    rows = list(csv.DictReader(open(SRC_CSV, newline='', encoding='utf-8')))
    fields = rows[0].keys()
    res, dup = load_results()
    stats = collections.Counter()
    verdicts = collections.Counter()
    ecarts = []
    impossibles = []
    still_never = []
    for r in rows:
        fid = r['id']
        v12 = r['verif_independante'].strip()
        was_never = v12.lower().startswith('jamais')
        if was_never:
            if fid in res:
                it = res[fid]
                col = it.get('col12') or ''
                if not col:
                    vd = it.get('verdict','?')
                    col = f"vérifié nu-3-O ({vd})"
                r['verif_independante'] = col
                vd = (it.get('verdict') or '').lower()
                verdicts[vd]+=1
                if vd == 'ecart':
                    ecarts.append((fid, it))
                elif vd == 'impossible':
                    impossibles.append((fid, it))
                    still_never.append(fid)  # impossible = non vérifié au sens strict
                stats['traite']+=1
            else:
                stats['non_traite']+=1
                still_never.append(fid)
    # write FAITS-verifies.csv
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(fields), quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows: w.writerow(r)
    # report stats
    print("=== LOT O — agrégation ===")
    print("faits jamais-vérifié au départ :", sum(1 for r0 in csv.DictReader(open(SRC_CSV,newline='',encoding='utf-8')) if r0['verif_independante'].strip().lower().startswith('jamais')))
    print("faits traités par un sous-auditeur :", stats['traite'])
    print("faits NON traités (pas de résultat) :", stats['non_traite'])
    print("verdicts :", dict(verdicts))
    print("ENCORE jamais-vérifié après lot O (non traités + impossibles) :", len(still_never))
    print("  -> non traités :", [f for f in still_never if f not in dict(impossibles)][:50])
    print("  -> impossibles :", [f for f,_ in impossibles])
    print("doublons d'id entre fichiers :", {k:v for k,v in dup.items() if v>1})
    print("\n=== ÉCARTS (", len(ecarts), ") ===")
    for fid,it in ecarts:
        print(f"  {fid}: {it.get('col12','')[:120]}")
        if it.get('cause'): print(f"      cause: {it.get('cause','')[:140]}")
    print("\nCSV écrit :", OUT_CSV)

if __name__ == '__main__':
    main()
