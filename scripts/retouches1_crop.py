#!/usr/bin/env python
"""RETOUCHES-1 — recadre une bande autour d'un texte cherché dans un PDF (avant/après par point).
Usage: retouches1_crop.py <pdf> <page> <search> <out.png> [contexte_px]
Localise le mot via `pdftotext -bbox` (points 72 dpi) → recadre à 150 dpi une bande large."""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

DPI = 150
SCALE = DPI / 72.0


def bbox_words(pdf: str, page: int):
    out = subprocess.run(["pdftotext", "-bbox", "-f", str(page), "-l", str(page), pdf, "-"],
                         capture_output=True, text=True).stdout
    pw = ph = None
    m = re.search(r'<page width="([\d.]+)" height="([\d.]+)"', out)
    if m:
        pw, ph = float(m.group(1)), float(m.group(2))
    words = []
    for w in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', out):
        words.append((float(w.group(1)), float(w.group(2)), float(w.group(3)), float(w.group(4)), w.group(5)))
    return pw, ph, words


def main() -> int:
    pdf, page, search, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    ctx = int(sys.argv[5]) if len(sys.argv) > 5 else 42
    pw, ph, words = bbox_words(pdf, page)
    hit = next((w for w in words if search.lower() in w[4].lower()), None)
    if not hit:
        print(f"  ! « {search} » introuvable p{page} de {pdf}")
        return 1
    ymin = hit[1]
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-png", "-r", str(DPI), "-f", str(page), "-l", str(page), pdf, f"{td}/p"], check=True)
        img = next(Path(td).glob("p*.png"))
        im = Image.open(img)
        w, h = im.size
        top = max(0, int((ymin - ctx) * SCALE))
        bot = min(h, int((ymin + ctx) * SCALE))
        im.crop((0, top, w, bot)).save(out)
    print(f"  ✓ {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
