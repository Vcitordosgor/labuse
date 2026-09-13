"""RECETTE-12 — génère un PDF (dossier|apporteur) pour un IDU, en LOCAL (DYLD intact, PAS via nohup
qui strippe DYLD → WeasyPrint échoue). Usage :
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src python scripts/_recette12_gen_pdf.py <document> <idu> <chemin.pdf>
"""
import sys

from labuse.db import session_scope
from labuse.exports import builder
from labuse.api.app import parcel_fiche


def main() -> None:
    document, idu, chemin = sys.argv[1], sys.argv[2], sys.argv[3]
    compte_id = int(sys.argv[4]) if len(sys.argv) > 4 else None
    with session_scope() as db:
        fiche = parcel_fiche(idu, db=db)          # la fiche PREMIUM complète (comme l'endpoint)
        pdf, res = builder.generer_pdf(db, idu, document, fiche=fiche, chemin_pdf=None, compte_id=compte_id)
    with open(chemin, "wb") as f:
        f.write(pdf)
    print(f"OK {document} {idu} → {chemin} ({len(pdf)} octets) · numéro {res.numero}")


if __name__ == "__main__":
    main()
