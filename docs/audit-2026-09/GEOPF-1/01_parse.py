#!/usr/bin/env python3
# GEOPF-1 — étape 1 : parser les 5 GetCapabilities → inventaire unifié + dédoublonné.
# Lecture seule, sans réseau (lit le cache). Sortie : layers_raw.json, layers_dedup.json.
import json, re, os
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")

def localname(tag):
    return tag.rsplit('}', 1)[-1]

def findall_local(root, name):
    return [e for e in root.iter() if localname(e.tag) == name]

def text(e):
    return (e.text or "").strip() if e is not None else ""

def child_local(e, name):
    for c in e:
        if localname(c.tag) == name:
            return c
    return None

records = []  # {service, identifier, title, abstract, theme, west,east,south,north(bbox), bbox_ok}

# ---------- WMTS ----------
def parse_wmts():
    root = ET.parse(os.path.join(CACHE, "getcap_wmts.xml")).getroot()
    n = 0
    for layer in findall_local(root, "Layer"):
        ident = None; title = ""; ab,ll,uc = "", None, None
        for c in layer:
            ln = localname(c.tag)
            if ln == "Identifier": ident = text(c)
            elif ln == "Title" and not title: title = text(c)
            elif ln == "Abstract": ab=text(c)
            elif ln == "WGS84BoundingBox":
                lc = child_local(c, "LowerCorner"); ucc = child_local(c, "UpperCorner")
                ll = text(lc); uc = text(ucc)
        if not ident: continue
        bbox = None
        if ll and uc:
            try:
                w,s = map(float, ll.split()); e,nn = map(float, uc.split())
                bbox = (w,e,s,nn)
            except: pass
        records.append(dict(service="WMTS", identifier=ident, title=title, abstract=abstract_of(abs_=abstract_or(layer)), bbox=bbox))
        n += 1
    return n

# simpler: re-extract abstract cleanly
def abstract_or(layer):
    a = child_local(layer, "Abstract")
    return text(a)
def abstract_of(abs_): return abs_

# ---------- WMS 1.3.0 (raster & vecteur) ----------
def parse_wms(fname, service):
    root = ET.parse(os.path.join(CACHE, fname)).getroot()
    n = 0
    for layer in findall_local(root, "Layer"):
        name_e = child_local(layer, "Name")
        if name_e is None:  # group layer w/o Name — skip
            continue
        ident = text(name_e)
        title = text(child_local(layer, "Title"))
        abs_ = text(child_local(layer, "Abstract"))
        bb = child_local(layer, "EX_GeographicBoundingBox")
        bbox = None
        if bb is not None:
            try:
                w = float(text(child_local(bb, "westBoundLongitude")))
                e = float(text(child_local(bb, "eastBoundLongitude")))
                s = float(text(child_local(bb, "southBoundLatitude")))
                nn = float(text(child_local(bb, "northBoundLatitude")))
                bbox = (w,e,s,nn)
            except: pass
        records.append(dict(service=service, identifier=ident, title=title, abstract=abs_, bbox=bbox))
        n += 1
    return n

# ---------- WFS 2.0 ----------
def parse_wfs():
    root = ET.parse(os.path.join(CACHE, "getcap_wfs.xml")).getroot()
    n = 0
    for ft in findall_local(root, "FeatureType"):
        ident = text(child_local(ft, "Name"))
        if not ident: continue
        title = text(child_local(ft, "Title"))
        abs_ = text(child_local(ft, "Abstract"))
        bb = child_local(ft, "WGS84BoundingBox")
        bbox = None
        if bb is not None:
            lc = child_local(bb, "LowerCorner"); ucc = child_local(bb, "UpperCorner")
            try:
                w,s = map(float, text(lc).split()); e,nn = map(float, text(ucc).split())
                bbox = (w,e,s,nn)
            except: pass
        records.append(dict(service="WFS", identifier=ident, title=title, abstract=abs_, bbox=bbox))
        n += 1
    return n

# ---------- TMS (index only : pas de bbox) ----------
def parse_tms():
    root = ET.parse(os.path.join(CACHE, "getcap_tms.xml")).getroot()
    n = 0
    for tm in findall_local(root, "TileMap"):
        href = tm.get("href","")
        ident = href.rsplit("/",1)[-1]
        title = tm.get("title","")
        if not ident: continue
        records.append(dict(service="TMS", identifier=ident, title=title, abstract="", bbox=None))
        n += 1
    return n

counts = {}
counts["WMTS"] = parse_wmts()
counts["WMS-raster"] = parse_wms("getcap_wms_r.xml", "WMS-r")
counts["WMS-vecteur"] = parse_wms("getcap_wms_v.xml", "WMS-v")
counts["WFS"] = parse_wfs()
counts["TMS"] = parse_tms()

# theme = namespace avant le premier "." (WFS : après le ":") ; producteur best-effort.
def theme_of(ident):
    base = ident.split(":")[-1]
    return base.split(".")[0].upper()

for r in records:
    r["theme"] = theme_of(r["identifier"])

# ---------- Dédoublonnage : clé canonique ----------
# WFS "ns:layer" -> layer ; upper ; retire millésimes (années/dates/.LATEST/éditions).
YEAR = re.compile(r'(?<![0-9])(19|20)\d{2}(?![0-9])')
DATE = re.compile(r'\d{4}[-_]\d{2}[-_]\d{2}')
def canon(ident):
    s = ident.split(":")[-1].upper()
    s = DATE.sub("", s)
    s = re.sub(r'\.LATEST$', '', s)
    s = YEAR.sub("", s)
    s = re.sub(r'[._-]V\d+$', '', s)
    s = re.sub(r'[._-]+$', '', s)
    s = re.sub(r'[._-]{2,}', '.', s)
    return s.strip("._-")

groups = {}
for r in records:
    k = canon(r["identifier"])
    g = groups.setdefault(k, dict(canon=k, identifiers=set(), titles=set(), themes=set(),
                                  services=set(), bboxes=[], abstracts=set()))
    g["identifiers"].add(r["identifier"])
    if r["title"]: g["titles"].add(r["title"])
    g["themes"].add(r["theme"])
    g["services"].add(r["service"])
    if r["abstract"]: g["abstracts"].add(r["abstract"][:400])
    if r["bbox"]: g["bboxes"].append(r["bbox"])

dedup = []
for k,g in groups.items():
    # bbox = union des bbox connues
    bxs = g["bboxes"]
    bbox = None
    if bxs:
        w = min(b[0] for b in bxs); e = max(b[1] for b in bxs)
        s = min(b[2] for b in bxs); nn = max(b[3] for b in bxs)
        bbox = (w,e,s,nn)
    dedup.append(dict(
        canon=k,
        title=sorted(g["titles"], key=len)[0] if g["titles"] else k,
        theme=sorted(g["themes"])[0],
        services=sorted(g["services"]),
        n_identifiers=len(g["identifiers"]),
        identifiers=sorted(g["identifiers"]),
        bbox=bbox,
        abstract=sorted(g["abstracts"], key=len, reverse=True)[0] if g["abstracts"] else "",
    ))

json.dump(records, open(os.path.join(HERE,"layers_raw.json"),"w"), ensure_ascii=False)
json.dump(dedup, open(os.path.join(HERE,"layers_dedup.json"),"w"), ensure_ascii=False)

raw_total = len(records)
print("RAW par service:", counts)
print("RAW total (lignes):", raw_total)
print("DEDUP (données distinctes):", len(dedup))
# combien de groupes multi-millésimes
multi = sum(1 for d in dedup if d["n_identifiers"]>1)
print("  dont groupes regroupant >1 identifiant:", multi)
