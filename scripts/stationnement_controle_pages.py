"""ETUDE-STATIONNEMENT-FIX-1 — CONTRÔLE DUR : chaque chiffre appliqué et la citation d'une zone doivent se
retrouver dans le TEXTE DE SA PAGE du PDF officiel (tolérant aux retours à la ligne). Tourne sur TOUTES les
règles ingérées, pas seulement le sondage. Rend le nombre d'échecs et le détail.

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
    return re.sub(r'\s+', '', (s or "").lower().replace(" ", " ").replace("’", "'"))


def _fr(x: float) -> str:
    """Nombre tel qu'écrit dans un PLU : '1,5', '0,85', '75', '2'."""
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return ("%g" % x).replace(".", ",")


def figures(b: R.BaremeStationnement):
    """Les chiffres DISTINCTIFS appliqués (ceux qui doivent apparaître verbatim sur la page). Les encodages
    N/M (ex. 0,3333 = « 1 pour 3 ») sont rendus par leur DÉNOMINATEUR attendu dans le texte."""
    out = set()
    if b.flat_places is not None:
        out.add(_fr(b.flat_places))
    if b.m2_par_place is not None:
        out.add(_fr(b.m2_par_place))
    for l in b.lignes:
        if l.places is not None:
            # encodages N/M (« 1 place pour M ») → on cherche le DÉNOMINATEUR M dans le texte
            if abs(l.places - 1 / 3) < 1e-3:
                out.add("3")
            elif abs(l.places - 0.5) < 1e-9:
                out.add("2")
            else:
                out.add(_fr(l.places))
        if l.par_m2 is not None:
            out.add(_fr(l.par_m2))
    if b.visiteurs:
        if b.visiteurs.par_logements:
            out.add(_fr(b.visiteurs.par_logements))
        if b.visiteurs.par_m2_sdp:
            out.add(_fr(b.visiteurs.par_m2_sdp))
    if b.integ_seuil_m2:
        out.add(_fr(b.integ_seuil_m2))
    # retire les tokens trop courts/ambigus (« 1 », « 2 ») : non distinctifs, présents partout
    return {f for f in out if not (len(f) == 1 and f in "012")}


def page_text(doc, page_pdf):
    """Texte de la page (1-indexée) + voisines (tableau à cheval sur deux pages)."""
    idx = page_pdf - 1
    txt = ""
    for j in (idx - 1, idx, idx + 1):
        if 0 <= j < doc.page_count:
            txt += "\n" + doc[j].get_text()
    return txt


def controle(verbose=False):
    communes = sorted({os.path.basename(p)[:5] for p in glob.glob("config/plu_destinations/974??_*.yaml")})
    total = 0
    echecs = []
    sans_pdf = set()
    for insee in communes:
        pdf = pdf_for(insee)
        docs = fitz.open(pdf) if pdf else None
        for r in D.regles_commune(insee):
            z = r["zone"]
            if not re.match(r'^\d*(U|AU)', z, re.I):
                continue
            b = R.charger(insee, z).stationnement
            if not b.validee or b.page_pdf is None:
                continue
            total += 1
            if docs is None:
                sans_pdf.add(insee)
                echecs.append((insee, z, b.page_pdf, "PDF absent", []))
                continue
            txt = _norm(page_text(docs, b.page_pdf))
            manquants = [f for f in figures(b) if _norm(f) not in txt]
            # citation : au moins un segment distinctif (> 12 car.) doit se retrouver
            cit_ok = True
            if b.citation:
                segs = [s.strip() for s in re.split(r'[.;]', b.citation) if len(s.strip()) > 15]
                cit_ok = any(_norm(s)[:40] in txt for s in segs) if segs else True
            if manquants or not cit_ok:
                echecs.append((insee, z, b.page_pdf, "figures" if manquants else "citation", manquants))
        if docs:
            docs.close()
    print(f"CONTRÔLE PAGES — {total} règles contrôlées · {len(echecs)} échecs"
          + (f" ({len(sans_pdf)} communes sans PDF local : {sorted(sans_pdf)})" if sans_pdf else ""))
    # regroupe par commune
    parc = {}
    for insee, z, pg, motif, mq in echecs:
        parc.setdefault(insee, []).append((z, pg, motif, mq))
    for insee in sorted(parc):
        zs = parc[insee]
        print(f"  {insee} : {len(zs)} échecs" + (f" — ex. {zs[0][0]} p{zs[0][1]} {zs[0][2]} {zs[0][3]}" if zs else ""))
        if verbose:
            for z, pg, motif, mq in zs:
                print(f"      {z} p{pg} — {motif} {mq}")
    return echecs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    controle(ap.parse_args().verbose)
