"""RETRAIT des 14 brûlantes bâties (verdict Vic 04/08, revue PDF dette #4) — type CH1893.

Les 14 suspectes brûlantes revues sur ortho portent TOUTES un bâti visible non capté par la
couche batiment → `declasse_non_constructible`, exception JOURNALISÉE par parcelle (motif Vic).
Idempotent : une parcelle déjà journalisée pour ce motif est sautée. Le geste complet inclut
ensuite build-mvt (tuiles) + régénération golden (garde #6) — voir qa/golden_regen.py.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine

LABEL = "q_v8_calibre"
MOTIF = "bâti visible non capté par la couche batiment — vérifié ortho 04/08"
LES_14 = [  # revue Vic sur qa/dette4/revue_suspectes.pdf (ordre = rang servi)
    "97416000EY1406", "97412000BX1903", "97415000DK1032", "97413000CT0129",
    "97407000AH0233", "97422000DM0647", "97409000AV1036", "97414000CH1740",
    "97415000BW1673", "97411000BP0966", "97413000CM0749", "97418000AT2374",
    "97404000AI2379", "97409000AW1508",
]

with engine().begin() as c:
    done, skipped = [], []
    for idu in LES_14:
        if c.execute(text("SELECT 1 FROM served_run_exceptions WHERE run_id=:l AND idu=:i AND motif=:m"),
                     {"l": LABEL, "i": idu, "m": MOTIF}).scalar():
            skipped.append(idu); continue
        nat = c.execute(text("SELECT tier FROM parcel_p_score_v2 WHERE run_id=:l AND parcelle_id=:i"),
                        {"l": LABEL, "i": idu}).scalar()
        c.execute(text("UPDATE parcel_p_score_v2 SET tier='declasse_non_constructible' "
                       "WHERE run_id=:l AND parcelle_id=:i"), {"l": LABEL, "i": idu})
        c.execute(text("INSERT INTO served_run_exceptions (run_id, idu, tier_origine, tier_servi, motif) "
                       "VALUES (:l, :i, :o, 'declasse_non_constructible', :m)"),
                  {"l": LABEL, "i": idu, "o": nat, "m": MOTIF})
        done.append((idu, nat))
    n_brul = c.execute(text("SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:l AND tier='brulante'"),
                       {"l": LABEL}).scalar()
    n_exc = c.execute(text("SELECT count(*) FROM served_run_exceptions WHERE run_id=:l"), {"l": LABEL}).scalar()

for idu, nat in done:
    print(f"  {idu} : {nat} → declasse_non_constructible (journalisée)")
for idu in skipped:
    print(f"  {idu} : déjà journalisée — sautée")
print(f"✓ retrait fait : {len(done)} retirées, {len(skipped)} sautées · brûlantes servies = {n_brul} · "
      f"exceptions au journal du run servi = {n_exc}")
print("  SUITE (même geste) : labuse build-mvt --label q_v8_calibre ; API up ; python qa/golden_regen.py")
