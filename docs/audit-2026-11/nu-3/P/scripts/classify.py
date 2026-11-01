import json, urllib.request, sys
BASE="http://127.0.0.1:9440"
def fiche(idu):
    with urllib.request.urlopen(f"{BASE}/parcels/{idu}?source=q_v20", timeout=60) as r:
        return json.load(r)
def g(d,*path,default=None):
    for p in path:
        if isinstance(d,dict): d=d.get(p)
        else: return default
    return d if d is not None else default
cands = [c.strip() for c in sys.argv[1:]]
for idu in cands:
    try:
        d=fiche(idu)
    except Exception as e:
        print(idu,"ERR",e); continue
    zone = g(d,'reglement_plu','zone') or g(d,'reglement_plu','zone_lib') or g(d,'le_bien','zone')
    rnu = d.get('rnu')
    etat = d.get('etat_bien')
    cont = d.get('contenance_m2')
    aleas = d.get('aleas') or {}
    al_n = aleas.get('n') or aleas.get('nombre') or (len(aleas.get('liste',[])) if isinstance(aleas.get('liste'),list) else None)
    ppr = json.dumps(aleas)[:120]
    dvf = d.get('dvf_parcelle') or {}
    copro = d.get('coproprietes') or []
    pm = d.get('proprietaire_moral')
    pt = d.get('potentiel_transformation') or {}
    ncp = pt.get('non_constructible_pct') if isinstance(pt,dict) else None
    print(f"{idu} | comm={d.get('commune')} | cont={cont} | zone={zone!r} rnu={bool(rnu)} | etat={etat} | aleas_n={al_n} | dvf_keys={list(dvf.keys())[:4]} | copro={len(copro)} | pm={pm if isinstance(pm,str) else (pm.get('denomination') if isinstance(pm,dict) else pm)} | ncp={ncp}")
