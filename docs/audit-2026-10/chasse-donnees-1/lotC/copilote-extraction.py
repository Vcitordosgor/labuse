import os, json
os.environ.setdefault("PGOPTIONS", "-c default_transaction_read_only=on -c statement_timeout=15s")
import sys
sys.path.insert(0, "/Users/openclaw/Desktop/labuse-chasse-donnees/src")
from labuse.db import session_scope  # noqa
from sqlalchemy import text
from labuse import db as dbm
IDUS = ['97409000AK0804','97415000CW0658','97415000BZ0007','97416000DV0285','97411000BZ1065']
from labuse.api.app import _build_fiche, _q_v2_fiche
from sqlalchemy.orm import Session
eng = dbm.engine()
out = {}
with Session(eng) as db:
    db.execute(text("SET statement_timeout='30s'"))
    for idu in IDUS:
        row = {}
        try:
            f2 = _q_v2_fiche(db, idu)
            pot = f2.get('potentiel_transformation') or {}
            al = f2.get('analyse_labuse') or {}
            zones = [z.get('zone') for z in ((f2.get('reglement_plu') or {}).get('zones') or [])]
            row['premium'] = {'surface_m2': f2.get('surface_m2'), 'surface_terrain_m2': f2.get('surface_terrain_m2'),
                              'contenance_m2': f2.get('contenance_m2'), 'zones': zones,
                              'sdp_residuelle_m2': pot.get('sdp_residuelle_m2'), 'bande': al.get('bande'),
                              'tier_v2': (f2.get('score_v2') or {}).get('tier'), 'rang_v2': (f2.get('score_v2') or {}).get('rang')}
        except Exception as e:
            db.rollback(); row['premium'] = {'erreur': repr(e)[:200]}
        try:
            f1 = _build_fiche(db, idu, with_assistant=False)
            fa = f1.get('faisabilite') or {}
            fr = fa.get('fourchette') or fa.get('capacite') or {}
            vd = f1.get('verdict') or {}
            row['legacy'] = {'surface_m2': (f1.get('parcel') or {}).get('surface_m2'),
                             'zone_resolue': fa.get('zone_resolue') or fa.get('zone'),
                             'surface_plancher_m2': fr.get('surface_plancher_m2'),
                             'niveaux': fr.get('niveaux'),
                             'tier': vd.get('tier'), 'rang': vd.get('rang'), 'status': vd.get('status'),
                             'opportunity_score': vd.get('opportunity_score'),
                             'faisa_surface_terrain': fa.get('surface_terrain_m2') or fa.get('surface_m2')}
        except Exception as e:
            db.rollback(); row['legacy'] = {'erreur': repr(e)[:200]}
        out[idu] = row
        db.rollback()
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
