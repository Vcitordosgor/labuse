"""REVUE · R5 — baseline p50/p95 des familles de routes (patron LOT AM). Mesure in-process
(TestClient) : warmup puis N mesures par route, sur la base servie q_v11_m137. Aucune écriture.
"""
import os, time, statistics, json
os.environ["LABUSE_DATABASE_URL"] = "postgresql+psycopg://openclaw@localhost:5432/labuse"
os.environ["LABUSE_DEV_MODE"] = "1"
from fastapi.testclient import TestClient
from sqlalchemy import text
from labuse.api.app import app
from labuse.db import engine

c = TestClient(app, base_url="http://testserver")
with engine().begin() as e:
    idu = e.execute(text("SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id='q_v11_m137' "
                         "AND tier='brulante' LIMIT 1")).scalar()

# familles de routes (GET) — représentatives du chemin client
ROUTES = [
    ("fiche", f"/parcels/{idu}"),
    ("v2_score", f"/v2/score/{idu}"),
    ("fiche_explain", f"/parcels/{idu}/explain"),
    ("faisabilite", f"/modules/faisabilite/{idu}"),
    ("carte_geojson_commune", "/map/parcels.geojson?commune=Saint-Paul"),
    ("tiles_meta", "/map/tiles/meta"),
    ("stats_entonnoir", "/stats/entonnoir"),
    ("communes", "/communes"),
    ("filtre_compteur", "/filtre?communes=Saint-Paul"),
    ("readyz", "/readyz"),
    ("accueil_chiffres", "/accueil/chiffres"),
    ("sources", "/sources"),
]
N = 12
print(f"idu de test = {idu} · N={N} mesures/route\n")
print(f"{'route':26} {'p50 ms':>9} {'p95 ms':>9} {'max ms':>9}  code")
results = {}
for nom, url in ROUTES:
    c.get(url)  # warmup
    ts = []
    code = None
    for _ in range(N):
        t0 = time.perf_counter()
        r = c.get(url)
        ts.append((time.perf_counter() - t0) * 1000)
        code = r.status_code
    ts.sort()
    p50 = statistics.median(ts)
    p95 = ts[int(len(ts) * 0.95) - 1]
    results[nom] = {"p50": round(p50, 1), "p95": round(p95, 1), "max": round(max(ts), 1), "code": code}
    print(f"{nom:26} {p50:9.1f} {p95:9.1f} {max(ts):9.1f}  {code}")

pires = sorted(results.items(), key=lambda kv: -kv[1]["p95"])[:10]
print("\n=== 10 PIRES (p95) ===")
for nom, m in pires:
    print(f"  {nom:26} p95={m['p95']} ms")
import pathlib
pathlib.Path("qa/revue/r5_baseline.json").write_text(json.dumps(results, indent=2))
