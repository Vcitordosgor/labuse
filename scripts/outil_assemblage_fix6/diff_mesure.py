"""OUTIL-ASSEMBLAGE-FIX-6 — diff des deux passes (courant vs prefix) : bilans dont le montant (charge
foncière centrale) change, PAR COMMUNE ET PAR ZONE. Tableau pour le rapport + CSV des écarts."""
import csv
import sys
from collections import defaultdict


def load(path, keycols):
    out = {}
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            out[tuple(row[k] for k in keycols)] = row
    return out


def main(kind):
    if kind == "single":
        keys = ["idu"]
        cur = load("/tmp/fix6_single_courant.csv", keys)
        pre = load("/tmp/fix6_single_prefix.csv", keys)
        cf = "cf_central"
        labelcols = ("commune", "zone")
    else:
        keys = ["a", "b"]
        cur = load("/tmp/fix6_asm_courant.csv", keys)
        pre = load("/tmp/fix6_asm_prefix.csv", keys)
        cf = "cf_central"
        labelcols = ("commune",)

    def val(d):
        v = d.get(cf, "")
        try:
            return round(float(v))
        except Exception:
            return None

    changed = []
    per = defaultdict(lambda: [0, 0])   # (commune,zone) -> [n_total, n_changed]
    for k, c in cur.items():
        p = pre.get(k)
        if not p:
            continue
        lab = tuple(c.get(x, "") for x in labelcols)
        per[lab][0] += 1
        vc, vp = val(c), val(p)
        if vc != vp:
            per[lab][1] += 1
            changed.append((k, lab, vp, vc, c.get("regime"), p.get("regime"),
                            c.get("log_prog", ""), c.get("log_rep", "")))
    print(f"=== {kind} — bilans comparés : {sum(v[0] for v in per.values())} | "
          f"montant changé : {len(changed)} ===")
    print("commune/zone | total | changés")
    for lab in sorted(per):
        n, ch = per[lab]
        print(f"  {' / '.join(lab):30} | {n:6} | {ch}")
    if changed:
        with open(f"/tmp/fix6_{kind}_ecarts.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cle", "label", "cf_prefix", "cf_courant", "regime_cour", "regime_pre",
                        "log_prog", "log_rep"])
            for row in changed:
                w.writerow([row[0], "/".join(row[1]), *row[2:]])
        print(f"\n{len(changed)} écarts -> /tmp/fix6_{kind}_ecarts.csv")
        for row in changed[:40]:
            print("  ", row)
    else:
        print("\nAUCUN montant ne bouge.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "asm")
