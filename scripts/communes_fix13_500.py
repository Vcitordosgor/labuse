#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-13 LOT 4 — MESURE des 500 du contexte commune (app.py:2957).

LECTURE SEULE : on appelle la FONCTION `_compute_commune_contexte(db, commune)` (le producteur coûteux
cité par l'audit, ligne 2957), PAS l'endpoint — donc AUCUNE écriture dans labuse (le cache
`commune_contexte_cache` n'est jamais touché). On REPRODUIT la condition « à froid + contention » de
l'audit de façon déterministe : un `statement_timeout` court fait expirer la requête du TABLEAU des
communes (`_communes_data`, ST_Extent sur tout le parc), pendant qu'une charge de lecture tourne en fond.

On compte, sur 50 appels répartis sur les 24 communes :
  · « 500 » = l'appel LÈVE (la requête qui expire fait tomber les blocs suivants → l'endpoint 500) ;
  · « servi » = l'appel RETOURNE un payload (dégradé si besoin : classement indisponible, jamais un 500).

AVANT le correctif : la requête classement (ligne 2957) n'est PAS isolée → son expiration avorte la
transaction → cascade → l'appel lève. APRÈS : elle est isolée (rollback propre) → classement=None
(indisponible, honnête) → l'appel est servi.

Usage : LABUSE_DATABASE_URL=... python scripts/communes_fix13_500.py [timeout_ms] [n_appels]
"""
from __future__ import annotations

import os
import sys
import threading
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
TIMEOUT_MS = int(sys.argv[1]) if len(sys.argv) > 1 else 300
N_APPELS = int(sys.argv[2]) if len(sys.argv) > 2 else 50

eng = create_engine(DB, pool_size=8, max_overflow=16)


def _communes_24() -> list[str]:
    with eng.connect() as c:
        return [r[0] for r in c.execute(text(
            "SELECT DISTINCT commune FROM parcels ORDER BY commune")).all()]


_STOP = threading.Event()


def _charge_lecture():
    """Charge de LECTURE en fond (contention), GENTILLE : une requête bornée puis une pause — on crée
    de la concurrence sans saturer tous les cœurs (le `statement_timeout` court suffit, lui, à faire
    expirer les requêtes lourdes du contexte de façon déterministe). Lecture seule."""
    while not _STOP.is_set():
        try:
            with eng.connect() as c:
                c.exec_driver_sql("SET statement_timeout = '5s'")
                c.execute(text(
                    "SELECT count(*) FROM parcels WHERE commune = 'Saint-Denis'")).first()
        except Exception:
            pass
        _STOP.wait(0.25)


def _mesure(label: str) -> dict:
    from labuse.api.app import _compute_commune_contexte
    communes = _communes_24()
    cibles = [communes[i % len(communes)] for i in range(N_APPELS)]
    n_500, n_servi, n_classement_none = 0, 0, 0
    t0 = time.monotonic()
    for i, commune in enumerate(cibles):
        with Session(eng) as db:
            # reproduit le plafond de l'API, posé bas pour faire expirer le TABLEAU (ST_Extent parc)
            db.execute(text(f"SET statement_timeout = {TIMEOUT_MS}"))
            try:
                payload = _compute_commune_contexte(db, commune)
                n_servi += 1
                if (payload.get("classement") is None):
                    n_classement_none += 1
            except Exception as exc:  # noqa: BLE001 — c'est précisément le « 500 » qu'on compte
                n_500 += 1
                if i < 3:
                    print(f"    [500] {commune}: {type(exc).__name__}: {str(exc)[:90]}")
    dt = time.monotonic() - t0
    return {"label": label, "n_appels": N_APPELS, "n_500": n_500, "n_servi": n_servi,
            "n_classement_indispo": n_classement_none, "duree_s": round(dt, 1)}


if __name__ == "__main__":
    os.environ.setdefault("LABUSE_DATABASE_URL", DB)
    t = threading.Thread(target=_charge_lecture, daemon=True)
    t.start()
    time.sleep(1.0)  # laisse la charge s'installer
    res = _mesure(f"timeout={TIMEOUT_MS}ms")
    _STOP.set()
    print(f"\n=== {res['label']} · {res['n_appels']} appels /communes/<nom>/contexte (fonction 2957) ===")
    print(f"    500 (appel qui lève)        : {res['n_500']}")
    print(f"    servi (payload retourné)    : {res['n_servi']}")
    print(f"    dont classement indisponible: {res['n_classement_indispo']}")
    print(f"    durée                       : {res['duree_s']} s")
