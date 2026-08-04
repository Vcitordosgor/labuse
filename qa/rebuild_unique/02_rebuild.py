"""REBUILD UNIQUE — Étape B : rebuild parcel_zone_plu + non-régression + re-classif au_statut.

Porte les correctifs dans les DONNÉES :
  * ingestion pt2.4/pt3 : zone_lib = 1er token de attrs.libelle (repli name) + zone_libelle complet
    → build_parcel_zone_plu (code déjà sur main).
  * 2.2 normalize_zone / 2.3 KW resserré / Saint-Benoît (72531db) : appliqués à la RE-CLASSIF
    parcel_au_statut via build_au_ouverture (zone_regime + classify lisent le nouveau zone_lib).

Contrôle non-régression : zone_lib AVANT (backup) vs APRÈS par commune — attendu ~0 sur les communes
déjà correctes, gros deltas sur les 8 communes dont la calibration était inerte.

Re-classif au_statut : UNIQUEMENT les 5 communes calibrées AU-ouverture (au_ouverture_planchers.yaml).
Les communes non calibrées gardent leurs lignes 'générique' (hors périmètre du mandat).
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope
from labuse.api.tiles import build_parcel_zone_plu
from labuse.faisabilite.au_ouverture import build_au_ouverture

CALIBREES = ["97415", "97408", "97413", "97423", "97410"]  # SP, LP, SL, T-B, Saint-Benoît

def q(s, sql, **p): return s.execute(text(sql), p)

# 1. REBUILD parcel_zone_plu (long)
t0 = time.time()
with session_scope() as s:
    n = build_parcel_zone_plu(s)
    print(f"  parcel_zone_plu rebâtie : {n} lignes en {time.time()-t0:.0f}s", flush=True)

# 2. NON-RÉGRESSION : zone_lib avant/après par commune
with session_scope() as s:
    print("\n  === NON-RÉGRESSION zone_lib (backup vs rebuild) ===", flush=True)
    tot = q(s, """SELECT count(*) FROM parcel_zone_plu n JOIN parcel_zone_plu_prebascule o USING(idu)
                  WHERE n.zone_lib IS DISTINCT FROM o.zone_lib""").scalar()
    print(f"  parcelles dont zone_lib change : {tot}", flush=True)
    rows = q(s, """SELECT substring(idu from 1 for 5) AS insee, count(*) n
                   FROM parcel_zone_plu n JOIN parcel_zone_plu_prebascule o USING(idu)
                   WHERE n.zone_lib IS DISTINCT FROM o.zone_lib GROUP BY 1 ORDER BY 2 DESC""").all()
    for r in rows:
        print(f"    {r.insee}: {r.n}", flush=True)
    print("  échantillon des transitions (avant → après) :", flush=True)
    for r in q(s, """SELECT o.zone_lib AS av, n.zone_lib AS ap, substring(o.idu from 1 for 5) AS insee, count(*) c
                     FROM parcel_zone_plu n JOIN parcel_zone_plu_prebascule o USING(idu)
                     WHERE n.zone_lib IS DISTINCT FROM o.zone_lib
                     GROUP BY 1,2,3 ORDER BY c DESC LIMIT 25""").all():
        print(f"    {r.insee} {str(r.av):>10s} → {str(r.ap):<10s} : {r.c}", flush=True)

# 3. RE-CLASSIF au_statut des 5 communes calibrées
with session_scope() as s:
    print("\n  === RE-CLASSIF au_statut (5 communes calibrées) ===", flush=True)
    print("  AVANT (backup) par commune/classe :", flush=True)
    for r in q(s, """SELECT substring(idu from 1 for 5) insee, classe, count(*) n
                     FROM parcel_au_statut_prebascule WHERE substring(idu from 1 for 5)=ANY(:c)
                     GROUP BY 1,2 ORDER BY 1,2""", c=CALIBREES).all():
        print(f"    {r.insee} {r.classe:28s} {r.n}", flush=True)
    # purge des lignes des 5 communes puis reconstruction propre
    d = q(s, "DELETE FROM parcel_au_statut WHERE substring(idu from 1 for 5)=ANY(:c)", c=CALIBREES).rowcount
    print(f"  {d} lignes supprimées (5 communes) ; reconstruction…", flush=True)
    compte = build_au_ouverture(s, CALIBREES)
    s.commit()
    print(f"  build_au_ouverture → {compte}", flush=True)
    print("  APRÈS par commune/classe :", flush=True)
    for r in q(s, """SELECT substring(idu from 1 for 5) insee, classe, count(*) n
                     FROM parcel_au_statut WHERE substring(idu from 1 for 5)=ANY(:c)
                     GROUP BY 1,2 ORDER BY 1,2""", c=CALIBREES).all():
        print(f"    {r.insee} {r.classe:28s} {r.n}", flush=True)
    print("  total parcel_au_statut :", q(s, "SELECT count(*) FROM parcel_au_statut").scalar(), flush=True)
print("ÉTAPE B FINIE", flush=True)
