"""Reproduit le set « entièrement en zone rouge » (zone d'implantation nulle après retrait du rouge,
définition PPR-UNIQUE-1 APRES_zone_nulle_0_logement) et capture la liste d'IDU → JSON."""
import json
from sqlalchemy import text
from labuse.db import session_scope
from labuse.implantation import terrain
EPS=1.0
with session_scope() as s:
    idus=[r[0] for r in s.execute(text(
        "SELECT DISTINCT p.idu FROM parcels p JOIN spatial_layers sl "
        "ON sl.kind='ppr' AND sl.subtype='i' AND ST_Intersects(p.geom_2975, sl.geom_2975) "
        "ORDER BY p.idu")).fetchall()]
    nulles=[]; nonnulles=0; traitees=0
    for idu in idus:
        try:
            t=terrain.charger(s,[idu],recul_voie_m=4.0,recul_separative_m=3.0,inset_m=0.0,avec_pente=False)
        except Exception:
            continue
        traitees+=1
        if t.zone_implantation.area<=EPS: nulles.append(idu)
        else: nonnulles+=1
    out={"traitees":traitees,"zone_nulle_n":len(nulles),"zone_non_nulle_n":nonnulles,"idus_zone_nulle":nulles}
    open("/tmp/fully_red.json","w").write(json.dumps(out))
    print("traitees",traitees,"| entièrement rouge (zone nulle) =",len(nulles),"| hors-rouge subsiste",nonnulles)
