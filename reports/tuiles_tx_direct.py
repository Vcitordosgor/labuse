#!/usr/bin/env python3
"""TUILES-TX-1 — preuve DÉTERMINISTE (indépendante de la version du framework) du mécanisme.

Le test serveur (tuiles_tx_proof.py) montre 0 « idle in transaction » après 200 tuiles dont des
annulées ; mais sous un FastAPI/Starlette récent la finalisation de `Depends(get_db)` se fait même
à la déconnexion, donc le chemin AVANT ne fuit pas localement. Ici on prouve le MÉCANISME sans
dépendre de ce comportement : on appelle les handlers de tuile DIRECTEMENT (aucune finalisation de
dépendance FastAPI n'existe alors) et on vérifie que CHAQUE tuile ferme sa transaction elle-même —
sur SUCCÈS comme sur ERREUR en pleine génération (l'analogue du client qui annule).

Étapes :
  (0) RAPPEL de l'état de panne : une session qui exécute un SELECT sans commit/close est « idle in
      transaction » — on le reproduit en process (c'est exactement ce que la prod voyait s'accumuler).
  (1) handler parcelles `mvt_tile(...)` appelé en direct, succès → 0 idle in transaction après retour.
  (2) handler couches `couche_tuile(...)` appelé en direct, succès → 0 idle in transaction.
  (3) ERREUR en pleine génération (ST_AsMVT monkeypatché pour lever = client qui annule) : le handler
      propage l'exception MAIS le `finally` de `with api_session()` a fermé la transaction → 0 idle.
"""
from __future__ import annotations

import os
import sys

import psycopg
from starlette.requests import Request

APP_NAME = "tuiles_tx_direct"
PROBE = os.environ["PROOF_PG_DSN"]


def _req() -> Request:
    return Request({"type": "http", "method": "GET", "http_version": "1.1",
                    "headers": [], "query_string": b"", "path": "/"})


def idle_in_tx() -> int:
    """Connexions « idle in transaction » ouvertes par le moteur de CE process (application_name)."""
    with psycopg.connect(PROBE, autocommit=True) as c, c.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE application_name = %s AND state = 'idle in transaction' "
            "AND pid <> pg_backend_pid()", (APP_NAME,))
        return cur.fetchone()[0]


def main() -> int:
    import labuse.api.couches_tuyau as C
    import labuse.api.tiles as T
    from labuse.db import session_factory

    ok = True

    # (0) RAPPEL — reproduit l'état de panne : SELECT sans commit/close = « idle in transaction ».
    leaky = session_factory()()
    from sqlalchemy import text
    leaky.execute(text("SELECT 1"))                    # autobegin : transaction ouverte, non fermée
    n0 = idle_in_tx()
    print(f"(0) session laissée ouverte après un SELECT  → idle in transaction = {n0}  "
          f"({'état de panne reproduit' if n0 >= 1 else 'inattendu'})")
    ok &= n0 >= 1
    leaky.rollback(); leaky.close()                    # on nettoie le rappel

    # tuiles non chauffées (z13) → génèrent à la volée, exercent la requête ST_TileEnvelope.
    pz, px, py = 13, 5095, 4613
    cz, cx, cy, kind = 12, 2547, 2306, "limites_parcelles"

    # (1) parcelles, succès
    r1 = T.mvt_tile(pz, px, py, _req())
    n1 = idle_in_tx()
    print(f"(1) mvt_tile parcelles succès (status {r1.status_code}) → idle in transaction = {n1}")
    ok &= n1 == 0

    # (2) couches, succès
    r2 = C.couche_tuile(kind, cz, cx, cy, _req())
    n2 = idle_in_tx()
    print(f"(2) couche_tuile « {kind} » succès (status {r2.status_code}) → idle in transaction = {n2}")
    ok &= n2 == 0

    # (3) ERREUR en pleine génération (= client qui annule / requête interrompue). On fait lever la
    #     requête ST_AsMVT elle-même ; le handler doit propager MAIS fermer sa transaction (finally).
    def boom(*_a, **_k):
        raise RuntimeError("interruption simulée en pleine génération de tuile")

    orig_p, orig_c = T._parcel_tile_bytes, C._construire_tuile
    T._parcel_tile_bytes = boom
    C._construire_tuile = boom
    raised_p = raised_c = False
    try:
        try:
            T.mvt_tile(pz, px + 1, py + 1, _req())     # tuile distincte, non cachée → atteint boom
        except RuntimeError:
            raised_p = True
        try:
            C.couche_tuile(kind, cz, cx + 1, cy + 1, _req())
        except RuntimeError:
            raised_c = True
    finally:
        T._parcel_tile_bytes, C._construire_tuile = orig_p, orig_c
    n3 = idle_in_tx()
    print(f"(3) erreur en pleine génération (parcelles levée={raised_p}, couches levée={raised_c}) "
          f"→ idle in transaction = {n3}")
    ok &= raised_p and raised_c and n3 == 0

    print("\nVERDICT :", "OK — chaque tuile ferme sa transaction (succès ET erreur/annulation)"
          if ok else "ÉCHEC")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
