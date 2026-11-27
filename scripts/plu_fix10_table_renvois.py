"""OUTIL-PLU-FIX-10 (LOT 1) — table des RENVOIS article par article.

Pour CHAQUE zone servie par renvoi (zone sans chapitre propre à son code exact), on dresse, article par
article (implantation, emprise, hauteur, stationnement, espaces libres…) :
  · la zone a-t-elle son PROPRE article dans le PDF (chapitre « AU indicée » pour les zones AU indicées) ?
    → page de l'article propre ;
  · le texte de CET article renvoie-t-il EXPRESSÉMENT à une autre zone (« se reporter au règlement de la
    zone X ») ? → zone cible citée.

Le nouveau critère : on sert l'article PROPRE s'il existe ; on ne sert une autre zone que sur renvoi
exprès, et on le dit. Ce tableau PROUVE que l'article propre existe et est servi.

Sortie BRUTE (stdout) + Markdown (--md). DSN via LABUSE_PLU_CORPUS_DSN (défaut openclaw@localhost/labuse).

Usage : PYTHONPATH=src python scripts/plu_fix10_table_renvois.py [--md]
"""
from __future__ import annotations

import argparse
import os
import re

from sqlalchemy import create_engine, text

from labuse.ingestion import plu_ingest as P

_DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")

# les 5 articles-clés imposés par le cahier des charges, par numéro d'article réunionnais standard.
ARTICLES = {6: "implantation/voies", 7: "implantation/limites", 9: "emprise", 10: "hauteur",
            12: "stationnement", 13: "espaces libres"}
_RENVOI_SRC = (r"se\s+reporter\s+au\s+r[èe]glement\s+de\s+la\s+zone\s+"
               r"([0-9]{0,2}(?:AU|U|A|N)[0-9A-Za-z]{0,6}|U\s+indiqu[ée]e\s+en\s+indice)")
_RENVOI = re.compile(_RENVOI_SRC, re.I)


def _art_num(ref: str) -> int | None:
    m = re.search(r"(?:AUINDICEE|AU\s*indic\w*|[A-Za-z]{1,4})\s*(\d{1,2})\b", ref or "", re.I)
    return int(m.group(1)) if m else None


def _renvoi_dans(texte: str, zone: str) -> str | None:
    """Renvoi EXPRÈS cité dans l'article pour cette zone (ou générique « zone U indiquée en indice »)."""
    # clause spécifique « Pour la/les zone(s) <zone>, … se reporter … zone X »
    strip = re.sub(r"^\d+", "", zone)
    m = re.search(r"(?i)zones?\s+[^.]*?\b" + re.escape(strip) + r"\b[^.]{0,120}?" + _RENVOI_SRC, texte or "")
    if m:
        return m.group(1).strip()
    m = _RENVOI.search(texte or "")
    return m.group(1).strip() if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="sortie Markdown")
    args = ap.parse_args()
    s = create_engine(_DSN).connect()

    # zones AU indicées sectorielles servies par le chapitre générique « AU indicée ».
    communes = [r[0] for r in s.execute(text(
        "SELECT DISTINCT insee FROM plu_reglement_extrait WHERE zone='AUINDICEE' ORDER BY insee")).all()]
    rows_out: list[tuple] = []
    for insee in communes:
        commune = s.execute(text("SELECT commune FROM plu_reglement_extrait WHERE insee=:i LIMIT 1"),
                            {"i": insee}).scalar()
        # articles du chapitre AU indicée, par numéro
        ch = {}
        for r in s.execute(text("SELECT article_ref,page_debut,page_fin,texte_verbatim "
                                "FROM plu_reglement_extrait WHERE insee=:i AND zone='AUINDICEE'"), {"i": insee}):
            n = _art_num(r.article_ref)
            if n is not None:
                ch[n] = r
        # zones AU indicées sectorielles du plan (depuis le texte : zones nommées dans le chapitre)
        corpus = " ".join(r[0] or "" for r in s.execute(text(
            "SELECT texte_verbatim FROM plu_reglement_extrait WHERE insee=:i AND zone='AUINDICEE'"), {"i": insee}))
        zones = sorted({_z.upper() for _z in re.findall(r"(?i)\bzones?\s+([0-9]{0,2}AU[0-9a-z]{1,5})\b", corpus)
                        if P.zones_apparentees(s, _z, insee) == ["AUINDICEE"]})
        for z in zones:
            app = P.zones_apparentees(s, z, insee)
            for n, lib in ARTICLES.items():
                r = ch.get(n)
                if not r:
                    rows_out.append((insee, commune, z, n, lib, "—", "aucun", app))
                    continue
                renvoi = _renvoi_dans(r.texte_verbatim, z)
                # « propre » = l'article porte une règle chiffrée pour la zone (mètre, %, place) et pas
                # seulement un renvoi ; sinon c'est un renvoi exprès.
                clause = re.search(r"(?i)zones?\s+[^.]*?\b" + re.escape(re.sub(r"^\d+", "", z))
                                   + r"\b[^.]{0,160}", r.texte_verbatim or "")
                propre = bool(clause and re.search(r"\d+\s*(?:m[èe]tres?|%|place)", clause.group(0))
                              and "reporter" not in clause.group(0).lower())
                page = f"p.{r.page_debut}" + (f"-{r.page_fin}" if r.page_fin != r.page_debut else "")
                rows_out.append((insee, commune, z, n, lib, page,
                                 ("PROPRE" if propre else (f"renvoi→{renvoi}" if renvoi else "générique")), app))

    if args.md:
        print("| INSEE | Commune | Zone | Art. | Objet | Page (chapitre AU indicée) | Règle propre / renvoi | Servi |")
        print("|---|---|---|---|---|---|---|---|")
        for insee, commune, z, n, lib, page, kind, app in rows_out:
            print(f"| {insee} | {commune} | {z} | {n} | {lib} | {page} | {kind} | {','.join(app)} |")
    else:
        print(f"{'INSEE':6} {'ZONE':8} {'ART':4} {'OBJET':20} {'PAGE':10} {'PROPRE/RENVOI':22} SERVI")
        for insee, commune, z, n, lib, page, kind, app in rows_out:
            print(f"{insee:6} {z:8} {n:<4} {lib:20} {page:10} {kind:22} {','.join(app)}")
    print(f"\n{len(rows_out)} lignes · {len(communes)} communes à chapitre « AU indicée » · "
          f"{len({(r[0], r[2]) for r in rows_out})} zones sectorielles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
