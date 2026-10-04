"""SCORING-8 lot A bis (1) — le DDL de démarrage ne prend AUCUN verrou quand le schéma est déjà
posé : démarrer l'app pendant une transaction ouverte sur `parcels` ne doit pas attendre.

Une transaction tient `parcels` en ACCESS SHARE (un simple SELECT non commité) ; ce verrou entre
en conflit avec l'ACCESS EXCLUSIVE d'un ALTER et avec le SHARE d'un CREATE INDEX. Les `ensure_*`
du boot, désormais gardés (information_schema / pg_class testés AVANT le DDL), doivent terminer
immédiatement. Si un garde saute, l'`ensure_*` tenterait le DDL, bloquerait derrière la
transaction, et ce test échouerait par timeout.
"""
import threading

import pytest
from sqlalchemy import text

from labuse import models


def test_boot_ne_bloque_pas_derriere_une_transaction_sur_parcels(engine):
    holder = engine.connect()
    trans = holder.begin()
    try:
        holder.execute(text("SELECT 1 FROM parcels LIMIT 1"))   # ACCESS SHARE tenu jusqu'au rollback

        done = threading.Event()
        err: dict = {}

        def run():
            try:
                # Toutes les fonctions de boot qui portaient un DDL verrouillant « à vide ».
                models.ensure_parcel_origine(engine)
                models.ensure_icd_columns(engine)
                models.ensure_sitadel_depot(engine)
                models.ensure_parcel_eval_status_dropped(engine)
                models.ensure_constructibilite_cache(engine)
            except Exception as exc:        # noqa: BLE001
                err["exc"] = exc
            finally:
                done.set()

        th = threading.Thread(target=run, daemon=True)
        th.start()
        fini = done.wait(timeout=10)
        assert fini, ("le boot a BLOQUÉ derrière la transaction ouverte sur parcels — "
                      "un DDL de démarrage n'est plus gardé par un test d'existence préalable")
        assert "exc" not in err, f"un ensure_* a levé : {err.get('exc')}"
    finally:
        trans.rollback()
        holder.close()


def test_origine_presente_apres_boot(engine):
    # La colonne est bien là (le chemin de pose a tourné une fois) : le garde est donc un no-op
    # SANS verrou, pas une suppression de fonctionnalité.
    with engine.connect() as c:
        assert models._col_presente(c, "parcels", "origine")
