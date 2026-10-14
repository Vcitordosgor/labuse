"""CHASSE-CALCULS-1 — harnais de collecte LECTURE SEULE (B1/C1/D2).
Pull fiche + outil faisabilité + gabarit pour une liste d'IDU, en-process (pas de serveur).
    LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
    PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/_harness.py B1
"""
import json, sys
from fastapi.testclient import TestClient
from labuse.api import auth
from labuse.api.app import app
from labuse.api.protection import HOTE_INTERNE
import psycopg

C = TestClient(app, client=(HOTE_INTERNE, 0)); C.cookies.set(auth.COOKIE, auth.make_token())
DB = psycopg.connect("postgresql://openclaw@localhost/labuse"); DB.autocommit = True

B1 = ["97411000BK0101","97411000AB0318","97410000AB0212","97415000BZ0007","97417000BN0002",
      "97409000AK0804","97415000CW0658","97412000BV0419","97419000AK0909","97409000AB0521",
      "97413000CA0243","97416000DV0285"]

def g(p):
    r = C.get(p)
    return (json.loads(r.content) if r.status_code == 200 else {"_http": r.status_code, "_t": r.text[:120]})

def deep(o, *keys):
    for k in keys:
        o = (o or {}).get(k) if isinstance(o, dict) else None
    return o

def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "B1"
    idus = B1
    cur = DB.cursor()
    for idu in idus:
        cur.execute("select round(contenance_m2), round(ST_Area(geom_2975)::numeric) from parcels where idu=%s",(idu,))
        row = cur.fetchone(); cont, dessin = (row if row else (None,None))
        f = g(f"/parcels/{idu}")
        fa = g(f"/modules/faisabilite/{idu}")
        gb = g(f"/outils/gabarit/{idu}")
        cap = fa.get("capacite") or {}
        fr = cap.get("fourchette") or {}
        rac = (gb.get("raccordement") or {}).get("plu") or {}
        print("="*90)
        print(f"{idu}  commune_zonefiche={deep(f,'zone_plu') or deep(f,'zone') or f.get('commune')}")
        print(f"  DB contenance={cont} dessin={dessin} | fiche surface_terrain_m2={f.get('surface_terrain_m2')} source={f.get('surface_source')} pente%={f.get('pente_pct')}")
        print(f"  fiche potentiel.sdp_residuelle_m2(SERVED)={deep(f,'potentiel_transformation','sdp_residuelle_m2')} cause={deep(f,'potentiel_transformation','cause')}")
        print(f"  OUTIL faisab: zone={cap.get('zone')} verdict={cap.get('verdict')} calibree={cap.get('calibree')} a_cheval={cap.get('a_cheval')}")
        print(f"     fourchette: niveaux={fr.get('niveaux')}/max={fr.get('niveaux_max')} H={fr.get('hauteur_m')} etage={fr.get('hauteur_etage_m')}")
        print(f"       zone_impl={fr.get('zone_implantation_m2')} emprise_sol_max={fr.get('emprise_sol_max_m2')} emprise_constr={fr.get('emprise_constructible_m2')} emprise_batie={fr.get('emprise_batie_max_m2')}")
        print(f"       SDP={fr.get('surface_plancher_m2')} shab_vend={fr.get('shab_vendable_m2')} logts_sol={fr.get('logements_au_sol')} logts_ss={fr.get('logements_sous_sol')} stat={fr.get('stationnement_regime')}")
        # règlement (sources articles) depuis steps
        for st in (cap.get("steps") or []):
            print(f"       · {st.get('label')} = {st.get('valeur')}  [{st.get('source')}] ({st.get('prov')})")
        print(f"  GABARIT status={gb.get('status')} surfaceParcelle={gb.get('surfaceParcelleM2')} zoneImpl={gb.get('zoneImplantationM2')} plafond={gb.get('plafondEmpriseM2')} hReg={gb.get('hauteurReglementaireM')} base={gb.get('hauteurBase')}")
        print(f"     raccordement.plu: emprise%={rac.get('emprise_pct')} Hfait={rac.get('hauteur_faitage_m')} Hegout={rac.get('hauteur_egout_m')} reculVoie={rac.get('recul_voie_m')} reculSep={rac.get('recul_sep_m')} src={rac.get('source')}")
        if gb.get("status")!="ok":
            print(f"     gabarit message: {gb.get('message')}")

if __name__ == "__main__":
    main()
