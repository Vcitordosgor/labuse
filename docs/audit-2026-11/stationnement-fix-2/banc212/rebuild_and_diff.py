import json, os, glob
from types import SimpleNamespace
from labuse.plu import destinations as D
from labuse.implantation import regles as R
BASE="docs/audit-2026-11/stationnement-fix-2/banc212"
def maison():    return [SimpleNamespace(pieces=4, surface_m2=120.0)]
def collectif(): return [SimpleNamespace(pieces=3, surface_m2=70.0) for _ in range(20)]
def mixte():     return [SimpleNamespace(pieces=4, surface_m2=110.0) for _ in range(10)]+[SimpleNamespace(pieces=1, surface_m2=30.0) for _ in range(10)]
PROGS=[("maison_T4_120","individuel",maison),("collectif_20T3_1400","collectif",collectif),
       ("aide_20T3_1400","social",collectif),("mixte_10x110_10x30","collectif",mixte)]
insees=sorted({os.path.basename(f)[:5] for f in glob.glob("config/plu_destinations/*.yaml") if os.path.basename(f)[:5].isdigit()})
B={}
for insee in insees:
    doc=D._doc(insee) or {}; rows=[]
    for z in (doc.get("zones") or {}):
        try: b=R.charger(insee,z).stationnement
        except Exception: continue
        if not b.validee: continue
        res={}
        for key,dest,prog in PROGS:
            try:
                ex=b.exiger(prog(),destination=dest)
                res[key]={"places":ex.places,"publiques":ex.places_publiques}
            except Exception as e: res[key]={"places":None,"err":str(e)[:60]}
        rows.append({"zone":z,"moteur":res})
    B[insee]={"couples":rows}
json.dump(B,open(f"{BASE}/moteur_baseline.json","w"),ensure_ascii=False)
# diff
SPECS=f"{BASE}/specs"; RES=f"{BASE}/results"
PROGN=["maison_T4_120","collectif_20T3_1400","aide_20T3_1400","mixte_10x110_10x30"]
def mot(insee,zone):
    for r in B[insee]["couples"]:
        if r["zone"]==zone: return r["moteur"]
def first(rid,spec):
    for r in spec["regles"]:
        if r["id"]==rid: return r["zones"]
    return []
ecarts=[]; ok=0; tot=0; cok=set(); call=set()
for rf in sorted(glob.glob(f"{RES}/*.json")):
    insee=os.path.basename(rf)[:5]; res=json.load(open(rf)); spec=json.load(open(f"{SPECS}/{insee}.json"))
    for rr in res["regles"]:
        zones=first(rr["rule_id"],spec); 
        for z in zones: call.add((insee,z))
        if not rr.get("found"): ecarts.append((insee,rr["rule_id"],zones,"NON-LU","found=false")); continue
        m=mot(insee,zones[0]) if zones else None; clean=True
        for p in PROGN:
            tot+=1; img=rr["programs"].get(p,{}).get("total"); ip=rr["programs"].get(p,{}).get("publiques",0)
            mm=(m or {}).get(p,{}).get("places"); mp=(m or {}).get(p,{}).get("publiques",0)
            if img==mm and ip==mp: ok+=1
            else:
                ex=f" [pub {ip}vs{mp}]" if ip!=mp else ""; ecarts.append((insee,rr["rule_id"],zones,p,f"img={img} vs mot={mm}{ex}")); clean=False
        if clean:
            for z in zones: cok.add((insee,z))
print(f"Cells {ok}/{tot} | COUPLES concordants {len(cok)}/{len(call)} | écarts {len(ecarts)}")
for insee,rid,zones,p,msg in ecarts: print(f"  {insee} {rid} [{len(zones)}z {zones[0] if zones else '?'}] {p}: {msg}")
