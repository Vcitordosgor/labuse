"""OUTIL-PLU-FIX-10 (LOT 2) — scan des ARTICLES COUPÉS dans les 21 communes servies.

Cherche tout extrait dont le texte VERBATIM se termine par un signe de troncature :
  · deux-points « : » (une énumération annoncée mais vide → la suite a été détachée) ;
  · une puce nue (•, ▪, ◦, ·, ‣, tiret) — un item de liste commencé sans contenu ;
  · un mot TRONQUÉ (dernier « mot » collé à une césure, ou ligne finissant par une préposition/
    article : « à », « de », « du », « en », « le »… — la phrase continue hors de l'extrait).

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
