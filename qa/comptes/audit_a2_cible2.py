import os, uuid
from pathlib import Path
os.environ["LABUSE_ENV"]="pilot"; os.environ["LABUSE_AUTH_PASSWORD"]="pilote-audit-a2"
os.environ["LABUSE_SECRET_KEY"]="secret-audit-a2-0000000000000000000000"
_app="postgresql+psycopg://openclaw@localhost:5432/labuse"
for l in (Path("/Users/openclaw/Desktop/labuse/.env").read_text().splitlines()):
    if l.startswith("LABUSE_DATABASE_URL="): _app=l.split("=",1)[1].strip()
os.environ["LABUSE_DATABASE_URL"]=_app.rsplit("/",1)[0]+"/labuse_test"
from fastapi.testclient import TestClient
from sqlalchemy import text
from labuse import comptes, config
from labuse.db import session_scope
config.get_settings.cache_clear()
from labuse.api.app import app
S=f"s-{uuid.uuid4().hex[:8]}@audit-test.re"; C=f"c-{uuid.uuid4().hex[:8]}@audit-test.re"
def compte(e,n):
    with session_scope() as s:
        try: comptes.supprimer_utilisateur(s,e)
        except: pass
        inv=comptes.creer_invitation(s,e,nom=f"[AUDIT-TEST] {n}")
        comptes.activer_par_invitation(s,inv["lien"].split("token=")[1],"motdepasse-audit-a2","2026-07-22")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"),{"c":inv["compte_id"]}); s.commit()
        return inv["compte_id"]
def login(e):
    c=TestClient(app,base_url="https://testserver")
    assert c.post("/login",data={"identifiant":e,"password":"motdepasse-audit-a2"},follow_redirects=False).status_code==303
    return c
cs_id=compte(S,"Stéphanie"); cc_id=compte(C,"Caroline")
cs,cc=login(S),login(C)
res=[]
def chk(n,cond,d=""): res.append((n,cond)); print(f"  {'✓' if cond else '🔴 FUITE'}  {n}  {d}")

# search de Caroline
cc.post("/events/searches", json={"nom":"Rech Caro","hash":"#caro"})
with session_scope() as s:
    sid=s.execute(text("SELECT id FROM saved_searches WHERE compte_id=:c ORDER BY id DESC LIMIT 1"),{"c":cc_id}).scalar()
r=cs.patch(f"/events/searches/{sid}", json={"nom":"VOL"})
with session_scope() as s:
    nom=s.execute(text("SELECT nom FROM saved_searches WHERE id=:i"),{"i":sid}).scalar()
chk("saved_search de Caroline non renommable par Stéphanie", nom=="Rech Caro", f"(HTTP {r.status_code}, nom={nom})")
rd=cs.delete(f"/events/searches/{sid}")
with session_scope() as s:
    ex=s.execute(text("SELECT COUNT(*) FROM saved_searches WHERE id=:i"),{"i":sid}).scalar()
chk("saved_search de Caroline non supprimable par Stéphanie", ex==1, f"(HTTP {rd.status_code}, existe={ex})")

# colonne CRM de Caroline
rc=cc.post("/pipeline/columns", json={"label":"Col Caro"})
with session_scope() as s:
    cid_col=s.execute(text("SELECT id FROM crm_columns WHERE compte_id=:c ORDER BY id DESC LIMIT 1"),{"c":cc_id}).scalar()
r=cs.patch(f"/pipeline/columns/{cid_col}", json={"label":"VOL"})
chk("crm_column de Caroline non modifiable par Stéphanie (404)", r.status_code==404, f"(HTTP {r.status_code})")
r=cs.request("DELETE", f"/pipeline/columns/{cid_col}", json={})
chk("crm_column de Caroline non supprimable par Stéphanie (404)", r.status_code==404, f"(HTTP {r.status_code})")

# event de Caroline (insertion event_log perso)
with session_scope() as s:
    eid=s.execute(text("INSERT INTO event_log (kind,titre,compte_id,lu) VALUES ('systeme','Event Caro',:c,false) RETURNING id"),{"c":cc_id}).scalar(); s.commit()
r=cs.post(f"/events/{eid}/read")
with session_scope() as s:
    lu=s.execute(text("SELECT lu FROM event_log WHERE id=:i"),{"i":eid}).scalar()
chk("event de Caroline non marquable-lu par Stéphanie", lu is False, f"(HTTP {r.status_code}, lu={lu})")
# Caroline le voit dans SA cloche, Stéphanie non
ev_c=cc.get("/events").json()
ev_s=cs.get("/events").json()
def ids(j): 
    it=j.get("items",[]) if isinstance(j,dict) else j
    return [e.get("id") for e in it] if isinstance(it,list) else []
chk("event de Caroline visible par Caroline seule", eid in ids(ev_c) and eid not in ids(ev_s), f"(caro={eid in ids(ev_c)}, steph={eid in ids(ev_s)})")

with session_scope() as s:
    s.execute(text("DELETE FROM event_log WHERE id=:i"),{"i":eid})
    for e in (S,C):
        try: comptes.supprimer_utilisateur(s,e)
        except: pass
    s.commit()
f=[n for n,c in res if not c]
print(f"\n=== {len(res)} vérifs · {len(f)} FUITE(S) ===")
import sys; sys.exit(0 if not f else 2)
