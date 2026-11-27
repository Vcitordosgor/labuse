"""OUTIL-PERMIS-FIX-12 (LOT 3) — reconstruction de `pc_caducs` sur `labuse`.

POURQUOI la table était vide : elle est RECALCULÉE hors-run par la chaîne des dérivés légers
(`labuse.ingestion.fraicheur.run_derives` → `build_pc_caducs`). En PRODUCTION cette chaîne est jouée
CHAQUE NUIT par le job `ingest-bodacc` (quotidien 06:40) qui enchaîne `fraicheur-derives` (cf.
jobs_impl.ingest_bodacc). Sur la base de DEV `labuse`, cette chaîne n'a jamais tourné : `fraicheur_etat`
ne portait AUCUNE entrée `pc_caducs` (jamais `marquer_regle_derivee`), la table était à 0. Le calcul,
lui, est juste : 4 836 parcelles depuis les sources.

Reconstruction AUTORISÉE par Vic — cette table SEULE. Lecture seule des sources (p_model_permits +
sitadel_permits + parcels), swap ~ms. Puis preuve PAR LES ROUTES RÉELLES.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.ingestion.pc_caducs import build_pc_caducs  # noqa: E402

PARC = "97401000AD0106"


def main() -> int:
    with session_scope() as s:
        base = s.execute(text("SELECT current_database()")).scalar()
        if base != "labuse":
            raise SystemExit(f"REFUS — base {base!r} ≠ 'labuse' (reconstruction autorisée sur labuse seule)")
        avant = s.execute(text("SELECT count(*) FROM pc_caducs")).scalar()
        regle_avant = s.execute(text("SELECT valeur FROM fraicheur_etat WHERE cle='derive:pc_caducs:rule_version'")).scalar()
        print(f"AVANT : pc_caducs = {avant} · fraicheur_etat['derive:pc_caducs:rule_version'] = {regle_avant}")
        out = build_pc_caducs(s, ref_year=2026, commit=True)
        print(f"build : {out}")
    # preuve PAR LES ROUTES, dans une nouvelle session (après commit)
    from fastapi.testclient import TestClient
    from labuse.api import accueil as acc
    from labuse.api.app import app
    acc._cache["data"] = None
    with TestClient(app) as cli:
        pc = cli.get("/accueil/chiffres").json().get("permis_caducs")
    with session_scope() as s:
        apres = s.execute(text("SELECT count(*) FROM pc_caducs")).scalar()
        regle_apres = s.execute(text("SELECT valeur FROM fraicheur_etat WHERE cle='derive:pc_caducs:rule_version'")).scalar()
        trouve = s.execute(text("SELECT EXISTS (SELECT 1 FROM pc_caducs WHERE idu = :i)"), {"i": PARC}).scalar()
    print(f"APRÈS : pc_caducs = {apres} · fraicheur_etat['derive:pc_caducs:rule_version'] = {regle_apres}")
    print(f"ROUTE GET /accueil/chiffres → permis_caducs = {pc}")
    print(f"FILTRE parcellaire permis_caduc trouve {PARC} : {trouve}")
    ok = (apres == 4836 and pc == 4836 and trouve is True)
    print("\n" + ("TOUT VERT" if ok else "ÉCART — vérifier"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
