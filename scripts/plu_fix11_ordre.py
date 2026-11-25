"""OUTIL-PLU-FIX-11 (LOT 2) — vérifie, pour TOUTES les zones des 21 communes et les 5 articles-clés
(implantation, emprise, hauteur, stationnement, espaces libres), que QUAND la zone a son article PROPRE,
celui-ci est le PREMIER résultat servi (jamais l'article d'une zone sœur/ancêtre).

Pour chaque (commune, zone, type) : on interroge `search_reglement` ; parmi les résultats ZONÉS, si l'un
au moins est PROPRE à la zone (`_propre_a` : étiqueté zf, ou barème/bannière nommant zf), alors le 1ᵉʳ
résultat zoné DOIT l'être aussi. Sinon on IMPRIME le cas en échec. Sortie brute. DSN LABUSE_PLU_CORPUS_DSN.

Usage : PYTHONPATH=src python scripts/plu_fix11_ordre.py
"""
from __future__ import annotations

import collections
import os
import pathlib

import yaml
from sqlalchemy import create_engine, text

from labuse.ingestion import plu_ingest as P

_DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")
ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTICLES = [("implantation", ["implantation"]), ("emprise", ["emprise", "au", "sol"]),
            ("hauteur", ["hauteur"]), ("stationnement", ["stationnement"]),
            ("espaces libres", ["espaces", "libres"])]


def main() -> int:
    s = create_engine(_DSN).connect()
    mil = yaml.safe_load((ROOT / "config" / "plu_millesimes.yaml").read_text())["communes"]
    servables = {k for k, v in mil.items() if v.get("statut") in ("a_jour", "annule_partiel")}
    rows = s.execute(text("SELECT right(attrs->>'partition',5) insee, attrs->>'libelle' lib "
                          "FROM spatial_layers WHERE kind='plu_gpu_zone' "
                          "AND attrs->>'partition' LIKE 'DU_%' GROUP BY 1,2")).all()
    zbyc = collections.defaultdict(set)
    for r in rows:
        if r.insee in servables and r.lib:
            zbyc[r.insee].add(r.lib)

    n_zones = n_checks = n_fail = 0
    fails = []
    for insee in sorted(zbyc):
        for z in sorted(zbyc[insee]):
            n_zones += 1
            zf = P._norm(z).upper()
            for libelle, terms in ARTICLES:
                res = P.search_reglement(s, " ".join(terms), insee=insee, zone=z, terms=terms, limit=20)
                zoned = [r for r in res if r["zone"]]
                if not zoned:
                    continue
                # « la zone a son article PROPRE » = un extrait ÉTIQUETÉ exactement avec son code (chapitre
                # propre : UE 12 zone « UE »). Une zone servie seulement par sa famille (Ub1 → chapitre « U »)
                # n'a PAS d'article propre pour ce critère : son 1ᵉʳ résultat de famille est légitime.
                own = [r for r in zoned if (r["zone"] or "").upper() == zf
                       and P._art_num(r["article_ref"]) is not None]
                if not own:                            # pas de vrai article propre (préambule « ZONE UE »
                    continue                           # seul, ou zone servie par sa famille) → hors scope
                n_checks += 1
                if not P._propre_a(zoned[0], zf):
                    n_fail += 1
                    fails.append((insee, z, libelle, zoned[0]["zone"], zoned[0]["article_ref"],
                                  zoned[0]["page_debut"]))

    if fails:
        print("ÉCHECS (1ᵉʳ résultat zoné NON propre alors qu'un article propre existe) :")
        for insee, z, lib, z0, art, p in fails:
            print(f"  {insee} {z:8} {lib:16} → 1er = {z0} {art} p{p}")
    else:
        print("AUCUN échec : l'article propre est toujours en tête quand il existe.")
    print(f"\n{n_zones} zones · {n_checks} couples (zone,article) avec article propre vérifiés · {n_fail} échec(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
