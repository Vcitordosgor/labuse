"""COMMUNE-RANGEMENT-2 lot 4 — recensement des lignes de données rendues par ContextePanel.tsx.
Extrait tous les accès à un champ du payload (d.<...>, r['<...>'], marche_annonces, parc_social…) dans le
bloc de rendu, pour prouver « 0 ligne perdue » avant/après le rangement. Usage : python census.py <label>"""
import re, sys, json
src = open("frontend/src/components/contexte/ContextePanel.tsx").read()
# on ne garde que le corps de rendu (après 'export function ContextePanel')
body = src[src.index("export function ContextePanel"):]
pats = set()
# accès d.<chemin> (jusqu'à un séparateur), r['x'], tend/tendPct, ma.<x>, o.<x>
for m in re.finditer(r"\bd\.(\w+(?:\.\w+)*)", body): pats.add("d."+m.group(1))
for m in re.finditer(r"\br\?\?\['(\w+)'\]|\br\['(\w+)'\]|\br\?\.\['(\w+)'\]", body):
    pats.add("r."+(m.group(1) or m.group(2) or m.group(3)))
for m in re.finditer(r"\bma!?\??\.(\w+)", body): pats.add("ma."+m.group(1))
for m in re.finditer(r"\bo!?\??\.(\w+)", body): pats.add("o."+m.group(1))
for m in re.finditer(r"\btend(?:Pct)?\b", body): pats.add("tend")
# labels de RowT (libellés de lignes)
labels = sorted(set(re.findall(r'RowT lbl=(?:\{`|")([^`"}]+)', body)))
# libellés de Bar (parts)
bars = sorted(set(re.findall(r"label:\s*'([^']+)'", body)))
out = {"n_field_accesses": len(pats), "fields": sorted(pats),
       "n_rowt_labels": len(labels), "rowt_labels": labels,
       "n_bar_labels": len(bars), "bar_labels": bars}
label = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
json.dump(out, open(f"qa/census_{label}.json","w"), ensure_ascii=False, indent=1)
print(f"[{label}] champs={len(pats)} · RowT libellés={len(labels)} · Bar libellés={len(bars)}")
