#!/usr/bin/env python
"""OUTIL-PERMIS-FIX-11 — nettoyage du BACKLOG de pollution de `labuse_test` (base de TEST uniquement).

AUTORISÉ par Vic dans labuse_test SEULEMENT. GARDE-FOU DUR : refuse de tourner si la base courante n'est
PAS `labuse_test` (jamais `labuse`). Supprime les lignes accumulées (comptes et leurs filles ON DELETE
CASCADE ; event_log à compte NULL = `systeme`/zone ; ops_incidents), table par table, avec un décompte
avant/après. La conftest (fixture de session `_nettoyer_accumulateurs_fix11`) empêche ensuite toute
ré-accumulation.

Usage : LABUSE_DATABASE_URL=postgresql+psycopg://…/labuse_test \
        PYTHONPATH=src python scripts/outil_permis_fix8/fix11_nettoyer_labuse_test.py
"""
from __future__ import annotations

import os
import sys

URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse_test")
os.environ["LABUSE_DATABASE_URL"] = URL

from sqlalchemy import create_engine, text  # noqa: E402

eng = create_engine(URL, future=True)

with eng.connect() as c:
    dbname = c.execute(text("SELECT current_database()")).scalar()
    if dbname != "labuse_test":
        sys.exit(f"REFUS — base courante = {dbname!r}, attendu 'labuse_test'. Rien supprimé "
                 "(jamais la base applicative 'labuse').")

ACC = ["comptes", "event_log", "ops_incidents", "watch_zones", "watched_parcels",
       "veilles", "saved_searches", "notif_prefs"]


def _counts(c):
    out = {}
    for t in ACC:
        try:
            out[t] = c.execute(text(f"SELECT count(*) FROM {t}")).scalar()  # noqa: S608
        except Exception:
            c.rollback()
            out[t] = None
    return out


with eng.connect() as c:
    avant = _counts(c)
    sys_null = c.execute(text("SELECT count(*) FROM event_log WHERE compte_id IS NULL")).scalar()

print(f"base = labuse_test (contrôlée) · event_log à compte NULL = {sys_null}")
print("\n=== AVANT ===")
for t in ACC:
    print(f"  {t:18s} {avant[t]}")

# Suppression : comptes (CASCADE emporte ses filles) ; puis les lignes à compte NULL ; puis ops_incidents.
with eng.begin() as c:
    n_comptes = c.execute(text("DELETE FROM comptes")).rowcount
    n_evlog_null = c.execute(text("DELETE FROM event_log WHERE compte_id IS NULL")).rowcount
    n_ops = c.execute(text("DELETE FROM ops_incidents")).rowcount
    # filet : toute ligne d'accumulation à compte NULL encore présente (watch_zones/… 0 attendu)
    for t in ("watch_zones", "watched_parcels", "veilles", "saved_searches"):
        try:
            c.execute(text(f"DELETE FROM {t}"))  # noqa: S608 — table de TEST, base contrôlée
        except Exception:
            pass

print("\n=== SUPPRIMÉ ===")
print(f"  comptes (+ filles CASCADE : event_log/watch_zones/watched_parcels/veilles/saved_searches/"
      f"notif_prefs à compte non nul) : {n_comptes} comptes")
print(f"  event_log (compte NULL — `systeme`/zone)                                : {n_evlog_null}")
print(f"  ops_incidents                                                           : {n_ops}")

with eng.connect() as c:
    apres = _counts(c)
print("\n=== APRÈS ===")
for t in ACC:
    print(f"  {t:18s} {apres[t]}")
print("\n✓ backlog labuse_test purgé (base de test uniquement). La conftest empêche la ré-accumulation.")
