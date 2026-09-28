#!/usr/bin/env python
"""Dump du texte d'une (ou plusieurs) page(s) d'un règlement PLU.

Usage:
  python scripts/plu_verif/page_text.py <insee> <page> [contexte=1]
  python scripts/plu_verif/page_text.py <insee> <p1>-<p2>

`page` est la page PDF 1-based (comme page_pdf des calibrages). `contexte` élargit
de ±N pages. Sert au Lot B pour relire le paragraphe cité.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import fitz
from labuse.plu import destinations as D

PDF_DIR = Path.home() / "Desktop" / "labuse" / "data" / "plu_reglements"

def main():
    insee = sys.argv[1]
    spec = sys.argv[2]
    ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    doc_name = D.etat_commune(insee).get("document")
    d = fitz.open(str(PDF_DIR / doc_name))
    if "-" in spec:
        a, b = spec.split("-"); pages = range(int(a), int(b) + 1)
    else:
        p = int(spec); pages = range(p - ctx, p + ctx + 1)
    for p in pages:
        i = p - 1
        if 0 <= i < d.page_count:
            print(f"\n===== PAGE PDF {p} (commune {insee}, {doc_name}) =====")
            print(d[i].get_text())

if __name__ == "__main__":
    main()
