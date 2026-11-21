import json, os, glob
BASE="docs/audit-2026-11/stationnement-fix-2/banc212"
B=json.load(open(f"{BASE}/moteur_baseline.json"))
SPECS=f"{BASE}/specs"; RES=f"{BASE}/results"
PROGS=["maison_T4_120","collectif_20T3_1400","aide_20T3_1400","mixte_10x110_10x30"]
def moteur_for(insee, zone):
    for r in B[insee]["couples"]:
        if r["zone"]==zone: return r["moteur"]
    return None
ecarts=[]; done=[]; ok=0; tot=0; couples_ok=set(); couples_all=set()
for rf in sorted(glob.glob(f"{RES}/*.json")):
    insee=os.path.basename(rf)[:5]
    res=json.load(open(rf)); spec=json.load(open(f"{SPECS}/{insee}.json"))
    rule_zones={r["id"]:r["zones"] for r in spec["regles"]}
    done.append(insee)
    for rr in res["regles"]:
        rid=rr["rule_id"]; zones=rule_zones.get(rid,[])
        for z in zones: couples_all.add((insee,z))
        z0=zones[0] if zones else None
        mot=moteur_for(insee,z0) if z0 else None
        rule_clean=True
        if not rr.get("found"):
            ecarts.append((insee,rid,zones,"NON-LU","found=false")); 
            continue
        for p in PROGS:
            tot+=1
            img=rr["programs"].get(p,{}).get("total")
            imgpub=rr["programs"].get(p,{}).get("publiques",0)
            m=(mot or {}).get(p,{}).get("places")
            mpub=(mot or {}).get(p,{}).get("publiques",0)
            if img==m and imgpub==mpub: ok+=1
            else:
                extra=f" [pub img={imgpub} vs mot={mpub}]" if imgpub!=mpub else ""
                ecarts.append((insee,rid,zones,p,f"image={img} vs moteur={m}{extra}")); rule_clean=False
        if rule_clean:
            for z in zones: couples_ok.add((insee,z))
print(f"Communes traitées ({len(done)}/23): {sorted(done)}")
print(f"Cells concordantes: {ok}/{tot}")
print(f"COUPLES entièrement concordants (4/4 programmes): {len(couples_ok)}/{len(couples_all)}")
print(f"\nÉCARTS ({len(ecarts)}):")
from collections import defaultdict
byc=defaultdict(list)
for insee,rid,zones,p,msg in ecarts: byc[insee].append((rid,len(zones),zones[0] if zones else '?',p,msg))
for insee in sorted(byc):
    for rid,nz,z0,p,msg in byc[insee]:
        print(f"  {insee} {rid} [{nz}z {z0}…] {p}: {msg}")
