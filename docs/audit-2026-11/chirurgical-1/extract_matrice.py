#!/usr/bin/env python3
"""AUDIT-CHIRURGICAL-1 — LOT 2 extracteur de faits.
Pour chaque IDU de l'échantillon : lit la FICHE (API /parcels/{idu}), génère et lit le DOSSIER PDF,
et produit des lignes parcelle×fait×source×valeur dans MATRICE.csv. Compare aussi aux valeurs ORACLE
(oracle.csv) si présent. LECTURE SEULE (aucune écriture en base). Les documents sont rangés dans ~/Desktop/chasse-1/<idu>/.
"""
import csv, json, os, re, subprocess, sys, urllib.request, shutil
from pathlib import Path

API = "http://127.0.0.1:7440"
AUD = Path("/Users/openclaw/Desktop/labuse-chasse/docs/audit-2026-11/chirurgical-1")
CHASSE = Path("/Users/openclaw/Desktop/chasse-1")
SAMPLE = AUD / "echantillon.csv"
OUT = AUD / "MATRICE.csv"

def get(url, dest=None, timeout=180):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = r.read()
        if dest:
            Path(dest).write_bytes(data)
        return data, r.status if hasattr(r, 'status') else 200
    except Exception as e:
        return None, f"ERR {e}"

def pdftext(path):
    try:
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=60)
        return out.stdout
    except Exception as e:
        return f"__pdftext_err {e}"

def num(x):
    if x is None: return None
    if isinstance(x,(int,float)): return float(x)
    m = re.search(r"-?[\d  \xa0]+(?:[.,]\d+)?", str(x))
    if not m: return None
    s = m.group(0).replace(" ","").replace("\xa0","").replace(" ","").replace(",",".")
    try: return float(s)
    except: return None

def fiche_facts(d):
    """Retourne {fait: valeur} depuis la fiche JSON."""
    f = {}
    f["surface_dessin_m2"] = d.get("surface_m2")
    f["surface_cadastre_m2"] = d.get("contenance_m2") or d.get("surface_terrain_m2")
    f["surface_source"] = d.get("surface_source")
    f["commune"] = d.get("commune")
    pab = d.get("potentiel_a_batir") or {}
    f["zone_fam"] = pab.get("zone_fam"); f["zone_lib"] = pab.get("zone_lib")
    f["constructible"] = pab.get("constructible")
    f["constructible_motif"] = pab.get("motif") or pab.get("libelle")
    f["sdp_restante_m2"] = pab.get("sdp_restante_m2")
    pt = d.get("potentiel_transformation") or {}
    if isinstance(pt, dict):
        f["capacite_transformation"] = pt.get("capacite_estimee") or pt.get("sdp_m2")
    lb = d.get("le_bien") or {}
    f["emprise_batie_m2_lebien"] = lb.get("emprise_batie_m2")
    f["emprise_source_lebien"] = lb.get("emprise_source")
    f["nb_batiments"] = lb.get("nb_batiments")
    f["hauteur_faitage_m"] = lb.get("hauteur_faitage_m")
    f["hauteur_egout_m"] = lb.get("hauteur_egout_m")
    f["hauteur_bdtopo_m"] = lb.get("hauteur_bdtopo_m")
    sv = d.get("score_v2") or {}
    f["score_tier"] = sv.get("tier"); f["score_label"] = sv.get("label")
    f["score_motif"] = sv.get("motif"); f["score_percentile"] = sv.get("percentile")
    # emprise lue dans le motif du score (souvent une 2e source du même fait)
    mm = re.search(r"emprise\s+([\d  \xa0]+)\s*m²", str(sv.get("motif") or ""))
    f["emprise_batie_m2_scoremotif"] = num(mm.group(1)) if mm else None
    al = d.get("aleas") or {}
    liste = al.get("liste") or []
    f["aleas_n"] = al.get("n")
    f["aleas_detail"] = "; ".join(f'{a.get("nature")}={a.get("niveau")}@{a.get("part_pct")}%' for a in liste)
    # PPR zone
    ppr = [a.get("ppr") for a in liste if a.get("ppr")]
    f["ppr_zone"] = ";".join(str(p) for p in ppr) if ppr else None
    dvf = d.get("dvf_parcelle") or {}
    f["derniere_vente"] = (dvf.get("derniere_mutation") or {}).get("date_mutation") if dvf.get("derniere_mutation") else None
    sect = dvf.get("secteur") or []
    terr = next((s for s in sect if s.get("type_bien")=="terrain"), None)
    if terr:
        f["prix_m2_terrain_secteur"] = terr.get("mediane_prix_m2")
        f["n_ventes_terrain_secteur"] = terr.get("n_ventes")
        f["prix_fenetre"] = terr.get("fenetre"); f["prix_perimetre"] = terr.get("perimetre")
    f["estimation_terrain_eur"] = dvf.get("valeur_terrain_secteur_eur")
    f["marche_synthese"] = d.get("marche_synthese")
    disp = d.get("dispositifs") or {}
    f["dpu"] = (disp.get("dpu") or {}).get("etat")
    tx = d.get("taxe_amenagement") or {}
    f["taxe_taux_communal_pct"] = tx.get("taux_communal_pct")
    f["taxe_taux_departemental_pct"] = tx.get("taux_departemental_pct")
    f["plu_fraicheur"] = d.get("plu_fraicheur")
    return f

def dossier_facts(txt):
    """Faits lus dans le TEXTE du Dossier PDF (grossier, pour comparer écran↔document)."""
    f = {}
    if not txt or txt.startswith("__pdftext_err"): return f
    # anomalies de contenu
    for tok in ["None","NaN","undefined","null","nan ","{{","}}","Traceback","KeyError"]:
        if tok in txt:
            f.setdefault("anomalies_texte", []).append(tok)
    if "anomalies_texte" in f: f["anomalies_texte"] = ";".join(sorted(set(f["anomalies_texte"])))
    return f

def main():
    if not SAMPLE.exists():
        print("echantillon.csv absent"); return 1
    rows = list(csv.DictReader(open(SAMPLE)))
    idus = [r["idu"] for r in rows]
    meta = {r["idu"]: r for r in rows}
    # oracle (si présent) : on le laisse en comparaison séparée via oracle.csv parsé plus tard
    out_rows = []
    for idu in idus:
        rec = CHASSE / idu
        rec.mkdir(parents=True, exist_ok=True)
        data, st = get(f"{API}/parcels/{idu}", dest=rec/"fiche.json")
        if data is None:
            out_rows.append([idu, meta[idu].get("famille",""), "fiche", "ERREUR", str(st)]);
            print(f"{idu}: fiche {st}"); continue
        try: d = json.loads(data)
        except: out_rows.append([idu, meta[idu].get("famille",""),"fiche","JSON_INVALID",""]); continue
        ff = fiche_facts(d)
        for k,v in ff.items():
            out_rows.append([idu, meta[idu].get("famille",""), f"FICHE:{k}", "", json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else ("" if v is None else str(v))])
        # Dossier PDF
        pdf, st2 = get(f"{API}/dossier/{idu}.pdf", dest=rec/"dossier.pdf")
        if pdf and pdf[:4]==b"%PDF":
            txt = pdftext(rec/"dossier.pdf"); (rec/"dossier.txt").write_text(txt)
            for k,v in dossier_facts(txt).items():
                out_rows.append([idu, meta[idu].get("famille",""), f"DOSSIER:{k}", "", str(v)])
            out_rows.append([idu, meta[idu].get("famille",""), "DOSSIER:genere", "", "ok"])
        else:
            out_rows.append([idu, meta[idu].get("famille",""), "DOSSIER:genere", "", f"ECHEC {st2} {pdf[:80] if pdf else ''}"])
        print(f"{idu}: ok")
    with open(OUT,"w",newline="") as fh:
        w = csv.writer(fh); w.writerow(["idu","famille","fait_source","oracle","valeur"])
        w.writerows(out_rows)
    print(f"MATRICE.csv : {len(out_rows)} lignes, {len(idus)} parcelles")
    return 0

if __name__ == "__main__":
    sys.exit(main())
