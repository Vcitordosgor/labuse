"""COMMUNE-AUDIT-1 — grille 19 cartes × 24 communes. Rubrique (documentée dans le rapport) :
  réelle    = la carte s'affiche avec une valeur concrète, sans réserve du code
  à valider = la carte s'affiche MAIS le code lève une réserve pour cette commune
              (perime/à rafraîchir · sous_seuil · statut 'document local'/source nulle ·
               non projetable · calculable=false)
  vide      = la carte NE s'affiche PAS (condition fausse) OU n'a qu'une valeur nulle/« non déterminée »
Encodage fidèle aux conditions de rendu de ContextePanel.tsx + payload servi + aux (rarete/marche)."""
import json
P=json.load(open("qa/commune_audit1_payloads.json"))
A=json.load(open("qa/commune_audit1_aux.json"))
communes=sorted(P.keys())

def classify(name, p, r, mar):
    def has(x): return x is not None
    if name=="regle-plu":
        s=p.get("plu_statut") or {}
        if s.get("statut") in (None,): return "vide"
        if s.get("statut")=="document local" or not s.get("source"): return "à valider"
        return "réelle"
    if name=="regle-zan":
        if not r: return "vide"
        reste=r.get("reste_zan_ha"); hz=r.get("horizon_epuisement_ans")
        if reste is None and hz is None: return "vide"
        if hz is None: return "à valider"
        return "réelle"
    if name=="regle-sru":
        s=p.get("sru")
        if not s: return "vide"
        return "réelle" if s.get("taux_lls") is not None else "à valider"
    if name=="construire":
        pb=p.get("permis_bloc") or {}
        if pb.get("permis_12m") is None: return "vide"
        return "réelle" if pb.get("delai_median_mois") is not None else "à valider"
    if name=="regle-plh":
        plh=p.get("plh")
        if not plh: return "vide"
        return "réelle" if plh.get("obj_logements_an") is not None else "à valider"
    if name=="marche":
        c=p.get("comparable") or {}
        return "réelle" if c.get("ancien_median_eur_m2") is not None else "vide"
    if name=="terrain-nu":
        f=p.get("foncier") or {}; pz=((f.get("prix_terrain_nu") or {}).get("par_zone")) or None
        if not pz: return "vide"
        u=(pz.get("U") or {})
        return "réelle" if u.get("calculable") else "à valider"
    if name=="annonces":
        ma=p.get("marche_annonces")
        if not ma: return "vide"
        return "à valider" if ma.get("sous_seuil") else "réelle"
    if name=="loyer":
        l=p.get("loyer")
        if not l: return "vide"
        return "réelle" if l.get("median_eur_m2") is not None else "vide"
    if name=="zonage-abc":
        z=p.get("zonage_abc")
        return "réelle" if z else "vide"
    if name=="fiscalite":
        fi=p.get("fiscalite")
        if not fi: return "vide"
        if fi.get("tfpb_commune_pct") is None: return "vide"
        return "à valider" if fi.get("perime") else "réelle"
    if name=="ort":
        o=p.get("ort")
        if not o or o.get("statut")=="hors": return "vide"
        return "réelle"
    if name=="zfang-frr":
        return "réelle" if p.get("zfang_frr") else "vide"
    if name=="foncier":
        f=p.get("foncier")
        if not f: return "vide"
        return "réelle" if f.get("n_parcelles") is not None else "vide"
    if name=="zonage":
        f=p.get("foncier") or {}
        return "réelle" if f.get("repartition_zonage") else "vide"
    if name=="risques":
        rq=p.get("risques") or {}
        if rq.get("ppr_pct") is not None: return "réelle"
        if rq.get("catnat_arretes") or rq.get("parc_national") or rq.get("mouvement_terrain_pct") is not None or rq.get("azi_tri"):
            return "à valider"
        return "vide"
    if name=="population":
        pop=p.get("population") or {}
        return "réelle" if pop.get("habitants") is not None else "vide"
    if name=="qpv":
        if (len(p.get("qpv") or [])>0) or (len(p.get("anru") or [])>0): return "réelle"
        return "vide"
    if name=="contacts":
        m=p.get("mairie")
        if not m: return "vide"
        core=[m.get("adresse"),m.get("telephone"),m.get("email"),m.get("site_officiel")]
        return "réelle" if any(core) else "à valider"
    return "?"

CARDS=[("regle-plu","Règles d'urbanisme"),("regle-zan","Enveloppe ZAN"),("regle-sru","Logement social — SRU"),
 ("construire","Permis & délais"),("regle-plh","Programme local — PLH"),("marche","Prix & tendance"),
 ("terrain-nu","Terrain nu"),("annonces","Annonces — Radar"),("loyer","Loyers"),
 ("zonage-abc","Zonage logement ABC"),("fiscalite","Taxe foncière"),("ort","Revitalisation ACV/PVD/ORT"),
 ("zfang-frr","ZFANG / FRR"),("foncier","Foncier repéré"),("zonage","Zonage (répartition)"),
 ("risques","Risques"),("population","Population & logement"),("qpv","Quartiers prioritaires"),
 ("contacts","Mairie & urbanisme")]

grid={}
tot={"réelle":0,"à valider":0,"vide":0}
rows=[]
for cid,lbl in CARDS:
    counts={"réelle":0,"à valider":0,"vide":0}
    per={}
    for c in communes:
        p=P[c]["payload"]; r=A["rarete"].get(c); mar=A["marche"].get(c)
        cl=classify(cid,p,r,mar); counts[cl]+=1; per[c]=cl; tot[cl]+=1
    grid[cid]={"label":lbl,"counts":counts,"per":per}
    rows.append((lbl,counts["réelle"],counts["à valider"],counts["vide"]))

print(f"{'CARTE':30s} {'réelle':>7s} {'à valider':>10s} {'vide':>5s}")
for lbl,re,av,vd in rows:
    print(f"{lbl:30s} {re:7d} {av:10d} {vd:5d}")
print("-"*56)
print(f"{'TOTAL (19×24=456 cellules)':30s} {tot['réelle']:7d} {tot['à valider']:10d} {tot['vide']:5d}")
json.dump(grid, open("qa/commune_audit1_grid.json","w"), ensure_ascii=False, indent=1)

# lists for à valider / vide detail
print("\n=== à valider (détail communes) ===")
for cid,lbl in CARDS:
    av=[c for c,v in grid[cid]["per"].items() if v=="à valider"]
    if av: print(f"  {lbl}: {', '.join(av)}")
print("\n=== vide (détail communes) ===")
for cid,lbl in CARDS:
    vd=[c for c,v in grid[cid]["per"].items() if v=="vide"]
    if vd: print(f"  {lbl}: {', '.join(vd)}")
