"""ETUDE-STATIONNEMENT-FIX-1 (LOT 3) — tirage à GRAINE FIXE de N règles de stationnement, sur l'ensemble
des zones constructibles SERVIES des communes à texte en base (pas choisies à la main).

Commande du tirage (déterministe) :
    PYTHONPATH=src python scripts/sondage_tirage.py --seed 20260115 --n 10

Pour chaque règle tirée : commune, zone, article, page, valeur appliquée. Un second passage
(scripts/sondage_images.py) rend l'image de la ligne entière depuis le PDF officiel.
"""
import argparse
import glob
import json
import os
import random
import re

from labuse.implantation import regles as R
from labuse.plu import destinations as D

# Communes à texte en base (hors textes manquants : Étang-Salé 97404, Saint-André 97409, Saint-Leu 97413,
# Plaine 97406 [annexe], Saint-Denis 97411 [dispositions générales]) et hors RNU. Saint-Paul 97415 differé.
COMMUNES_TEXTE = ["97401", "97402", "97403", "97405", "97407", "97408", "97410", "97412",
                  "97414", "97416", "97418", "97419", "97420", "97421", "97422", "97423", "97424"]


def pool():
    """Toutes les (insee, zone) U/AU dont le barème est VALIDÉ, triées de façon stable."""
    out = []
    for insee in COMMUNES_TEXTE:
        for r in D.regles_commune(insee):
            z = r["zone"]
            if not re.match(r'^\d*(U|AU)', z, re.I):
                continue
            b = R.charger(insee, z).stationnement
            if b.validee:
                out.append((insee, z))
    return sorted(set(out))


def synth(b):
    if b.mode == "par_logement":
        s = f"{b.flat_places:g} place/logt (arr. {b.arrondi})"
    elif b.mode == "par_m2_sdp":
        s = f"1 place / {b.m2_par_place:g} m² (arr. {b.arrondi})"
    else:
        s = "typologie : " + " ; ".join(
            f"{l.destination} " + (f"{l.places:g}/logt" if l.places is not None else f"1/{l.par_m2:g} m²")
            + (f" [{l.role}]" if l.role != "base" else "") for l in b.lignes)
    if b.visiteurs:
        base = f"{b.visiteurs.par_logements} logts" if b.visiteurs.par_logements else f"{b.visiteurs.par_m2_sdp:g} m²"
        s += f" · visiteur {b.visiteurs.places:g}/{base}"
    if b.integ_pct:
        s += f" · intégrées {b.integ_pct:g}%>{b.integ_seuil_m2:g}m²"
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    p = pool()
    rng = random.Random(a.seed)
    picks = rng.sample(p, a.n)
    rows = []
    for insee, z in picks:
        b = R.charger(insee, z).stationnement
        rows.append({"insee": insee, "zone": z, "article": b.article, "page": b.page_pdf,
                     "valeur": synth(b), "citation": b.citation,
                     "conditions": list(b.conditions)})
    if a.json:
        print(json.dumps(rows, ensure_ascii=False))
    else:
        print(f"# Tirage graine={a.seed}, n={a.n}, pool={len(p)} zones servies ({len(COMMUNES_TEXTE)} communes)")
        for i, r in enumerate(rows, 1):
            print(f"{i:2d}. {r['insee']} {r['zone']:8s} art {r['article']} p.{r['page']} — {r['valeur']}")


if __name__ == "__main__":
    main()
