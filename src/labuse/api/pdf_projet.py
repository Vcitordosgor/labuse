"""Export PDF d'un PROJET (copilote-projet, V3) — la fiche de cadrage + les meilleures
parcelles avec leur « pourquoi ». Même identité d'impression que la fiche parcelle
(fond blanc, menthe en accents, fontes du design system). Réutilise la palette et les
fontes de pdf_premium ; les chiffres viennent du MOTEUR (aperçu), jamais de l'IA.
"""
from __future__ import annotations

from datetime import date

from fpdf import FPDF

from .pdf_premium import (FONTS, LINE, MINT, MINT_SOFT, SURFACE, TXT, TXT_DIM,
                          TXT_HI, TXT_MUT, _logo)

TYPE_LABEL = {"logements": "Logements", "etudiant": "Logement étudiant",
              "bureaux": "Bureaux", "autre": "Projet"}
CONTRAINTE_LABEL = {"eviter_ppr": "hors zone à risque (PPR)", "eviter_pollution": "sol non pollué",
                    "eviter_abf": "hors périmètre ABF", "eviter_icpe": "hors nuisance ICPE"}
SECTEUR = "secteur"


class _Pdf(FPDF):
    def header(self):
        self.set_draw_color(*MINT)
        self.set_line_width(0.6)
        self.line(14, 8, self.w - 14, 8)
        self.set_line_width(0.2)
        self.set_y(12)

    def footer(self):
        self.set_y(-16)
        self.set_font("inter", size=6.5)
        self.set_text_color(*TXT_DIM)
        self.cell(0, 4, "Estimations indicatives issues de données publiques — ne valent ni conseil "
                        "juridique/notarial ni garantie de constructibilité. À vérifier au règlement.",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, f"LA BUSE · radar foncier La Réunion · projet exporté le {date.today().isoformat()} · "
                        f"page {self.page_no()}/{{nb}}", align="C")


def _perimetre_label(fiche: dict) -> str:
    p = fiche.get("perimetre") or {}
    if p.get("mode") == SECTEUR:
        return f"Secteur {p.get('secteur')}"
    if p.get("mode") == "communes":
        cs = p.get("communes") or []
        return cs[0] if len(cs) == 1 else f"{len(cs)} communes"
    return "Toute l'île"


def render_projet_pdf(projet: dict, apercu: dict) -> bytes:
    fiche = projet.get("fiche") or {}
    pdf = _Pdf(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_font("inter", fname=str(FONTS / "Inter-Regular.ttf"))
    pdf.add_font("mono", fname=str(FONTS / "JetBrainsMono-Regular.ttf"))
    pdf.add_font("grotesk", fname=str(FONTS / "SpaceGrotesk-Bold.ttf"))
    pdf.set_margins(14, 12, 14)
    pdf.add_page()

    # ── En-tête produit
    _logo(pdf, 14, pdf.get_y() + 1, 13)
    pdf.set_x(30)
    pdf.set_font("grotesk", size=13)
    pdf.set_text_color(*MINT)
    pdf.cell(0, 6, "LA BUSE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=7.5)
    pdf.set_text_color(*TXT_DIM)
    pdf.cell(0, 4, "Radar foncier premium — La Réunion · dossier PROJET", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Titre du projet
    pdf.set_font("grotesk", size=16)
    pdf.set_text_color(*TXT_HI)
    pdf.multi_cell(0, 7, projet.get("nom") or "Projet", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # ── Fiche de cadrage
    def ligne(label: str, valeur: str) -> None:
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(34, 5, label)
        pdf.set_text_color(*TXT_HI)
        pdf.multi_cell(0, 5, valeur, new_x="LMARGIN", new_y="NEXT")

    pdf.set_fill_color(*SURFACE)
    pdf.set_draw_color(*LINE)
    y0 = pdf.get_y()
    pdf.rect(14, y0, pdf.w - 28, 1, style="F")  # filet fin
    pdf.ln(2)
    pdf.set_font("mono", size=7)
    pdf.set_text_color(*TXT_MUT)
    pdf.cell(0, 5, "FICHE DE CADRAGE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    t = fiche.get("type_programme")
    amp = fiche.get("ampleur") or {}
    ampleur = (f"{amp['logements']} logements" if amp.get("logements")
               else f"{amp['sdp_m2']:.0f} m² SDP" if amp.get("sdp_m2") else "—")
    ligne("Programme", TYPE_LABEL.get(t, "—"))
    ligne("Ampleur", ampleur)
    if apercu.get("sdp_besoin_m2"):
        ligne("SDP besoin", f"{apercu['sdp_besoin_m2']:,} m² (formule capacitaire M22)".replace(",", " "))
    ligne("Périmètre", _perimetre_label(fiche))
    contraintes = fiche.get("contraintes") or []
    if contraintes:
        ligne("Contraintes", ", ".join(CONTRAINTE_LABEL.get(c, c) for c in contraintes))
    if fiche.get("budget_foncier_eur"):
        ligne("Budget foncier", f"{fiche['budget_foncier_eur'] / 1000:,.0f} k€".replace(",", " "))
    if fiche.get("criteres_libres"):
        ligne("Notes", fiche["criteres_libres"])
    pdf.ln(3)

    # ── Les meilleures parcelles + leur POURQUOI
    pdf.set_font("mono", size=7)
    pdf.set_text_color(*TXT_MUT)
    total = apercu.get("n", 0)
    top = apercu.get("top", [])
    pdf.cell(0, 5, f"MEILLEURES PARCELLES  ·  {total:,} correspondent au projet".replace(",", " "),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    for i, it in enumerate(top, 1):
        pdf.set_font("mono", size=8.5)
        pdf.set_text_color(*TXT_HI)
        idu = it.get("idu", "")
        pdf.cell(0, 5, f"{i}.  {idu[8:10]} {idu[10:]}  ·  {it.get('commune', '')}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(*TXT)
        for l in it.get("pourquoi", []):
            pdf.set_text_color(*MINT)
            pdf.cell(4, 4.4, "·")
            pdf.set_text_color(*TXT)
            pdf.multi_cell(0, 4.4, l, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)

    if not top:
        pdf.set_font("inter", size=8)
        pdf.set_text_color(*TXT_MUT)
        pdf.multi_cell(0, 5, "Aucune parcelle ne correspond encore à ce cadrage — élargissez le "
                             "périmètre ou l'ampleur.", new_x="LMARGIN", new_y="NEXT")

    # ── mention
    pdf.ln(2)
    pdf.set_fill_color(*MINT_SOFT)
    pdf.set_font("inter", size=7)
    pdf.set_text_color(*TXT_MUT)
    pdf.multi_cell(0, 4.4, "Le « pourquoi » de chaque parcelle est assemblé depuis les données du "
                           "moteur déterministe (SDP résiduelle, hauteur PLU, statut/score, contexte "
                           "SRU). Les chiffres d'aide au choix sont sourcés ; l'IA n'en produit aucun.",
                   border=0, fill=True, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
