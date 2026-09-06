"""CIRCUIT-P2 lot 5.2 — le tour de TOUS les endpoints de la page Circuit : /admin/circuit, le
détail du compteur, le journal, la pompe, les tâches, ET la page de détail de CHAQUE réservoir et
de CHAQUE robinet. Chacun doit répondre 200, sans erreur, en moins d'une seconde."""
from __future__ import annotations

import time

import pytest


@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


@pytest.fixture
def seed(engine):
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    with engine.begin() as c:
        appliquer_modes_cadences(c)


def _mesurer(client, url: str) -> float:
    t0 = time.perf_counter()
    r = client.get(url)
    dt = time.perf_counter() - t0
    assert r.status_code == 200, f"{url} → {r.status_code}"
    assert dt < 1.0, f"{url} a mis {dt:.2f}s (> 1 s)"
    return dt


@pytest.mark.db
def test_tour_complet_des_endpoints(client, seed):
    # les endpoints d'agrégat
    for url in ("/admin/circuit", "/admin/circuit/compteur", "/admin/circuit/journal",
                "/admin/circuit/pompe", "/admin/circuit/taches"):
        _mesurer(client, url)

    circ = client.get("/admin/circuit").json()
    reservoirs = circ["reservoirs"]
    robinets = circ["robinets"]
    # un vrai parc (les 68 réservoirs, les 130 robinets en prod ; ici la base de test)
    assert len(reservoirs) >= 60 and len(robinets) >= 120

    # la page de détail de CHAQUE réservoir
    for r in reservoirs:
        _mesurer(client, f"/admin/circuit/reservoir/{r['id']}")
    # la page de détail de CHAQUE robinet
    for rb in robinets:
        _mesurer(client, f"/admin/circuit/robinet/{rb['id']}")


@pytest.mark.db
def test_un_seul_nombre_de_reservoirs_partout(client, seed):
    """CIRCUIT-P2 (lot 2.2) — le même nombre de réservoirs dans /admin/circuit et /compteur."""
    circ = client.get("/admin/circuit").json()
    cpt = client.get("/admin/circuit/compteur").json()
    n = circ["compteurs"]["reservoirs"]
    assert n == len(circ["reservoirs"]) == cpt["compteurs"]["reservoirs"]
    assert circ["resume"]["kpis"][0]["sur"] == n           # le repère du Résumé lit le même nombre
