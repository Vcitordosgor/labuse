"""10 parcelles qui CHANGENT de palier q_v20→q_v21, vérifiées une à une avec preuve."""
import json
from sqlalchemy import text
from labuse.db import session_scope
from labuse.scoring.tiers_client import court as palier_court

def rows(db,q):
    return db.execute(text(q)).mappings().all()

with session_scope() as db:
    # 5 COPRO : actionnable (q_v20) -> sans_signal (q_v21)
    copro = rows(db, """
      SELECT a.parcelle_id, a.tier t20, b.tier t21, a.p_raw p20, b.p_raw p21, a.mult_base m20, b.copro
      FROM parcel_p_score_v2 a JOIN parcel_p_score_v2 b USING(parcelle_id)
      WHERE a.run_id='q_v20' AND b.run_id='q_v21' AND a.tier IN ('priorite','a_suivre')
        AND b.tier='sans_signal' AND b.copro=true ORDER BY a.parcelle_id LIMIT 5""")
    # 5 PPR : non-ecartee (q_v20) -> ecartee (q_v21), dans une zone i
    ppr = rows(db, """
      SELECT a.parcelle_id, a.tier t20, b.tier t21, a.p_raw p20, b.p_raw p21, b.copro
      FROM parcel_p_score_v2 a JOIN parcel_p_score_v2 b USING(parcelle_id)
      WHERE a.run_id='q_v20' AND b.run_id='q_v21' AND a.tier<>'ecartee' AND b.tier='ecartee'
      ORDER BY a.parcelle_id LIMIT 5""")
    print("="*70,"\n5 COPROPRIÉTÉS — actionnable → Sans signal (E-010)\n","="*70)
    for i,r in enumerate(copro,1):
        idu=r['parcelle_id']
        # preuve copro + statut cascade identique (pas écartée)
        cop=db.execute(text("SELECT (copro_rnic OR copro_dvf) FROM p_model_ext_copro WHERE idu=:i"),{"i":idu}).scalar()
        print(f"\n{i}. {idu}")
        print(f"   palier q_v20={palier_court(r['t20'])!r} -> q_v21={palier_court(r['t21'])!r}  (tier stocké {r['t20']}->{r['t21']})")
        print(f"   p_raw identique : {r['p20']}=={r['p21']} -> {r['p20']==r['p21']}  (classement inchangé, seul le palier change)")
        print(f"   copro: stocké={r['copro']}  source p_model_ext_copro={cop}  (mult_base q_v20 stocké={r['m20']}, NON servi)")
    print("\n"+"="*70,"\n5 PPR code « i » (Saint-Philippe) — → Écartée (zone rouge)\n","="*70)
    for i,r in enumerate(ppr,1):
        idu=r['parcelle_id']
        cov=db.execute(text("""SELECT round((100*ST_Area(ST_Union(ST_Intersection(sl.geom_2975,p.geom_2975)))/ST_Area(p.geom_2975))::numeric,1)
             FROM parcels p JOIN spatial_layers sl ON sl.kind='ppr' AND sl.subtype='i' AND ST_Intersects(p.geom_2975,sl.geom_2975)
             WHERE p.idu=:i GROUP BY p.geom_2975"""),{"i":idu}).scalar()
        st20=db.execute(text("SELECT status FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id WHERE d.run_label='q_v19_sources' AND p.idu=:i"),{"i":idu}).scalar()
        st21=db.execute(text("SELECT status FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id WHERE d.run_label='q_v21_sources' AND p.idu=:i"),{"i":idu}).scalar()
        print(f"\n{i}. {idu}")
        print(f"   palier q_v20={palier_court(r['t20'])!r} -> q_v21={palier_court(r['t21'])!r}  (tier stocké {r['t20']}->{r['t21']})")
        print(f"   couverture zone rouge « i » = {cov} %  (seuil exclusion 50 %)")
        print(f"   cascade status : q_v19_sources={st20!r} -> q_v21_sources={st21!r}")
        print(f"   p_raw identique : {r['p20']}=={r['p21']} -> {r['p20']==r['p21']}")
