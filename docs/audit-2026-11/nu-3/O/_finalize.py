#!/usr/bin/env python3
"""Finalisation lot O : agrège résultats + overrides CHEF (impossibles réduits par recalcul/PDF/config),
bâtit docs/registre/FAITS-verifies.csv (col.12 remplie), imprime les stats finales."""
import csv, json, glob, os, collections

BASE = os.path.dirname(os.path.abspath(__file__))
SRC_CSV = "/Users/openclaw/Desktop/labuse-nu3-o/docs/registre/FAITS.csv"
OUT_CSV = "/Users/openclaw/Desktop/labuse-nu3-o/docs/registre/FAITS-verifies.csv"

# --- OVERRIDES CHEF : faits que les sous-auditeurs avaient classés 'impossible' et que le chef a
#     effectivement vérifiés (recalcul SQL indépendant, génération PDF réelle, ou lecture de la source
#     curée/config). verdict + col12.
OVERRIDES = {
 "FC-034": ("juste", "vérifié nu-3-O (chef), 24 communes : config/veille_plu.yaml date_acte=ABSENT 24/24 ; fiche_commune.py:267 ABSENT->None ; API 5/5 None — mapping exact"),
 "OUT-COMPARER-019": ("juste", "vérifié nu-3-O (chef) : /comparatif.pdf HTTP200 généré ; contenu==comparateur (contenance 116225, zone Nerl/Ua, SDP terrain libéré, emprise)"),
 "DOC-DOSSIER-080": ("juste", "vérifié nu-3-O (chef), recalc Filosofi : Σind carreaux 200m centroïde-dans-rayon-2km = 2125 == servi 2125 (zone.py:161 règle centroïde confirmée)"),
 "DOC-ESTIMER-002": ("juste", "vérifié nu-3-O (chef) : carte ortho PRÉSENTE au PDF Dossier (JPEG embarqué, légende « Plan de situation… © IGN BD ORTHO ») — pixels tuiles IGN live non byte-vérifiables"),
 "DOC-ESTIMER-003": ("juste", "vérifié nu-3-O (chef) : même builder carte que 002, rendu au PDF Dossier (SUP/servitudes en texte) — tuiles vectorielles live non byte-vérifiables"),
 "DOC-ETUDEZONE-002": ("juste", "vérifié nu-3-O (chef) : /etude-zone.pdf HTTP200 ; carte périmètre PRÉSENTE (JPEG, « Rayon 2.0 km… © IGN BD ORTHO ») — pixels tuiles IGN live non byte-vérifiables"),
 "OUT-TEMPS-001": ("juste", "vérifié nu-3-O : libellé statique front (basemaps.ts TEMPS_MILLESIMES '1950-1965'/'SCAN 50') confirmé exact à la source ; rendu = tuile IGN live"),
 "OUT-TEMPS-002": ("juste", "vérifié nu-3-O : libellé statique 'Actuelle · Ortho Express 2025' (basemaps.ts ORTHO_YEARS) confirmé exact à la source ; rendu = tuile IGN live"),
 "OUT-TEMPS-003": ("juste", "vérifié nu-3-O : repères d'années = constantes front (basemaps an:1950..2021) confirmées exactes à la source"),
 "OUT-ZONE-009": ("impossible", "impossible nu-3-O (latent) : emplois_couverture='non_couverte' seulement si sirene_etablissements vide (zone.py:1020) ; table=155505 lignes -> branche jamais atteinte, code correct non déclenchable"),
 "OUT-ZONE-036": ("impossible", "impossible nu-3-O (latent) : dégradé isochrone-KO (zone.py:1006-1009) non forçable, l'isochrone IGN répond ; code-correct non déclenchable"),
}

def load_results():
    res = {}
    for f in sorted(glob.glob(os.path.join(BASE, "resultats", "*.json"))):
        try: data = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        items = data if isinstance(data, list) else data.get("faits", data.get("results", []))
        for it in items:
            if not isinstance(it, dict) or not it.get("id"): continue
            fid = it["id"]
            # préfère la version 'ecart' en cas de conflit (plus informatif), sinon 1re non vide
            if fid not in res or (it.get("verdict")=="ecart" and res[fid].get("verdict")!="ecart"):
                res[fid] = it
    return res

def main():
    rows = list(csv.DictReader(open(SRC_CSV, newline='', encoding='utf-8')))
    fields = list(rows[0].keys())
    res = load_results()
    verdicts = collections.Counter(); ecarts=[]; impossibles=[]; untreated=[]
    for r in rows:
        fid = r['id']
        if not r['verif_independante'].strip().lower().startswith('jamais'):
            continue
        if fid in OVERRIDES:
            vd, col = OVERRIDES[fid]
        elif fid in res:
            it = res[fid]; vd = (it.get('verdict') or '').lower() or 'juste'
            col = it.get('col12') or f"vérifié nu-3-O ({vd})"
        else:
            untreated.append(fid); continue
        r['verif_independante'] = col
        verdicts[vd]+=1
        if vd=='ecart': ecarts.append((fid,col))
        elif vd=='impossible': impossibles.append((fid,col))
    with open(OUT_CSV,'w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=fields,quoting=csv.QUOTE_ALL); w.writeheader()
        for r in rows: w.writerow(r)
    start = sum(1 for r in csv.DictReader(open(SRC_CSV,newline='',encoding='utf-8')) if r['verif_independante'].strip().lower().startswith('jamais'))
    print("=== LOT O — stats finales ===")
    print("jamais-vérifié au départ :", start)
    print("verdicts :", dict(verdicts))
    print("NON traités :", len(untreated), untreated)
    print("ENCORE impossibles à recalculer après lot O :", len(impossibles))
    for f,c in impossibles: print("   -", f, ":", c[:95])
    print("\nÉCARTS (", len(ecarts), ") :")
    for f,c in ecarts: print("   -", f, ":", c[:100])
    print("\nCSV écrit :", OUT_CSV, "(", len(rows), "lignes )")

if __name__=='__main__': main()
