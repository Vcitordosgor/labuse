#!/usr/bin/env python
"""PLU-VERIF-1 Étape 0 — inventaire des règles calibrées.

Compte les règles par commune et par statut, vérifie que chaque feuille porte
une référence (article + page_pdf), et rapproche le millésime calibré du PDF
local servi. Ne lit AUCUN PDF ici — c'est le socle du lot A.
"""
import sys, csv, json, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from labuse.plu import destinations as D  # noqa: E402

PDF_DIR = Path.home() / "Desktop" / "labuse" / "data" / "plu_reglements"

def pdf_index():
    idx = {}
    for p in sorted(PDF_DIR.glob("*.pdf")):
        m = re.match(r"(\d{5})_", p.name)
        if m:
            idx.setdefault(m.group(1), []).append(p.name)
    return idx

def main():
    pidx = pdf_index()
    rows = list(D.iter_regles_calibrees())
    # par commune : compter statut, absence de reference
    par_commune = {}
    sans_ref = []
    for r in rows:
        insee = r.get("insee")
        c = par_commune.setdefault(insee, {"insee": insee, "fichier": r.get("fichier"),
                                           "n": 0, "valide": 0, "propose": 0, "autre": 0,
                                           "absent": 0, "sans_page": 0, "sans_article": 0})
        c["n"] += 1
        st = (r.get("statut") or "").strip().lower()
        if st == "valide":
            c["valide"] += 1
        elif st == "propose":
            c["propose"] += 1
        else:
            c["autre"] += 1
        if r.get("absent"):
            c["absent"] += 1
        has_page = r.get("page_pdf") not in (None, "")
        has_art = bool((r.get("article") or "").strip())
        if not has_page:
            c["sans_page"] += 1
        if not has_art:
            c["sans_article"] += 1
        # une feuille "absent" (silence prouvé) n'a pas de valeur mais doit garder article+page
        if not has_page or not has_art:
            sans_ref.append({"insee": insee, "zone": r.get("zone"), "chemin": r.get("chemin"),
                             "article": r.get("article"), "page_pdf": r.get("page_pdf"),
                             "statut": st, "absent": r.get("absent")})

    print("=== RÈGLES PAR COMMUNE ===")
    print(f"{'insee':6} {'commune':22} {'PDF servi':30} {'n':>4} {'val':>4} {'prop':>4} {'aut':>4} {'abs':>4} {'noPg':>4} {'noArt':>4}")
    tot = {"n":0,"valide":0,"propose":0,"autre":0,"absent":0,"sans_page":0,"sans_article":0}
    for insee in sorted(par_commune):
        c = par_commune[insee]
        etat = D.etat_commune(insee)
        commune = etat.get("commune") or ""
        pdfs = ",".join(pidx.get(insee, [])) or "!! AUCUN PDF"
        print(f"{insee:6} {commune[:22]:22} {pdfs[:30]:30} {c['n']:>4} {c['valide']:>4} {c['propose']:>4} {c['autre']:>4} {c['absent']:>4} {c['sans_page']:>4} {c['sans_article']:>4}")
        for k in tot:
            tot[k] += c[k]
    print(f"{'TOTAL':6} {'':22} {'':30} {tot['n']:>4} {tot['valide']:>4} {tot['propose']:>4} {tot['autre']:>4} {tot['absent']:>4} {tot['sans_page']:>4} {tot['sans_article']:>4}")

    print(f"\n=== COMMUNES calibrées : {len(par_commune)} / PDF disponibles : {len(pidx)} ===")
    # millésime calibré vs PDF local
    print("\n=== MILLÉSIME calibré vs PDF local vs servi ===")
    for insee in sorted(par_commune):
        etat = D.etat_commune(insee)
        doc_cal = etat.get("document")
        pdfs = pidx.get(insee, [])
        match = doc_cal in pdfs if doc_cal else False
        flag = "OK" if match else "!! DIFF"
        print(f"{insee}  cal={doc_cal}  local={pdfs}  etat={etat.get('etat')}  {flag}")

    print(f"\n=== FEUILLES SANS RÉFÉRENCE complète : {len(sans_ref)} ===")
    for s in sans_ref[:50]:
        print(s)

    # dump json for downstream
    out = REPO / "docs/audit-2026-09/PLU-VERIF-1"
    (out / "inventaire.json").write_text(json.dumps(
        {"par_commune": par_commune, "sans_ref": sans_ref, "total": tot,
         "n_communes": len(par_commune)}, ensure_ascii=False, indent=2))
    print(f"\nÉcrit {out/'inventaire.json'}")

if __name__ == "__main__":
    main()
