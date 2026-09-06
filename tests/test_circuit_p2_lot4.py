"""CIRCUIT-P2 lot 4 — le journal lisible : passages groupés sur une ligne dépliable, cibles par
nom affiché, catégories FR en ordre fixe, « par » qui dit un nom, pagination par lignes groupées."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import circuit_journal as J


# ── 4.3 / 4.4 — les mappings purs ─────────────────────────────────────────────────────────────
def test_categories_ordre_fixe():
    slugs = [s for s, _ in J.CATEGORIES]
    assert slugs == ["vanne", "calcul", "bascule", "agent", "controle", "filtre", "sonde", "cron"]


def test_geste_vers_categorie():
    assert J.categorie_de("injecter") == "vanne"
    assert J.categorie_de("calculer") == "calcul"
    assert J.categorie_de("basculer") == "bascule"
    assert J.categorie_de("controle") == "controle"
    assert J.categorie_de("job") == "cron"
    assert set(J.gestes_de_categorie("vanne")) == {"injecter"}


def test_par_nom_jamais_cli_ni_admin():
    assert J.par_nom("cli") == "système"
    assert J.par_nom("admin") == "Vic"
    assert J.par_nom(None) == "système"
    assert J.par_nom("système") == "système"
    assert J.par_nom("ingest-catnat") == "ingest-catnat"
    assert J.par_nom("kampus@labuse.re") == "kampus@labuse.re"


# ── endpoint (DB) ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


@pytest.mark.db
def test_journal_groupe_et_isole(client, engine):
    lot = J.nouveau_lot()          # unique par exécution (le test peut rejouer sur la même base)
    with engine.begin() as c:
        J.ensure(c)
        # un passage groupé de filtres (même lot) sur trois sources, par « cli »
        J.journaliser(c, "filtre", "sitadel", "cli", "ok", {"verdict": "ok"}, lot=lot)
        J.journaliser(c, "filtre", "georisques_mvt", "cli", "refuse", {"verdict": "quarantaine"}, lot=lot)
        J.journaliser(c, "filtre", "dvf", "cli", "ok", {"verdict": "avertissements"}, lot=lot)
        # un geste isolé (pas de lot), par « admin »
        J.journaliser(c, "basculer", "q_v11_m137", "admin", "ok", {})

    d = client.get("/admin/circuit/journal?taille=50").json()
    # la barre de filtres = les catégories FIXES (pas les gestes techniques)
    assert [x["slug"] for x in d["categories"]] == \
        ["vanne", "calcul", "bascule", "agent", "controle", "filtre", "sonde", "cron"]

    par_gk = {e["gk"]: e for e in d["entrees"]}
    grp = par_gk.get(lot)
    assert grp and grp["n"] == 3 and grp["categorie"] == "filtre"
    assert grp["par_nom"] == "système"                 # « cli » → système (jamais « cli »)
    assert grp["verdicts"] == {"ok": 1, "quarantaine": 1, "avertissements": 1}
    assert len(grp["membres"]) == 3
    # chaque membre porte le NOM affiché, pas l'identifiant technique
    noms = {m["cible_nom"] for m in grp["membres"]}
    assert "Géorisques — mouvements de terrain" in noms
    assert "SITADEL (autorisations d'urbanisme)" in noms

    # le geste isolé : une ligne, « admin » → Vic, catégorie « bascule »
    isole = next(e for e in d["entrees"] if e["geste"] == "basculer" and e["n"] == 1)
    assert isole["categorie"] == "bascule" and isole["par_nom"] == "Vic"
    assert isole["membres"] == []


@pytest.mark.db
def test_journal_filtre_par_categorie(client, engine):
    with engine.begin() as c:
        J.ensure(c)
        J.journaliser(c, "injecter", "sitadel", "Vic", "lance", {})
    d = client.get("/admin/circuit/journal?type=vanne&taille=50").json()
    # tous les groupes rendus tombent dans la catégorie « vanne »
    assert all(e["categorie"] == "vanne" for e in d["entrees"])
    assert any(e["geste"] == "injecter" for e in d["entrees"])
