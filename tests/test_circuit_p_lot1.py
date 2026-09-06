"""CIRCUIT-P lot 1 — la fonction d'état unique, le résumé composé côté serveur, les endpoints
détail + journal. La maquette v8 (tankEtat/tapEtat) est la spécification des états."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import circuit_etats as E
from labuse import circuit_resume as R


# ── 1.4 — l'état d'un réservoir : un cas par branche de la maquette ──────────────────────────
@pytest.mark.parametrize("r,attendu", [
    ({"filtre": {"verdict": "quarantaine"}}, ("rouge", "en quarantaine")),
    ({"horloge_ment": True}, ("rouge", "horloge qui ment")),
    ({"mode": "absente"}, ("gris", "vide")),
    ({"veille": {"statut": "nouvelle_version"}}, ("ambre", "nouvelle version à injecter")),
    ({"veille": {"statut": "ok"}, "agent_en_cours": True}, ("mauve", "agent en route")),
    ({"veille": {"statut": "ok"}, "filtre": {"verdict": "avertissements"}},
     ("ambre", "filtre avec des KO")),
    ({}, ("ambre", "jamais vérifié")),
    ({"veille": {"statut": "ok"}, "a_verifier": True}, ("ambre", "à vérifier")),
    ({"veille": {"statut": "injoignable"}}, ("ambre", "producteur injoignable")),
    ({"veille": {"statut": "ok"}, "mode": "depot_manuel"}, ("gris", "dépôt manuel")),
    ({"veille": {"statut": "ok"}}, ("mint", "à jour")),
])
def test_etat_reservoir(r, attendu):
    assert E.etat_reservoir(r) == attendu


# ── 1.4 — l'état d'un robinet ────────────────────────────────────────────────────────────────
def _ctx(**kw):
    base = {"fuite_robinets": set(), "eau_ancienne_robinets": set(),
            "ecart_regle_robinets": set(), "choix_robinets": set(), "chiffres": {}}
    base.update(kw)
    return base


def test_etat_robinet_fuite():
    assert E.etat_robinet({"id": "x", "chiffres": ["a"]},
                          _ctx(fuite_robinets={"x"})) == ("rouge", "fuite mesurée")


def test_etat_robinet_eau_ancienne():
    assert E.etat_robinet({"id": "x", "chiffres": ["a"]},
                          _ctx(eau_ancienne_robinets={"x"})) == ("ambre", "eau ancienne")


def test_etat_robinet_ecart_regle():
    assert E.etat_robinet({"id": "x", "chiffres": ["a"]},
                          _ctx(ecart_regle_robinets={"x"})) == ("rouge", "écart à la règle")


def test_etat_robinet_hors_moteur():
    ctx = _ctx(chiffres={"a": {"calcul": "passe_plat"}, "b": {"calcul": "moteur"}})
    assert E.etat_robinet({"id": "x", "chiffres": ["a", "b"]}, ctx) == ("ambre", "1 hors moteur")


def test_etat_robinet_choix():
    ctx = _ctx(chiffres={"a": {"calcul": "moteur"}}, choix_robinets={"x"})
    assert E.etat_robinet({"id": "x", "chiffres": ["a"]}, ctx) == ("gris", "choix à confirmer")


def test_etat_robinet_aucun_chiffre():
    assert E.etat_robinet({"id": "x", "chiffres": []}, _ctx()) == ("gris", "aucun chiffre")


def test_etat_robinet_coherent():
    ctx = _ctx(chiffres={"a": {"calcul": "moteur"}})
    assert E.etat_robinet({"id": "x", "chiffres": ["a"]}, ctx) == ("mint", "cohérent")


def test_familles_categories_affichage():
    assert E.famille_affichage("cadastre") == "Parcelles et propriété"
    assert E.famille_affichage(None) == "Voulues, absentes"          # « aucune »
    assert E.categorie_affichage("fond") == "Fonds de carte"
    assert E.slug_reservoir("SITADEL (autorisations d'urbanisme)") == "sitadel"
    assert E.slug_reservoir("inconnu") is None


# ── 1.1 — le résumé : zéro problème → « Tout coule. » et chaque ligne rend son verbe ──────────
def test_resume_tout_coule():
    res = R.composer([{"id": 1, "nom": "x", "etat": ["mint", "à jour"], "veille": {"statut": "ok"}}],
                     [{"id": "r", "etat": ["mint", "cohérent"], "chiffres": ["a"]}],
                     compteurs={"chiffres": 1}, residuel={"changees": False}, run_servi="q_v11",
                     candidat=None, fuites=[], eau_ancienne=[])
    assert res["total"] == 0
    assert all(g["lignes"] == [] for g in res["groupes"])
    assert res["kpis"][0]["valeur"] == 1 and res["kpis"][3]["valeur"] == "q_v11"


def _lignes(res):
    return {li["titre"]: li for g in res["groupes"] for li in g["lignes"]}


def test_resume_une_ligne_par_type():
    reservoirs = [
        {"id": 1, "nom": "Q", "etat": ["rouge", "en quarantaine"], "filtre": {"verdict": "quarantaine"}},
        {"id": 2, "nom": "N", "etat": ["ambre", "nouvelle version à injecter"],
         "veille": {"statut": "nouvelle_version"}},
        {"id": 3, "nom": "J", "etat": ["ambre", "jamais vérifié"]},
        {"id": 4, "nom": "V", "etat": ["ambre", "à vérifier"], "veille": {"statut": "ok"},
         "a_verifier": True},
        {"id": 5, "nom": "W", "etat": ["ambre", "filtre avec des KO"], "veille": {"statut": "ok"},
         "filtre": {"verdict": "avertissements"}},
        {"id": 6, "nom": "C", "etat": ["gris", "à jour"], "veille": {"statut": "ok"},
         "cadence_statut": "proposee"},
    ]
    robinets = [
        {"id": "rf", "etat": ["rouge", "fuite mesurée"], "chiffres": ["c1"], "hors_moteur": 0},
        {"id": "rh", "etat": ["ambre", "1 hors moteur"], "chiffres": ["c2"], "hors_moteur": 1},
    ]
    res = R.composer(
        reservoirs, robinets, compteurs={"chiffres": 2},
        residuel={"changees": True, "detail": "2 entrées"}, run_servi="q_v11", candidat="q_v12",
        fuites=[{"robinet_a": "rf", "robinet_b": None}],
        eau_ancienne=[{"robinet": "re", "statut": "ouvert"}],
        regles_ecart=["rf"], regles_choix=["rc"], horloges=[3])
    L = _lignes(res)
    # groupe 1
    assert L["version en quarantaine"]["verbe"] == "Décider" and L["version en quarantaine"]["couleur"] == "rouge"
    assert L["version en quarantaine"]["cible"] == {"type": "reservoir", "ids": [1]}
    assert L["réservoir plein, à injecter"]["verbe"] == "Injecter"
    assert L["eau nouvelle dans la pompe"]["verbe"] == "Calculer" and L["eau nouvelle dans la pompe"]["cible"]["type"] == "pompe"
    assert L["robinets servent de l'eau ancienne"]["cible"]["ids"] == ["re"]
    assert L["réservoirs jamais vérifiés"]["verbe"] == "Envoyer les agents"
    assert L["réservoirs à revérifier"]["verbe"] == "Vérifier" and L["réservoirs à revérifier"]["cible"]["ids"] == [4]
    # groupe 2
    assert L["fuites mesurées"]["couleur"] == "rouge" and L["fuites mesurées"]["cible"]["ids"] == ["rf"]
    assert L["écarts à la règle"]["cible"]["ids"] == ["rf"]
    assert L["horloge qui ment"]["cible"]["ids"] == [3]
    assert L["filtres passés avec des KO"]["cible"]["ids"] == [5]
    assert L["affichages calculés hors moteur"]["cible"]["ids"] == ["rh"]
    # groupe 3
    assert L["choix LABUSE à confirmer"]["couleur"] == "gris" and L["choix LABUSE à confirmer"]["cible"]["ids"] == ["rc"]
    assert L["cadences proposées à valider"]["cible"]["ids"] == [6]
    # les trois groupes dans l'ordre
    assert [g["titre"] for g in res["groupes"]] == [
        "À faire, un geste de toi", "À corriger, un mandat pour CC", "À décider, quand tu veux"]


# ── 1.1 / 1.2 / 1.3 — les endpoints, sur la base réelle ──────────────────────────────────────
pytestmark_db = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


@pytest.mark.db
def test_circuit_enrichi_resume_familles_etat(client, engine):
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    with engine.begin() as c:
        appliquer_modes_cadences(c)
    d = client.get("/admin/circuit").json()
    assert {"resume", "familles", "categories", "candidat"} <= set(d)
    # résumé : trois groupes ordonnés + quatre repères
    assert [g["titre"] for g in d["resume"]["groupes"]] == [
        "À faire, un geste de toi", "À corriger, un mandat pour CC", "À décider, quand tu veux"]
    assert len(d["resume"]["kpis"]) == 4
    # familles : ordonnées, sous-ensemble de l'ordre déclaré
    noms = [f["nom"] for f in d["familles"]]
    connues = [n for n in noms if n in E.FAMILLES_ORDRE]
    assert connues == [n for n in E.FAMILLES_ORDRE if n in noms]
    # chaque réservoir porte son état + son slug + ce qu'il alimente
    for r in d["reservoirs"]:
        assert isinstance(r["etat"], list) and len(r["etat"]) == 2
        assert r["etat"][0] in ("mint", "ambre", "rouge", "gris", "mauve")
        assert "slug" in r and "taps" in r
    for rb in d["robinets"]:
        assert rb["etat"][0] in ("mint", "ambre", "rouge", "gris", "mauve")
        assert "hors_moteur" in rb
    # les catégories d'affichage sont les 12 du registre
    assert {c["slug"] for c in d["categories"]} <= {s for s, _ in E.CATEGORIES_ORDRE}


@pytest.mark.db
def test_journal_filtrable_pagine(client):
    d = client.get("/admin/circuit/journal?taille=5").json()
    assert {"entrees", "page", "taille", "total", "aujourdhui", "gestes"} <= set(d)
    assert d["taille"] == 5
    for e in d["entrees"]:
        assert e["par"]  # le « qui » toujours présent


@pytest.mark.db
def test_detail_reservoir_robinet_pompe_rapides(client, engine):
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    with engine.begin() as c:
        appliquer_modes_cadences(c)
    d = client.get("/admin/circuit").json()
    sid = d["reservoirs"][0]["id"]
    rid = d["robinets"][0]["id"]

    t0 = time.perf_counter()
    rv = client.get(f"/admin/circuit/reservoir/{sid}").json()
    dt_res = time.perf_counter() - t0
    assert rv["reservoir"]["id"] == sid and "alimente" in rv and "chiffres" in rv

    t0 = time.perf_counter()
    rb = client.get(f"/admin/circuit/robinet/{rid}").json()
    dt_rob = time.perf_counter() - t0
    assert rb["robinet"]["id"] == rid and "amont" in rb and "chiffres" in rb

    t0 = time.perf_counter()
    pp = client.get("/admin/circuit/pompe").json()
    dt_pp = time.perf_counter() - t0
    assert pp["run_servi"] and len(pp["jobs_eau"]) == 13 and pp["n_moteurs"] >= 1

    # 1.3 — un appel chacun, < 500 ms sur la base réelle
    assert dt_res < 0.5 and dt_rob < 0.5 and dt_pp < 0.5


@pytest.mark.db
def test_detail_reservoir_404(client):
    r = client.get("/admin/circuit/reservoir/99999999")
    assert r.status_code == 404
