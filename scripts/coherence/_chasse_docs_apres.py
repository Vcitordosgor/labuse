#!/usr/bin/env python3
"""CHASSE-DOCS-FIX-1 — collecte « APRÈS » (pdftotext des documents TOUCHÉS, 10 parcelles).

Rend Dossier · Apporteur · Étude de zone · Gabarit · Comparatif pour chaque IDU sur l'API corrigée
(port 8831 par défaut) et écrit leur pdftotext sous docs/audit-2026-10/chasse-docs-fix/<idu>/.
Preuve avant/après : comparer à docs/audit-2026-10/chasse-docs/<idu>/*.pdf.txt (branche audit).
"""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = os.environ.get("CHASSE_DOCS_BASE", "http://127.0.0.1:8831")
OUT = Path("docs/audit-2026-10/chasse-docs-fix")
IDUS = [
    "97415000BO0852", "97401000AD0554", "97416000DY0106", "97411000AV0110",
    "97410000AN0347", "97411000BZ1065", "97415000BW0102", "97416000CZ0678",
    "97415000EV0324", "97411000DS0186",
]
VOISIN = "97415000BO0852"   # 2e parcelle pour le Comparatif


def _fetch(path: str, dest: Path) -> str:
    try:
        with urllib.request.urlopen(BASE + path, timeout=180) as r:
            raw = r.read()
    except Exception as e:  # noqa: BLE001
        return f"ERR {e!r}"
    if len(raw) < 800:
        return f"petit/err {len(raw)}o"
    dest.write_bytes(raw)
    txt = dest.with_suffix(".pdf.txt")
    try:
        subprocess.run(["pdftotext", "-layout", str(dest), str(txt)], check=True,
                       capture_output=True, timeout=90)
    except Exception as e:  # noqa: BLE001
        return f"pdf ok, pdftotext ERR {e!r}"
    dest.unlink(missing_ok=True)   # on ne garde que le texte (preuve), pas le binaire
    return f"ok {txt.stat().st_size}o"


for idu in IDUS:
    d = OUT / idu
    d.mkdir(parents=True, exist_ok=True)
    voisin = VOISIN if idu != VOISIN else "97415000BW0102"
    jobs = {
        "dossier": f"/dossier/{idu}.pdf?carte=false",
        "apporteur": f"/apporteur/{idu}.pdf",
        "etude_zone": f"/etude-zone.pdf?idu={idu}",
        "gabarit_doc": f"/gabarit/{idu}.pdf",
        "comparatif": f"/comparatif.pdf?idus={idu},{voisin}",
    }
    print(f"=== {idu} ===")
    for nom, path in jobs.items():
        print(f"  {nom}: {_fetch(path, d / (nom + '.pdf'))}")
