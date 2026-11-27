#!/usr/bin/env python
"""OUTIL-PERMIS-FIX-10 (LOT 3) — DÉSACTIVE + SUPPRIME le déclencheur `trg_m10_permit_delais_sync` dans
la base `labuse` (AUTORISÉ par Vic, CE déclencheur et lui seul ; la table n'est PAS supprimée), puis
PROUVE qu'un UPDATE d'une ligne Sitadel, annulé ensuite, n'écrit plus dans `m10_permit_delais`.

Le déclencheur frère `trg_via_permits_geo_sync` (couche de voisinage servie) n'est PAS touché.

Usage : LABUSE_DATABASE_URL=… PYTHONPATH=src python scripts/outil_permis_fix8/fix10_drop_trigger_labuse.py
"""
from __future__ import annotations

import os

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

from sqlalchemy import text  # noqa: E402

from labuse.db import engine as _engine  # noqa: E402


def _triggers(conn):
    return [r[0] for r in conn.execute(text(
        "SELECT tgname FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
        "WHERE c.relname='sitadel_permits' AND NOT t.tgisinternal ORDER BY tgname"))]


eng = _engine()

print("=== AVANT ===")
with eng.connect() as c:
    trs0 = _triggers(c)
    print("  déclencheurs sitadel_permits :", trs0)

# ── DÉSACTIVE + SUPPRIME (une transaction committée) — ce déclencheur et lui seul ──
if "trg_m10_permit_delais_sync" in trs0:
    with eng.begin() as c:
        c.execute(text("ALTER TABLE sitadel_permits DISABLE TRIGGER trg_m10_permit_delais_sync"))
        c.execute(text("DROP TRIGGER trg_m10_permit_delais_sync ON sitadel_permits"))
    print("  → déclencheur DÉSACTIVÉ puis SUPPRIMÉ (committé).")
else:
    print("  → déclencheur déjà absent (idempotent).")

print("=== APRÈS ===")
with eng.connect() as c:
    trs = _triggers(c)
    print("  déclencheurs sitadel_permits :", trs)
    assert "trg_m10_permit_delais_sync" not in trs, "le déclencheur m10 est encore là"
    assert "trg_via_permits_geo_sync" in trs, "le déclencheur frère voisinage a été touché — INTERDIT"

# ── PREUVE : un UPDATE Sitadel annulé n'écrit plus dans m10 ──
print("=== PREUVE : UPDATE d'une ligne Sitadel + ROLLBACK, m10 inchangée ===")
_SEL = ("SELECT date_depot::text, valide, computed_at::text "
        "FROM m10_permit_delais WHERE permit_id=:p")
with eng.connect() as c:
    pid = c.execute(text(
        "SELECT permit_id FROM m10_permit_delais WHERE valide ORDER BY permit_id LIMIT 1")).scalar()
    avant = dict(c.execute(text(_SEL), {"p": pid}).mappings().first())
    print(f"  témoin permis {pid} — m10 AVANT : {avant}")
    # un an_depot qui, AVEC le trigger, aurait réécrit date_depot (→ 1999-01-01) et `valide`.
    c.execute(text("UPDATE sitadel_permits SET raw = jsonb_set(raw, '{an_depot}', '\"1999\"') "
                   "WHERE permit_id=:p"), {"p": pid})
    apres = dict(c.execute(text(_SEL), {"p": pid}).mappings().first())
    print(f"  après UPDATE (dans la transaction) — m10 : {apres}")
    c.rollback()   # annule l'UPDATE (la transaction auto-ouverte)
    print("  (transaction ANNULÉE)")
    final = dict(c.execute(text(_SEL), {"p": pid}).mappings().first())
    print(f"  m10 APRÈS rollback : {final}")
    c.rollback()
    ok = avant == apres == final
    print(f"\n→ m10 n'a PAS bougé pendant l'UPDATE (déclencheur retiré) : {ok} (attendu True)")
    assert ok, "m10 a changé — le déclencheur alimente encore la table"
print("✓ LOT 3 : déclencheur retiré de labuse, m10 n'est plus alimentée, table conservée.")
