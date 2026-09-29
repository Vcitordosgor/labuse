#!/usr/bin/env python
"""RETOUCHES-1 — génère Dossier + Apporteur des 2 témoins par les VRAIES routes (TestClient),
carte=false (déterministe, sans réseau). Usage :

  PYTHONPATH=src LABUSE_DATABASE_URL=... DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  ~/Desktop/labuse/.venv/bin/python scripts/retouches1_gen.py <dossier_sortie>
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TEMOINS = ["97408000AO1424", "97415000EO0796"]  # La Possession (A) · Saint-Paul (U5b)


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/audit-2026-09/retouches-1/avant")
    out.mkdir(parents=True, exist_ok=True)
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    c = TestClient(app)
    for idu in TEMOINS:
        for name, url in ((f"dossier_{idu}.pdf", f"/dossier/{idu}.pdf?carte=false"),
                          (f"apporteur_{idu}.pdf", f"/apporteur/{idu}.pdf")):
            r = c.get(url)
            if r.status_code != 200:
                print(f"  ✗ {name} : HTTP {r.status_code} — {r.text[:200]}")
                continue
            p = out / name
            p.write_bytes(r.content)
            subprocess.run(["pdftotext", "-layout", str(p), str(p.with_suffix(".txt"))], check=False)
            print(f"  ✓ {name} : {len(r.content)} o")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
