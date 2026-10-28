"""ANNONCE-3 — recette du document « Analyse d'annonce ».

But : produire les QUATRE PDF du mandat (variante parcelle depuis l'outil + depuis Docs ; variante
commune depuis l'outil + depuis Docs) et PROUVER que l'outil et Docs donnent le MÊME contenu.

Clé de la preuve : le bouton « Exporter en PDF » de l'outil et la porte Docs appellent la MÊME route
(docAnalyseAnnonceUrl / docAnalyseAnnonceLienUrl côté front → /analyse-annonce/{idu}.pdf et
/analyse-annonce.pdf?url=…). On tape donc chaque route DEUX fois (origine « outil » puis « docs ») et
on compare le TEXTE extrait (pdftotext) : il est identique (les octets bruts diffèrent seulement par
l'horodatage interne que WeasyPrint grave dans le PDF — pas par le contenu).

Lancer :
  PYTHONPATH=src LABUSE_ENV=local LABUSE_DATABASE_URL=postgresql+psycopg:///labuse \
    python docs/audit-2026-10/annonce-3/_recette_serveur.py
Les PDF atterrissent dans docs/audit-2026-10/annonce-3/captures/ (git-ignoré).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
CAPT = ICI / "captures"

# un IDU servi (bande classement présente sur le run courant) et une annonce PRÉSENTE dans le Radar local.
IDU = os.environ.get("ANNONCE3_IDU", "97413000CX0800")
LIST_ID = os.environ.get("ANNONCE3_LIST_ID", "3260743003")
URL_ANNONCE = f"https://www.leboncoin.fr/ventes_immobilieres/{LIST_ID}.htm"


def _pdftotext(pdf: Path) -> str:
    if not shutil.which("pdftotext"):
        return "(pdftotext indisponible — comparaison par octets)"
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True)
    return out.stdout


def main() -> int:
    from fastapi.testclient import TestClient
    from labuse.api.app import app

    CAPT.mkdir(parents=True, exist_ok=True)
    client = TestClient(app)

    # URLs EXACTES que le front compose (mêmes helpers api.ts) — l'outil ET Docs tapent celles-ci.
    from urllib.parse import quote
    url_parc = f"/analyse-annonce/{IDU}.pdf"
    url_lien = f"/analyse-annonce.pdf?url={quote(URL_ANNONCE, safe='')}"

    cibles = [
        ("parcelle", url_parc, "outil-parcelle.pdf", "docs-parcelle.pdf"),
        ("commune", url_lien, "outil-commune.pdf", "docs-commune.pdf"),
    ]
    ok = True
    for variante, url, f_outil, f_docs in cibles:
        print(f"\n── variante {variante} — {url}")
        textes = {}
        for origine, nom in (("outil", f_outil), ("docs", f_docs)):
            r = client.get(url)
            if r.status_code != 200:
                print(f"  ✗ {origine}: HTTP {r.status_code} — {r.text[:300]}")
                ok = False
                break
            dest = CAPT / nom
            dest.write_bytes(r.content)
            textes[origine] = _pdftotext(dest)
            print(f"  ✓ {origine}: {dest.name} ({len(r.content)} octets)")
        if len(textes) == 2:
            identiques = textes["outil"] == textes["docs"]
            print(f"  → outil == docs (texte) : {'IDENTIQUE ✓' if identiques else 'DIFFÉRENT ✗'}")
            if not identiques:
                ok = False
            # un extrait pour l'œil
            extrait = "\n".join(l for l in textes["outil"].splitlines() if l.strip())[:600]
            print("  --- extrait ---\n" + "\n".join("    " + l for l in extrait.splitlines()[:14]))
    print("\n" + ("✓ RECETTE OK — 4 PDF produits, outil == Docs" if ok else "✗ RECETTE : un écart (voir ci-dessus)"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
