#!/usr/bin/env python3
# GEOPF-1 — étape 2/3 : filtre emprise déclarée + test réel Réunion.
# Politesse : 5 req/s max (0.2 s mini entre requêtes). Lecture seule. Réseau via cache SSL non vérifié
# (chaîne TLS interceptée localement ; données 100% publiques en lecture).
import json,os,io,re,math,time,ssl,urllib.request,urllib.parse
from xml.etree import ElementTree as ET
from PIL import Image

HERE=os.path.dirname(os.path.abspath(__file__))
CTX=ssl._create_unverified_context()
UA={"User-Agent":"LABUSE-GEOPF-1-audit/1.0 (read-only coverage survey; contact kampusreunion)"}
RW,RE,RS,RN=55.20,55.85,-21.40,-20.85
WIT=[("StDenis",55.4481,-20.8823),("StPierre",55.4809,-21.3393),("Cilaos",55.4713,-21.1361)]

_last=[0.0]
def throttle():
    dt=time.time()-_last[0]
    if dt<0.21: time.sleep(0.21-dt)
    _last[0]=time.time()
def get(url,t=30,retry=1):
    for a in range(retry+1):
        throttle()
        try:
            r=urllib.request.Request(url,headers=UA)
            with urllib.request.urlopen(r,timeout=t,context=CTX) as f:
                return f.status,f.read(),f.headers.get("Content-Type","")
        except Exception as e:
            if a==retry: return 0,str(e).encode()[:120],"error"
    return 0,b"",""

def img_state(b):
    try: im=Image.open(io.BytesIO(b)).convert("RGBA")
    except Exception: return "noimg"
    cols=im.getcolors(maxcolors=200000)
    if cols is None: return "rich"
    nz=[c for cnt,c in cols if c[3]>0]
    if not nz: return "transparent"
    u=len(set(c for cnt,c in cols))
    return "rich" if u>2 else ("uni%d"%u)

def is_covered_img(states):
    # couvre si au moins un point témoin a une image riche (>2 couleurs / rich)
    return any(s=="rich" for s in states)

# ---- WFS hits ----
def probe_wfs(name):
    bbox=f"{RS},{RW},{RN},{RE},urn:ogc:def:crs:EPSG::4326"
    q={"SERVICE":"WFS","VERSION":"2.0.0","REQUEST":"GetFeature","TYPENAMES":name,"RESULTTYPE":"hits","BBOX":bbox}
    st,body,ct=get("https://data.geopf.fr/wfs/ows?"+urllib.parse.urlencode(q))
    if st!=200: return dict(method="WFS-hits",verdict="indetermine",detail=f"http{st}:{body[:60]}")
    if b"ExceptionReport" in body: return dict(method="WFS-hits",verdict="indetermine",detail="exception")
    m=re.search(rb'numberMatched="(\d+)"',body) or re.search(rb'numberOfFeatures="(\d+)"',body)
    if not m: return dict(method="WFS-hits",verdict="indetermine",detail="no-count")
    n=int(m.group(1))
    return dict(method="WFS-hits",verdict=("couvre" if n>0 else "declaree_vide"),detail=f"hits={n}")

# ---- WMS GetMap ----
def probe_wms(name,base,d=0.008):
    states=[]
    for w,lon,lat in WIT:
        q={"SERVICE":"WMS","VERSION":"1.3.0","REQUEST":"GetMap","LAYERS":name,"STYLES":"",
           "CRS":"CRS:84","BBOX":f"{lon-d},{lat-d},{lon+d},{lat+d}","WIDTH":128,"HEIGHT":128,
           "FORMAT":"image/png","TRANSPARENT":"TRUE"}
        st,body,ct=get(base+"?"+urllib.parse.urlencode(q))
        states.append(img_state(body) if "image" in ct else ("http%s"%st))
    verdict="couvre" if is_covered_img(states) else ("declaree_vide" if all(s in ("transparent","uni1","uni2") for s in states) else "indetermine")
    return dict(method="WMS-GetMap",verdict=verdict,detail="/".join(f"{w}:{s}" for (w,_,_),s in zip(WIT,states)))

# ---- WMTS GetTile ----
def tilexy(lon,lat,z):
    n=2**z; x=int((lon+180)/360*n)
    y=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
    return x,y
WMTS_META=json.load(open(os.path.join(HERE,"wmts_meta.json")))
def probe_wmts(ident):
    m=WMTS_META.get(ident)
    if not m: return dict(method="WMTS-GetTile",verdict="indetermine",detail="no-meta")
    tms=(m["tms"] or ["PM"])[0]; style=(m["style"] or ["normal"])[0]; fmt=(m["fmt"] or ["image/png"])[0]
    mm=re.search(r'_(\d+)_(\d+)$',tms); zmax=int(mm.group(2)) if mm else 19
    z=min(15,zmax)
    states=[]
    for w,lon,lat in WIT:
        x,y=tilexy(lon,lat,z)
        q={"SERVICE":"WMTS","VERSION":"1.0.0","REQUEST":"GetTile","LAYER":ident,"STYLE":style,
           "TILEMATRIXSET":tms,"TILEMATRIX":str(z),"TILEROW":y,"TILECOL":x,"FORMAT":fmt}
        st,body,ct=get("https://data.geopf.fr/wmts?"+urllib.parse.urlencode(q))
        states.append(img_state(body) if "image" in ct else ("http%s"%st))
    verdict="couvre" if is_covered_img(states) else ("declaree_vide" if all(s in ("transparent","uni1","uni2","http404") for s in states) else "indetermine")
    return dict(method=f"WMTS-GetTile(z{z})",verdict=verdict,detail="/".join(f"{w}:{s}" for (w,_,_),s in zip(WIT,states)))

# ---- TMS bbox resolution for TMS-only (no declared bbox) ----
def merc_to_lonlat(x,y):
    lon=x/20037508.34*180.0
    lat=math.degrees(2*math.atan(math.exp(y/20037508.34*math.pi))-math.pi/2)
    return lon,lat
def tms_bbox(ident):
    st,body,ct=get("https://data.geopf.fr/tms/1.0.0/"+ident)
    if st!=200: return None
    try:
        root=ET.fromstring(body)
        bb=None
        for e in root.iter():
            if e.tag.rsplit('}',1)[-1]=="BoundingBox": bb=e;break
        if bb is None: return None
        minx=float(bb.get("minx"));miny=float(bb.get("miny"));maxx=float(bb.get("maxx"));maxy=float(bb.get("maxy"))
        w,s=merc_to_lonlat(minx,miny); e,n=merc_to_lonlat(maxx,maxy)
        return (w,e,s,n)
    except Exception: return None

def crosses(b):
    if not b: return False
    w,e,s,n=b; return not(e<RW or w>RE or n<RS or s>RN)

def main():
    dedup=json.load(open(os.path.join(HERE,"layers_dedup.json")))
    # 1) résoudre bbox des TMS-only sans emprise
    tms_only=[x for x in dedup if not x["bbox"] and x["services"]==["TMS"]]
    print(f"TMS-only sans bbox à résoudre: {len(tms_only)}")
    for i,x in enumerate(tms_only):
        x["bbox"]=tms_bbox(x["identifiers"][0])
        x["bbox_resolue_tms"]=True
        if (i+1)%20==0: print(f"  ...{i+1}/{len(tms_only)}")
    # 2) candidats = emprise déclarée croise Réunion
    cand=[x for x in dedup if crosses(x["bbox"])]
    print(f"Candidats (emprise déclarée croise Réunion): {len(cand)}")
    # 3) test réel
    results=[]
    for i,x in enumerate(cand):
        svc=set(x["services"]); ids=x["identifiers"]
        # choisir la meilleure preuve
        wfs_id=next((i for i in ids if ":" in i), ids[0])
        if "WFS" in svc:
            res=probe_wfs(wfs_id)
        elif "WMS-r" in svc:
            res=probe_wms(ids[0],"https://data.geopf.fr/wms-r/ows")
        elif "WMS-v" in svc:
            res=probe_wms(ids[0],"https://data.geopf.fr/wms-v/ows")
        elif "WMTS" in svc:
            res=probe_wmts(ids[0])
        else:
            res=dict(method="TMS-only",verdict="indetermine",detail="pas de service testable simple")
        rec=dict(canon=x["canon"],title=x["title"],theme=x["theme"],services=x["services"],
                 identifier=ids[0],bbox=x["bbox"],**res)
        results.append(rec)
        if (i+1)%50==0:
            print(f"  {i+1}/{len(cand)}  [{res['verdict']}] {x['title'][:40]}")
            json.dump(results,open(os.path.join(HERE,"probe_results.json"),"w"),ensure_ascii=False)
    json.dump(results,open(os.path.join(HERE,"probe_results.json"),"w"),ensure_ascii=False)
    from collections import Counter
    print("VERDICTS:",Counter(r["verdict"] for r in results))
    print("terminé:",len(results))

if __name__=="__main__":
    main()
