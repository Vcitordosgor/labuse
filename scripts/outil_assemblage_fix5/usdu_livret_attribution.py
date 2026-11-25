"""OUTIL-ASSEMBLAGE-FIX-5 (LOT 2) — rattache chaque parcelle Usdu de Saint-Paul à son LIVRET de bassin
par la zone à livret (U1-6/AU1-6) la plus proche (polygones plu_gpu_zone), avec marge « à cheval » 50 m.
Base `labuse` en LECTURE SEULE. Sort la distribution par livret + le nombre d'inattribuables."""
import psycopg
from collections import Counter
cx=psycopg.connect('postgresql://openclaw@localhost:5432/labuse',connect_timeout=30)
cx.execute('SET default_transaction_read_only = on'); cx.execute('SET statement_timeout=180000')
MARGE=50.0
q="""
WITH liv AS (SELECT geom_2975 g, substring(attrs->>'libelle' from '^A?U([1-6])')::int AS livret
             FROM spatial_layers WHERE kind='plu_gpu_zone' AND commune='Saint-Paul' AND attrs->>'libelle' ~ '^A?U[1-6]'),
usdu AS (SELECT p.id, p.geom_2975 g FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
         WHERE p.commune='Saint-Paul' AND z.zone_lib='Usdu'),
dist AS (SELECT u.id, l.livret, min(ST_Distance(u.g,l.g)) d FROM usdu u, liv l GROUP BY u.id, l.livret),
rk AS (SELECT id, livret, d, row_number() OVER (PARTITION BY id ORDER BY d) rn FROM dist)
SELECT a.id, a.livret l1, a.d d1, b.d d2 FROM rk a LEFT JOIN rk b ON b.id=a.id AND b.rn=2 WHERE a.rn=1
"""
rows=cx.execute(q).fetchall()
PAGE={3:"pp. 106-107",4:"p. 168",5:"p. 214",6:"p. 274"}
attrib=Counter(); nocheval=0
for _id,l1,d1,d2 in rows:
    if d2 is not None and (d2-d1)<MARGE: nocheval+=1
    else: attrib[l1]+=1
print("Usdu total:", len(rows))
for liv in sorted(attrib): print(f"  livret {liv} ({PAGE[liv]}): {attrib[liv]}")
print("à cheval (aucune page):", nocheval)
