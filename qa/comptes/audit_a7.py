"""AUDIT COMPTES · A7 — montée en charge MODÉRÉE (15 comptes). Le vrai risque : un cache ou
une variable partagée (ContextVar mal isolée) qui renverrait, SOUS CONCURRENCE, les données du
mauvais compte. Chaque compte a un marqueur unique dans ses objets ; on lance des lectures ET
écritures concurrentes, puis on vérifie qu'AUCUN compte ne voit le marqueur d'un autre et
qu'aucune écriture n'est partielle. (Pas de test à 500 : mono-worker, cf. GB-040.)
"""
import os, uuid, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
os.environ["LABUSE_ENV"]="pilot"; os.environ["LABUSE_AUTH_PASSWORD"]="pilote-audit-a7"
os.environ["LABUSE_SECRET_KEY"]="secret-audit-a7-0000000000000000000000"
_app="postgresql+psycopg://openclaw@localhost:5432/labuse"
for l in Path("/Users/openclaw/Desktop/labuse/.env").read_text().splitlines():
    if l.startswith("LABUSE_DATABASE_URL="): _app=l.split("=",1)[1].strip()
os.environ["LABUSE_DATABASE_URL"]=_app.rsplit("/",1)[0]+"/labuse_test"
from fastapi.testclient import TestClient
from sqlalchemy import text
from labuse import comptes, config
from labuse.db import session_scope
config.get_settings.cache_clear()
from labuse.api.app import app

N=15
emails=[f"charge{i}-{uuid.uuid4().hex[:6]}@audit-test.re" for i in range(N)]
marque={}  # email -> marqueur unique
def creer(e):
    with session_scope() as s:
        inv=comptes.creer_invitation(s,e,nom=f"[AUDIT-TEST] Charge {e[:12]}")
        comptes.activer_par_invitation(s,inv["lien"].split("token=")[1],"motdepasse-audit-a7","2026-07-22")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"),{"c":inv["compte_id"]}); s.commit()
        return inv["compte_id"]
cids={e:creer(e) for e in emails}
def login(e):
    c=TestClient(app,base_url="https://testserver")
    c.post("/login",data={"identifiant":e,"password":"motdepasse-audit-a7"},follow_redirects=False)
    return c
clients={e:login(e) for e in emails}

# chaque compte crée un projet AVEC SON MARQUEUR unique
def creer_projet(e):
    m=f"MARK-{uuid.uuid4().hex[:10]}"; marque[e]=m
    r=clients[e].post("/projets", json={"nom": m, "cadrage":{"communes":["Saint-Denis"]}})
    return r.status_code==200
with ThreadPoolExecutor(max_workers=N) as ex:
    oks=list(ex.map(creer_projet, emails))
assert all(oks), f"créations projet échouées: {oks.count(False)}"

# CONCURRENCE : chaque compte lit /projets EN PARALLÈLE, en boucle — cherche une fuite de marqueur
fuites=[]; lock=threading.Lock()
def hammer(e):
    for _ in range(20):
        js=clients[e].get("/projets").json()
        noms={p.get("nom") for p in js}
        # doit contenir SON marqueur, JAMAIS celui d'un autre
        autres={marque[o] for o in emails if o!=e}
        vus_autres = noms & autres
        if marque[e] not in noms or vus_autres:
            with lock:
                fuites.append({"compte":e,"manque_le_sien": marque[e] not in noms,
                               "voit_autres": list(vus_autres)[:3]})
            return
with ThreadPoolExecutor(max_workers=N) as ex:
    list(ex.map(hammer, emails))

# écritures concurrentes : chaque compte ajoute une entrée CRM sur SA parcelle, en parallèle
IDU=f"974A7{uuid.uuid4().hex[:5].upper()}"
with session_scope() as s:
    s.execute(text("INSERT INTO parcels (idu,commune,section,numero,geom,geom_2975,surface_m2,centroid,bbox)"
      " VALUES (:i,'Saint-Denis','ZA','1',ST_GeomFromText(:w,4326),ST_Transform(ST_GeomFromText(:w,4326),2975),900,"
      " ST_Centroid(ST_GeomFromText(:w,4326)),ST_Envelope(ST_GeomFromText(:w,4326))) ON CONFLICT (idu) DO NOTHING"),
      {"i":IDU,"w":"POLYGON((55.5 -21,55.501 -21,55.501 -21.001,55.5 -21.001,55.5 -21))"}); s.commit()
def crm(e):
    return clients[e].post("/pipeline", json={"idu":IDU}).status_code==200
with ThreadPoolExecutor(max_workers=N) as ex:
    crm_oks=list(ex.map(crm, emails))

# chaque compte doit avoir EXACTEMENT 1 entrée CRM sur cette parcelle (la sienne), pas plus
partiel=[]
for e in emails:
    with session_scope() as s:
        n=s.execute(text("SELECT count(*) FROM pipeline_entries WHERE compte_id=:c AND parcel_id=(SELECT id FROM parcels WHERE idu=:i)"),
                    {"c":cids[e],"i":IDU}).scalar()
    if n!=1: partiel.append({"compte":e,"n_entries":n})

print(f"comptes: {N} · projets créés: {oks.count(True)} · CRM créés: {crm_oks.count(True)}")
print(f"FUITES de marqueur sous concurrence: {len(fuites)}")
for f in fuites[:5]: print("  🔴",f)
print(f"écritures partielles (≠1 entrée CRM/compte): {len(partiel)}")
for p in partiel[:5]: print("  🔴",p)

# PURGE
with session_scope() as s:
    s.execute(text("DELETE FROM parcels WHERE idu=:i"),{"i":IDU})
    for e in emails:
        try: comptes.supprimer_utilisateur(s,e)
        except: pass
    s.commit()
import sys
ok = not fuites and not partiel
print("\n"+("✓ AUCUN croisement de données, aucune écriture partielle" if ok else "🔴 ANOMALIE DE CONCURRENCE"))
sys.exit(0 if ok else 2)
