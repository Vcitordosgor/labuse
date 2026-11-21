"""ETUDE-STATIONNEMENT-FIX-1 (LOT 3) — rend l'IMAGE de la ligne entière de chaque règle tirée, depuis le
PDF officiel (data/plu_reglements), + écrit SONDAGE-10-LOT3.md.

    PYTHONPATH=src python scripts/sondage_images.py --seed 20260115 --n 10
"""
import argparse
import glob
import os
import re

import fitz

from labuse.implantation import regles as R
from sondage_tirage import pool, synth  # type: ignore

PDFDIR = os.path.expanduser("~/Desktop/labuse/data/plu_reglements/")
OUTDIR = "docs/audit-2026-11/etude-stationnement-fix-1/pages_lot3/"


def pdf_for(insee):
    hits = glob.glob(PDFDIR + f"{insee}_[rR]eglement_*.pdf")
    return hits[0] if hits else None


def anchor_from(b):
    """Un fragment distinctif à chercher sur la page (début de citation, ou valeur clé)."""
    if b.citation:
        # premier segment « parlant » de la citation
        seg = re.split(r'[.:;]', b.citation)[0].strip()
        return seg[:38]
    if b.mode == "par_m2_sdp":
        return f"{b.m2_par_place:g} m"
    if b.mode == "par_logement":
        return "par logement"
    return "logement"


def render(insee, zone, b, key):
    pdf = pdf_for(insee)
    if pdf is None or b.page_pdf is None:
        return None
    d = fitz.open(pdf)
    idx = b.page_pdf - 1               # page_pdf 1-indexé (DB) → pymupdf 0-indexé
    if idx < 0 or idx >= d.page_count:
        d.close(); return None
    pg = d[idx]
    anc = anchor_from(b)
    rects = pg.search_for(anc) or pg.search_for("par logement") or pg.search_for("stationnement")
    if not rects:
        d.close(); return None
    r = rects[0]
    clip = fitz.Rect(0, max(0, r.y0 - 70), pg.rect.width, min(pg.rect.height, r.y0 + 200))
    os.makedirs(OUTDIR, exist_ok=True)
    pg.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=clip).save(OUTDIR + key + ".png")
    d.close()
    return key + ".png"


def main():
    import random
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args()
    picks = random.Random(a.seed).sample(pool(), a.n)
    o = [f"# SONDAGE-10-LOT3 — dix règles tirées à GRAINE FIXE, prouvées par la page\n",
         f"ETUDE-STATIONNEMENT-FIX-1 (LOT 3). Tirage **déterministe** (non choisi) sur les {len(pool())} zones "
         f"constructibles servies des communes à texte en base.\n",
         "**Commande du tirage :**\n```\n"
         f"PYTHONPATH=src python scripts/sondage_tirage.py --seed {a.seed} --n {a.n}\n"
         f"PYTHONPATH=src python scripts/sondage_images.py --seed {a.seed} --n {a.n}\n```\n",
         "Chaque règle : la valeur appliquée, la citation, l'article · page, et l'**image de la ligne entière** "
         "du PDF officiel.\n"]
    for i, (insee, z) in enumerate(picks, 1):
        b = R.charger(insee, z).stationnement
        key = f"{i:02d}_{insee}_{z}"
        img = render(insee, z, b, key)
        o.append(f"## {i}. {insee} — zone {z} (article {b.article} · p.{b.page_pdf})")
        o.append(f"- **Valeur appliquée** : {synth(b)}")
        if b.conditions:
            o.append(f"- **Condition(s) à vérifier** : " + " ; ".join(b.conditions))
        o.append(f"- **Citation** : « {b.citation} »")
        if img:
            o.append(f"- **Preuve (image de la ligne, p.{b.page_pdf}) :**\n\n  ![{insee} {z}](pages_lot3/{img})\n")
        else:
            o.append(f"- **Image** : non rendue automatiquement (page {b.page_pdf}) — à vérifier au PDF {os.path.basename(pdf_for(insee) or '?')}\n")
    open("docs/audit-2026-11/etude-stationnement-fix-1/SONDAGE-10-LOT3.md", "w", encoding="utf-8").write("\n".join(o))
    print("SONDAGE-10-LOT3.md écrit ·", sum(1 for _ in picks), "règles ·",
          len(glob.glob(OUTDIR + "*.png")), "images")


if __name__ == "__main__":
    main()
