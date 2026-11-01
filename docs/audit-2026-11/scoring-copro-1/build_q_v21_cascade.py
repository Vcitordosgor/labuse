import time
from sqlalchemy import text
from labuse.db import session_scope
from labuse.cascade import evaluate_parcels

SRC="q_v19_sources"; DST="q_v21_sources"
t0=time.time()
with session_scope() as s:
    exists=s.execute(text("SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label=:d"),{"d":DST}).scalar()
    if exists:
        print(f"{DST} existe déjà ({exists}) — purge avant rebuild."); 
        s.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE run_label=:d"),{"d":DST}); s.commit()
    aff=[r[0] for r in s.execute(text(
        "SELECT DISTINCT p.id FROM parcels p JOIN spatial_layers sl "
        "ON sl.kind='ppr' AND sl.subtype='i' AND ST_Intersects(p.geom_2975, sl.geom_2975)")).all()]
    print(f"parcelles i-affectées : {len(aff)}")
    # 1) copie q_v19_sources (hors affectées) -> q_v21_sources
    n=s.execute(text("""
       INSERT INTO dryrun_parcel_evaluations
         (run_label, parcel_id, completeness_score, opportunity_score, opportunity_base,
          status, rules_version, q_score, a_score, a_completude, matrice_statut)
       SELECT :d, parcel_id, completeness_score, opportunity_score, opportunity_base,
          status, rules_version, q_score, a_score, a_completude, matrice_statut
       FROM dryrun_parcel_evaluations WHERE run_label=:src AND parcel_id <> ALL(:aff)
    """),{"d":DST,"src":SRC,"aff":aff}).rowcount
    s.commit()
    print(f"copie (hors affectées) : {n} lignes ({time.time()-t0:.0f}s)")
    # 2) ré-évalue les affectées sous le nouveau code PPR -> q_v21_sources
    for k in range(0,len(aff),500):
        evaluate_parcels(aff[k:k+500], s, persist=True, dryrun_label=DST); s.commit(); s.expunge_all()
    print(f"ré-évaluation {len(aff)} affectées faite ({time.time()-t0:.0f}s)")
with session_scope() as s:
    tot=s.execute(text("SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label=:d"),{"d":DST}).scalar()
    srctot=s.execute(text("SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label=:s"),{"s":SRC}).scalar()
    print(f"TOTAL {DST}={tot}  (SRC {SRC}={srctot})")
    for lbl in (SRC,DST):
        br=dict(s.execute(text("SELECT status,count(*) FROM dryrun_parcel_evaluations WHERE run_label=:l GROUP BY 1"),{"l":lbl}).all())
        print(f"  {lbl}: {br}")
