#!/usr/bin/env python3
# GEOPF-1 — étape 5 : chiffres finaux + regroupement des absentes par FAMILLE de produit.
import json,os,re
from collections import Counter,defaultdict
HERE=os.path.dirname(os.path.abspath(__file__))
r=json.load(open(os.path.join(HERE,"matched.json")))
dedup=json.load(open(os.path.join(HERE,"layers_dedup.json")))
raw=json.load(open(os.path.join(HERE,"layers_raw.json")))

# famille de produit : on rabote millésimes 2 & 4 chiffres, _DOM, GRID, R, dates, variantes de nom
def famille(rec):
    idt=rec["identifier"]; t=rec["title"]
    # CORINE : toutes variantes -> une famille
    if re.search(r'corine\s+land\s+cover|LANDCOVER|CLC|\bCHA\d',idt+" "+t,re.I): return ("CORINE Land Cover","LANDCOVER")
    if re.search(r'geodesie|g[ée]od[ée]sie|RGP|RDF|\bRN\b|RBF|nivellement|GNSS|point.?rdf|data_geod',idt+" "+t,re.I): return ("Réseaux géodésiques IGN","GEODESIE")
    if re.search(r'\bPOI\b|enseignement|ecole|écoles|gares|hospital|hôpit|santé|sante|pompiers|police|gendarm|thermau|personnes âgées|postau|camping|mus[ée]e|stade|sport|piscine|tourisme|administration locale|associations|justice|s[ée]curit[ée].?d[ée]fense|travail.?emploi',idt+" "+t,re.I): return ("Points d'intérêt / équipements (POI IGN)","POI")
    if re.search(r'SCAN\s?\d|carte des pentes|carte littorale|COASTALMAP|natural\s?earth|EDUGEO|mini-vue|OVERVIEW|Plan IGN J|habillage|graphe de mosa|pays du monde',idt+" "+t,re.I): return ("Fonds de carte / habillage (SCAN, pentes, littorale…)","BACKDROP")
    if re.search(r'patrimoine (architectural|culturel|naturel)|conservation du patrimoine',idt+" "+t,re.I): return ("Atlas des patrimoines (architectural/culturel/naturel)","PATRIMOINE")
    if re.search(r'stations? (class|verte)|pavillon bleu|clef ?verte',idt+" "+t,re.I): return ("Labels tourisme (stations classées/vertes, Pavillon bleu, Clef verte)","TOURISME")
    if re.search(r'potentiel (éolien|eolien|solaire|photovolt)|clé en main|stationnement.*photovolt',idt+" "+t,re.I): return ("Potentiel EnR (éolien/PV « clé en main »)","ENR")
    if re.search(r'carhab|habitats?_carhab',idt+" "+t,re.I): return ("CarHab — habitats naturels Réunion","ENV")
    if re.search(r'mesures compensatoires',idt+" "+t,re.I): return ("Mesures compensatoires biodiversité","ENV")
    if re.search(r'\bOFB\b|gestionnaire',idt+" "+t,re.I): return ("OFB — zones avis gestionnaire","ENV")
    if re.search(r'\bSCOT\b|coh[ée]rence territorial',idt+" "+t,re.I): return ("SCOT — schéma de cohérence territoriale","URBA")
    if re.search(r'\bENR\b|contraintes r[ée]glementaires.*habitat',idt+" "+t,re.I): return ("Contraintes réglementaires EnR / habitations","ENR")
    if re.search(r'r[ée]gions? [ée]cologiques',idt+" "+t,re.I): return ("Régions écologiques","ENV")
    if re.search(r'restrictions? UAS|drones?|circulation a[ée]rienne',idt+" "+t,re.I): return ("Restrictions aériennes / drones (UAS)","AERO")
    if re.search(r'pr[ée]dictions? de mar[ée]e',idt+" "+t,re.I): return ("Prédictions de marée (SHOM)","MER")
    if re.search(r'consommation.*[ée]lectric',idt+" "+t,re.I): return ("Consommation d'électricité par commune","ENERGIE")
    if re.search(r'plans? d.?eau',idt+" "+t,re.I): return ("Inventaire national des plans d'eau (INPE)","ENV")
    if re.search(r'prairies permanentes|BCAE|tourbi[èe]re',idt+" "+t,re.I): return ("Prairies permanentes / zones humides BCAE (PAC)","AGRI")
    if re.search(r'qualit[ée] de l.?air',idt+" "+t,re.I): return ("Stations qualité de l'air","ENV")
    if re.search(r'PLEIADES|SPOT',idt+" "+t,re.I): return ("Images satellite (Pléiades / SPOT)","ORTHO")
    if re.search(r'zones interdites|captation a[ée]rienne|RESTRICTEDAREA',idt+" "+t,re.I): return ("Zones interdites à la captation aérienne","AERO")
    if re.search(r'densit[ée] homog[èe]ne|\bZDH\b',idt+" "+t,re.I): return ("Zones de densité homogène (ZDH)","BRUIT")
    if re.search(r'noms|geographicalnames|toponym',idt+" "+t,re.I): return ("Toponymes / noms géographiques","TOPO")
    if re.search(r'estompage|SHADOW',idt+" "+t,re.I): return ("Estompage du relief","RELIEF")
    if re.search(r'test|voeux|festival|datacenter|\bproduct\b|communication|t[ée]l[ée]communication|carroyage insee',idt+" "+t,re.I): return ("Couches de test / hors-sujet","TEST")
    if re.search(r'ressources et [ée]quipements|salubrit|s[ée]curit[ée] publique|conservation',idt+" "+t,re.I): return ("Atlas des patrimoines — autres thèmes","PATRIMOINE")
    # défaut : famille = identifiant sans millésime
    base=re.sub(r'[._-]?\d{4}([._-]\d{2,4})?','',idt.split(":")[-1])
    return (rec["title"][:48] or base, rec["theme"])

cov=[x for x in r if x["verdict"]=="couvre"]
absent=[x for x in cov if x["labuse"]=="absente"]

fams=defaultdict(list)
for x in absent:
    f,thm=famille(x); fams[(thm,f)].append(x)

# chiffres inventaire
raw_by_svc=Counter(x["service"] for x in raw)
multi=sum(1 for d in dedup if d["n_identifiers"]>1)

print("=== INVENTAIRE ===")
print("brut par service:",dict(raw_by_svc),"total",len(raw))
print("dédoublonné:",len(dedup),"(dont",multi,"groupes multi-identifiants)")
print("\n=== FILTRE + TEST ===")
print("testés (emprise déclarée croise Réunion):",len(r))
print("verdicts:",Counter(x["verdict"] for x in r))
print("\n=== PARMI COUVRE ===",len(cov))
print(Counter(x["labuse"] for x in cov))
print("\n=== ABSENTES : familles de produit ===",len(fams),"familles pour",len(absent),"couches")
for (thm,f),g in sorted(fams.items(),key=lambda kv:-len(kv[1])):
    print(f"  [{len(g):2}] {thm:12} | {f}")

# écrire un json des familles pour le rapport
out={ "familles":[{"theme":thm,"famille":f,"n_couches":len(g),
                    "exemples":[x["identifier"] for x in g[:3]]} for (thm,f),g in
                    sorted(fams.items(),key=lambda kv:-len(kv[1]))] }
json.dump(out,open(os.path.join(HERE,"absentes_familles.json"),"w"),ensure_ascii=False,indent=1)
