"""LIENS-1 (lot 0) — le boot ne prend AUCUN verrou quand le schéma est déjà posé.

Reproduit l'incident du 05/10 : un `ALTER TABLE parcel_residuel_runs ADD COLUMN IF NOT EXISTS
assiette_source` *no-op* prenait quand même un ACCESS EXCLUSIVE, attendait derrière une
transaction ouverte, et figeait TOUTES les lectures du résiduel 8 min. Deux transactions tiennent
ici un ACCESS SHARE (lecture) sur `parcel_residuel_runs` ET `parcels` — exactement la situation qui
met un ALTER en FILE. Schéma déjà posé → `ensure_runs_schema` ne doit émettre AUCUN DDL, donc ne
jamais se mettre en file → démarrage immédiat.

Le `lock_timeout` court transforme une régression (un DDL non gardé réintroduit) en ÉCHEC RAPIDE :
l'ALTER buterait sur le verrou tenu et lèverait au lieu de geler le test (et la prod) 8 min.
"""
from __future__ import annotations

import time

from sqlalchemy import text

from labuse.faisabilite import residuel_runs as rr


def test_boot_runs_schema_sans_verrou(engine):
    # Le fixture `engine` a déjà migré le schéma (migrate_to_runs → ensure_runs_schema) : les
    # colonnes et index existent. On ne teste QUE le chemin nominal (schéma posé).
    with engine.connect() as c:
        for col in ("assiette_source", "hauteur_source", "regles_non_modelisees"):
            assert rr._colonne_presente(c, "parcel_residuel_runs", col), (
                f"pré-requis : {col} doit déjà exister (sinon on ne teste pas le chemin nominal)")

    # Deux BLOQUEURS : connexions distinctes, transaction ouverte (autobegin), ACCESS SHARE tenu.
    bloqueur_runs = engine.connect()
    bloqueur_parcels = engine.connect()
    try:
        bloqueur_runs.execute(text("LOCK TABLE parcel_residuel_runs IN ACCESS SHARE MODE"))
        bloqueur_parcels.execute(text("LOCK TABLE parcels IN ACCESS SHARE MODE"))

        with engine.connect() as boot:
            with boot.begin():
                # Filet : un DDL non gardé (ACCESS EXCLUSIVE) butera sur l'ACCESS SHARE tenu et
                # lèvera au bout de 4 s au lieu de geler indéfiniment.
                boot.execute(text("SET LOCAL lock_timeout = '4s'"))
                t0 = time.perf_counter()
                rr.ensure_runs_schema(boot)          # chemin nominal → zéro DDL → zéro attente
                dt = time.perf_counter() - t0
        assert dt < 10, (
            f"ensure_runs_schema a mis {dt:.1f}s avec deux ACCESS SHARE tenus → un DDL non gardé "
            "s'est remis en file (régression du correctif LIENS-1 lot 0).")
    finally:
        bloqueur_runs.rollback()
        bloqueur_runs.close()
        bloqueur_parcels.rollback()
        bloqueur_parcels.close()
