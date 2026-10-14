"""CHASSE-CALCULS-1 — C1 : mesure AU MÈTRE des reculs du Gabarit sur la géométrie servie.
LECTURE SEULE. Pour chaque IDU : récupère le gabarit en-process, et si status=ok, mesure
en PostGIS (EPSG:2975, mètres) la zone d'implantation Z contre la parcelle P :
  · Z ⊂ P ? (aire de débordement)
  · distance min Z→bord parcelle  = recul le plus serré appliqué
  · distance Z→voirie la plus proche = recul voie effectif
  · intersection Z ∩ PPR (interdiction) = doit être 0
Confronté aux reculs ANNONCÉS (raccordement.plu) + classification des arêtes + pente fiche.
    LABUSE_DATABASE_URL=... PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/_mesure_gabarit.py
"""
import json
from fastapi.testclient import TestClient
from labuse.api import auth
from labuse.api.app import app
from labuse.api.protection import HOTE_INTERNE
import psycopg

C = TestClient(app, client=(HOTE_INTERNE, 0)); C.cookies.set(auth.COOKIE, auth.make_token())
DB = psycopg.connect("postgresql://openclaw@localhost/labuse"); DB.autocommit = True

POOL = ["97409000AK0804","97411000BK0101","97412000BV0419","97412000BK0866","97412000BV0039",
        "97408000AP1344","97408000AN0062","97408000BO0267","97409000AY0786","97419000AK0909",
        "97416000ES2238","97411000AB0061"]

def measure(idu, zgeo):
    cur = DB.cursor()
    cur.execute("""
      WITH p AS (SELECT geom_2975 g FROM parcels WHERE idu=%s),
           z AS (SELECT ST_MakeValid(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),2975)) g)
      SELECT
        round(ST_Area((SELECT g FROM z))::numeric) z_area,
        round(ST_Area(ST_Difference((SELECT g FROM z),(SELECT g FROM p)))::numeric,1) z_hors_p,
        round(ST_Distance((SELECT g FROM z), ST_Boundary((SELECT g FROM p)))::numeric,2) d_bord,
        round((SELECT min(ST_Distance((SELECT g FROM z), v.geom_2975)) FROM spatial_layers v
                WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975,(SELECT g FROM p),60))::numeric,2) d_voirie,
        round(coalesce((SELECT sum(ST_Area(ST_Intersection((SELECT g FROM z), pr.geom_2975)))
                FROM spatial_layers pr WHERE pr.kind='ppr' AND ST_Intersects(pr.geom_2975,(SELECT g FROM z)))::numeric,0),1) z_inter_ppr
    """, (idu, json.dumps(zgeo)))
    return cur.fetchone()

for idu in POOL:
    gb = json.loads(C.get(f"/outils/gabarit/{idu}").content)
    rac = (gb.get("raccordement") or {}).get("plu") or {}
    cls = (gb.get("raccordement") or {}).get("classification") or {}
    f = json.loads(C.get(f"/parcels/{idu}").content)
    pente = f.get("pente_pct")
    st = gb.get("status")
    if st != "ok" or not gb.get("zoneImplantationGeoJSON"):
        print(f"{idu}  status={st}  (pas de zone mesurable)")
        continue
    z_area, z_hors_p, d_bord, d_voirie, z_ppr = measure(idu, gb["zoneImplantationGeoJSON"])
    print(f"{idu}  zone={gb.get('zoneImplantationM2')}  pente%={pente}")
    print(f"   ANNONCÉ  reculVoie={rac.get('recul_voie_m')} reculSep={rac.get('recul_sep_m')} Hfait={rac.get('hauteur_faitage_m')} Hegout={rac.get('hauteur_egout_m')} | arêtes voie={cls.get('voie')} side={cls.get('side')} rear={cls.get('rear')}")
    print(f"   MESURÉ   Z={z_area} m² | hors parcelle={z_hors_p} m² (⊂P si ~0) | d(Z,bord)={d_bord} m (≈ recul serré) | d(Z,voirie)={d_voirie} m (≈ recul voie) | Z∩PPR={z_ppr} m²")
