"""ÉTUDE DE ZONE · Z5 — rapport PDF de l'outil (maquette, écran 3).

Rend l'agrégat de zone (sortie de `etude_zone`) en une page A4 sobre : population, activité &
concurrence, marché immobilier. Chaîne fpdf2 existante (mêmes polices/pied que la fiche premium).

Honnêteté (mandat) : revenu marqué ESTIMÉ (astérisque + note), chaque bloc sourcé, AUCUNE prévision
de chiffre d'affaires — des faits sourcés et datés.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

FONTS = Path(__file__).resolve().parent / "fonts"
GREEN = (74, 222, 128)
INK = (24, 32, 28)
DIM = (120, 132, 125)
FILET = (210, 220, 214)
MINT_PRINT = (30, 158, 88)


def _fam(pdf: FPDF, name: str) -> str:
    return name if name in getattr(pdf, "fonts", {}) else "helvetica"


def _nb(n) -> str:
    if n is None:
        return "—"
    return f"{int(round(n)):,}".replace(",", " ")


def _minis(pdf: FPDF, cards: list[tuple[str, str]]) -> None:
    """Rangée de mini-cartes (valeur en gras + légende), 4 par ligne comme la maquette."""
    fam = _fam(pdf, "inter")
    x0, y0 = pdf.get_x(), pdf.get_y()
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    n = len(cards)
    gap = 2.2
    w = (usable - gap * (n - 1)) / n
    h = 13.0
    for i, (v, k) in enumerate(cards):
        x = x0 + i * (w + gap)
        pdf.set_xy(x, y0)
        pdf.set_draw_color(*FILET)
        pdf.set_line_width(0.2)
        pdf.rect(x, y0, w, h)
        pdf.set_xy(x + 2, y0 + 2)
        pdf.set_font(fam, size=10)
        pdf.set_text_color(*INK)
        pdf.cell(w - 4, 5, v)
        pdf.set_xy(x + 2, y0 + 7.5)
        pdf.set_font(fam, size=6.5)
        pdf.set_text_color(*DIM)
        pdf.multi_cell(w - 4, 3, k)
    pdf.set_xy(x0, y0 + h + 4)


def _titre_section(pdf: FPDF, txt: str) -> None:
    fam = _fam(pdf, "mono")
    pdf.set_font(fam, size=7)
    pdf.set_text_color(*DIM)
    pdf.cell(0, 4, txt.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)


def render_zone_pdf(data: dict, *, titre: str | None = None) -> bytes:
    pop = data.get("population") or {}
    conc = data.get("concurrents") or {}
    marche = data.get("marche") or {}
    emp = data.get("emplois") or {}              # LOT 2 : fourchette de postes salariés (SIRENE)
    gen = data.get("generateurs_flux") or []
    postes = (f"{emp['postes_min']}–{emp['postes_max']}{'+' if emp.get('postes_max_ouvert') else ''}"
              if data.get("emplois_couverture") == "servie" and (emp.get("postes_max") or 0) > 0 else None)
    ecoles = sum(1 for g in gen if "enseignement" in (g.get("label", "").lower()))
    hab_conc = data.get("habitants_par_concurrent")
    minutes, mode = data.get("minutes"), data.get("mode")
    mode_lib = "en voiture" if mode == "voiture" else "à pied"

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    for fam, fn in (("inter", "Inter-Regular.ttf"), ("mono", "JetBrainsMono-Regular.ttf"),
                    ("grotesk", "SpaceGrotesk-Bold.ttf")):
        f = FONTS / fn
        if f.exists():
            pdf.add_font(fam, fname=str(f))
    pdf.set_margins(16, 14, 16)
    pdf.add_page()

    # en-tête : LABUSE + ÉTUDE DE ZONE + date, filet vert
    pdf.set_font(_fam(pdf, "grotesk"), size=13)
    pdf.set_text_color(*MINT_PRINT)
    pdf.cell(0, 7, "LABUSE")
    pdf.set_font(_fam(pdf, "mono"), size=7.5)
    pdf.set_text_color(*DIM)
    pdf.cell(0, 7, f"ÉTUDE DE ZONE · {date.today().strftime('%d/%m/%Y')}", align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*MINT_PRINT)
    pdf.set_line_width(0.4)
    pdf.line(16, pdf.get_y() + 1, pdf.w - 16, pdf.get_y() + 1)
    pdf.ln(4)

    # titre + sous-titre (zone + activité)
    pdf.set_font(_fam(pdf, "inter"), size=13)
    pdf.set_text_color(*INK)
    pdf.cell(0, 7, titre or "Étude de zone", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(_fam(pdf, "inter"), size=8)
    pdf.set_text_color(*DIM)
    sous = f"Zone : {minutes} min {mode_lib} (isochrone IGN, hors trafic)"
    if data.get("naf_label"):
        sous += f" · Activité étudiée : {data['naf_label']}"
    pdf.cell(0, 5, sous, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # POPULATION
    _titre_section(pdf, "Population de la zone")
    if pop.get("inhabitee"):
        pdf.set_font(_fam(pdf, "inter"), size=8)
        pdf.set_text_color(*DIM)
        pdf.multi_cell(0, 4.5, "Zone peu ou pas habitée — aucun carreau INSEE peuplé.",
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    else:
        rev = pop.get("revenu_median_eur")
        _minis(pdf, [
            (_nb(pop.get("habitants")), "habitants"),
            (_nb(pop.get("menages")), "ménages"),
            (f"{_nb(rev)} €*" if rev is not None else "—*", "revenu médian / an"),
            (f"{pop.get('pct_moins_25')} %" if pop.get("pct_moins_25") is not None else "—", "− de 25 ans"),
        ])

    # ACTIVITÉ & CONCURRENCE (si un NAF a été étudié)
    if data.get("naf_label") or conc:
        _titre_section(pdf, "Activité & concurrence")
        _minis(pdf, [
            (_nb(conc.get("n")), "concurrents"),
            (_nb(hab_conc), "hab. / concurrent"),
            (postes or "—", "postes salariés"),
            (_nb(ecoles), "écoles & collèges"),
        ])

    # MARCHÉ IMMOBILIER
    _titre_section(pdf, "Marché immobilier de la zone")
    _minis(pdf, [
        (_nb(marche.get("ventes_12m")), "ventes / 12 mois"),
        (f"{_nb(marche.get('prix_m2_median_bati'))} €" if marche.get("prix_m2_median_bati") is not None else "—", "médian €/m² bâti"),
        (_nb(marche.get("annonces_actives")), "annonces actives"),
        (_nb(marche.get("permis_36m")), "permis / 36 mois"),
    ])

    # pied : note d'honnêteté + sources
    pdf.ln(4)
    pdf.set_draw_color(*FILET)
    pdf.set_line_width(0.2)
    pdf.line(16, pdf.get_y(), pdf.w - 16, pdf.get_y())
    pdf.ln(2)
    pdf.set_font(_fam(pdf, "inter"), size=6.2)
    pdf.set_text_color(*DIM)
    pdf.multi_cell(0, 3, "* Revenu estimé — carreaux INSEE Filosofi 2021, valeurs lissées pour la "
                         "confidentialité. Sources : INSEE (Filosofi, MOBPRO), SIRENE (établissements "
                         "actifs), BPE 2025, DVF, IGN (isochrones — temps hors trafic), Radar LABUSE. "
                         "Aucune prévision de chiffre d'affaires — des faits sourcés et datés.",
                   new_x="LMARGIN", new_y="NEXT")

    out = pdf.output()
    return bytes(out)
