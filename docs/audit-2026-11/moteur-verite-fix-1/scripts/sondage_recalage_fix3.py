"""MOTEUR-VERITE-FIX-3 LOT 4 — recalage du sondage (2e relecture indépendante).

Bandes REFAITES sous les MÊMES noms, à la page de la RÈGLE réellement appliquée :
F02/F22 → 97415 p.21 (art. 7 : U1b « pourra s'implanter sur une limite… 18 m » ;
U1a « les rez-de-chaussée… d'une limite séparative à l'autre » dans la bande de
10 m depuis la voie) — l'ancienne bande montrait p.20 (exceptions de l'art. 6).
F05 → 97414 p.46 (UC 7.3 fond, « L'implantation en limite est possible dès lors
que la nouvelle construction n'excède pas 4 mètres… »). F06 → 97420 p.13 (U5.3
régime UA, « implantées en limite de fond de terrain »). F12/F17 → 97415 p.112
(U3a « devront s'implanter sur une limite séparative ou en retrait minimum de
3 m » ; U3b et U3c « pourront s'implanter sur une limite séparative »).

LECTURES corrigées (section RECALAGE FIX-3 ajoutée au MD, rien n'est déplacé) :
F17 — la zone est AU3b par RENVOI vers U3b : la règle U3b est une FACULTÉ sous
conditions (« pourront »), pas une obligation ; sous liste blanche FIX-3 elle
reste FERMÉE (conditions non toutes mesurées). F21 — Trois-Bassins Uaa : la
limite est IMPOSÉE mais l'article porte une CONDITION PATIO (habitations > 10 m
de profondeur en limite → patio 3 m min) non modélisée → prudence maintenue.
F23 — Le Port Ud art. 5 : « en limite séparative ET/OU suivant l'alignement des
constructions limitrophes existantes » : l'alignement des voisins est une
ALTERNATIVE → reclassé, pas une limite imposée pure.

    python docs/audit-2026-11/moteur-verite-fix-1/scripts/sondage_recalage_fix3.py
"""
from __future__ import annotations

import glob
import re
import subprocess
import unicodedata
from pathlib import Path
from xml.etree import ElementTree

FIX = Path(__file__).resolve().parents[1]
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


def bande(tag: str, insee: str, cherche: str, page: int) -> str:
    """Image la bande de la phrase à LA page donnée (vérifiée à la main au PDF)."""
    from PIL import Image
    pdf = _pdf(insee)
    cles = _norm(cherche).split()[:10]
    lgs = lignes_page(pdf, page)

    def score(l):
        return sum(1 for m in cles if m in l[2])
    best = [l for l in sorted(lgs, key=lambda l: -score(l))
            if score(l) >= max(4, len(cles) - 3)][:4]
    if not best:
        return f"ÉCHEC : phrase non trouvée p.{page}"
    # le rendu passe par un préfixe TEMPORAIRE : `next(glob("SONDAGE-Fxx-page*.png"))` attrapait
    # l'ANCIEN SONDAGE-Fxx-page.png (découpe sur la mauvaise page, vu sur F17).
    for vieux in OUT.glob(f"SONDAGE-{tag}-pagetmp*.png"):
        vieux.unlink()
    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", "150", "-png",
                    str(pdf), str(OUT / f"SONDAGE-{tag}-pagetmp")], check=True)
    pagepng = next(OUT.glob(f"SONDAGE-{tag}-pagetmp*.png"))
    pagepng = pagepng.replace(OUT / f"SONDAGE-{tag}-page.png")
    pagepng = OUT / f"SONDAGE-{tag}-page.png"
    y0 = min(l[0] for l in best) - 6
    y1 = max(l[1] for l in best) + 6
    img = Image.open(pagepng)
    k = 150 / 72.0
    img.crop((0, max(0, int(y0 * k)), img.width,
              min(img.height, int(y1 * k)))).save(OUT / f"SONDAGE-{tag}-bande.png")
    return f"bande refaite ({pdf.name} p.{page})"


#: tag → (insee, phrase de la RÈGLE, page VÉRIFIÉE, note pour le MD)
RECALAGES = {
    "F02": ("97415", "en zone U1b Chaque construction pourra s'implanter sur une limite "
            "séparative sur une longueur maximale de 18 m", 21,
            "règle U1b (art. 7) imagée p.21 — l'ancienne bande montrait p.20 (exceptions art. 6)"),
    "F05": ("97414", "L'implantation en limite est possible dès lors que la nouvelle construction "
            "n'excède pas 4 mètres de hauteur absolue", 46,
            "règle UC 7.3 (fond) imagée à sa vraie page (46), plus de « ligne non localisée »"),
    "F06": ("97420", "les constructions peuvent être implantées en limite de fond de terrain", 13,
            "règle U5.3 (fond, régime UA) imagée à sa vraie page (13)"),
    "F12": ("97415", "en zone U3a Les constructions devront s'implanter sur une limite séparative "
            "ou en retrait minimum", 112,
            "alinéa U3a imagé p.112 (et non 111)"),
    "F17": ("97415", "en zone U3b et U3c Les constructions pourront s'implanter sur une limite "
            "séparative", 112,
            "règle U3b/U3c imagée p.112 — LECTURE : AU3b renvoie vers U3b, FACULTÉ sous "
            "conditions (« pourront »), fermée sous liste blanche FIX-3"),
    "F22": ("97415", "les rez-de-chaussée de constructions devront être édifiés d'une limite "
            "séparative à l'autre", 21,
            "règle U1a imagée p.21 : le RDC est imposé d'une limite à l'autre DANS LA BANDE DE "
            "10 m depuis la voie (pas sur toute la parcelle)"),
}

LECTURES = [
    "- **F17** (97415 AU3b → U3b) : la règle U3b est une FACULTÉ sous conditions "
    "(« pourront s'implanter sur une limite séparative sur une longueur maximale… ») — pas une "
    "obligation ; sous la liste blanche FIX-3 la zone reste FERMÉE (conditions non toutes mesurées).",
    "- **F21** (97423 Uaa, p.15) : limite IMPOSÉE AVEC CONDITION PATIO — le même article 7.2 "
    "impose « des espaces libres de type patio de 3 mètres minimum » aux habitations de plus de "
    "10 m de profondeur en limite (5 m au-delà de 20 m pour les autres constructions). La "
    "condition patio n'est pas modélisée → l'imposée ne sert aucun scénario chiffré en limite "
    "(prudence maintenue, condition `patio` de la liste blanche non mesurée).",
    "- **F23** (97407 Ud, art. 5) : « Les constructions doivent être implantées en limite "
    "séparative ET/OU suivant l'alignement des constructions limitrophes existantes » — "
    "l'alignement des voisins est une ALTERNATIVE à la limite : RECLASSÉ, ce n'est pas une "
    "limite imposée pure (aucun scénario « en limite 0 m » garanti).",
]


def main() -> None:
    md = (OUT / "SONDAGE-20.md").read_text()
    lignes = ["", "---", "", "## RECALAGE FIX-3 (2e relecture indépendante)", "",
              "Bandes REFAITES sous les mêmes noms, à la page de la règle réellement appliquée :", ""]
    for tag, (insee, phrase, page, note) in RECALAGES.items():
        statut = bande(tag, insee, phrase, page)
        print(f"{tag}: {statut}")
        lignes.append(f"- **{tag}** ({insee}) : {note} — {statut}. Phrase imagée : « {phrase[:120]} »")
    lignes += ["", "Lectures corrigées :", ""] + LECTURES + [""]
    (OUT / "SONDAGE-20.md").write_text(md + "\n".join(lignes))
    print("SONDAGE-20.md complété (section RECALAGE FIX-3)")


if __name__ == "__main__":
    main()
