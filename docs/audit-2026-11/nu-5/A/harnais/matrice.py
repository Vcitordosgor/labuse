#!/usr/bin/env python
"""NU5-A — matrice outil × parcelle (vert/orange/rouge) depuis preuves/resultats.json.

Règles de verdict (documentées) :
  V (vert)    : l'outil répond ET le chiffre est cohérent avec la fiche / le métier.
  O (orange)  : l'outil répond mais réserve de cohérence, de libellé ou de logique.
  R (rouge)   : plante, invente un fait, ou renvoie un chiffre faux présenté comme sûr.
  - (n/a)     : non applicable à cette parcelle (ex. Patrimoine sans personne morale).

Écrit preuves/matrice.csv.
"""
from __future__ import annotations
import json, csv

R = json.load(open("docs/audit-2026-11/nu-5/A/preuves/resultats.json"))

def g(d,*ks,default=None):
    for k in ks:
        if not isinstance(d,dict): return default
        d=d.get(k)
    return d if d is not None else default
def J(c): return c.get("json",{}) if isinstance(c,dict) else {}
def ok(c): return isinstance(c,dict) and c.get("status")==200

COLS = ["risques","gabarit","taxe","estimer","solaire","temps","permis","comparer","etude_zone","calculette","patrimoine"]

def verdicts(piege, blk):
    f=blk["fiche"]; o=blk["outils"]; v={}
    constr=f.get("constructible")
    # risques : toujours comparé à fiche.aleas -> vert (vérifié ≡ ailleurs)
    v["risques"]="V" if ok(o.get("risques")) else "R"
    # gabarit
    jg=J(o.get("gabarit")); gs=jg.get("status")
    if not ok(o.get("gabarit")): v["gabarit"]="R"
    elif gs=="ok" and constr is False and (jg.get("zoneImplantationM2") or 0)>0:
        v["gabarit"]="O"      # enveloppe dessinée alors que la fiche dit « rien à bâtir »
    elif gs=="incomplete" and constr is False:
        v["gabarit"]="O"      # « donnée manquante » pour une parcelle définitivement inconstructible
    else:
        v["gabarit"]="V"
    # taxe prefill (cohérence zone/sdp/surface)
    v["taxe"]="V" if ok(o.get("taxe_prefill")) else "R"
    # estimer
    je=J(o.get("estimation"))
    if not ok(o.get("estimation")): v["estimer"]="R"
    elif je.get("median") is None: v["estimer"]="V"          # honnête : pas de comparable
    elif je.get("type_comparateur")=="bati" and constr is False:
        v["estimer"]="O"      # prix « bâti » servi sur une parcelle inconstructible, sans réserve
    else: v["estimer"]="V"
    # solaire / temps / permis / comparer / etude / calculette : répondent proprement
    v["solaire"]="V" if ok(o.get("solaire_parcelle")) else "R"
    v["temps"]="V" if ok(o.get("temps_epoque")) else "R"
    v["permis"]="V" if ok(o.get("parcelle_permis")) else "R"
    v["comparer"]="V" if ok(o.get("comparer")) and J(o.get("comparer")).get("count")==1 else "R"
    v["etude_zone"]="V" if ok(o.get("etude_zone")) else "R"
    v["calculette"]="V" if ok(o.get("calculette")) else "R"
    pa=o.get("patrimoine")
    v["patrimoine"]= "-" if (isinstance(pa,dict) and pa.get("skip")) else ("V" if ok(pa) else "R")
    return v

def main():
    rows=[]
    for piege,blk in R["parcelles"].items():
        v=verdicts(piege,blk)
        rows.append([piege, blk["idu"], blk["commune"]]+[v[c] for c in COLS])
    with open("docs/audit-2026-11/nu-5/A/preuves/matrice.csv","w",newline="") as fcsv:
        w=csv.writer(fcsv); w.writerow(["piege","idu","commune"]+COLS); w.writerows(rows)
    # affichage aligné
    hdr=["piege","risq","gaba","taxe","esti","sola","temp","perm","comp","zone","calc","patr"]
    print(" | ".join(f"{h:>22}" if i==0 else f"{h:>4}" for i,h in enumerate(hdr)))
    for r in rows:
        print(" | ".join([f"{r[0]:>22}"]+[f"{x:>4}" for x in r[3:]]))
    # compte
    from collections import Counter
    c=Counter(x for r in rows for x in r[3:])
    print("\nTotaux:", dict(c))

if __name__=="__main__":
    main()
