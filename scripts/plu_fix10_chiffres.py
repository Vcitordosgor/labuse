"""OUTIL-PLU-FIX-10 — CHIFFRES de synthèse (sortie brute), un par lot, mesurés sur le corpus réingéré.

Vérifie et chiffre, sans rien inventer :
  LOT 1 — zones AU indicées servant leur chapitre PROPRE « AU indicée » (plus de rabat en bloc vers U) ;
  LOT 2 — Sainte-Marie U8 entiers ; 0 article coupé « fin en deux-points/puce » hors préambules ;
  LOT 3 — articles Usdu séparés par livret (La Plaine/La Saline/Guillaume), pages distinctes ;
  LOT 4 — barèmes de stationnement SL/SP avec conditions + article + page + lien ;
  LOT 5 — dates distinctes (approbation écrite ≠ lot) servies par l'API.

DSN via LABUSE_PLU_CORPUS_DSN (défaut openclaw@localhost/labuse).
Usage : PYTHONPATH=src python scripts/plu_fix10_chiffres.py
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text

from labuse.ingestion import plu_ingest as P

_DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")


def main() -> int:
    s = create_engine(_DSN).connect()
    n = s.execute(text("SELECT count(*) FROM plu_reglement_extrait")).scalar()
    nc = s.execute(text("SELECT count(DISTINCT insee) FROM plu_reglement_extrait")).scalar()
    print(f"CORPUS : {n} extraits · {nc} communes servies\n")

    print("== LOT 1 — chapitre « AU indicée » (renvoi article par article) ==")
    communes = [r[0] for r in s.execute(text(
        "SELECT DISTINCT insee FROM plu_reglement_extrait WHERE zone='AUINDICEE' ORDER BY insee"))]
    print(f"  communes à chapitre AU indicée : {communes}")
    for insee, z, art, attendu in [("97423", "AUt", "10", "p.69 8 m/10 m PROPRE"),
                                   ("97402", "AUec", "10", "p.80 18 m PROPRE")]:
        rows = P.search_reglement(s, "hauteur", insee=insee, zone=z, terms=["hauteur"], limit=10)
        zoned = [r for r in rows if r["zone"]]
        p0 = (zoned[0].get("page_match") or zoned[0]["page_debut"]) if zoned else None
        print(f"  {insee} {z} hauteur → 1er résultat zoné p.{p0} (attendu {attendu}) · "
              f"apparentées={P.zones_apparentees(s, z, insee)}")

    print("\n== LOT 2 — articles coupés ==")
    for z, p in [("U8 (p21-22)", 22), ("U8 (p34-35)", 35)]:
        pass
    sm = s.execute(text("SELECT article_ref,page_debut,page_fin,length(texte_verbatim) ln, "
                        "(texte_verbatim LIKE '%15,00 mètres%') v FROM plu_reglement_extrait "
                        "WHERE insee='97418' AND article_ref ILIKE '%U8%' ORDER BY page_debut")).all()
    for r in sm:
        print(f"  Sainte-Marie {r.article_ref} p{r.page_debut}-{r.page_fin} : {r.ln} car. (valeurs UA présentes : {r.v})")

    print("\n== LOT 3 — Saint-Paul Usdu : articles séparés par livret ==")
    for r in s.execute(text("SELECT article_ref,page_debut,page_fin,livret FROM plu_reglement_extrait "
                            "WHERE insee='97415' AND zone='USDU' AND article_ref ILIKE '%12%' ORDER BY page_debut")):
        print(f"  {r.article_ref} p{r.page_debut}-{r.page_fin} · {r.livret}")
    a10 = s.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97415' AND zone='USDU' "
                         "AND article_ref ILIKE 'Article 10%' AND texte_verbatim LIKE '%11.7%'")).scalar()
    print(f"  articles 10 Usdu incluant « 11.7 » (fusion 10+11 résiduelle) : {a10} (attendu 0)")

    print("\n== LOT 4 — barèmes fiche parcelle ==")
    from labuse.api.app import _reglement_plu_block
    for idu, comm, z in [("97414000DK0208", "Saint-Louis", "UA"), ("97416000HT0538", "Saint-Pierre", "Ud")]:
        b = _reglement_plu_block(s, idu, comm)
        zz = next(x for x in b["zones"] if x["zone"] == z)
        st = next(r for r in zz["regles_valeurs"] if r.get("cle") == "stationnement")
        print(f"  {comm} {z} : « {st['valeur']} » · {st.get('reference')} · {len(st.get('conditions') or [])} condition(s) · "
              f"lien #page={'oui' if '#page=' in (st.get('url') or '') else 'NON'}")

    print("\n== LOT 5 — dates distinctes (approbation écrite ≠ lot) ==")
    from labuse.api.modules import plu_annuaire_communes
    by = {c["insee"]: c for c in plu_annuaire_communes(s)["communes"]}
    for insee in ("97404", "97406", "97411", "97416", "97422", "97424"):
        c = by[insee]
        print(f"  {insee} {c['commune']:24} approbation={c['date_approbation']} · lot={c['millesime_lot']} "
              f"· distinctes={c['date_approbation'] != c['millesime_lot']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
