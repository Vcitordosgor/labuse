"""PLU-MAJ-2 — sondage de dix règles chiffrées tirées à GRAINE FIXE, chacune prouvée par l'IMAGE de
la ligne de la page officielle + la citation mot pour mot.

Tire 10 règles parmi les règles calibrées `valide` des communes mises à jour (Saint-Denis 97411,
La Possession 97408), ouvre le règlement PDF officiel à la page gravée, localise la ligne qui porte la
citation et en découpe une bande PNG (via PyMuPDF). Écrit les images sous docs/.../images/ et un
tableau Markdown + un JSON reproductible.

Usage : PYTHONPATH=src <venv>/python scripts/plu_maj_2_sondage.py
"""
from __future__ import annotations

import json
import random
import re
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF

from labuse.plu import destinations as D

GRAINE = 20262115  # graine fixe « PLU-MAJ-2 » — tirage reproductible
COMMUNES = {"97411", "97408"}
PDF = {
    "97411": "data/plu_reglements/97411_reglement_20260805.pdf",
    "97408": "data/plu_reglements/97408_reglement_20260625.pdf",
}
OUT_IMG = Path("docs/audit-2026-11/plu-maj-2/images")
OUT_MD = Path("docs/audit-2026-11/plu-maj-2/SONDAGE-10-REGLES.md")
OUT_JSON = Path("docs/audit-2026-11/plu-maj-2/sondage-10-regles.json")

_META = {"insee", "zone", "chemin", "article", "page_pdf", "citation", "statut", "fichier"}


def _valeur(r: dict) -> str:
    vals = {k: v for k, v in r.items() if k not in _META and v is not None}
    return ", ".join(f"{k}={v}" for k, v in vals.items()) or "—"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def _localiser(page: fitz.Page, citation: str, valeur: str) -> fitz.Rect | None:
    """La bande (rect) qui contient la citation sur la page. On cherche d'abord un fragment net de la
    citation, puis la valeur, puis un fragment plus court — pour résister aux sauts de ligne du PDF."""
    cit = re.sub(r"\s+", " ", citation or "").strip()
    essais = []
    if cit:
        mots = cit.split(" ")
        essais.append(" ".join(mots[:8]))        # début de citation
        essais.append(" ".join(mots[2:9]))       # un peu plus loin (si la 1re ligne déborde)
        essais.append(" ".join(mots[:5]))
    # la valeur chiffrée nue (ex. « 16 m », « 16 mètres », « 60 % »)
    for m in re.findall(r"\d+[\s.,]?\d*\s?(?:m|mètre|metres|mètres|%|logement)", cit):
        essais.append(m)
    for frag in essais:
        if len(frag) < 4:
            continue
        rects = page.search_for(frag, quads=False)
        if rects:
            u = rects[0]
            for rr in rects[1:]:
                u = u | rr
            return u
    return None


def _crop(page: fitz.Page, rect: fitz.Rect | None, dest: Path, dpi: int = 160) -> str:
    """Découpe une BANDE pleine largeur autour de `rect` (la ligne), avec un peu de contexte vertical.
    Si la ligne n'est pas localisée, rend le tiers haut de la page (toujours une preuve de page)."""
    pw, ph = page.rect.width, page.rect.height
    if rect is not None:
        pad = 10.0
        clip = fitz.Rect(0, max(0, rect.y0 - pad), pw, min(ph, rect.y1 + pad))
        localisee = True
    else:
        clip = fitz.Rect(0, 0, pw, ph / 3.0)
        localisee = False
    pix = page.get_pixmap(dpi=dpi, clip=clip)
    pix.save(str(dest))
    return "ligne" if localisee else "page (ligne non localisée)"


def main() -> None:
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    regles = [r for r in D.iter_regles_calibrees()
              if r.get("insee") in COMMUNES and r.get("statut") == "valide"
              and r.get("citation") and r.get("page_pdf")]
    # tri stable AVANT tirage (reproductibilité indépendante de l'ordre d'itération)
    regles.sort(key=lambda r: (r["insee"], r["zone"], r["chemin"], r["page_pdf"]))
    rng = random.Random(GRAINE)
    tirage = rng.sample(regles, 10)

    docs = {i: fitz.open(p) for i, p in PDF.items()}
    lignes_md, recs = [], []
    for k, r in enumerate(tirage, 1):
        insee = r["insee"]
        page = docs[insee][r["page_pdf"] - 1]
        rect = _localiser(page, r["citation"], _valeur(r))
        nom = f"{k:02d}_{insee}_{r['zone']}_{r['chemin'].replace('.', '-')}.png"
        mode = _crop(page, rect, OUT_IMG / nom)
        commune = "Saint-Denis" if insee == "97411" else "La Possession"
        rec = {"n": k, "insee": insee, "commune": commune, "zone": r["zone"],
               "regle": r["chemin"], "valeur": _valeur(r), "article": r.get("article"),
               "page_pdf": r["page_pdf"], "citation": re.sub(r"\s+", " ", r["citation"]).strip(),
               "image": f"images/{nom}", "image_mode": mode}
        recs.append(rec)
        lignes_md.append(
            f"### {k}. {commune} — zone {r['zone']} — {r['chemin']}\n\n"
            f"- **Valeur calibrée** : `{rec['valeur']}`\n"
            f"- **Article** : {rec['article']} · **page PDF** : {r['page_pdf']} "
            f"({mode})\n"
            f"- **Citation (mot pour mot)** : « {rec['citation']} »\n\n"
            f"![{rec['zone']} {r['chemin']}]({rec['image']})\n")

    OUT_JSON.write_text(json.dumps({"graine": GRAINE, "regles": recs}, ensure_ascii=False, indent=1))
    entete = (f"# PLU-MAJ-2 — sondage de 10 règles (graine fixe {GRAINE})\n\n"
              "Dix règles chiffrées tirées au hasard (graine fixe, donc reproductible) parmi les règles "
              "calibrées `valide` des communes mises à jour (Saint-Denis `97411_PLU_20260805`, "
              "La Possession `97408_PLU_20260625`). Chacune est prouvée par l'IMAGE de la ligne de la "
              "page officielle du règlement opposable + la citation mot pour mot.\n\n"
              "> Rejouer : `PYTHONPATH=src <venv>/python scripts/plu_maj_2_sondage.py`\n\n---\n\n")
    OUT_MD.write_text(entete + "\n".join(lignes_md))
    loc = sum(1 for r in recs if r["image_mode"] == "ligne")
    print(f"— 10 règles tirées (graine {GRAINE}) · {loc}/10 lignes localisées à l'image")
    for r in recs:
        print(f"  {r['n']:2} {r['commune']:14} {r['zone']:10} {r['regle']:20} {r['valeur']:14} "
              f"p{r['page_pdf']} [{r['image_mode']}]")
    print(f"— images : {OUT_IMG}/  · tableau : {OUT_MD}")


if __name__ == "__main__":
    main()
