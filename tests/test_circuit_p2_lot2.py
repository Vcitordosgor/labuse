"""CIRCUIT-P2 lot 2 — les nombres. Une seule fonction `compteurs()` (partition exacte des
réservoirs), et la cohérence Résumé ↔ Circuit : toute ligne du Résumé pointe des éléments « à
regarder », et tout élément « à regarder » a sa ligne."""
from __future__ import annotations

import pytest

from labuse import circuit_etats as E
from labuse import circuit_resume as R


# ── 2.2 — la partition des réservoirs est exacte : a_jour + a_regarder + vides = réservoirs ────
def _res(etat):
    return {"id": id(etat), "nom": "r", "etat": list(etat)}


def test_partition_somme_egale_total():
    reservoirs = [
        _res(("mint", "à jour")), _res(("mint", "à jour")),
        _res(("ambre", "jamais vérifié")), _res(("rouge", "en quarantaine")),
        _res(("mauve", "agent en route")), _res(("gris", "vide")), _res(("gris", "dépôt manuel")),
    ]
    c = E.compteurs(reservoirs, [])
    assert c["reservoirs"] == 7
    assert c["a_jour"] == 2 and c["a_regarder"] == 3 and c["vides"] == 2
    assert c["a_jour"] + c["a_regarder"] + c["vides"] == c["reservoirs"]


def test_compteurs_robinets():
    robinets = [
        {"id": "a", "etat": ["mint", "cohérent"]},
        {"id": "b", "etat": ["ambre", "eau ancienne"]},
        {"id": "c", "etat": ["gris", "choix à confirmer"]},   # gris MAIS ko (à trancher)
        {"id": "d", "etat": ["gris", "aucun chiffre"]},
    ]
    c = E.compteurs([], robinets)
    assert c["robinets"] == 4 and c["robinets_a_regarder"] == 2  # b (eau) + c (choix)
    assert c["robinets_coherents"] == 2


# NB : le test de RÉCIPROCITÉ Résumé ↔ Circuit (règle 2.4) a été REFAIT pour de bon en P3 — il part
# des tables (`circuit_ecarts`, `circuit_eau_ancienne`, registre) et exige l'égalité stricte avec
# `/admin/circuit` : voir tests/test_circuit_p3_lot2.py. L'ancien test synthétique (qui validait des
# états posés à la main, pas les vraies sources) est supprimé, pas ajusté.


def test_kpis_lus_des_compteurs():
    reservoirs = [
        {"id": 1, "nom": "a", "etat": ["mint", "à jour"]},
        {"id": 2, "nom": "b", "etat": ["ambre", "jamais vérifié"]},
    ]
    robinets = [
        {"id": "r1", "etat": ["mint", "cohérent"]},
        {"id": "r2", "etat": ["ambre", "eau ancienne"]},
    ]
    cpt = {**E.compteurs(reservoirs, robinets), "chiffres": 5}
    resume = R.composer(reservoirs, robinets, compteurs=cpt, residuel=None,
                        run_servi="q1", candidat=None)
    k0, k1 = resume["kpis"][0], resume["kpis"][1]
    assert k0["valeur"] == cpt["a_jour"] and k0["sur"] == cpt["reservoirs"]
    assert k0["detail"] == "compteur"                       # le repère est cliquable
    assert k1["valeur"] == cpt["robinets_coherents"] and k1["sur"] == cpt["robinets"]


# ── 2.2 (DB) — la page de détail du compteur : partition + non servies, un seul nombre ────────
@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


@pytest.mark.db
def test_endpoint_compteur(client, engine):
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    with engine.begin() as c:
        appliquer_modes_cadences(c)
    circ = client.get("/admin/circuit").json()
    d = client.get("/admin/circuit/compteur").json()
    cpt = d["compteurs"]
    # même nombre de réservoirs partout (règle 2.2)
    assert cpt["reservoirs"] == circ["compteurs"]["reservoirs"] == len(circ["reservoirs"])
    # invariant de partition
    assert cpt["a_jour"] + cpt["a_regarder"] + cpt["vides"] == cpt["reservoirs"]
    # les trois blocs recomposent le total, chaque réservoir une seule fois
    total_blocs = sum(len(g["reservoirs"]) for g in d["groupes"])
    assert total_blocs == cpt["reservoirs"]
    # la définition « à jour et vérifiés » est présente (règle 2.3)
    assert "sentinelle" in d["definition"] and "cadence" in d["definition"]
    # les lignes non servies existent et ne sont pas des réservoirs servis
    servis = {r["id"] for r in circ["reservoirs"]}
    for n in d["non_servies"]:
        assert n["id"] not in servis and n["raison"]
