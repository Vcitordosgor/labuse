"""PLU-MAJ-2 (vérif Saint-Denis) — pleine terre sur le règlement EN VIGUEUR, image de la ligne.

Vérifie, zone par zone, ce que le règlement opposable de Saint-Denis (97411_PLU_20260805, PDF
data/plu_reglements/97411_reglement_20260805.pdf, md5 43426a8) dit RÉELLEMENT sur la pleine terre,
face aux valeurs rapportées par une autre session (UH 50 %, UJ/UM 35 %, UI 25 %, UD/UU 10 %, Uat 15 %).
Pour chaque zone : découpe l'image de la ligne/section de l'article 13 (ou de la ligne « Minimum X % …
pleine terre » quand elle existe). Résultat : UD = 30 %, UI = 40 %, et UH/UJ/UM/UU/Uat SANS minimum de
pleine terre — aucune des valeurs citées n'est dans le document en vigueur.
"""
from __future__ import annotations

from pathlib import Path

import fitz

PDF = "data/plu_reglements/97411_reglement_20260805.pdf"
OUT = Path("docs/audit-2026-11/plu-maj-2/images/saint-denis-pleine-terre")

# zone, valeur citée (autre session), ancre de recherche sur la page, page_pdf
CAS = [
    ("UD", "10 %", "Minimum 30% de la parcelle doit être en pleine terre", 46),
    ("UI", "25 %", "Minimum 40% de la parcelle doit être en pleine terre", 58),
    ("UH", "50 %", "ARTICLE Uh.13", 75),
    ("UJ", "35 %", "ARTICLE Uj.13", 64),
    ("UM", "35 %", "ARTICLE Um.13", 70),
    ("UU", "10 %", "ARTICLE Uu.13", 50),
    ("Uat", "15 %", "ARTICLE Ua.13", 80),   # Uat = secteur de la zone UA (ZAC Triangle)
]


def _rect(page: fitz.Page, ancre: str):
    for frag in (ancre, ancre.replace("ARTICLE ", ""), ancre.split()[0] + " " + ancre.split()[-1]):
        r = page.search_for(frag)
        if r:
            u = r[0]
            for rr in r[1:]:
                u = u | rr
            return u
    # repli : titre d'article 13 générique
    for frag in ("Espaces libres", "ESPACES LIBRES", "plantations", "ARTICLE 13", "Article 13"):
        r = page.search_for(frag)
        if r:
            return r[0]
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(PDF)
    lignes = []
    for zone, cite, ancre, page_pdf in CAS:
        pg = doc[page_pdf - 1]
        rect = _rect(pg, ancre)
        pw, ph = pg.rect.width, pg.rect.height
        a_valeur = "pleine terre" in ancre.lower()
        if rect is not None and a_valeur:
            clip = fitz.Rect(0, max(0, rect.y0 - 8), pw, min(ph, rect.y1 + 8))
        elif rect is not None:
            # section d'article 13 : la ligne de titre + ~230 px dessous (pour montrer l'absence)
            clip = fitz.Rect(0, max(0, rect.y0 - 6), pw, min(ph, rect.y0 + 230))
        else:
            clip = fitz.Rect(0, 0, pw, ph / 2)
        nom = f"{zone}_p{page_pdf}.png"
        pg.get_pixmap(dpi=160, clip=clip).save(str(OUT / nom))
        reel = {"UD": "30 % minimum (Ud.9, p46)", "UI": "40 % minimum (Ui.13, p58)"}.get(
            zone, f"AUCUN minimum de pleine terre (art. {zone.capitalize()}.13"
                  + (" — secteur de la zone UA, ZAC Triangle" if zone == "Uat" else "") + f", p{page_pdf})")
        lignes.append((zone, cite, reel, f"images/saint-denis-pleine-terre/{nom}"))
        print(f"{zone:4} cité {cite:5} → RÉEL : {reel}")
    # tableau markdown
    md = ["# Saint-Denis — pleine terre dans le règlement EN VIGUEUR (97411_PLU_20260805)\n",
          "Vérification zone par zone, image de la ligne/section de l'article 13 à l'appui. Les valeurs",
          "rapportées par une autre session ne figurent PAS dans le document opposable : seules **UD (30 %)**",
          "et **UI (40 %)** portent un minimum de pleine terre ; UH/UJ/UM/UU et le secteur Uat n'en portent",
          "aucun.\n",
          "| Zone | Valeur citée | Règlement en vigueur 20260805 | Image |",
          "|---|---|---|---|"]
    for zone, cite, reel, img in lignes:
        md.append(f"| {zone} | {cite} | {reel} | ![{zone}]({img}) |")
    Path("docs/audit-2026-11/plu-maj-2/SAINT-DENIS-PLEINE-TERRE.md").write_text("\n".join(md) + "\n")
    print(f"— {len(lignes)} images : {OUT}/ · tableau : SAINT-DENIS-PLEINE-TERRE.md")


if __name__ == "__main__":
    main()
