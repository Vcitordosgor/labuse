"""OUTIL-ASSEMBLAGE-FIX-4 — MESURE (lecture seule) : montant du bilan qui change par zone.

Double passage du moteur servi (`compute_bilan_servi`) sur les parcelles des zones euro-capables de
FIX-4 (Saint-Paul AU3st = ZAC Savane des Tamarins, exemptée ; Saint-Denis AUj/AUm/AUh, nouvellement
armées) + un échantillon de CONTRÔLE (divers livrets SP + zones SD) pour prouver que les changements
d'affichage (page du livret, source) ne bougent AUCUN euro.

Reproduction :
  1. candidats → /tmp/fix4_candidates.csv (id,idu,commune,zone,kind) :
       euro   : AU3st (Saint-Paul) + AUj/AUm/AUh (Saint-Denis)  — toutes leurs parcelles
       control: U1a/U2a/U3c/U4a/U5a/U6a (Saint-Paul) + Uavap/Um (Saint-Denis) — 20 par zone
     (SELECT p.id,p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu WHERE p.commune=? AND z.zone_lib=?)
  2. python mesure_montant_double_passage.py courant      # code FIX-4
  3. git stash push -- src/ config/ ; python … base ; git stash pop   # code d'avant
  4. python diff_par_zone.py                              # écart par zone (médian/max/total)
Base `labuse` en LECTURE SEULE (SET default_transaction_read_only = on), aucune écriture.
"""
import csv, os, sys
from concurrent.futures import ProcessPoolExecutor
DBURL='postgresql+psycopg://openclaw@localhost:5432/labuse'
TAG=sys.argv[1] if len(sys.argv)>1 else 'courant'
_S=None
def _init():
    global _S
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    _S=Session(create_engine(DBURL,future=True)); _S.execute(text('SET default_transaction_read_only = on'))
def _one(rec):
    pid,idu,commune,zone,kind=rec
    from labuse.faisabilite.bilan import compute_bilan_servi
    try:
        _S.rollback(); b,_=compute_bilan_servi(_S,int(pid))
    except Exception as e:
        return (idu,commune,zone,kind,'ERR','','','','', repr(e)[:60])
    if not b: return (idu,commune,zone,kind,'none','','','','','')
    m=getattr(b,'mixite',None) or {}
    ca=(b.ca or {}).get('central') if b.ca else ''
    cf=(b.charge_fonciere or {}).get('central') if b.charge_fonciere else ''
    return (idu,commune,zone,kind,'ok' if b.fiable else 'ko',
            '1' if m.get('declenchee') else '0', m.get('regime') or '',
            m.get('page') or '', ca if ca is not None else '', cf if cf is not None else '')
def main():
    recs=[]
    with open('/tmp/fix4_candidates.csv') as f:
        r=csv.reader(f); next(r)
        for row in r: recs.append((row[0],row[1],row[2],row[3],row[4]))
    out=open(f'/tmp/fix4_{TAG}.csv','w',newline=''); w=csv.writer(out)
    w.writerow(['idu','commune','zone','kind','status','declenchee','regime','page','ca_central','cf_central'])
    done=0
    with ProcessPoolExecutor(max_workers=8, initializer=_init) as ex:
        for res in ex.map(_one, recs, chunksize=20):
            w.writerow(res); done+=1
            if done%300==0: out.flush(); sys.stderr.write(f'{TAG} {done}/{len(recs)}\n')
    out.close(); sys.stderr.write(f'{TAG} DONE {done}\n')
if __name__=='__main__': main()
