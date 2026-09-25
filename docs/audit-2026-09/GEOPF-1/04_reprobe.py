#!/usr/bin/env python3
# GEOPF-1 — étape 3bis : re-tester les 49 "indéterminé" avec des méthodes adaptées.
# TMS vecteur (pbf, Y inversé) ; WMTS/TMS raster à zoom plus faible ; WFS retry ; rasters alti étiquetés.
import json,os,re,io,math,time,ssl,urllib.request,urllib.parse
from xml.etree import ElementTree as ET
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__))
CTX=ssl._create_unverified_context();UA={"User-Agent":"LABUSE-GEOPF-1-audit/1.0"}
WIT=[("StDenis",55.4481,-20.8823),("StPierre",55.4809,-21.3393),("Cilaos",55.4713,-21.1361)]
_last=[0.0]
def throttle():
    dt=time.time()-_last[0]
    if dt<0.21: time.sleep(0.21-dt)
    _last[0]=time.time()
def get(url,t=35):
    throttle()
    try:
        r=urllib.request.Request(url,headers=UA)
        with urllib.request.urlopen(r,timeout=t,context=CTX) as f: return f.status,f.read(),f.headers.get("Content-Type","")
    except urllib.error.HTTPError as e: return e.code,b"",e.headers.get("Content-Type","") if e.headers else ""
    except Exception as e: return 0,str(e).encode()[:80],"err"
def tilexy(lon,lat,z):
    n=2**z; return int((lon+180)/360*n), int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
def img_rich(b):
    try: im=Image.open(io.BytesIO(b)).convert("RGBA")
    except: return None
    c=im.getcolors(200000)
    if c is None: return True
    nz=[x for n,x in c if x[3]>0]
    if not nz: return False
    return len(set(x for n,x in c))>2

# TMS extensions
ext={}
xt=open(os.path.join(HERE,"cache","getcap_tms.xml"),encoding="utf-8").read()
for m in re.finditer(r'<TileMap title="[^"]*"[^>]*extension="([^"]+)"[^>]*href="[^"]*/([^"/]+)"',xt):
    ext[m.group(2)]=m.group(1)
WMTS_META=json.load(open(os.path.join(HERE,"wmts_meta.json")))

RASTER_ALTI=re.compile(r'ELEVATIONGRIDCOVERAGE|RGEALTI|LIDAR-HD_(MNT|MNS|MNH)|\.SLOPES|SRTM|\.MNS|\.LEVEL0',re.I)

def reprobe_tms(ident):
    e=ext.get(ident,"pbf")
    if e in ("bil","zbil"): return "indetermine","tuiles-alti-brutes(bil) non rendues"
    hits=[]
    for w,lon,lat in WIT:
        for z in (14,12,10):
            x,y=tilexy(lon,lat,z); ty=(2**z-1)-y
            st,b,ct=get(f"https://data.geopf.fr/tms/1.0.0/{ident}/{z}/{x}/{ty}.{e}")
            if st==200 and b:
                if e in ("png","jpeg"):
                    if img_rich(b): hits.append(f"{w}:z{z}img"); break
                else:  # pbf : tuile non vide = quelques octets de features
                    if len(b)>40: hits.append(f"{w}:z{z}pbf{len(b)}b"); break
    if hits: return "couvre","TMS "+ "/".join(hits)
    return "declaree_vide","TMS aucune tuile non vide (z14/12/10)"

def reprobe_wmts(ident):
    m=WMTS_META.get(ident)
    if not m: return "indetermine","no-wmts-meta"
    tms=(m["tms"] or ["PM"])[0]; style=(m["style"] or ["normal"])[0]; fmt=(m["fmt"] or ["image/png"])[0]
    mm=re.search(r'_(\d+)_(\d+)$',tms); zmax=int(mm.group(2)) if mm else 18
    hits=[]
    for w,lon,lat in WIT:
        for z in sorted({min(zmax,13),min(zmax,10),min(zmax,7)},reverse=True):
            x,y=tilexy(lon,lat,z)
            q={"SERVICE":"WMTS","VERSION":"1.0.0","REQUEST":"GetTile","LAYER":ident,"STYLE":style,
               "TILEMATRIXSET":tms,"TILEMATRIX":str(z),"TILEROW":y,"TILECOL":x,"FORMAT":fmt}
            st,b,ct=get("https://data.geopf.fr/wmts?"+urllib.parse.urlencode(q))
            if st==200 and "image" in ct and img_rich(b): hits.append(f"{w}:z{z}"); break
    if hits: return "couvre","WMTS(bas zoom) "+"/".join(hits)
    return "declaree_vide","WMTS aucune tuile riche (z≤13)"

def reprobe_wfs(name):
    for tn in ("TYPENAMES","TYPENAME"):
        q={"SERVICE":"WFS","VERSION":"2.0.0","REQUEST":"GetFeature",tn:name,"COUNT":"1",
           "SRSNAME":"urn:ogc:def:crs:EPSG::4326","BBOX":f"-21.40,55.20,-20.85,55.85,urn:ogc:def:crs:EPSG::4326"}
        st,b,ct=get("https://data.geopf.fr/wfs/ows?"+urllib.parse.urlencode(q))
        if st==200 and b"ExceptionReport" not in b:
            nb=re.search(rb'numberReturned="(\d+)"',b) or re.search(rb'numberMatched="(\d+)"',b)
            has=b"<wfs:member" in b or b"<member" in b or (nb and int(nb.group(1))>0)
            return ("couvre" if has else "declaree_vide"), f"WFS GetFeature ({tn})"
    return "indetermine","WFS 400 (2 variantes)"

def main():
    r=json.load(open(os.path.join(HERE,"probe_results.json")))
    ind=[x for x in r if x["verdict"]=="indetermine"]
    print("à re-tester:",len(ind))
    fixed=0
    for x in ind:
        ident=x["identifier"]; meth=x["method"]
        if RASTER_ALTI.search(ident):
            x["verdict"]="indetermine"; x["detail"]="raster altimétrique brut — non testable par image (donnée alti IGN)"
            x["method"]=meth+"|alti"; continue
        if meth=="TMS-only":
            v,d=reprobe_tms(ident)
        elif meth.startswith("WMTS"):
            v,d=reprobe_wmts(ident)
        elif meth.startswith("WFS"):
            v,d=reprobe_wfs(x["identifier"] if ":" in x["identifier"] else x["identifier"])
        elif meth.startswith("WMS"):
            # WMS http0 non-alti : retenter en WMTS si dispo, sinon laisser
            if ident in WMTS_META: v,d=reprobe_wmts(ident)
            else: v,d=("indetermine","WMS GetMap en erreur, pas de WMTS")
        else:
            v,d=("indetermine",x["detail"])
        if v!="indetermine": fixed+=1
        x["verdict"]=v; x["detail"]=d; x["method"]=meth+"|re"
    json.dump(r,open(os.path.join(HERE,"probe_results.json"),"w"),ensure_ascii=False)
    from collections import Counter
    print("résolus:",fixed)
    print("VERDICTS finaux:",Counter(x["verdict"] for x in r))

if __name__=="__main__": main()
