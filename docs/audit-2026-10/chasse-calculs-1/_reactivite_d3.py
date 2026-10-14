"""CHASSE-CALCULS-1 — D3 : réactivité des exports à un changement de donnée.
La modification est faite dans une TRANSACTION ANNULÉE (rollback) : le `get_db` de l'app est
surchargé pour pointer sur une session liée à une connexion dont la transaction n'est JAMAIS
commitée. Aucune écriture durable. On regénère fiche + Dossier et on regarde ce qui bouge.
    LABUSE_DATABASE_URL=... PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/_reactivite_d3.py
"""
import json, subprocess, tempfile, os, re
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from labuse import db as dbmod
from labuse.api import auth
import labuse.api.app as A
from labuse.api.app import app, get_db
from labuse.api.protection import HOTE_INTERNE

IDU = "97412000BV0419"   # St-Joseph U2, constructible, contenance 2983

conn = dbmod.engine().connect()
trans = conn.begin()                       # transaction qui sera ROLLBACK
sess = Session(bind=conn)
app.dependency_overrides[get_db] = lambda: (yield sess)

C = TestClient(app, client=(HOTE_INTERNE, 0)); C.cookies.set(auth.COOKIE, auth.make_token())

def pdfsurf(idu):
    r = C.get(f"/dossier/{idu}.pdf")
    if r.status_code != 200: return f"HTTP{r.status_code}"
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f: f.write(r.content); p=f.name
    try:
        t = subprocess.run(["pdftotext",p,"-"],capture_output=True,timeout=60).stdout.decode("utf-8","replace")
    finally: os.unlink(p)
    m = re.findall(r'([0-9][0-9  ]{1,8}) m²', t)
    return [x.strip() for x in m[:6]]

def fiche():
    f = json.loads(C.get(f"/parcels/{IDU}").content)
    return f.get("surface_terrain_m2"), (f.get("potentiel_transformation") or {}).get("sdp_residuelle_m2")

try:
    base = sess.execute(text("SELECT round(contenance_m2) FROM parcels WHERE idu=:i"),{"i":IDU}).scalar()
    print(f"contenance base = {base} m²")
    A._FICHE_CACHE.clear()
    s0, sdp0 = fiche(); d0 = pdfsurf(IDU)
    print(f"[avant]      fiche surface={s0}  SDP(run)={sdp0}  Dossier m²={d0}")

    sess.execute(text("UPDATE parcels SET contenance_m2 = contenance_m2 + 10000 WHERE idu=:i"),{"i":IDU})
    print(f"→ UPDATE contenance +10000 (dans la transaction, non commitée)")

    # (a) SANS vider le cache de fiche
    s1, sdp1 = fiche()
    print(f"[après/cache] fiche surface={s1}  SDP={sdp1}   (cache non vidé)")
    # (b) EN vidant le cache (chemin lecture vive)
    A._FICHE_CACHE.clear()
    s2, sdp2 = fiche(); d2 = pdfsurf(IDU)
    print(f"[après/vif]   fiche surface={s2}  SDP(run)={sdp2}  Dossier m²={d2}")

    print("\nVERDICT :")
    print(f"  surface terrain : avant {s0} → après(vif) {s2}  → {'RÉAGIT' if s2!=s0 else 'NE BOUGE PAS'}")
    print(f"  cache fiche     : après(cache non vidé) {s1}  → {'STALE (sert avant)' if s1==s0 else 'réagit'}")
    print(f"  SDP/faisabilité : avant {sdp0} → après {sdp2}  → {'RÉAGIT' if sdp2!=sdp0 else 'NE BOUGE PAS (run gelé parcel_residuel)'}")
    print(f"  Dossier m²      : avant {d0} → après {d2}")
finally:
    trans.rollback(); conn.close()
    app.dependency_overrides.clear()
    chk = dbmod.engine().connect().execute(text("SELECT round(contenance_m2) FROM parcels WHERE idu=:i"),{"i":IDU}).scalar()
    print(f"\nrollback OK — contenance en base = {chk} m² (doit = {base})")
