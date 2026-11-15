#!/usr/bin/env python3
"""Consolide MATRICE.csv : parcelle × fait × source × valeur (FICHE / DOSSIER / ORACLE),
avec colonne divergence. Lit fiche.json + dossier.txt (~/Desktop/chasse-1) + oracle.csv.
LECTURE SEULE."""
import csv, json, glob, os, re
AUD="/Users/openclaw/Desktop/labuse-chasse/docs/audit-2026-11/chirurgical-1"
CH=os.path.expanduser("~/Desktop/chasse-1")
SAMPLE=os.path.join(AUD,"echantillon.csv")

def num(x):
    if x is None: return None
    m=re.search(r"-?[\d  \xa0]+(?:[.,]\d+)?",str(x))
    if not m: return None
    try: return float(m.group(0).replace(" ","").replace("\xa0","").replace(" ","").replace(",","."))
    except: return None

# oracle
orc={}
for ln in open(os.path.join(AUD,"oracle.csv")):
    p=ln.rstrip("\n").split("|")
    if len(p)==3: orc.setdefault(p[0],{})[p[1]]=p[2]

meta={r["idu"]:r for r in csv.DictReader(open(SAMPLE))}
rows=[]  # idu, famille, fait, source, valeur
div=[]   # idu, fait, valeurs, note

def add(idu,fam,fait,src,val):
    rows.append([idu,fam,fait,src,"" if val is None else str(val)])

for fj in sorted(glob.glob(f"{CH}/974*/fiche.json")):
    idu=os.path.basename(os.path.dirname(fj)); fam=meta.get(idu,{}).get("famille","")
    d=json.load(open(fj)); o=orc.get(idu,{})
    txt=""
    tp=f"{CH}/{idu}/dossier.txt"
    if os.path.exists(tp): txt=open(tp).read()
    # --- SURFACE ---
    s_fiche=d.get("surface_m2"); s_cad=d.get("contenance_m2") or d.get("surface_terrain_m2")
    s_orc=num(o.get("surface_sql_m2"))
    add(idu,fam,"surface_dessin_m2","FICHE",round(s_fiche,1) if s_fiche else None)
    add(idu,fam,"surface_cadastre_m2","FICHE",s_cad)
    add(idu,fam,"surface_m2","ORACLE(ST_Area)",s_orc)
    if s_fiche and s_orc and abs(s_fiche-s_orc)>max(1,0.01*s_fiche):
        div.append([idu,"surface_m2",f"fiche={s_fiche:.1f} oracle={s_orc}","ecart surface vs recompute"])
    # --- ZONE ---
    pab=d.get("potentiel_a_batir") or {}
    add(idu,fam,"zone_fam","FICHE",pab.get("zone_fam"))
    add(idu,fam,"zone_lib","FICHE",pab.get("zone_lib"))
    zparts={k:o[k] for k in o if k.startswith("zone_part_")}
    add(idu,fam,"zone_parts","ORACLE"," ".join(f"{k.replace('zone_part_','')}={v}%" for k,v in zparts.items()))
    # --- CONSTRUCTIBLE ---
    add(idu,fam,"constructible","FICHE",pab.get("constructible"))
    add(idu,fam,"constructible_motif","FICHE",(pab.get("motif") or pab.get("libelle")))
    add(idu,fam,"sdp_restante_m2","FICHE",pab.get("sdp_restante_m2"))
    # --- EMPRISE ---
    lb=d.get("le_bien") or {}
    e_lb=lb.get("emprise_batie_m2"); e_orc=num(o.get("emprise_bdtopo_union_m2"))
    add(idu,fam,"emprise_batie_m2","FICHE(le_bien)",e_lb)
    add(idu,fam,"emprise_batie_m2","ORACLE(BDTOPO union)",e_orc)
    sv=d.get("score_v2") or {}
    m=re.search(r"emprise\s+([\d  ]+)\s*m²",str(sv.get("motif") or ""))
    e_sc=num(m.group(1)) if m else None
    if e_sc is not None:
        add(idu,fam,"emprise_batie_m2","SCORE_MOTIF",e_sc)
        if e_lb and abs(e_sc-e_lb)>max(5,0.1*e_lb):
            div.append([idu,"emprise_batie_m2",f"le_bien={e_lb} score_motif={e_sc} oracle_union={e_orc}","score motif (run figé) ≠ emprise servie — cf. calcul de nuit gelé"])
    if e_lb is not None and e_orc is not None and abs(e_lb-e_orc)>max(5,0.1*max(e_lb,1)):
        div.append([idu,"emprise_batie_m2",f"le_bien={e_lb} oracle={e_orc}","emprise servie vs recompute union"])
    # --- HAUTEUR ---
    add(idu,fam,"hauteur_faitage_m","FICHE",lb.get("hauteur_faitage_m"))
    # --- ALEAS (niveau+part) ---
    al=d.get("aleas") or {}
    add(idu,fam,"aleas","FICHE","; ".join(f'{a.get("nature")}/{a.get("niveau")}/{a.get("part_pct")}%' for a in (al.get("liste") or [])))
    af={k:o[k] for k in o if k.startswith("alea_fort_")}
    add(idu,fam,"aleas_fort","ORACLE"," ".join(f"{k.replace('alea_fort_','')}={v}%" for k,v in af.items()))
    # --- SCORE ---
    add(idu,fam,"score_tier","FICHE",sv.get("tier"))
    add(idu,fam,"score_label","FICHE",sv.get("label"))
    add(idu,fam,"score_declasse","FICHE",sv.get("declasse"))
    # --- PRIX / ESTIMATION ---
    dvf=d.get("dvf_parcelle") or {}
    terr=next((x for x in (dvf.get("secteur") or []) if x.get("type_bien")=="terrain"),None)
    if terr:
        add(idu,fam,"prix_m2_terrain_secteur","FICHE",terr.get("mediane_prix_m2"))
        add(idu,fam,"n_ventes_terrain_secteur","FICHE",terr.get("n_ventes"))
        add(idu,fam,"prix_fenetre","FICHE",terr.get("fenetre"))
    add(idu,fam,"estimation_terrain_eur","FICHE",dvf.get("valeur_terrain_secteur_eur"))
    dm=dvf.get("derniere_mutation")
    add(idu,fam,"derniere_vente","FICHE",(dm or {}).get("date_mutation") if dm else "(aucune)")
    add(idu,fam,"derniere_vente","ORACLE",o.get("derniere_vente"))
    # --- DPU / TAXE / PLU ---
    disp=d.get("dispositifs") or {}
    add(idu,fam,"dpu","FICHE",(disp.get("dpu") or {}).get("etat"))
    tx=d.get("taxe_amenagement") or {}
    add(idu,fam,"taxe_taux_communal_pct","FICHE",tx.get("taux_communal_pct"))
    add(idu,fam,"plu_fraicheur","FICHE",d.get("plu_fraicheur"))
    # --- PENTE ---
    add(idu,fam,"pente_moy_pct","ORACLE",o.get("pente_moy_pct"))
    # --- DOSSIER anomalies (hors faux positif 'nulle') ---
    anoms=[t for t in ["None","NaN","undefined","Traceback","KeyError","{{","}}"] if t in txt]
    if anoms: div.append([idu,"dossier_texte","; ".join(anoms),"jeton de dev dans le PDF"])

with open(os.path.join(AUD,"MATRICE.csv"),"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["idu","famille","fait","source","valeur"]); w.writerows(rows)
with open(os.path.join(AUD,"DIVERGENCES_auto.csv"),"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["idu","fait","valeurs","note"]); w.writerows(div)
print(f"MATRICE.csv: {len(rows)} lignes / {len(set(r[0] for r in rows))} parcelles")
print(f"DIVERGENCES_auto.csv: {len(div)} divergences")
for dd in div: print("  ",dd)
