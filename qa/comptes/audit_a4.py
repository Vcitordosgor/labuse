"""AUDIT COMPTES · A4 — le 403 admin tient-il sur TOUTES les routes /admin/* ?
Balaye les 22 routes admin depuis (a) un compte CLIENT (role titulaire) → attendu 403,
(b) un NON-CONNECTÉ → attendu 401/403/redirect (jamais 200). Une route admin qui répond
< 400 à un client ou un anonyme = 🔴.
"""
import os, json, uuid
from pathlib import Path
os.environ["LABUSE_ENV"]="pilot"; os.environ["LABUSE_AUTH_PASSWORD"]="pilote-audit-a4"
os.environ["LABUSE_SECRET_KEY"]="secret-audit-a4-0000000000000000000000"
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

C=f"client-{uuid.uuid4().hex[:8]}@audit-test.re"
def compte(e):
    with session_scope() as s:
        try: comptes.supprimer_utilisateur(s,e)
        except: pass
        inv=comptes.creer_invitation(s,e,nom="[AUDIT-TEST] Client A4")
        comptes.activer_par_invitation(s,inv["lien"].split("token=")[1],"motdepasse-audit-a4","2026-07-22")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"),{"c":inv["compte_id"]}); s.commit()
        return inv["compte_id"]
cid=compte(C)
client=TestClient(app,base_url="https://testserver")
assert client.post("/login",data={"identifiant":C,"password":"motdepasse-audit-a4"},follow_redirects=False).status_code==303
anon=TestClient(app,base_url="https://testserver")  # jamais loggé

routes=[(m.upper(),p) for p,ms in json.loads(Path("qa/comptes/openapi_snapshot.json").read_text())["paths"].items()
        for m in ms if "/admin" in p and m in ("get","post","patch","delete","put")]
def sub(p):
    return (p.replace("{compte_id}",str(cid)).replace("{retour_id}","999999")
            .replace("{source_id}","999999").replace("{demande_id}","999999")
            .replace("{sujet}","x").replace("{permit_id}","999999"))
def call(c,m,p):
    p=sub(p)
    try:
        r=getattr(c,m.lower())(p) if m in ("GET","DELETE") else getattr(c,m.lower())(p,json={})
        return r.status_code
    except Exception as e: return -1

rows=[]; fuites=[]
for m,p in sorted(routes,key=lambda x:x[1]):
    cc=call(client,m,p); ca=call(anon,m,p)
    ok_client = cc in (403,) 
    ok_anon = ca in (401,403,302,303,307)
    if not ok_client: fuites.append(("CLIENT",m,p,cc))
    if not ok_anon: fuites.append(("ANON",m,p,ca))
    rows.append({"method":m,"route":p,"client":cc,"anon":ca,
                 "verdict":"OK" if (ok_client and ok_anon) else "🔴"})
    flag = "✓" if (ok_client and ok_anon) else "🔴"
    print(f"  {flag}  {m:6} {p:48} client={cc} anon={ca}")

Path("qa/comptes/out").mkdir(exist_ok=True)
Path("qa/comptes/out/a4_admin.json").write_text(json.dumps({"rows":rows,"fuites":fuites},indent=2,ensure_ascii=False))
print(f"\n{len(routes)} routes admin · {len(fuites)} accès anormal(aux)")
for f in fuites: print("  🔴",f)
with session_scope() as s:
    try: comptes.supprimer_utilisateur(s,C)
    except: pass
    s.commit()
import sys; sys.exit(0 if not fuites else 2)
