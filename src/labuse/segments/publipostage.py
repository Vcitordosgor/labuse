"""Export PUBLIPOSTAGE des segments (mandat wave-adresses, Lot 2A).

Un ZIP : CSV normalisé (Destinataire « À l'occupant » — RGPD : JAMAIS de nom de
personne physique — Adresse ligne 1/2, CP, Ville) + planches d'étiquettes PDF
(format standard 63,5 × 38,1 mm — Avery L7160, 3 × 7 par A4 — configurable
LABUSE_ETIQUETTES_FORMAT). Seules les parcelles AVEC adresse BAN rattachée sont
émises : un courrier sans adresse fiable ne part pas.

Le watermarking du Lot 3 s'applique (colonne ref + canaris) — voir l'endpoint.
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

_FONTS = Path(__file__).resolve().parents[1] / "api" / "fonts"

#: en-têtes du CSV publipostage (l'artisan le glisse tel quel dans Word/LibreOffice)
ENTETES = ["Destinataire", "Adresse ligne 1", "Adresse ligne 2",
           "Code postal", "Ville", "Parcelle (IDU)"]
DESTINATAIRE = "À l'occupant"

# Géométrie de planche par format d'étiquette (mm) : (larg, haut, colonnes, lignes,
# marge gauche, marge haute, gouttière x). A4 = 210 × 297.
_PLANCHES = {
    "63.5x38.1": (63.5, 38.1, 3, 7, 7.25, 15.15, 2.5),   # Avery L7160 (21/planche)
    "70x35": (70.0, 35.0, 3, 8, 0.0, 8.5, 0.0),          # 24/planche (3 × 8)
    "105x37": (105.0, 37.0, 2, 8, 0.0, 0.5, 0.0),        # 16/planche (2 × 8)
}


def lignes_publipostage(rows) -> list[list[str]]:
    """Lignes d'export moteur (dicts avec adresse_* BAN) → lignes CSV normalisées.
    Les parcelles SANS adresse BAN sont écartées (courrier non distribuable)."""
    out = []
    for r in rows:
        voie = r.get("adresse_voie")
        if not voie:
            continue
        numero = r.get("adresse_numero") or ""
        out.append([DESTINATAIRE, f"{numero} {voie}".strip(), "",
                    r.get("adresse_cp") or "", r.get("adresse_ville") or "",
                    r.get("idu") or ""])
    return out


def csv_bytes(headers: list[str], lignes: list[list]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(headers)
    w.writerows(lignes)
    return buf.getvalue().encode("utf-8-sig")     # BOM : accents corrects dans Excel


def etiquettes_pdf(lignes: list[list], fmt: str = "63.5x38.1", ref: str = "") -> bytes:
    """Planches d'étiquettes PDF — une étiquette = destinataire + adresse + CP ville."""
    from fpdf import FPDF

    lw, lh, cols, rows_pp, ml, mt, gx = _PLANCHES.get(fmt, _PLANCHES["63.5x38.1"])
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_font("inter", fname=str(_FONTS / "Inter-Regular.ttf"))
    pdf.set_margins(0, 0, 0)
    par_page = cols * rows_pp
    for i, ligne in enumerate(lignes):
        pos = i % par_page
        if pos == 0:
            pdf.add_page()
            if ref:   # référence de traçabilité (Lot 3) — discrète, en pied de planche
                pdf.set_font("inter", size=5)
                pdf.set_text_color(150, 150, 150)
                pdf.set_xy(4, 292)
                pdf.cell(0, 3, f"LA BUSE · {ref}")
        col, row = pos % cols, pos // cols
        x = ml + col * (lw + gx)
        y = mt + row * lh
        destinataire, l1, l2, cp, ville, _idu = (str(v or "") for v in ligne[:6])
        pdf.set_text_color(20, 25, 22)
        pdf.set_xy(x + 4, y + 7)
        pdf.set_font("inter", size=9)
        pdf.cell(lw - 8, 4.5, destinataire)
        pdf.set_xy(x + 4, y + 13)
        pdf.set_font("inter", size=8.5)
        pdf.cell(lw - 8, 4.2, l1[:38])
        if l2:
            pdf.set_xy(x + 4, y + 17.5)
            pdf.cell(lw - 8, 4.2, l2[:38])
        pdf.set_xy(x + 4, y + 22)
        pdf.cell(lw - 8, 4.2, f"{cp} {ville}".strip())
    if not lignes:      # planche vide explicite plutôt qu'un PDF 0 page invalide
        pdf.add_page()
        pdf.set_font("inter", size=9)
        pdf.set_xy(20, 20)
        pdf.cell(0, 5, "Aucune adresse distribuable dans cette sélection.")
    return bytes(pdf.output())


def zip_publipostage(csv_data: bytes, pdf_data: bytes, gabarit: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("publipostage.csv", csv_data)
        z.writestr("etiquettes.pdf", pdf_data)
        if gabarit:
            z.writestr("gabarit_courrier.txt", gabarit)
    return buf.getvalue()
