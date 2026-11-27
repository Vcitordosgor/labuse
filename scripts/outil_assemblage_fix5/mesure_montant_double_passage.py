import csv, sys
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
    pid,idu,commune,zone=rec
    from labuse.faisabilite.bilan import compute_bilan_servi
    try:
        _S.rollback(); b,_=compute_bilan_servi(_S,int(pid))
    except Exception as e:
        return (idu,commune,zone,'ERR','','','','','')
    if not b: return (idu,commune,zone,'none','','','','','')
    m=getattr(b,'mixite',None) or {}
    ca=(b.ca or {}).get('central') if b.ca else ''
    cf=(b.charge_fonciere or {}).get('central') if b.charge_fonciere else ''
    u4=1 if any('Marie Caze' in a for a in (b.avertissements or [])) else 0
    return (idu,commune,zone,'ok' if b.fiable else 'ko','1' if m.get('declenchee') else '0',
            m.get('page') or '', ca if ca is not None else '', cf if cf is not None else '', u4)
def main():
    recs=[]
    with open('/tmp/fix5_candidates.csv') as f:
        r=csv.reader(f); next(r)
        for row in r: recs.append((row[0],row[1],row[2],row[3]))
    out=open(f'/tmp/fix5_{TAG}.csv','w',newline=''); w=csv.writer(out)
    w.writerow(['idu','commune','zone','status','declenchee','page','ca_central','cf_central','u4_avert'])
    n=0
    with ProcessPoolExecutor(max_workers=8, initializer=_init) as ex:
        for res in ex.map(_one, recs, chunksize=20):
            w.writerow(res); n+=1
            if n%400==0: out.flush(); sys.stderr.write(f'{TAG} {n}/{len(recs)}\n')
    out.close(); sys.stderr.write(f'{TAG} DONE {n}\n')
if __name__=='__main__': main()
