#!/usr/bin/env python3
"""NU4-E — déclencheur d'injection SÛRE répétée pendant la charge.

Rejoue le CHEMIN SÛR (`injection_sure.injecter_table_sure`, doctrine INJECTION-SOLIDE : staging +
contrôle de delta + verrou consultatif + swap atomique DELETE+INSERT en une transaction, SANS
ACCESS EXCLUSIVE) sur une table SERVIE que la fiche lit : `dvf_mutations_parcelle` (lue par la vue
`v_parcel_dvf_last`). Le `charger_staging` recopie la table servie à l'identique → delta 0 % →
contrôles OK → swap. Données finales IDENTIQUES (local, idempotent, réversible).

But : mesurer si une injection sûre bloque/ralentit les lectures client sous charge (le swap
revendique ne PAS prendre d'ACCESS EXCLUSIVE ; on le vérifie via les lock_waits de l'échantillonneur).

Usage : PY inject_safe.py <duree_s> [table=dvf_mutations_parcelle] [pause_s=5]
"""
import sys, time
from sqlalchemy import text
from labuse.db import engine
from labuse.ingestion import injection_sure

DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 600.0
TABLE = sys.argv[2] if len(sys.argv) > 2 else "dvf_mutations_parcelle"
PAUSE = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

def charger_staging(conn, staging):
    conn.execute(text(f'INSERT INTO "{staging}" SELECT * FROM "{TABLE}"'))

eng = engine()
t0 = time.time(); n = 0
while time.time() - t0 < DUR:
    ts = time.time()
    res = injection_sure.injecter_table_sure(
        eng, table=TABLE, charger_staging=charger_staging,
        a_geometrie=False, couverture_974_min=0, delta_max_pct=35.0,
        log=lambda *a: None)
    n += 1
    print(f"[{time.time()-t0:7.1f}s] inject #{n} {TABLE}: injecte={res.get('injecte')} "
          f"swap={time.time()-ts:.2f}s rows={res.get('mesures',{}).get('comptes_apres')}", flush=True)
    time.sleep(PAUSE)
print(f"done: {n} safe injections of {TABLE}")
