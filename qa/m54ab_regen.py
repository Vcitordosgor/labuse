"""M54-AB — régénération des exportables réels sur une parcelle, pour mesure & validation.

Usage :
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  PROJ_DATA=/Users/openclaw/miniforge3/envs/labusedb/share/proj \
  PYTHONPATH=src /Users/openclaw/Desktop/labuse/.venv/bin/python qa/m54ab_regen.py [IDU]

Rend les documents accessibles simplement (premium, dossier, one-pager). Banquier/projet/flash
sont ajoutés au fur et à mesure. Écrit sous qa/m54ab_out/ et extrait le texte des PDF (pdftotext
si présent, sinon pypdf) pour le grep des codes techniques.
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

IDU = sys.argv[1] if len(sys.argv) > 1 else "97415000CT1389"
OUT = Path(__file__).parent / "m54ab_out"
OUT.mkdir(exist_ok=True)


def _save(name: str, content: bytes) -> Path:
    p = OUT / name
    p.write_bytes(content)
    return p


def _text_of(p: Path) -> str:
    if p.suffix == ".html":
        return p.read_text(errors="replace")
    # PDF → texte
    try:
        return subprocess.run(["pdftotext", "-layout", str(p), "-"],
                              capture_output=True, text=True, timeout=60).stdout
    except FileNotFoundError:
        try:
            from pypdf import PdfReader
            return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
        except Exception as e:  # noqa: BLE001
            return f"[extraction impossible: {e}]"


def main() -> None:
    from labuse.api.app import app
    client = TestClient(app, base_url="https://testserver")

    docs: dict[str, Path] = {}

    # 1) fiche premium
    r = client.get(f"/parcels/{IDU}/export.pdf")
    print(f"premium: {r.status_code} {len(r.content)}o")
    if r.status_code == 200:
        docs["premium"] = _save(f"premium_{IDU}.pdf", r.content)

    # 2) one-pager comité (HTML)
    r = client.get(f"/parcels/{IDU}/export", params={"format": "onepager"})
    print(f"onepager: {r.status_code} {len(r.content)}o")
    if r.status_code == 200:
        docs["onepager"] = _save(f"onepager_{IDU}.html", r.content)

    # 3) dossier parcelle
    r = client.get(f"/dossier/{IDU}.pdf", params={"carte": "false"})
    print(f"dossier: {r.status_code} {len(r.content)}o")
    if r.status_code == 200:
        docs["dossier"] = _save(f"dossier_{IDU}.pdf", r.content)

    # 4) banquier + 5) flash : générateurs appelés en direct (on mesure le rendu, pas la porte)
    from labuse.db import session_scope
    with session_scope() as db:
        try:
            from labuse.api.banquier import _build_pdf
            pdf = _build_pdf(db, IDU, marque=None)
            docs["banquier"] = _save(f"banquier_{IDU}.pdf", pdf)
            print(f"banquier: OK {len(pdf)}o")
        except Exception as e:  # noqa: BLE001
            print(f"banquier: ERREUR {type(e).__name__}: {e}")
        try:
            from labuse.flash.report import render_report_html
            html = render_report_html(db, IDU, order_ref="M54AB", with_map=False,
                                      produit="Rapport Flash",
                                      produit_sous_titre="RAPPORT FLASH · parcelle à l'unité")
            docs["flash"] = _save(f"flash_{IDU}.html", html.encode())
            print(f"flash: OK {len(html)}o")
        except Exception as e:  # noqa: BLE001
            print(f"flash: ERREUR {type(e).__name__}: {e}")

    # extraction texte + grep de codes techniques
    codes = ["declasse_bati_sature", "declasse_", "_sature", " v2", "au_sous_plancher",
             "conditionnelle_operation", "declasse_au"]
    print("\n=== grep codes techniques dans le texte extrait ===")
    for name, p in docs.items():
        txt = _text_of(p)
        (OUT / f"{name}_{IDU}.txt").write_text(txt)
        hits = {c: txt.count(c) for c in codes if c in txt}
        print(f"  {name}: {hits or 'aucun code'}  ({len(txt)} car.)")


if __name__ == "__main__":
    main()
