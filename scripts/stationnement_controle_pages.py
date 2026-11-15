"""ETUDE-STATIONNEMENT-FIX-1 — CONTRÔLE DUR (relecture 3). La vraie preuve d'une règle :
  (1) sa CITATION se retrouve MOT POUR MOT dans le texte de SA page du PDF officiel (tolérant aux retours
      à la ligne ; pages voisines pour un tableau à cheval) ;
  (2) CHAQUE chiffre appliqué par le barème figure DANS CETTE CITATION (pas seulement « quelque part sur la
      page » : un « 1 » ou « 1,5 » s'y trouve partout).
Tourne sur TOUTES les règles ingérées. Rend : règles, échecs de citation, chiffres hors citation.

    PYTHONPATH=src python scripts/stationnement_controle_pages.py [--verbose]
"""
import argparse
import glob
import os
import re

import fitz

from labuse.implantation import regles as R
from labuse.plu import destinations as D

PDFDIR = os.path.expanduser("~/Desktop/labuse/data/plu_reglements/")


def pdf_for(insee):
    hits = sorted(glob.glob(PDFDIR + f"{insee}_[rR]eglement_*.pdf"))
    return hits[0] if hits else None


def _norm(s: str) -> str:
    return re.sub(r'\s+', '', (s or "").lower().replace("’", "'").replace("œ", "oe"))


def _fr(x: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return ("%g" % x).replace(".", ",")


def figures(b: R.BaremeStationnement):
    """Chiffres appliqués, en forme TEXTE telle qu'écrite dans un PLU. Les encodages N/M (0,3333 = « 1 pour
    3 » ; 0,5 = « 1 pour 2 ») sont rendus par leur DÉNOMINATEUR, attendu dans la citation."""
    out = set()
    def add(v):
        if abs(v - 1 / 3) < 1e-3:
            out.add("3")
        elif abs(v - 0.5) < 1e-9:
            out.add("2")
        else:
            out.add(_fr(v))
    if b.flat_places is not None:
        add(b.flat_places)
    if b.m2_par_place is not None:
        out.add(_fr(b.m2_par_place))
    for l in b.lignes:
        if l.places is not None:
            add(l.places)
        if l.par_m2 is not None:
            out.add(_fr(l.par_m2))
        for bound in (l.sdp_min, l.sdp_max):
            if bound:
                out.add(_fr(bound))
    if b.visiteurs:
        if b.visiteurs.par_logements:
            out.add(_fr(b.visiteurs.par_logements))
        if b.visiteurs.par_m2_sdp:
            out.add(_fr(b.visiteurs.par_m2_sdp))
    # integ (« places intégrées ») porte sa PROPRE citation (`integ_citation`), vérifiée à part — pas dans la
    # citation de la norme d'habitation.
    return out


def page_text(doc, page_pdf):
    idx = page_pdf - 1
    txt = ""
    for j in (idx - 1, idx, idx + 1):
        if 0 <= j < doc.page_count:
            txt += "\n" + doc[j].get_text()
    return txt


def controle(verbose=False):
    communes = sorted({os.path.basename(p)[:5] for p in glob.glob("config/plu_destinations/974??_*.yaml")})
    total = 0
    ech_cit = []     # citation pas verbatim sur la page
    ech_fig = []     # chiffre appliqué absent de la citation
    sans_pdf = set()
    for insee in communes:
        pdf = pdf_for(insee)
        doc = fitz.open(pdf) if pdf else None
        for r in D.regles_commune(insee):
            z = r["zone"]
            if not re.match(r'^\d*(U|AU)', z, re.I):
                continue
            b = R.charger(insee, z).stationnement
            if not b.validee or b.page_pdf is None:
                continue
            total += 1
            cit = b.citation or ""
            cit_n = _norm(cit)
            # (2) chaque chiffre appliqué DANS la citation. Les dénominateurs N/M peuvent être écrits EN
            # TOUTES LETTRES dans le PLU (« 1 place pour trois chambres ») : on accepte le mot équivalent.
            _mots = {"2": ("2", "deux"), "3": ("3", "trois")}
            hors = sorted(f for f in figures(b)
                          if not any(_norm(a) in cit_n for a in _mots.get(f, (f,))))
            if hors:
                ech_fig.append((insee, z, b.page_pdf, hors))
            # (1) citation verbatim sur la page (par segments de ligne)
            if doc is None:
                sans_pdf.add(insee)
                ech_cit.append((insee, z, b.page_pdf, "PDF absent"))
                continue
            page_n = _norm(page_text(doc, b.page_pdf))
            segs = [s for s in re.split(r'[\n]+', cit) if len(_norm(s)) >= 12]
            manque = [s for s in segs if _norm(s) not in page_n]
            if (segs and manque) or (not segs and cit_n and cit_n not in page_n):
                ech_cit.append((insee, z, b.page_pdf, "citation hors page"))
        if doc:
            doc.close()
    print(f"CONTRÔLE — {total} règles · {len(ech_cit)} citations hors page · {len(ech_fig)} règles avec chiffre hors citation"
          + (f" ({sorted(sans_pdf)} sans PDF)" if sans_pdf else ""))
    parc = {}
    for insee, z, pg, _m in ech_cit:
        parc.setdefault(insee, {"cit": 0, "fig": 0})["cit"] += 1
    for insee, z, pg, _h in ech_fig:
        parc.setdefault(insee, {"cit": 0, "fig": 0})["fig"] += 1
    for insee in sorted(parc):
        print(f"  {insee} : {parc[insee]['cit']} citation · {parc[insee]['fig']} chiffre hors citation")
    if verbose:
        for insee, z, pg, h in ech_fig:
            print(f"    FIG {insee} {z} p{pg} hors citation : {h}")
    return {"total": total, "cit": ech_cit, "fig": ech_fig}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    controle(ap.parse_args().verbose)
