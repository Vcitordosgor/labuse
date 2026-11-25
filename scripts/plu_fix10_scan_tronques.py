"""OUTIL-PLU-FIX-10/11 (LOT 2 / LOT 1) — scan des ARTICLES COUPÉS dans les 21 communes servies.

Cherche tout extrait dont le texte VERBATIM se termine par un signe de troncature :
  · deux-points « : » (une énumération annoncée mais vide → la suite a été détachée) ;
  · une puce nue (•, ▪, ◦, ·, ‣, tiret) — un item de liste commencé sans contenu ;
  · un mot TRONQUÉ (dernier « mot » collé à une césure, ou ligne finissant par une préposition/
    article : « à », « de », « du », « en », « le »… — la phrase continue hors de l'extrait).

OUTIL-PLU-FIX-11 (LOT 1) — ajoute le cas « VALEURS FUITÉES » : un article dont le TITRE annonce une règle
chiffrée (hauteur, emprise, gabarit, stationnement, espaces libres) mais dont le corps ne contient AUCUN
chiffre (mètre, %, place), ALORS QUE l'article SUIVANT de la même commune en contient (les valeurs ont
migré vers l'article d'après — défaut Saint-Denis Up.10). C'est le motif « valeurs-fuitees ».

Chaque cas est une coupure potentielle d'article. Sortie BRUTE triée par commune. `--strict` ne garde
que les deux-points / puce (les plus sûrs). DSN via LABUSE_PLU_CORPUS_DSN.

Usage : PYTHONPATH=src python scripts/plu_fix10_scan_tronques.py [--strict]
"""
from __future__ import annotations

import argparse
import os
import re

from sqlalchemy import create_engine, text

_DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")

_BULLET = "•▪◦·‣∙"
_MOTS_SUSPENDUS = {"à", "a", "de", "du", "des", "en", "et", "le", "la", "les", "un", "une", "au",
                   "aux", "pour", "par", "sur", "dans", "ou", "soit", "que", "qui", "selon"}


def _fin_tronquee(texte: str, strict: bool) -> str | None:
    t = (texte or "").rstrip()
    if not t:
        return None
    last = t[-1]
    if last == ":":
        return "deux-points"
    if last in _BULLET or (last == "-" and not re.search(r"\w-$", t)):
        return "puce"
    if strict:
        return None
    # dernier mot = préposition/article en suspens (la phrase continue hors extrait)
    m = re.search(r"([0-9A-Za-zÀ-ÿ'’]+)\s*$", t)
    if m and m.group(1).lower() in _MOTS_SUSPENDUS:
        return f"mot suspendu « {m.group(1)} »"
    # césure de fin : « …station- » / soft-hyphen collé
    if re.search(r"[A-Za-zÀ-ÿ][­-]$", t):
        return "césure"
    return None


# OUTIL-PLU-FIX-11 (LOT 1) — article dont le titre annonce une règle CHIFFRÉE.
_TITRE_CHIFFRE = re.compile(r"(?i)hauteur|emprise|gabarit|stationnement|espaces? libres?|implantation|"
                            r"coefficient|pleine terre|aires? de")
_NOMBRE_UNITE = re.compile(r"(?i)\d[\d ,\.]*\s*(?:m\b|mètre|m²|%|place|niveau|étage|logement)")


def _valeurs_fuitees(rows: list) -> list:
    """Article dont le TITRE annonce une règle chiffrée mais dont le corps n'a AUCUN chiffre, alors que
    l'article SUIVANT de la même commune en contient (valeurs migrées — Saint-Denis Up.10)."""
    out = []
    for i, r in enumerate(rows):
        ref = r["article_ref"] or ""
        if not _TITRE_CHIFFRE.search(ref):
            continue
        if _NOMBRE_UNITE.search(r["texte_verbatim"] or ""):
            continue                                   # l'article porte ses chiffres → OK
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        if nxt and nxt["insee"] == r["insee"] and _NOMBRE_UNITE.search(nxt["texte_verbatim"] or ""):
            out.append((r["insee"], r["commune"], r["zone"], ref, r["page_debut"], r["page_fin"],
                        "valeurs-fuitees", f"→ chiffres dans {nxt['article_ref']}"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    s = create_engine(_DSN).connect()
    rows = s.execute(text(
        "SELECT insee, commune, zone, article_ref, page_debut, page_fin, texte_verbatim "
        "FROM plu_reglement_extrait ORDER BY insee, page_debut")).mappings().all()
    hits = []
    for r in rows:
        motif = _fin_tronquee(r["texte_verbatim"], args.strict)
        if motif:
            hits.append((r["insee"], r["commune"], r["zone"], r["article_ref"],
                         r["page_debut"], r["page_fin"], motif, (r["texte_verbatim"] or "")[-60:]))
    hits += _valeurs_fuitees(list(rows))
    by_comm: dict[str, int] = {}
    for h in hits:
        by_comm[h[0]] = by_comm.get(h[0], 0) + 1
    print(f"{'INSEE':6} {'ZONE':8} {'ARTICLE':22} {'PAGE':9} {'MOTIF':16} FIN")
    for insee, commune, zone, art, p0, p1, motif, tail in hits:
        tail = re.sub(r"\s+", " ", tail).strip()
        print(f"{insee:6} {str(zone):8} {str(art)[:22]:22} p{p0}-{p1:<5} {motif:16} …{tail!r}")
    print(f"\n{len(hits)} extrait(s) à fin tronquée · {len(rows)} extraits · "
          f"{len(by_comm)} commune(s) concernée(s) : "
          + ", ".join(f"{k}×{v}" for k, v in sorted(by_comm.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
