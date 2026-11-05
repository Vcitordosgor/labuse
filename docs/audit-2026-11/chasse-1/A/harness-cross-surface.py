import json, subprocess, urllib.request, urllib.parse

BASE="http://127.0.0.1:9590"
IDUS=[l.strip() for l in open('/tmp/chasse-a/sample_all.txt') if l.strip()]

def api(path):
    try:
        with urllib.request.urlopen(BASE+path, timeout=30) as r:
            return json.load(r), None
    except Exception as e:
        return None, str(e)

# batch DB read
def psql(sql):
    out=subprocess.check_output(["psql","-At","-F","\t","-d","labuse","-c",sql],text=True)
    return out

idu_list="','".join(IDUS)
rows=psql(f"""
SELECT p.idu, p.commune, p.surface_m2, p.contenance_m2,
       m.surface_m2, m.tier_v2, m.rang_v2, m.sdp_residuelle_m2, m.zone_lib, m.zone_fam, m.surface_incertaine,
       z.zone_lib, z.zone_fam
FROM parcels p
LEFT JOIN mvt_parcels m ON m.idu=p.idu
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.idu IN ('{idu_list}');
""")
db={}
for ln in rows.splitlines():
    c=ln.split("\t")
    def num(x):
        return None if x=='' else x
    db[c[0]]=dict(commune=c[1], p_surf=float(c[2]) if c[2] else None, p_cont=int(c[3]) if c[3] else None,
                  m_surf=int(c[4]) if c[4] else None, m_tier=num(c[5]), m_rang=int(c[6]) if c[6] else None,
                  m_sdp=int(c[7]) if c[7] else None, m_zlib=num(c[8]), m_zfam=num(c[9]), m_incert=(c[10]=='t'),
                  z_zlib=num(c[11]), z_zfam=num(c[12]))

findings=[]
def add(idu,cat,detail):
    findings.append((idu,cat,detail))

n_ok=0; n_err=0
for i,idu in enumerate(IDUS):
    f,e1=api(f"/parcels/{idu}")
    s,e2=api(f"/parcels/search?q={idu}")
    d=db.get(idu,{})
    if f is None:
        add(idu,"FICHE_ERR",e1); n_err+=1; continue
    srow = s[0] if s else None
    # surface
    f_surf=f.get("surface_terrain_m2")
    s_surf=srow.get("surface_terrain_m2") if srow else None
    m_surf=d.get("m_surf")
    # expected served surface = contenance if present else round(surface_m2)
    exp = d.get("p_cont") if d.get("p_cont") is not None else (round(d["p_surf"]) if d.get("p_surf") else None)
    if f_surf!=exp: add(idu,"SURF_FICHE_vs_DB",f"fiche={f_surf} exp(COALESCE cont,round(dessin))={exp}")
    if srow and s_surf!=f_surf: add(idu,"SURF_SEARCH_vs_FICHE",f"search={s_surf} fiche={f_surf}")
    if m_surf is not None and f_surf is not None and m_surf!=f_surf:
        add(idu,"SURF_MAP_vs_FICHE",f"map={m_surf} fiche={f_surf} (cont={d.get('p_cont')})")
    # surface_incertaine flag consistency
    f_inc=f.get("surface_incertaine")
    if d.get("m_surf") is not None and f_inc is not None and bool(f_inc)!=bool(d.get("m_incert")):
        add(idu,"INCERT_MAP_vs_FICHE",f"fiche={f_inc} map={d.get('m_incert')}")
    # zone
    rp=f.get("reglement_plu") or {}
    zones=rp.get("zones") or []
    f_zone=zones[0].get("zone") if zones else None
    if d.get("z_zlib") and f_zone and f_zone!=d.get("z_zlib"):
        add(idu,"ZONE_FICHE_vs_DB",f"fiche={f_zone} zone_plu={d.get('z_zlib')}")
    if d.get("m_zlib") and d.get("z_zlib") and d.get("m_zlib")!=d.get("z_zlib"):
        add(idu,"ZONE_MAP_vs_DB",f"map={d.get('m_zlib')} zone_plu={d.get('z_zlib')}")
    # tier/rang
    sv=f.get("score_v2") or {}
    f_tier=sv.get("tier"); f_rang=sv.get("rang")
    if srow and srow.get("tier_v2")!=f_tier: add(idu,"TIER_SEARCH_vs_FICHE",f"search={srow.get('tier_v2')} fiche={f_tier}")
    if d.get("m_tier") and f_tier and d.get("m_tier")!=f_tier: add(idu,"TIER_MAP_vs_FICHE",f"map={d.get('m_tier')} fiche={f_tier}")
    if srow and srow.get("rang_v2")!=f_rang: add(idu,"RANG_SEARCH_vs_FICHE",f"search={srow.get('rang_v2')} fiche={f_rang}")
    if d.get("m_rang") is not None and f_rang is not None and d.get("m_rang")!=f_rang:
        add(idu,"RANG_MAP_vs_FICHE",f"map={d.get('m_rang')} fiche={f_rang}")
    # sdp
    pt=f.get("potentiel_transformation") or {}
    calc=pt.get("calcul") or {}
    f_sdp=calc.get("sdp_residuelle_m2")
    if d.get("m_sdp") is not None and f_sdp is not None and d.get("m_sdp")!=f_sdp:
        add(idu,"SDP_MAP_vs_FICHE",f"map={d.get('m_sdp')} fiche={f_sdp}")
    n_ok+=1

print(f"parcels checked={n_ok} fiche_err={n_err} findings={len(findings)}")
from collections import Counter
cc=Counter(x[1] for x in findings)
for k,v in cc.most_common(): print(f"  {k}: {v}")
print("--- samples (up to 4 per category) ---")
seen=Counter()
for idu,cat,det in findings:
    if seen[cat]<4:
        print(f"  [{cat}] {idu}: {det}"); seen[cat]+=1
json.dump(findings, open('/tmp/chasse-a/findings.json','w'))
