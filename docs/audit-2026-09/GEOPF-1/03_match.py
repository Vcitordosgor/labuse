#!/usr/bin/env python3
# GEOPF-1 — étape 4 : présence LABUSE pour chaque couche qui COUVRE La Réunion.
# Trois valeurs : "deja_en_couche" / "en_base" / "absente".
# Preuves LABUSE : (1) identifiant geopf cité en dur dans le dépôt (référence directe, le plus fort),
#                  (2) recouvrement de jetons du TITRE avec un nom de couche declarations/,
#                  (3) idem avec un nom de source data_sources.
import json,os,re,csv,unicodedata

HERE=os.path.dirname(os.path.abspath(__file__))

def strip(s):
    s=unicodedata.normalize("NFD",s or "")
    s="".join(c for c in s if unicodedata.category(c)!="Mn")
    return s.lower()

STOP=set("de des du la le les et en un une a au aux pour par sur dans ce d l n s reunion "
         "carte cartes zone zones plan plans donnee donnees couche couches national nationale "
         "regional systeme information base v1 v2 v3 v5 ign 974 976 971 972 973 point points "
         "limite limites edition derniere type i ii ligne lignes secteur secteurs".split())
def toks(s):
    s=strip(s)
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return set(t for t in s.split() if len(t)>2 and t not in STOP)

# ---- 1) références geopf directes de LABUSE (curées à partir des grep du dépôt) ----
# préfixe d'identifiant geopf -> (presence, quoi chez LABUSE)
LABUSE_DIRECT={
 "ORTHOIMAGERY.ORTHOPHOTOS":("deja_en_couche","BD ORTHO / Remonter le temps (fond ortho)"),
 "ELEVATION.CONTOUR.LINE":("deja_en_couche","Courbes de niveau (couche fiche)"),
 "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES":("en_base","RGE ALTI / profil altimétrique"),
 "IGNF_LIDAR-HD_MNH":("en_base","LiDAR HD MNH 50 cm (data_sources #70)"),
 "ELEVATIONGRIDCOVERAGE.RGR92UTM40S":("en_base","LiDAR HD MNH (data_sources #70)"),
 "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2":("en_base","Plan IGN v2 (fond de carte)"),
 "OCSGE":("deja_en_couche","Artificialisation (OCS GE) — couche"),
 "OCS-GE":("deja_en_couche","Artificialisation (OCS GE) — couche"),
 "BDTOPO_V3":("en_base","BD TOPO IGN (data_sources #17)"),
 "BDTOPO":("en_base","BD TOPO IGN (data_sources #17)"),
 "BDCARTO_V5":("en_base","BD CARTO V5 (data_sources #22)"),
 "BDCARTO":("en_base","BD CARTO V5 (data_sources #22)"),
 "BAN-PLUS":("en_base","BAN PLUS (data_sources #147)"),
 "CADASTRALPARCELS":("en_base","Cadastre (API Carto/Etalab, data_sources #1/#2)"),
 # familles IGN produit-identiques que LABUSE ingère déjà :
 "ADMINEXPRESS":("en_base","ADMIN EXPRESS — contours communes/dép. (data_sources #148)"),
 "ADMIN_EXPRESS":("en_base","ADMIN EXPRESS (data_sources #148)"),
 "ADMIN-EXPRESS":("en_base","ADMIN EXPRESS (data_sources #148)"),
 "INSEE.FILOSOFI":("en_base","Filosofi INSEE carreaux 200 m (data_sources)"),
 "INSEE.BPE":("en_base","BPE INSEE (data_sources)"),
 "RGEALTI":("en_base","RGE ALTI (data_sources #6/#65)"),
 "IGNF_LIDAR-HD_MNS":("en_base","LiDAR HD MNS (data_sources #70)"),
 "IGNF_LIDAR-HD_MNT":("en_base","LiDAR HD MNT (data_sources #70)"),
 "CoSIA":("en_base","CoSIA (data_sources #83)"),
 "COSIA":("en_base","CoSIA (data_sources #83)"),
 "IGNF_COSIA":("en_base","CoSIA (data_sources #83)"),
 "RPG":("en_base","RPG déclarations agricoles (data_sources #10)"),
 "IGNF_RPG":("en_base","RPG (data_sources #10)"),
 "PARCELLES_GRAPHIQUES":("en_base","RPG parcelles graphiques (data_sources #10)"),
 # noms INSPIRE de données IGN que LABUSE ingère en masse :
 "ADMINISTRATIVEUNITS":("en_base","ADMIN EXPRESS (data_sources #148)"),
 "LIMITES_ADMINISTRATIVES":("en_base","ADMIN EXPRESS (data_sources #148)"),
 "AU.":("en_base","ADMIN EXPRESS — unités administratives (#148)"),
 "AU:":("en_base","ADMIN EXPRESS (#148)"),
 "BU.":("en_base","BD TOPO bâtiments (#17)"),
 "BU:":("en_base","BD TOPO bâtiments (#17)"),
 "HY.":("en_base","BD TOPO / hydrographie (#17)"),
 "HY:":("en_base","BD TOPO / hydrographie (#17)"),
 "CP.":("en_base","Cadastre / BD Parcellaire (#1/#2)"),
 "CP:":("en_base","Cadastre (#1/#2)"),
 "DIVCAD":("en_base","BD Parcellaire / cadastre (#1/#2)"),
 "TN.":("en_base","BD TOPO — réseaux de transport (#17)"),
 "TN:":("en_base","BD TOPO transport (#17)"),
 "TRANSPORTNETWORK":("en_base","BD TOPO — réseaux de transport (#17) / axes structurants"),
 "IGNF_TRANSPORTNETWORKS":("en_base","BD TOPO transport (#17)"),
}

# ---- 2/3) index de jetons LABUSE + synonymes ----
COUCHES=[]  # (nom, tokens)
for f in os.listdir(os.path.join(HERE,"..","..","..","declarations","couches")):
    pass
DECL=os.path.join(HERE,"..","..","..","declarations","couches")
import glob
for path in glob.glob(os.path.join(DECL,"*.yaml")):
    for line in open(path,encoding="utf-8"):
        m=re.match(r'\s*nom:\s*"?(.+?)"?\s*$',line)
        if m: COUCHES.append((m.group(1),toks(m.group(1))))

DS=[]  # (name, tokens)
tsv=open(os.path.join(HERE,"cache","data_sources.tsv"),encoding="utf-8").read().splitlines()
for line in tsv[1:]:
    parts=line.split("\t")
    if len(parts)>=2 and parts[1]!="name": DS.append((parts[1],toks(parts[1])))

# synonymes : jeton geopf (FR/EN) -> jetons LABUSE équivalents
SYN={
 "orthophotos":{"ortho"},"orthophoto":{"ortho"},"altitude":{"alti","altimetrie"},
 "batiment":{"bati","topo","rnb"},"batiments":{"bati","topo","rnb"},
 "parcellaire":{"cadastre","cadastral","parcelle","parcelles"},"cadastraux":{"cadastre"},
 "bruit":{"bruit","sonore"},"inondation":{"inondation","tri","azi"},
 "mouvement":{"mouvement","cavite"},"mouvements":{"mouvement"},
 "protege":{"protege","znieff","enp","natura"},"protegees":{"protege"},
 "znieff":{"znieff"},"boise":{"ebc","boises","foret"},"boises":{"ebc","foret"},
 "foret":{"foret","onf","ebc"},"forets":{"foret"},
 "preemption":{"preemption","dpu"},"servitude":{"servitude","sup"},"servitudes":{"sup"},
 "reserve":{"reserve","er"},"reserves":{"reserve","er"},
 "urbanisme":{"urbanisme","plu","gpu"},"urba":{"plu","gpu"},"plu":{"plu","urbanisme"},
 "assainissement":{"assainissement","vrd"},"bruits":{"bruit"},
 "risque":{"risque","ppr"},"risques":{"ppr","risque"},"prevention":{"ppr"},
 "electrique":{"electrique","edf","hta","htb"},"electriques":{"edf"},
 "transport":{"transport","tcsp","gtfs"},"transports":{"transport"},
 "occupation":{"ocs","cosia","occupation"},"sol":{"ocs","sol","cosia"},"sols":{"sis","sol","pollue"},
 "administratif":{"admin","commune","communes"},"communes":{"commune","admin"},"commune":{"commune"},
 "hydrographie":{"hydrographie","ravine","bassin","versant","eau"},"eau":{"eau","ravine"},
 "agricole":{"agricole","rpg","safer"},"agricoles":{"rpg"},
 "adresse":{"adresse","ban"},"adresses":{"ban"},
 "littoral":{"littoral","cote","erosion","pas"},"cote":{"cote","erosion","trait"},
 "pollue":{"pollue","casias","sis"},"pollues":{"casias","sis"},"industriel":{"casias","icpe"},
 "monument":{"abf","monument"},"monuments":{"abf"},"patrimoine":{"abf","zppa","patrimoine"},
 "archeolog":{"zppa","archeolog"},"parc":{"parc"},"national":{"parc"},
 "iris":{"iris"},"population":{"insee","iris","rp"},"logement":{"logement","rpls","lls"},
}
def expand(ts):
    out=set(ts)
    for t in ts: out|=SYN.get(t,set())
    return out

def best_overlap(title_tokens, vocab):
    tt=expand(title_tokens)
    best=(0,None)
    for name,vt in vocab:
        ov=len(tt & vt)
        if ov>best[0]: best=(ov,name)
    return best

# Règles curées sur le TITRE ou l'identifiant, appliquées après la référence directe.
# (mêmes données que LABUSE possède déjà, mais publiées par l'IGN sous un nom technique
#  qui ne string-matche pas le vocabulaire LABUSE.)
EXTRA_RULES=[
 (r'patrinat|znieff|r[ée]serves?\s+(naturelle|biologique)|ramsar|biotope|arr[êe]t[ée]\s+de\s+protection|conservatoire\s+(du\s+)?littoral|parcs?\s+national|\bp\.?n\.?\b|site\s+class|patrimoine\s+mondial|\binpg\b|espaces?\s+prot[ée]g',
   "en_base","Espaces protégés (INPN #25 / ZNIEFF #76 / DEAL Carmen RAMSAR / Parc national)"),
 (r'territoires?\s+des\s+epci|\bepci\b',"en_base","Périmètres EPCI (data_sources EPCI/ORT)"),
 (r'bd\s?parcellaire',"en_base","Cadastre / BD Parcellaire (#1/#2)"),
 (r'^prescriptions?\s+(lin[ée]aire|ponctuelle|surfacique)|^informations?\s+(lin[ée]aire|ponctuelle|surfacique)|zone[_ ]?urba|document\s+d.?urbanisme',
   "en_base","GPU/PLU — prescriptions & zonages (API Carto #3/#44/#105/#106/#107)"),
]
def match(rec):
    ident=rec["identifier"]; title=rec["title"]
    for pref,(pres,quoi) in LABUSE_DIRECT.items():
        if ident.upper().startswith(pref.upper()) or ident.upper().split(":")[0]==pref.upper():
            return pres,quoi,"ref-directe"
    tl=strip(title)
    for pat,pres,quoi in EXTRA_RULES:
        if re.search(pat,tl):
            return pres,quoi,"regle-titre"
    tt=toks(title)
    cov=best_overlap(tt,COUCHES)
    bo=best_overlap(tt,DS)
    # ≥2 jetons partagés : match fiable (1 seul jeton → faux positifs sur « haute », « droit »…)
    if cov[0]>=2:
        return "deja_en_couche",cov[1],f"jetons({cov[0]})"
    if bo[0]>=2:
        return "en_base",bo[1],f"jetons({bo[0]})"
    # jeton unique mais spécifique au domaine (liste blanche) → présence confirmée
    for t in tt:
        if t in STRONG_SINGLE:
            pres,quoi=STRONG_SINGLE[t]
            return pres,quoi,f"jeton-fort({t})"
    return "absente","",""

# jetons uniques mais sans ambiguïté : impliquent seuls une donnée LABUSE
STRONG_SINGLE={
 "bati":("en_base","BD TOPO bâti / RNB"),"batiment":("en_base","BD TOPO bâti / RNB"),
 "batiments":("en_base","BD TOPO bâti / RNB"),
 "hydrographie":("deja_en_couche","Bassins versants (hydrographie)"),
 "foret":("deja_en_couche","Forêts publiques"),"forets":("deja_en_couche","Forêts publiques"),
 "cadastre":("en_base","Cadastre (API Carto/Etalab)"),"cadastral":("en_base","Cadastre"),
 "cadastrales":("en_base","Cadastre"),"parcellaire":("en_base","Cadastre / BD Parcellaire"),
 "ortho":("en_base","BD ORTHO"),"orthophoto":("en_base","BD ORTHO"),"orthophotos":("en_base","BD ORTHO"),
 "lidar":("en_base","LiDAR HD (data_sources #70)"),
 "bruit":("deja_en_couche","Classement sonore / cartes de bruit"),
 "icpe":("deja_en_couche","Installations classées (ICPE)"),
 "cavite":("deja_en_couche","Cavités souterraines"),"cavites":("deja_en_couche","Cavités souterraines"),
 "ebc":("deja_en_couche","Espaces boisés classés (EBC)"),
 "qpv":("deja_en_couche","Quartiers prioritaires (QPV)"),
 "safer":("deja_en_couche","Foncier agricole (RPG/SAFER)"),
 "sitadel":("en_base","SITADEL (data_sources #16)"),
 "iris":("en_base","Contours IRIS (data_sources #64)"),
}

# producteur inféré (les GetCapabilities ne portent pas le producteur par couche)
def producteur(ident,title,theme):
    s=(ident+" "+title+" "+theme).lower()
    if re.search(r'corine|landcover',s): return "SDES / Union européenne (CORINE)"
    if re.search(r'filosofi|insee|carroyage',s): return "INSEE"
    if re.search(r'patrinat|znieff|protectedarea|biotope|ramsar|conservatoire',s): return "INPN/MNHN · OFB"
    if re.search(r'\bofb\b',s): return "OFB"
    if re.search(r'shom|mar[ée]e',s): return "SHOM"
    if re.search(r'dgac|drone|uas|captation a[ée]rienne',s): return "DGAC"
    if re.search(r'georisqu|gaspar|pprn|cavit|mouvement de terrain',s): return "BRGM / Géorisques"
    if re.search(r'deal|carmen|lizmap',s): return "DEAL Réunion"
    if re.search(r'potentiel (éol|eol|solaire|photov)|enr\b|consommation.*électr|clé en main',s): return "ADEME / opérateurs EnR"
    if re.search(r'carhab|nature en ville',s): return "PatriNat / IGN"
    if re.search(r'clef ?verte|pavillon bleu|station (classée|verte)|tourisme',s): return "opérateurs tourisme / DGE"
    if re.search(r'scot|urba|prescription|gpu',s): return "DGALN / GPU"
    return "IGN / Géoplateforme (ou partenaire)"

def main():
    res=json.load(open(os.path.join(HERE,"probe_results.json")))
    for r in res:
        r["couvre"]= (r["verdict"]=="couvre")
    covering=[r for r in res if r["couvre"]]
    for r in res:
        p,quoi,how=match(r)
        r["labuse"]=p; r["labuse_quoi"]=quoi; r["labuse_comment"]=how
    # CSV complet
    cols=["identifier","title","theme","services","verdict","labuse","labuse_quoi","labuse_comment","method","detail"]
    with open(os.path.join(HERE,"GEOPF-REUNION.csv"),"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(["identifiant","titre","producteur_infere","theme","service","verdict_reunion","presence_labuse","labuse_quoi","labuse_preuve","methode_test","detail_test"])
        for r in sorted(res,key=lambda x:(x["verdict"]!="couvre",x["theme"],x["title"])):
            w.writerow([r["identifier"],r["title"],producteur(r["identifier"],r["title"],r["theme"]),
                        r["theme"],"|".join(r["services"]),r["verdict"],
                        r["labuse"],r["labuse_quoi"],r["labuse_comment"],r["method"],r["detail"]])
    json.dump(res,open(os.path.join(HERE,"matched.json"),"w"),ensure_ascii=False)
    # chiffres
    from collections import Counter
    print("Total testés:",len(res))
    print("Verdicts:",Counter(r["verdict"] for r in res))
    print("Parmi COUVRE — présence LABUSE:",Counter(r["labuse"] for r in covering))
    absent=[r for r in covering if r["labuse"]=="absente"]
    print("Absentes qui couvrent:",len(absent))
    print("Thèmes des absentes:",Counter(r["theme"] for r in absent).most_common(12))

if __name__=="__main__":
    main()
