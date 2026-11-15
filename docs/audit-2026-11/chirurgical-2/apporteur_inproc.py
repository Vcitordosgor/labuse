#!/usr/bin/env python3
"""Génère l'Apporteur EN PROCESS (hors HTTP → hors quota d'export), avec le compte de test
AUDIT-TEST (compte_id 142, nom='AUDIT-TEST') comme marque signataire. Lecture seule.
LABUSE_PDF_PROCESS_ISOLE=0 force le rendu WeasyPrint in-process (pas de pool spawn)."""
import os, subprocess
os.environ.setdefault("LABUSE_PDF_PROCESS_ISOLE", "0")
from pathlib import Path
from labuse.db import session_scope
from labuse.exports import builder
from labuse.exports.rendu import render_pdf
from labuse.api.app import parcel_fiche

OUT = Path.home() / "Desktop" / "chasse-1"
COMPTE = 142  # AUDIT-TEST
PARCELLES = [
    "97416000HT0538","97403000AR1517","97404000AM0838","97417000AO0050",
    "97411000IS0448","97404000AY0153","97414000CO0153","97421000BN0260",
    "97422000BW2635","97412000CV0446","97424000AO1198",
]

def main():
    for idu in PARCELLES:
        out = OUT / idu / "apporteur.pdf"
        try:
            with session_scope() as db:
                fiche = parcel_fiche(idu, db=db, request=None)
                res = builder.construire(db, idu, "apporteur", fiche=fiche, compte_id=COMPTE)
                pdf = render_pdf(res.html, forms=True)
            out.write_bytes(pdf)
            subprocess.run(["pdftotext", "-layout", str(out), str(out.with_suffix(".txt"))], check=False)
            print(f"[OK] {idu} apporteur {len(pdf):>8}B  {res.numero}")
        except Exception as e:  # noqa: BLE001
            print(f"[ERR] {idu} apporteur : {type(e).__name__}: {str(e)[:140]}")

if __name__ == "__main__":
    main()
