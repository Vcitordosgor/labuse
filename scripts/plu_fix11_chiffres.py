"""OUTIL-PLU-FIX-11 — CHIFFRES de synthèse (sortie brute), un par point de relecture-plu-8, mesurés sur le
corpus réingéré. DSN via LABUSE_PLU_CORPUS_DSN (défaut openclaw@localhost/labuse).

Usage : PYTHONPATH=src python scripts/plu_fix11_chiffres.py
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text

from labuse.ingestion import plu_ingest as P

_DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")


def main() -> int:
    s = create_engine(_DSN).connect()
    print(f"CORPUS : {s.execute(text('SELECT count(*) FROM plu_reglement_extrait')).scalar()} extraits · "
          f"{s.execute(text('SELECT count(DISTINCT insee) FROM plu_reglement_extrait')).scalar()} communes\n")

    print("== POINT 1 — Saint-Denis Up.10 (Hauteur) : valeurs rattachées au bon article ==")
    for ref in ("Article Up.10", "Article Up.11"):
        r = s.execute(text("SELECT page_debut,page_fin,length(texte_verbatim) ln,"
                           "(texte_verbatim LIKE '%16 m%') v16,(texte_verbatim LIKE '%11 m%') v11 "
                           "FROM plu_reglement_extrait WHERE insee='97411' AND article_ref ILIKE :r LIMIT 1"),
                      {"r": ref + "%"}).first()
        print(f"  {ref}: p{r.page_debut}-{r.page_fin} len={r.ln} · 16 m={r.v16} · 11 m={r.v11}")
    print("  (attendu : Up.10 porte 16 m ET 11 m ; Up.11 ne les porte PAS)")

    print("\n== POINT 2 — article propre AVANT article de zone sœur (3 témoins) ==")
    for insee, z, q in (("97401", "UE", "stationnement"), ("97421", "UT", "stationnement"),
                        ("97405", "UEa", "hauteur")):
        rows = P.search_reglement(s, q, insee=insee, zone=z, terms=[q], limit=10)
        zoned = [r for r in rows if r["zone"]]
        r0 = zoned[0] if zoned else None
        print(f"  {insee} {z} {q} → 1er zoné = {r0 and (r0['zone'], r0['article_ref'], 'p%d' % r0['page_debut'])}")

    print("\n== POINT 3 — ligne logement (locatif) social sur la fiche (2 témoins) ==")
    from labuse.api.app import _reglement_plu_block
    for idu, comm, z in (("97414000DK0208", "Saint-Louis", "UA"), ("97416000HT0538", "Saint-Pierre", "Ud")):
        b = _reglement_plu_block(s, idu, comm)
        zz = next(x for x in b["zones"] if x["zone"] == z)
        st = next(r for r in zz["regles_valeurs"] if r.get("cle") == "stationnement")
        soc = [c["texte"] for c in (st.get("conditions") or [])
               if "social" in c["texte"].lower()]
        print(f"  {comm} {z} ({st.get('reference')}) → {soc}")
    print("\n  (balayage complet des 21 communes : scripts/plu_fix11_ordre.py — 0 échec attendu)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
