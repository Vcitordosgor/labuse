"""OUTIL-ASSEMBLAGE-FIX-6 (LOT 1) — preuve PAR LE DOCUMENT : rend le Bilan PDF et l'Excel pour un
programme SAISI (nombre de logements), relit le texte du PDF. Base labuse en LECTURE SEULE."""
import os
import subprocess
import tempfile

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DBURL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
S = Session(create_engine(DBURL, future=True))
S.execute(text("SET default_transaction_read_only=on"))

from labuse.api.bilan import CalculIn, ProduitIn, ProgrammeIn, _entrees, _mixite_note
from labuse.bilan import excel as _xl
from labuse.bilan import pdf as _pdf
from labuse.bilan.moteur import Moteur


def corps(n, sdp, prix=5000.0):
    return CalculIn(programme=ProgrammeIn(terrain=1000.0, sdp=float(sdp)),
                    produits=[ProduitIn(libelle="Logements", lots=float(n), suv=float(sdp * 0.85),
                                        prix_ttc_m2_suv=prix, tva=0.2)])


def pdftxt(octets):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(octets); p = f.name
    t = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True).stdout
    os.unlink(p)
    return t


def main():
    for idu, n, sdp, commune in [("97411000AB0006", 24, 1700, "Saint-Denis"),
                                 ("97411000AB0006", 40, 3000, "Saint-Denis"),
                                 ("97411000BZ0824", 35, 2600, "Saint-Denis")]:
        S.rollback()
        c = corps(n, sdp)
        note = _mixite_note(S, idu, c)
        print(f"\n### {idu} — {n} logts\n   note      = {note}")
        r = Moteur().calculer(_entrees(c))
        octets = _pdf.construire_pdf(r, idu=idu, commune=commune, adresse="", donnees_au=None,
                                     programme=c.programme.model_dump(), calendrier={}, map_html="",
                                     etude_reliee=None, prix_demande=5000.0,
                                     garde_fou={"mixite_note": note})
        t = pdftxt(octets)
        found = [ln.strip() for ln in t.splitlines()
                 if any(k in ln for k in ("Mixité", "BORNE", "15 %", "déclenchée", "non chiffrée"))]
        for ln in found:
            print("   PDF       :", ln)
        print("   PDF contient 'BORNE HAUTE' ?", "BORNE HAUTE" in t, "| '15 %' ?", "15 %" in t)
        # Excel
        e = _entrees(c)
        xls = _xl.classeur_bilan_bytes(e, titre=f"Bilan — {idu}", garde_fou={"mixite_note": note})
        from openpyxl import load_workbook
        import io
        wb = load_workbook(io.BytesIO(xls))
        cells = [str(cl.value) for ws in wb.worksheets for row in ws.iter_rows() for cl in row
                 if cl.value and "mixit" in str(cl.value).lower() or (cl.value and "BORNE" in str(cl.value))]
        print("   XLSX note :", cells[:2] if cells else "(dans garde-fou, voir note)")


if __name__ == "__main__":
    main()
