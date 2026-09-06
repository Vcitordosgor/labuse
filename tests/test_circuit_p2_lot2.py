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


# ── 2.4 — Résumé ↔ Circuit : chaque ligne → des « à regarder », et réciproquement ─────────────
def _reservoir(i, etat, **kw):
    r = {"id": i, "nom": f"res{i}", "etat": list(etat)}
    r.update(kw)
    return r


def _fixture():
    """Des réservoirs couvrant tous les états ko atteignables en live, + des non-ko."""
    reservoirs = [
        _reservoir(1, ("rouge", "en quarantaine"), filtre={"verdict": "quarantaine"}),
        _reservoir(2, ("ambre", "nouvelle version à injecter"),
                   veille={"statut": "nouvelle_version"}),
        _reservoir(3, ("ambre", "jamais vérifié")),                       # pas de veille
        _reservoir(4, ("ambre", "à vérifier"), a_verifier=True, veille={"statut": "ok"}),
        _reservoir(5, ("ambre", "producteur injoignable"), veille={"statut": "injoignable"}),
        _reservoir(6, ("ambre", "filtre avec des KO"), filtre={"verdict": "avertissements"}),
        _reservoir(7, ("mint", "à jour"), veille={"statut": "ok"}),       # non ko
        _reservoir(8, ("gris", "vide"), mode="absente"),                  # non ko
    ]
    robinets = [
        {"id": "rob_fuite", "etat": ["rouge", "fuite mesurée"], "chiffres": ["c1"], "hors_moteur": 0},
        {"id": "rob_eau", "etat": ["ambre", "eau ancienne"], "chiffres": ["c2"], "hors_moteur": 0},
        {"id": "rob_hm", "etat": ["ambre", "1 hors moteur"], "chiffres": ["c3"], "hors_moteur": 1},
        {"id": "rob_choix", "etat": ["gris", "choix à confirmer"], "chiffres": ["c4"], "hors_moteur": 0},
        {"id": "rob_ok", "etat": ["mint", "cohérent"], "chiffres": ["c5"], "hors_moteur": 0},
    ]
    # une fuite mesurée sur un seul robinet (robinet_b absent) — le témoin n'est pas un robinet.
    fuites = [{"chiffre_id": "c1", "robinet_a": "rob_fuite", "robinet_b": None}]
    eau = [{"robinet": "rob_eau", "statut": "ouvert"}]
    return reservoirs, robinets, fuites, eau


def test_resume_circuit_coherents():
    reservoirs, robinets, fuites, eau = _fixture()
    cpt = E.compteurs(reservoirs, robinets)
    cpt["chiffres"] = 5
    resume = R.composer(reservoirs, robinets, compteurs=cpt, residuel=None,
                        run_servi="q1", candidat=None, fuites=fuites, eau_ancienne=eau,
                        regles_choix=["rob_choix"])
    res_par_id = {r["id"]: r for r in reservoirs}
    rob_par_id = {rb["id"]: rb for rb in robinets}

    # forward — chaque id d'une ligne pointe un élément « à regarder »
    cibles_res, cibles_rob = set(), set()
    for g in resume["groupes"]:
        for li in g["lignes"]:
            t, ids = li["cible"]["type"], li["cible"]["ids"]
            for i in ids:
                if t == "reservoir":
                    cibles_res.add(i)
                    assert E.ko_reservoir(*res_par_id[i]["etat"]), f"ligne pointe un réservoir non-ko {i}"
                elif t == "robinet":
                    cibles_rob.add(i)
                    assert E.ko_robinet(*rob_par_id[i]["etat"]), f"ligne pointe un robinet non-ko {i}"

    # backward — chaque élément « à regarder » a une ligne
    for r in reservoirs:
        if E.ko_reservoir(*r["etat"]):
            assert r["id"] in cibles_res, f"réservoir à regarder sans ligne : {r['id']}"
    for rb in robinets:
        if E.ko_robinet(*rb["etat"]):
            assert rb["id"] in cibles_rob, f"robinet à regarder sans ligne : {rb['id']}"


def test_kpis_lus_des_compteurs():
    reservoirs, robinets, fuites, eau = _fixture()
    cpt = E.compteurs(reservoirs, robinets)
    cpt["chiffres"] = 5
    resume = R.composer(reservoirs, robinets, compteurs=cpt, residuel=None,
                        run_servi="q1", candidat=None, fuites=fuites, eau_ancienne=eau)
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
