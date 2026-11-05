#!/usr/bin/env python3
"""NU4-E — banc de charge : N clients virtuels « navigateur » pendant D secondes.

Chaque client a son PROPRE httpx.AsyncClient (keep-alive comme un navigateur ; les connexions
TCP se répartissent sur les workers par le noyau). Boucle d'actions pondérées avec temps de
réflexion (think time) humain entre deux actions :
  navigate  : grappe de tuiles MVT (pan/zoom)                      — trafic dominant
  search    : /parcels/search?q=<préfixe commune>
  fiche     : /parcels/{idu} (+ mode-b/zone parfois)
  explain   : /parcels/{idu}/explain (bloc lourd)
  tool      : gabarit.pdf | export.pdf | POST evaluate
  copilote  : POST /parcels/{idu}/ask  (APPEL MODÈLE RÉEL — plafonné globalement, cf. COPILOTE_MAX)

Chaque requête est journalisée (action, endpoint, status, latence) dans un CSV. Lecture seule
côté données (sauf evaluate/ask qui écrivent des compteurs/quotas mineurs — chemin nominal client).

Usage : PY load.py <base> <clients> <duree_s> <out.csv> [copilote_max=24] [seed=0]
"""
import asyncio, csv, os, random, sys, time
import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9670"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 50
DUR = float(sys.argv[3]) if len(sys.argv) > 3 else 1800.0
OUT = sys.argv[4] if len(sys.argv) > 4 else "docs/audit-2026-11/nu-4/E/raw/load.csv"
COPILOTE_MAX = int(sys.argv[5]) if len(sys.argv) > 5 else 24
SEED = int(sys.argv[6]) if len(sys.argv) > 6 else 0

RAW = "docs/audit-2026-11/nu-4/E/raw"
TILES = [l.strip() for l in open(f"{RAW}/tiles.txt") if l.strip()]
WARM = [l.strip() for l in open(f"{RAW}/pool_parcels.txt") if l.strip()]
COLD = [l.strip() for l in open(f"{RAW}/pool_cold_dvf.txt") if l.strip()]
ALL_PARCELS = WARM + COLD
COMMUNES = ["97411", "97412", "97408", "97401", "97402", "97415", "97418", "97421"]

# action weights. MIX=stress (défaut) sur-pondère les endpoints modèle (/explain) pour pousser
# l'occupation des workers ; MIX=real reflète le trafic LIVE (le front n'appelle plus /explain
# depuis M54-EXPO-2 ; seul /ask/Copilote déclenche un appel modèle, et rarement).
_MIX = os.environ.get("LOAD_MIX", "stress")
if _MIX == "real":
    ACTIONS = (["navigate"]*55 + ["search"]*12 + ["fiche"]*25 + ["tool"]*7 + ["copilote"]*1)
else:
    ACTIONS = (["navigate"]*50 + ["search"]*10 + ["fiche"]*25 + ["explain"]*5
               + ["tool"]*8 + ["copilote"]*2)

rows = []           # (t_start, client, action, endpoint, status, latency_ms)
copilote_used = [0]
_lock = asyncio.Lock()
start_wall = [0.0]

async def req(client, cid, method, path, label, action, **kw):
    t = time.perf_counter()
    try:
        r = await client.request(method, f"{BASE}{path}", timeout=120.0, **kw)
        st = r.status_code
    except Exception as e:
        st = f"ERR:{type(e).__name__}"
    dt = (time.perf_counter() - t) * 1000
    rows.append((round(time.perf_counter()-start_wall[0], 2), cid,
                 action, path.split("?")[0], st, round(dt, 1)))
    return st

async def client_loop(cid, rnd):
    limits = httpx.Limits(max_connections=6, max_keepalive_connections=6)
    async with httpx.AsyncClient(limits=limits, follow_redirects=True) as client:
        # each session starts by loading the map meta + a tile cluster
        await req(client, cid, "GET", "/map/tiles/meta", "meta", "navigate")
        while time.perf_counter() - start_wall[0] < DUR:
            act = rnd.choice(ACTIONS)
            if act == "navigate":
                for t in rnd.sample(TILES, rnd.randint(2, 4)):
                    await req(client, cid, "GET", f"/map/tiles/{t}.pbf", "tile", "navigate")
            elif act == "search":
                q = rnd.choice(COMMUNES)
                await req(client, cid, "GET", f"/parcels/search?q={q}", "search", "search")
            elif act == "fiche":
                idu = rnd.choice(ALL_PARCELS)
                await req(client, cid, "GET", f"/parcels/{idu}", "fiche", "fiche")
                if rnd.random() < 0.4:
                    await req(client, cid, "GET", f"/parcels/{idu}/mode-b", "mode-b", "fiche")
            elif act == "explain":
                idu = rnd.choice(ALL_PARCELS)
                await req(client, cid, "GET", f"/parcels/{idu}/explain", "explain", "explain")
            elif act == "tool":
                idu = rnd.choice(WARM)
                pick = rnd.choice(["gabarit", "export", "evaluate"])
                if pick == "gabarit":
                    await req(client, cid, "GET", f"/gabarit/{idu}.pdf", "gabarit.pdf", "tool")
                elif pick == "export":
                    await req(client, cid, "GET", f"/parcels/{idu}/export.pdf", "export.pdf", "tool")
                else:
                    await req(client, cid, "POST", f"/parcels/{idu}/evaluate", "evaluate", "tool",
                              json={})
            elif act == "copilote":
                async with _lock:
                    go = copilote_used[0] < COPILOTE_MAX
                    if go: copilote_used[0] += 1
                if go:
                    idu = rnd.choice(WARM)
                    await req(client, cid, "POST", f"/parcels/{idu}/ask", "ask", "copilote",
                              json={"question": "Cette parcelle est-elle constructible ?"})
            await asyncio.sleep(rnd.uniform(0.5, 3.0))   # think time

async def main():
    start_wall[0] = time.perf_counter()
    rnds = [random.Random(SEED*1000 + i) for i in range(N)]
    await asyncio.gather(*[client_loop(i, rnds[i]) for i in range(N)])
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["t", "client", "action", "endpoint", "status", "ms"])
        w.writerows(rows)
    print(f"done: {len(rows)} requests, copilote={copilote_used[0]}, wrote {OUT}")

asyncio.run(main())
