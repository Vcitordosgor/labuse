"""MOTEUR-VERITE-FIX-1 LOT 2 — sondage de DIX règles d'implantation à graine fixe, chacune
prouvée par l'IMAGE DE LA LIGNE ENTIÈRE de la page officielle du règlement.

Tirage : md5(insee|zone|cote|'VT-FIX-SONDAGE-1') sur l'union des 5 CSV — les 10 premiers.
Pour chaque règle : page `page_pdf` du PDF officiel → `pdftotext -bbox` pour localiser la ou les
lignes de la citation → rendu `pdftoppm` 150 dpi → bande PLEINE LARGEUR autour des lignes
(SONDAGE-<n>-bande.png) + page entière (SONDAGE-<n>-page.png). SONDAGE.md récapitule.

    python docs/audit-2026-11/moteur-verite-fix-1/scripts/sondage_images.py
"""
from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import unicodedata
from pathlib import Path
from xml.etree import ElementTree

FIX = Path(__file__).resolve().parents[1]
IMPL = FIX / "implantation"
REGL = FIX / "reglements"
OUT = FIX / "sondage"
GRAINE = "VT-FIX-SONDAGE-1"
PDF = {
    "97407": REGL / "97407" / "97407_reglement_20241209.pdf",
    "97409": REGL / "97409" / "97409_reglement_20190228.pdf",
    "97412": REGL / "97412" / "97412_Reglement_20251210.pdf",
    "97414": REGL / "97414" / "97414_reglement_20251218.pdf",
    "97416": REGL / "97416" / "97416_reglement_20240625.pdf",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def lignes_page(pdf: Path, page: int):
    """[(y_min, y_max, texte_normalisé)] des lignes de la page (bbox pdftotext, unité pt)."""
    xml = subprocess.run(["pdftotext", "-bbox", "-f", str(page), "-l", str(page),
                          str(pdf), "-"], capture_output=True, text=True).stdout
    xml = re.sub(r'xmlns="[^"]+"', "", xml, count=1)
    root = ElementTree.fromstring(xml)
    mots = [(float(w.get("yMin")), float(w.get("yMax")), w.text or "")
            for w in root.iter("word")]
    lignes: dict[int, list] = {}
    for y0, y1, t in mots:
        lignes.setdefault(int(y0 // 4), []).append((y0, y1, t))
    out = []
    for grp in lignes.values():
        out.append((min(g[0] for g in grp), max(g[1] for g in grp),
                    _norm(" ".join(g[2] for g in grp))))
    out.sort()
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows = []
    for f in sorted(IMPL.glob("979*.csv")) + sorted(IMPL.glob("974*.csv")):
        for r in csv.DictReader(open(f, newline=""), delimiter=";"):
            if (r.get("citation_verbatim") or "").strip() and (r.get("page_pdf") or "").strip():
                rows.append(r)
    rows.sort(key=lambda r: hashlib.md5(
        f"{r['insee']}|{r['zone']}|{r['cote']}|{GRAINE}".encode()).hexdigest())
    tirage = rows[:10]

    from PIL import Image
    md = ["# SONDAGE — 10 règles d'implantation, graine " + GRAINE, ""]
    for i, r in enumerate(tirage, 1):
        pdf = PDF[r["insee"]]
        page = int(float(r["page_pdf"]))
        cit = _norm(r["citation_verbatim"])[:120]
        cles = cit.split()[:8]
        lgs = lignes_page(pdf, page)
        hits = [l for l in lgs if all(False for _ in ())]  # placeholder
        # lignes contenant au moins 4 des 8 premiers mots de la citation, en séquence partielle
        def score(l):
            return sum(1 for m in cles if m in l[2])
        cands = sorted(lgs, key=lambda l: -score(l))
        best = [l for l in cands if score(l) >= max(3, len(cles) // 2)][:4]
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", "150", "-png",
                        str(pdf), str(OUT / f"SONDAGE-{i:02d}-page")], check=True)
        pagepng = next(OUT.glob(f"SONDAGE-{i:02d}-page*.png"))
        pagepng = pagepng.rename(OUT / f"SONDAGE-{i:02d}-page.png")
        statut = "ligne non localisée — page entière fournie"
        if best:
            y0 = min(l[0] for l in best) - 6
            y1 = max(l[1] for l in best) + 6
            img = Image.open(pagepng)
            k = 150 / 72.0           # pt → px à 150 dpi
            crop = img.crop((0, max(0, int(y0 * k)), img.width, min(img.height, int(y1 * k))))
            crop.save(OUT / f"SONDAGE-{i:02d}-bande.png")
            statut = f"bande extraite (y {y0:.0f}-{y1:.0f} pt, {len(best)} ligne(s))"
        md += [f"## {i:02d} — {r['insee']} zone {r['zone']} ({r['cote']}) · mode `{r['mode']}`",
               f"- Article {r['article']} · page PDF {page} · {statut}",
               f"- Citation : « {r['citation_verbatim'][:300]} »",
               f"- Images : `SONDAGE-{i:02d}-bande.png` (la ligne), `SONDAGE-{i:02d}-page.png` (la page)",
               ""]
    (OUT / "SONDAGE.md").write_text("\n".join(md))
    print(f"→ {OUT} (10 règles, images + SONDAGE.md)")


if __name__ == "__main__":
    main()
