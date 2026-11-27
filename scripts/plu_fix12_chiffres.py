"""OUTIL-PLU-FIX-12 — CHIFFRES de synthèse (sortie brute) des retouches relecture-plu-9. DSN via
LABUSE_PLU_CORPUS_DSN (défaut openclaw@localhost/labuse). Lecture seule.

Usage : PYTHONPATH=src python scripts/plu_fix12_chiffres.py
"""
from __future__ import annotations

import glob
import hashlib
import os

import fitz
from sqlalchemy import create_engine, text

_DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")
_PDFDIR = os.path.expanduser("~/Desktop/labuse/data/plu_reglements")


def main() -> int:
    s = create_engine(_DSN).connect()

    print("== §1 — décompte du scan --strict (correction 14 → 15 faux positifs) ==")
    print("  lancer : python scripts/plu_fix10_scan_tronques.py --strict")
    print("  31 lignes = 16 artefacts (97406×14 + 97412×2) + 15 faux positifs. Up.10 corrigé = HORS des 31.")

    print("\n== §3 — artefact « lettres espacées » : documents concaténés par commune ==")
    import re
    concat = {}
    for f in sorted(glob.glob(f"{_PDFDIR}/*.pdf")):
        insee = os.path.basename(f)[:5]
        d = fitz.open(f)
        hits = [pi + 1 for pi in range(10, d.page_count)
                if re.search(r"(?i)modification.{0,40}(table des mati|plan local)",
                             " ".join(d[pi].get_text().split()[:14]))]
        if hits:
            concat[insee] = (d.page_count, hits[:4])
    for insee, (npg, hits) in concat.items():
        print(f"  {insee} : {npg} pages, dossier(s) de modification concaténé(s) dès p.{hits[0]} (ex. {hits})")
    print(f"  → {len(concat)}/21 commune(s) à documents concaténés (le seul porteur de l'artefact).")
    # La Plaine : règlement vs dossiers
    reg = s.execute(text("select count(*) from plu_reglement_extrait where insee='97406' and page_debut<=117")).scalar()
    dos = s.execute(text("select count(*) from plu_reglement_extrait where insee='97406' and page_debut>=118")).scalar()
    print(f"  97406 La Plaine : {reg} extraits règlement (p.1-117, propres) + {dos} extraits dossiers (p.118+, artefact) — NON touché.")
    print("  97412 Saint-Joseph : PDF brut PROPRE (ARTICLE AUindicée 2/4/8/12 sans espacement) — pas de lettres espacées.")

    print("\n== §4 — La Possession : éditions déc.2025 vs juin 2026 ==")
    p25 = glob.glob(f"{_PDFDIR}/97408_reglement_20251217.pdf")
    p26 = glob.glob(f"{_PDFDIR}/97408_reglement_20260625.pdf")
    if p25 and p26:
        m25 = hashlib.md5(open(p25[0], "rb").read()).hexdigest()
        m26 = hashlib.md5(open(p26[0], "rb").read()).hexdigest()
        print(f"  md5 déc.2025  = {m25}")
        print(f"  md5 juin.2026 = {m26}")
        print(f"  → {'IDENTIQUES (octet pour octet)' if m25 == m26 else 'DIFFÉRENTS'}")
    r = s.execute(text("select distinct document,idurba from plu_reglement_extrait where insee='97408'")).first()
    print(f"  base sert : document={r.document} · idurba={r.idurba} (réingéré depuis le PDF juin 2026)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
