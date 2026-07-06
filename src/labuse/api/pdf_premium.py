"""Export PDF de la fiche premium (Brique 3) — design system LABUSE (noir #060A08 / menthe #5CE6A1).

Rendu fpdf2 (pur Python) avec les fontes du design system (OFL, embarquées dans api/fonts/).
Contenu = la fiche complète : en-tête (IDU/statut/surface), bandeau événement, scores Q/A +
complétude, lignes cascade TRACÉES par onglet (poids signé, détail, source, date), flags,
footer non-garantie. Les données viennent de _q_v2_fiche — même source que l'écran.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

FONTS = Path(__file__).resolve().parent / "fonts"

# Palette design system (hex → RGB)
BG = (6, 10, 8)            # #060A08
SURFACE = (17, 24, 20)     # #111814
LINE = (30, 42, 35)        # #1E2A23
MINT = (92, 230, 161)      # #5CE6A1
MINT_INK = (6, 19, 12)
TXT_HI = (236, 245, 239)
TXT = (201, 220, 209)
TXT_MUT = (143, 166, 154)
TXT_DIM = (92, 114, 104)
RED = (232, 105, 90)       # #E8695A
AMBER = (232, 180, 76)     # #E8B44C

STATUT = {
    "chaude": ("Chaude", MINT),
    "a_surveiller": ("À surveiller", (74, 222, 150)),
    "a_creuser": ("À creuser", AMBER),
    "ecartee": ("Écartée", RED),
    "exclue": ("Exclue", (107, 122, 114)),
}
ONGLETS = [("regles", "RÈGLES"), ("risques", "RISQUES"), ("marche", "MARCHÉ"), ("proprio", "PROPRIO")]


class _Pdf(FPDF):
    def header(self):  # fond sombre pleine page, posé à chaque page
        self.set_fill_color(*BG)
        self.rect(0, 0, self.w, self.h, style="F")
        self.set_y(12)

    def footer(self):
        self.set_y(-16)
        self.set_font("inter", size=6.5)
        self.set_text_color(*TXT_DIM)
        self.cell(0, 4, "Estimations indicatives issues de données publiques — ne valent ni conseil "
                        "juridique/notarial ni garantie de constructibilité. À vérifier au règlement et "
                        "auprès des services.", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, f"LA BUSE · radar foncier La Réunion · export du {date.today().isoformat()} · "
                        f"page {self.page_no()}/{{nb}}", align="C")


def _chip(pdf: _Pdf, x: float, y: float, label: str, color: tuple) -> float:
    pdf.set_font("inter", size=7.5)
    w = pdf.get_string_width(label) + 6
    pdf.set_fill_color(int(color[0] * 0.22), int(color[1] * 0.22), int(color[2] * 0.22))
    pdf.rect(x, y, w, 5.4, style="F", round_corners=True, corner_radius=2.6)
    pdf.set_text_color(*color)
    pdf.set_xy(x + 3, y + 0.7)
    pdf.cell(w - 6, 4, label)
    return w


def render_fiche_pdf(fiche: dict) -> bytes:
    pdf = _Pdf(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_font("inter", fname=str(FONTS / "Inter-Regular.ttf"))
    pdf.add_font("mono", fname=str(FONTS / "JetBrainsMono-Regular.ttf"))
    pdf.add_font("grotesk", fname=str(FONTS / "SpaceGrotesk-Bold.ttf"))
    pdf.set_margins(14, 12, 14)
    pdf.add_page()

    # ── En-tête produit
    pdf.set_font("grotesk", size=13)
    pdf.set_text_color(*MINT)
    pdf.cell(0, 6, "LA BUSE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=7.5)
    pdf.set_text_color(*TXT_DIM)
    pdf.cell(0, 4, "Radar foncier premium — La Réunion · fiche parcelle (scoring v2, run q_v2)",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Bandeau événement (héros)
    if fiche.get("evenement") == "rouge":
        detail = fiche.get("evenement_detail") or ""
        # hauteur du bandeau = titre + détail wrap (mesuré avant de peindre le fond)
        pdf.set_font("inter", size=7)
        n_lines = max(1, len(pdf.multi_cell(pdf.w - 36, 3.6, detail, dry_run=True, output="LINES")))
        h = 7.6 + n_lines * 3.6 + 2
        y = pdf.get_y()
        pdf.set_fill_color(58, 22, 20)
        pdf.rect(14, y, pdf.w - 28, h, style="F", round_corners=True, corner_radius=2)
        pdf.set_xy(18, y + 1.6)
        pdf.set_font("inter", size=8.5)
        pdf.set_text_color(*RED)
        pdf.cell(0, 4, "● ÉVÉNEMENT — force « chaude »", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(18, y + 7.2)
        pdf.set_font("inter", size=7)
        pdf.set_text_color(232, 169, 159)
        pdf.multi_cell(pdf.w - 36, 3.6, detail)
        pdf.set_y(y + h + 3)

    # ── IDU + statut + méta
    pdf.set_font("mono", size=14)
    pdf.set_text_color(*TXT_HI)
    pdf.cell(0, 7, fiche["idu"], new_x="LMARGIN", new_y="NEXT")
    label, color = STATUT.get(fiche["statut"], ("?", TXT_MUT))
    y = pdf.get_y() + 1
    w = _chip(pdf, 14, y, label, color)
    pdf.set_font("inter", size=8)
    pdf.set_text_color(*TXT_MUT)
    surf = f"{fiche['surface_m2']:,} m²".replace(",", " ") if fiche.get("surface_m2") else "surface n/d"
    lon, lat = fiche.get("coords", [None, None])
    pdf.set_xy(14 + w + 4, y + 0.4)
    pdf.cell(0, 4.6, f"{surf} · {fiche.get('commune', '')} · {lat}, {lon}")
    pdf.set_y(y + 9)

    # ── Scores (Q / A / complétude — le score ne s'affiche jamais seul)
    y = pdf.get_y()
    cw = (pdf.w - 28 - 8) / 3
    vals = [("QUALITÉ", fiche["q_score"], MINT), ("ACCESSIBILITÉ", fiche["a_score"], (74, 222, 150)),
            ("COMPLÉTUDE", fiche["completeness_score"],
             MINT if fiche["completeness_score"] >= 50 else AMBER)]
    for i, (k, v, c) in enumerate(vals):
        x = 14 + i * (cw + 4)
        pdf.set_fill_color(*SURFACE)
        pdf.rect(x, y, cw, 17, style="F", round_corners=True, corner_radius=2.4)
        pdf.set_xy(x + 5, y + 2.6)
        pdf.set_font("grotesk", size=15)
        pdf.set_text_color(*c)
        pdf.cell(cw - 10, 7, str(v))
        pdf.set_xy(x + 5, y + 10.6)
        pdf.set_font("mono", size=6.3)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(cw - 10, 4, f"{k} / 100" if k != "COMPLÉTUDE" else f"{k} %")
    pdf.set_y(y + 21)

    # ── Lignes tracées, par onglet
    for key, titre in ONGLETS:
        lines = [ln for ln in fiche["lines"] if ln["onglet"] == key]
        if not lines:
            continue
        pdf.ln(1.5)
        pdf.set_font("mono", size=7.5)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 5, titre, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*LINE)
        pdf.line(14, pdf.get_y(), pdf.w - 14, pdf.get_y())
        pdf.ln(1.2)
        for ln in lines:
            if pdf.get_y() > pdf.h - 34:
                pdf.add_page()
            w0 = ln.get("weight")
            wtxt = ("+" + str(w0) if (w0 or 0) > 0 else str(w0)) if w0 is not None else \
                ("?" if ln["result"] == "UNKNOWN" else "·")
            wcol = MINT if (w0 or 0) > 0 else (RED if (w0 or 0) < 0 else TXT_DIM)
            pdf.set_font("mono", size=8)
            pdf.set_text_color(*wcol)
            pdf.cell(11, 4.4, wtxt, align="R")
            pdf.set_font("inter", size=8)
            pdf.set_text_color(*TXT)
            pdf.cell(40, 4.4, ln["layer"][:26])
            pdf.set_font("inter", size=7.2)
            pdf.set_text_color(*TXT_MUT)
            x = pdf.get_x()
            pdf.multi_cell(pdf.w - 14 - x, 3.6, ln["detail"] or "", new_x="LMARGIN", new_y="NEXT")
            # traçabilité : source + référence + date (exigence fraîcheur par ligne)
            src = ln.get("source") or ""
            ref = f"{ln['source_table']}#{ln['source_id']}" if ln.get("source_id") is not None else ""
            pdf.set_x(65)
            pdf.set_font("mono", size=6)
            pdf.set_text_color(*TXT_DIM)
            pdf.cell(0, 3.4, "  ".join(x for x in (src, ref, ln.get("date") or "") if x),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.8)

    out = pdf.output()
    return bytes(out)
