"""AUDIT COMPTES · A2 (ciblé) — lève les ambiguïtés du balayage :
1. les DELETE idempotents (200 {ok:false}) : vérifier qu'ils ne suppriment PAS l'objet de l'autre ;
2. les 422 (payload vide) : rejouer avec un payload VALIDE et confirmer le 404 de cloison ;
3. les routes admin dans la liste : confirmer 403 depuis un client.
Un objet RÉEL de Caroline est créé pour chaque cas, on vérifie qu'il SURVIT à l'attaque.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

os.environ["LABUSE_ENV"] = "pilot"
os.environ["LABUSE_AUTH_PASSWORD"] = "pilote-audit-a2"
os.environ["LABUSE_SECRET_KEY"] = "secret-audit-a2-0000000000000000000000"
_app_url = "postgresql+psycopg://openclaw@localhost:5432/labuse"
for _l in (Path(__file__).resolve().parents[2] / ".env").read_text().splitlines():
    if _l.startswith("LABUSE_DATABASE_URL="):
        _app_url = _l.split("=", 1)[1].strip()
os.environ["LABUSE_DATABASE_URL"] = os.environ.get("LABUSE_TEST_DATABASE_URL") or (_app_url.rsplit("/", 1)[0] + "/labuse_test")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from labuse import comptes, config  # noqa: E402
from labuse.db import session_scope  # noqa: E402
config.get_settings.cache_clear()
from labuse.api.app import app  # noqa: E402

STEPH = f"stephanie-{uuid.uuid4().hex[:8]}@audit-test.re"
CARO = f"caroline-{uuid.uuid4().hex[:8]}@audit-test.re"
IDU = f"974AUD{uuid.uuid4().hex[:5].upper()}C"
WKT = "POLYGON((55.46 -20.92,55.461 -20.92,55.461 -20.921,55.46 -20.921,55.46 -20.92))"


def compte(email, nom):
    with session_scope() as s:
        try: comptes.supprimer_utilisateur(s, email)
        except Exception: pass
        inv = comptes.creer_invitation(s, email, nom=f"[AUDIT-TEST] {nom}")
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-audit-a2", "2026-07-22")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def login(email):
    c = TestClient(app, base_url="https://testserver")
    assert c.post("/login", data={"identifiant": email, "password": "motdepasse-audit-a2"}, follow_redirects=False).status_code == 303
    return c


results = []
def check(nom, cond, detail=""):
    results.append((nom, cond, detail))
    print(f"  {'✓' if cond else '🔴 FUITE'}  {nom}  {detail}")


cid_s = compte(STEPH, "Stéphanie")
cid_c = compte(CARO, "Caroline")
with session_scope() as s:
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox)"
        " VALUES (:i,'Saint-Denis','ZA','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975),"
        " 900, ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) ON CONFLICT (idu) DO NOTHING"),
        {"i": IDU, "w": WKT}); s.commit()
cs, cc = login(STEPH), login(CARO)

# 1. VEILLE réelle de Caroline (insertion via le module, type évaluable) → Stéphanie DELETE
with session_scope() as s:
    from labuse.copilote_v2 import veilles
    v = veilles.creer(s, compte_id=cid_c, type_="permis", commune="Saint-Denis"); s.commit()
    vid = v["id"]
r = cs.delete(f"/api/copilote-v2/veilles/{vid}")
supprime_par_steph = r.status_code == 200 and r.json().get("ok") is True
with session_scope() as s:
    survit = s.execute(text("SELECT actif FROM veilles WHERE id=:i"), {"i": vid}).scalar()
check("copilote-v2 veille de Caroline NON supprimable par Stéphanie",
      (not supprime_par_steph) and survit is True, f"(HTTP {r.status_code} ok={r.json().get('ok')}, veille.actif={survit})")
# et Caroline, elle, la supprime bien
rc = cc.delete(f"/api/copilote-v2/veilles/{vid}")
check("copilote-v2 Caroline supprime SA veille", rc.status_code == 200 and rc.json().get("ok") is True, f"(HTTP {rc.status_code})")

# 2. Objets réels de Caroline pour les routes 422 → rejouées avec payload VALIDE
proj = cc.post("/projets", json={"nom": f"Caro {uuid.uuid4().hex[:6]}", "cadrage": {"communes": ["Saint-Denis"]}}).json()["projet"]["id"]
zone = cc.post("/watch-zones", json={"name": "Zone Caro", "geometry": {"type": "Polygon", "coordinates": [[[55.46, -20.92], [55.47, -20.92], [55.47, -20.93], [55.46, -20.92]]]}}).json()
zone_id = zone.get("id") or (zone.get("zone") or {}).get("id")

# watch-zones PATCH payload valide
r = cs.patch(f"/watch-zones/{zone_id}", json={"name": "VOL par Stéphanie"})
check("watch-zones PATCH (payload valide) cloisonné", r.status_code in (403, 404), f"(HTTP {r.status_code})")
# projets/{pid}/ajouter payload valide
r = cs.post(f"/projets/{proj}/ajouter", json={"idu": IDU})
check("projets/ajouter (payload valide) cloisonné", r.status_code in (403, 404), f"(HTTP {r.status_code})")
# projets/{pid}/parcelle/{idu} PATCH payload valide
r = cs.patch(f"/projets/{proj}/parcelle/{IDU}", json={"statut": "retenue"})
check("projets/parcelle PATCH (payload valide) cloisonné", r.status_code in (403, 404), f"(HTTP {r.status_code})")
# projets/{pid}/proposer, /derive
r = cs.post(f"/projets/{proj}/proposer", json={})
check("projets/proposer cloisonné", r.status_code in (403, 404, 422), f"(HTTP {r.status_code})")

# 3. courrier/admin/demandes/{id}/statut → route ADMIN, 403 depuis un client
dem = cc.post("/courrier/demande", json={"parcelles": [IDU], "communes": "Saint-Denis", "modele": "standard", "corps": "Caro courrier."}).json()
dem_id = dem.get("id")
r = cs.post(f"/courrier/admin/demandes/{dem_id}/statut", json={"statut": "imprime"})
check("courrier/admin/statut refuse un client (403)", r.status_code == 403, f"(HTTP {r.status_code})")
# et la demande de Caroline n'a pas bougé
with session_scope() as s:
    st = s.execute(text("SELECT statut FROM courrier_demandes WHERE id=:i"), {"i": dem_id}).scalar()
check("demande courrier de Caroline intacte", st == "demande", f"(statut={st})")

# 4. Caroline retrouve TOUS ses objets (non-sur-filtrage)
projs = cc.get("/projets").json()
check("non-sur-filtrage : Caroline voit SON projet", any(p["id"] == proj for p in projs), f"({len(projs)} projets)")

fuites = [n for n, c, _ in results if not c]
print(f"\n=== {len(results)} vérifications · {len(fuites)} FUITE(S) ===")
for n in fuites:
    print("  🔴", n)

# purge
with session_scope() as s:
    for e in (STEPH, CARO):
        try: comptes.supprimer_utilisateur(s, e)
        except Exception: pass
    s.execute(text("DELETE FROM parcels WHERE idu=:i"), {"i": IDU}); s.commit()

import sys
sys.exit(0 if not fuites else 2)
