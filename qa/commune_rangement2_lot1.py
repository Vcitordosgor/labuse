"""COMMUNE-RANGEMENT-2 lot 1 — comparaison LECTURE SEULE des données maille commune entre la fiche
commune et les autres surfaces (comparateur /communes) sur les 24 communes : même id ? même valeur ?
Via TestClient (in-process). Écrit un tableau markdown + un JSON."""
import json, warnings; warnings.filterwarnings("ignore")
from fastapi.testclient import TestClient
from labuse.api.app import app
from labuse import communes
c = TestClient(app)
noms = sorted(communes.load_communes().keys())

# fiche commune payloads
fiche = {n: c.get(f"/communes/{n}/contexte").json() for n in noms}
# comparateur / table Communes
comp = c.get("/comparateur-communes").json() if c.get("/comparateur-communes").status_code == 200 else c.get("/communes").json()
comp_rows = comp.get("communes") if isinstance(comp, dict) else comp
comp_by = {r.get("commune"): r for r in (comp_rows or [])}

# notions partagées : (libellé, extracteur fiche, extracteur comparateur)
def g(d, *ks):
    for k in ks:
        d = (d or {}).get(k) if isinstance(d, dict) else None
    return d
NOTIONS = [
 ("Prix ancien médian €/m²",  lambda f: g(f,"comparable","ancien_median_eur_m2"), lambda r: r.get("prix_ancien")),
 ("Prix neuf VEFA €/m²",      lambda f: g(f,"comparable","neuf_eur_m2"),          lambda r: r.get("prix_neuf")),
 ("Pression ZAN (ha, comparateur)", lambda f: None, lambda r: r.get("pression_zan")),  # communal AILLEURS, pas sur la fiche → Lot 2/4
 ("Permis 5 ans",             lambda f: g(f,"permis_bloc","permis_5a"),           lambda r: r.get("permis")),
 ("Délai médian (mois)",      lambda f: g(f,"permis_bloc","delai_median_mois"),   lambda r: round(float(r["velocite"]),1) if r.get("velocite") is not None else None),
 ("Stock opportunités (n)",   lambda f: g(f,"foncier","stock_opportunites","n"), lambda r: r.get("stock")),
 ("SRU statut",               lambda f: g(f,"sru","statut"),                      lambda r: r.get("sru_statut")),
 ("SRU déficit (pts)",        lambda f: g(f,"sru","deficit"),                     lambda r: round(float(r["deficit_sru"]),1) if r.get("deficit_sru") is not None else None),
 ("Terrain nu €/m²",          lambda f: g(f,"foncier","prix_terrain_nu","par_zone","U","median_eur_m2") or g(f,"foncier","prix_terrain_nu","par_zone","AU","median_eur_m2"), lambda r: r.get("prix_terrain_nu")),
]
def close(a,b):
    if a is None and b is None: return True
    if a is None or b is None: return False
    if isinstance(a,str) or isinstance(b,str): return str(a)==str(b)
    try: return abs(float(a)-float(b)) <= 0.06*max(1,abs(float(a)))
    except: return a==b

report=["| Notion | fiche commune | comparateur | communes concordantes /24 | divergences |","|---|---|---|---|---|"]
divs={}
for lbl, ef, ec in NOTIONS:
    ok=0; bad=[]
    for n in noms:
        vf=ef(fiche[n]); vc=ec(comp_by.get(n,{}))
        if close(vf,vc): ok+=1
        else: bad.append(f"{n}({vf}≠{vc})")
    divs[lbl]=bad
    report.append(f"| {lbl} | payload | raw_rows | {ok}/24 | {len(bad)} |")
print("\n".join(report))
print("\n=== DIVERGENCES détaillées ===")
tot=0
for lbl,bad in divs.items():
    if bad: tot+=len(bad); print(f"- {lbl}: {bad}")
print(f"\nTOTAL divergences: {tot}")
json.dump({"divergences":divs}, open("qa/commune_rangement2_lot1.json","w"), ensure_ascii=False, indent=1)
