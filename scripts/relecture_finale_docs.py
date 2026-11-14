"""RELECTURE FINALE (branche fix/gabarit-3d-3) — régénère les documents des DEUX parcelles en cause et en
extrait le TEXTE (Règle B : chaque correction citée depuis le PDF régénéré).

  BI0351 = 97408000BI0351 (La Possession, 28 445 m²)  → Comparatif, Dossier, Étude
  HT0538 = 97416000HT0538 (Saint-Pierre, 509 m²)      → Dossier, Comparatif, Étude, pré-dossier

Sortie : docs/audit-2026-11/relecture-finale/<doc>.pdf + .txt (pdftotext). In-process (TestClient, base
locale), PDF in-process (LABUSE_PDF_PROCESS_ISOLE=0). AUCUNE écriture prod.

  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python scripts/relecture_finale_docs.py [etude|dossier|comparatif|all]
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
os.environ.setdefault("LABUSE_PDF_PROCESS_ISOLE", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

OUT = Path("docs/audit-2026-11/relecture-finale")
BI = "97408000BI0351"
HT = "97416000HT0538"
BI_VOISINES = ["97408000BI0346", "97408000AC2749"]
QUOI = sys.argv[1] if len(sys.argv) > 1 else "all"


def _compte_actif(db):
    from sqlalchemy import text
    for q in ("SELECT compte_id FROM parcel_access LIMIT 1", "SELECT id FROM comptes ORDER BY id LIMIT 1"):
        try:
            r = db.execute(text(q)).scalar()
            if r:
                return int(r)
        except Exception:  # noqa: BLE001 — table absente selon la base
            pass
    return 1


def _txt(nom: str, octets: bytes):
    p = OUT / nom
    p.write_bytes(octets)
    if nom.endswith(".pdf"):
        try:
            subprocess.run(["pdftotext", "-layout", str(p), str(p.with_suffix(".txt"))], check=True)
        except Exception as e:  # noqa: BLE001
            print(f"  (pdftotext {nom}: {e})")
    print(f"  écrit {nom} ({len(octets)} o)")


def main():
    from fastapi.testclient import TestClient
    from labuse.api import bilan as _bilan, tenant
    from labuse.api.app import app
    from labuse.db import session_factory

    OUT.mkdir(parents=True, exist_ok=True)
    cid = _compte_actif(session_factory()())
    tenant.current_compte = lambda request=None: cid           # type: ignore[assignment]
    _bilan.current_compte = lambda request=None: cid            # type: ignore[assignment]
    client = TestClient(app)

    def get(route):
        r = client.get(route); return r

    if QUOI in ("all", "etude"):
        print("Étude de faisabilité :")
        for idu in (HT, BI):
            e = client.post("/modules/etude/pdf", json={"idus": [idu]})
            if e.status_code == 200 and e.content[:4] == b"%PDF":
                _txt(f"etude_{idu[-6:]}.pdf", e.content)
            else:
                print(f"  Étude {idu} NON RENDU {e.status_code}: {e.text[:200]}")
    if QUOI in ("all", "dossier"):
        print("Dossier :")
        for idu in (HT, BI):
            r = get(f"/dossier/{idu}.pdf")
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                _txt(f"dossier_{idu[-6:]}.pdf", r.content)
            else:
                print(f"  Dossier {idu} NON RENDU {r.status_code}")
    if QUOI in ("all", "comparatif"):
        print("Comparatif :")
        r = get(f"/comparatif.pdf?idus={BI},{BI_VOISINES[0]},{BI_VOISINES[1]}")
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            _txt("comparatif_BI0351.pdf", r.content)
        else:
            print(f"  Comparatif BI0351 NON RENDU {r.status_code}")
        r = get(f"/comparatif.pdf?idus={HT},97416000HT0537,97416000HT0517")
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            _txt("comparatif_HT0538.pdf", r.content)
        else:
            print(f"  Comparatif HT0538 NON RENDU {r.status_code}")
    if QUOI in ("all", "analyse"):
        print("Analyse d'annonce (Estimer) :")
        for idu in (BI, HT):
            r = get(f"/analyse-annonce/{idu}.pdf")
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                _txt(f"analyse_{idu[-6:]}.pdf", r.content)
            else:
                print(f"  Analyse {idu} NON RENDU {r.status_code}")
    if QUOI in ("all", "predossier"):
        print("Pré-dossier :")
        r = get(f"/pre-dossier/{HT}.zip")
        if r.status_code == 200:
            _txt(f"predossier_{HT[-6:]}.zip", r.content)
        else:
            print(f"  Pré-dossier {HT} NON RENDU {r.status_code}")
    print("→", OUT)


if __name__ == "__main__":
    main()
