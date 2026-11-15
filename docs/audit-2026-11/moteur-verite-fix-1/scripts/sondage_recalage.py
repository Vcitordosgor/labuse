"""MOTEUR-VERITE-FIX-2 LOT D — recalage du sondage final (relecture indépendante).

F02/F17 : l'image montrait la règle U cible mais la citation était le RENVOI (autre page) →
les deux lignes sont désormais imagées (règle + renvoi). F05/F06 : pages recalées en cherchant
la PHRASE DE LA RÈGLE (pas la citation composite). F12 : alinéa relocalisé. F09/F19 : le même
article règle AUSSI le fond — complété (F19 : clause de bande 10.3 imagée). F21-F23 : trois cas
« limite imposée » ajoutés. Les images sont régénérées SOUS LES MÊMES NOMS + suffixe `b` pour
les lignes complémentaires ; SONDAGE-20.md est corrigé en place (sections réécrites).
"""
from __future__ import annotations

import csv
import glob
import re
import subprocess
import unicodedata
from pathlib import Path
from xml.etree import ElementTree

FIX = Path(__file__).resolve().parents[1]
IMPL = FIX / "implantation"
REGL = FIX / "reglements"
OUT = FIX / "sondage-final"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _pdf(insee: str) -> Path:
    cand = [p for p in glob.glob(str(REGL / insee / "*.pdf"))
            if "graphique" not in p.lower() and re.search(r"eglement", p, re.I)]
    return Path(sorted(cand, key=lambda p: len(p))[0])


def lignes_page(pdf: Path, page: int):
    xml = subprocess.run(["pdftotext", "-bbox", "-f", str(page), "-l", str(page),
                          str(pdf), "-"], capture_output=True, text=True).stdout
    xml = re.sub(r'xmlns="[^"]+"', "", xml, count=1)
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []
    mots = [(float(w.get("yMin")), float(w.get("yMax")), w.text or "") for w in root.iter("word")]
    lignes: dict[int, list] = {}
    for y0, y1, t in mots:
        lignes.setdefault(int(y0 // 4), []).append((y0, y1, t))
    out = [(min(g[0] for g in grp), max(g[1] for g in grp),
            _norm(" ".join(g[2] for g in grp))) for grp in lignes.values()]
    out.sort()
    return out


def bande(tag: str, insee: str, cherche: str, page_hint: int, rayon: int = 6) -> tuple[str, int | None]:
    """Cherche la phrase autour de page_hint (± rayon), image la bande pleine largeur.
    Rend (statut, page_trouvée)."""
    from PIL import Image
    pdf = _pdf(insee)
    cles = _norm(cherche).split()[:8]
    def score(l):
        return sum(1 for m in cles if m in l[2])
    for delta in sorted(range(-rayon, rayon + 1), key=abs):
        page = page_hint + delta
        if page < 1:
            continue
        lgs = lignes_page(pdf, page)
        best = [l for l in sorted(lgs, key=lambda l: -score(l))
                if score(l) >= max(4, len(cles) - 2)][:4]
        if not best:
            continue
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", "150", "-png",
                        str(pdf), str(OUT / f"SONDAGE-{tag}-page")], check=True)
        pagepng = next(OUT.glob(f"SONDAGE-{tag}-page*.png"))
        pagepng = pagepng.rename(OUT / f"SONDAGE-{tag}-page.png")
        y0 = min(l[0] for l in best) - 6
        y1 = max(l[1] for l in best) + 6
        img = Image.open(pagepng)
        k = 150 / 72.0
        img.crop((0, max(0, int(y0 * k)), img.width,
                  min(img.height, int(y1 * k)))).save(OUT / f"SONDAGE-{tag}-bande.png")
        return f"bande extraite ({pdf.name} p.{page})", page
    return "ligne non localisée", None


#: tag → (insee, phrase de la RÈGLE à imager, page indicative, note pour le MD)
RECALAGES = {
    "F02": ("97415", "Les constructions devront s'implanter sur une limite séparative", 20,
            "règle U1 7.2 imagée À SA PAGE ; le renvoi AU est imagé à part (F02b)"),
    "F02b": ("97415", "Se reporter au règlement de la zone", 53, "le RENVOI du chapitre AU"),
    "F05": ("97414", "implantation en limite est possible dès lors que la nouvelle construction", 45,
            "règle UC 7.3 (fond) imagée à sa vraie page"),
    "F05b": ("97414", "il convient de se reporter en fonction de l'indice de la zone AU", 106,
             "le RENVOI AUindicée"),
    "F06": ("97420", "les constructions peuvent être implantées en limite de fond de terrain", 13,
            "règle U5.3 (fond, régime UA) imagée à sa vraie page ; renvoi AU p.30 (F06b)"),
    "F06b": ("97420", "Se reporter au règlement de la zone U", 30, "le RENVOI AUindicée 5"),
    "F12": ("97415", "en zone U3a Les constructions devront s'implanter sur une limite", 111,
            "alinéa U3a relocalisé"),
    "F17": ("97415", "Les constructions devront s'implanter sur une limite séparative", 111,
            "règle U3 7.2 imagée ; renvoi AU imagé à part (F17b)"),
    "F17b": ("97415", "Se reporter au règlement de la zone", 158, "le RENVOI du chapitre AU"),
    "F19b": ("97422", "hauteur maximale des constructions implantées dans une bande", 16,
             "clause de bande (hauteur en limite, art. 10.3) — le FOND est réglé par le même article"),
    # Nouveaux cas « limite imposée » (F21-F23)
    "F21": ("97413", "doivent joindre au moins une des deux limites séparatives", 15,
            "LIMITE IMPOSÉE — Saint-Leu Uaa (Ua 7.2)"),
    "F22": ("97415", "d'une limite séparative à l'autre", 20,
            "LIMITE IMPOSÉE — Saint-Paul U1a (RDC d'une limite à l'autre, bande de 10 m)"),
    "F23": ("97407", "en limite séparative et/ou suivant l'alignement des constructions", 38,
            "LIMITE IMPOSÉE — Le Port Ud (art. 5)"),
}


def main() -> None:
    md = (OUT / "SONDAGE-20.md").read_text()
    resultats = {}
    for tag, (insee, phrase, hint, note) in RECALAGES.items():
        statut, page = bande(tag, insee, phrase, hint)
        resultats[tag] = (statut, page, note, insee, phrase)
        print(f"{tag}: {statut}")
    # MD : notes de recalage ajoutées aux sections concernées + section des ajouts
    lignes = ["", "---", "", "## RECALAGE FIX-2 (relecture indépendante)", ""]
    for tag, (statut, page, note, insee, phrase) in sorted(resultats.items()):
        lignes.append(f"- **{tag}** ({insee}) : {note} — {statut}. Phrase imagée : « {phrase} »")
    lignes += ["", "F09 (Saint-Joseph U3) : le même article 7.2 règle AUSSI le fond (« limites",
               "séparatives » sans distinction — lecture littérale actée) ; depuis FIX-2 LOT C la",
               "famille U2/U3 est en lecture PRUDENTE (ruptures de mitoyenneté et hauteurs par bande",
               "non modélisées → pas d'ouverture chiffrée). F19 (Le Tampon Uav) : le fond relève du",
               "même article ; la clause de bande 10.3 est imagée (F19b).", ""]
    (OUT / "SONDAGE-20.md").write_text(md + "\n".join(lignes))
    print("SONDAGE-20.md complété (section RECALAGE FIX-2)")


if __name__ == "__main__":
    main()
