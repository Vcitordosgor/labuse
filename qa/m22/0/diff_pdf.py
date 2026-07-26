#!/usr/bin/env python
"""M22-0 — diff visuel de deux PDF page à page (rasterisation PyMuPDF, 150 dpi).

Sort 0 si toutes les pages sont pixel-identiques, 1 sinon (liste des pages en écart).
Écrit les rendus PNG des deux documents (preuve « capture des deux »).

Usage : .venv/bin/python qa/m22/0/diff_pdf.py avant.pdf apres.pdf [dossier_png]
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF


def render(pdf_path: str, out_dir: Path, tag: str) -> list[bytes]:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        png = pix.tobytes("png")
        (out_dir / f"{tag}_p{i + 1}.png").write_bytes(png)
        pages.append(pix.samples)  # pixels bruts (comparaison exacte)
    doc.close()
    return pages


def main() -> int:
    avant, apres = sys.argv[1], sys.argv[2]
    out_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(avant).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    pa = render(avant, out_dir, Path(avant).stem)
    pb = render(apres, out_dir, Path(apres).stem)
    if len(pa) != len(pb):
        print(f"ECART : {len(pa)} pages vs {len(pb)} pages")
        return 1
    ecarts = [i + 1 for i, (a, b) in enumerate(zip(pa, pb)) if a != b]
    if ecarts:
        print(f"ECART pixels sur pages : {ecarts}")
        return 1
    print(f"IDENTIQUE : {len(pa)} pages, pixels identiques a 150 dpi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
