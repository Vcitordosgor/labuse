#!/usr/bin/env python
"""NU5-A — produit un extrait COMPACT de resultats.json (preuves versionnables).

resultats.json (brut, ~7 Mio : JSON intégral de chaque appel) n'est PAS versionné
(rejouable via harness.py, et bloqué par le hook >2 Mio). Ce script en extrait, par
parcelle × outil, le statut + les champs clés sur lesquels s'appuie le RAPPORT.
→ preuves/resultats_resume.json (quelques dizaines de Ko).
"""
from __future__ import annotations
import json

R = json.load(open("docs/audit-2026-11/nu-5/A/preuves/resultats.json"))
def g(d,*ks,default=None):
    for k in ks:
        if not isinstance(d,dict): return default
        d=d.get(k)
    return d if d is not None else default
def J(c): return c.get("json",{}) if isinstance(c,dict) else {}
def S(c): return c.get("status") if isinstance(c,dict) else None

out={"base":R.get("base"),"parcelles":{}}
for piege,blk in R["parcelles"].items():
    o=blk["outils"]; f=blk["fiche"]
    out["parcelles"][piege]={
      "idu":blk["idu"],"commune":blk["commune"],"fiche":f,
      "outils":{
        "risques":{"status":S(o.get("risques")),"n":g(J(o.get("risques")),"n"),
                   "categories":[s.get("categorie") for s in g(J(o.get("risques")),"servitudes",default=[])]},
        "gabarit":{"status":S(o.get("gabarit")),"etat":g(J(o.get("gabarit")),"status"),
                   "message":g(J(o.get("gabarit")),"message"),
                   "zoneImplantationM2":g(J(o.get("gabarit")),"zoneImplantationM2"),
                   "hauteur":g(J(o.get("gabarit")),"hauteurReglementaireM"),
                   "coverage":g(J(o.get("gabarit")),"coverage"),
                   "multizone":g(J(o.get("gabarit")),"raccordement","multizone")},
        "taxe_prefill":{"status":S(o.get("taxe_prefill")),"zone_plu":g(J(o.get("taxe_prefill")),"zone_plu"),
                   "surface_terrain_m2":g(J(o.get("taxe_prefill")),"surface_terrain_m2"),
                   "sdp_gabarit_m2":g(J(o.get("taxe_prefill")),"sdp_gabarit_m2"),
                   "taux_communal_pct":g(J(o.get("taxe_prefill")),"taux_communal_pct")},
        "estimation":{"status":S(o.get("estimation")),"median":g(J(o.get("estimation")),"median"),
                   "n":g(J(o.get("estimation")),"n"),"fiabilite":g(J(o.get("estimation")),"fiabilite_mot"),
                   "type":g(J(o.get("estimation")),"type_comparateur"),"note":g(J(o.get("estimation")),"note"),
                   "valeur_indicative":g(J(o.get("estimation")),"valeur_indicative")},
        "solaire":{"status":S(o.get("solaire_parcelle")),"ok":g(J(o.get("solaire_parcelle")),"ok"),
                   "productible":g(J(o.get("solaire_parcelle")),"productible"),"abf":g(J(o.get("solaire_parcelle")),"abf")},
        "temps":{"status":S(o.get("temps_epoque")),"n_features":len(g(J(o.get("temps_epoque")),"features",default=[])),
                   "millesimes":g(J(o.get("temps_epoque")),"millesimes")},
        "parcelle_permis":{"status":S(o.get("parcelle_permis")),
                   "n":len(g(J(o.get("parcelle_permis")),"permis",default=g(J(o.get("parcelle_permis")),"items",default=[])))},
        "comparer":{"status":S(o.get("comparer")),"count":g(J(o.get("comparer")),"count"),
                   "p0":{kk:g((J(o.get("comparer")).get("parcels") or [{}])[0],kk) for kk in
                         ("surface_m2","zone","sdp_max_m2","sdp_residuelle_m2","proprietaire","constructible")}},
        "etude_zone":{"status":S(o.get("etude_zone")),"zone_disponible":g(J(o.get("etude_zone")),"zone_disponible"),
                   "rayon_km":g(J(o.get("etude_zone")),"rayon_km"),"habitants":g(J(o.get("etude_zone")),"population","habitants")},
        "calculette":{"status":S(o.get("calculette")),"calculable":g(J(o.get("calculette")),"calculable"),
                   "charge_central":g(J(o.get("calculette")),"charge_fonciere","central"),
                   "par_m2":g(J(o.get("calculette")),"charge_fonciere","par_m2_terrain")},
        "patrimoine":("skip" if (isinstance(o.get("patrimoine"),dict) and o["patrimoine"].get("skip"))
                      else {"status":S(o.get("patrimoine")),"nom":g(J(o.get("patrimoine")),"nom")}),
        "assemblage_seule":{"status":S(o.get("assemblage_seule"))},
        "communes_acq":{"status":S(o.get("communes_acq")),"n":g(J(o.get("communes_acq")),"n")},
      }}
json.dump(out, open("docs/audit-2026-11/nu-5/A/preuves/resultats_resume.json","w"),
          ensure_ascii=False, indent=1, default=str)
print("resume écrit")
