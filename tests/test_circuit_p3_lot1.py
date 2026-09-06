"""CIRCUIT-P3 lot 1 — le journal. La recette du 06/09 montrait « 0 passage » sur une table de 90
lignes : la base d'avant-P2 n'avait pas la colonne `lot`, la requête `COALESCE(lot,…)` levait, et
l'ancien `except` renvoyait vide. On garantit le schéma dans l'endpoint et on ne masque plus rien."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import circuit_journal as J


@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


# ── 1.2 — l'endpoint rend les lignes, avec le regroupement attendu, sur chaque filtre et « tous » ──
@pytest.mark.db
def test_journal_rend_vanne_lot_bascule(client, engine):
    lot = J.nouveau_lot()
    with engine.begin() as c:
        J.ensure(c)
        J.journaliser(c, "injecter", "sitadel", "Vic", "lance", {})
        for i in range(39):                      # un LOT de filtres sur 39 sources
            J.journaliser(c, "filtre", f"src_{i}", "cron", "ok", {"verdict": "ok"}, lot=lot)
        J.journaliser(c, "basculer", "q_v11_m137", "Vic", "ok", {})

    tous = client.get("/admin/circuit/journal?taille=50").json()
    assert tous["total"] > 0 and tous["entrees"]           # jamais « 0 passage » avec des lignes
    grp = next((e for e in tous["entrees"] if e["gk"] == lot), None)
    assert grp and grp["n"] == 39 and grp["categorie"] == "filtre"   # 39 sources = UNE ligne
    assert any(e["geste"] == "injecter" and e["n"] == 1 for e in tous["entrees"])
    assert any(e["geste"] == "basculer" and e["n"] == 1 for e in tous["entrees"])

    # filtre « vanne » → l'injecter, pas le lot de filtres
    v = client.get("/admin/circuit/journal?type=vanne&taille=50").json()
    assert all(e["categorie"] == "vanne" for e in v["entrees"])
    assert any(e["geste"] == "injecter" for e in v["entrees"])
    # filtre « filtre » → le lot groupé
    f = client.get("/admin/circuit/journal?type=filtre&taille=50").json()
    assert all(e["categorie"] == "filtre" for e in f["entrees"])
    assert next((e for e in f["entrees"] if e["gk"] == lot), None)["n"] == 39


# ── 1.1 / 1.4 — la régression EXACTE : sans colonne `lot`, l'endpoint la rétablit et rend les lignes ──
@pytest.mark.db
def test_journal_self_heal_colonne_lot(client, engine):
    with engine.begin() as c:
        J.ensure(c)
        J.journaliser(c, "injecter", "sitadel", "Vic", "lance", {})
        # on REPRODUIT une base d'avant-P2 : la colonne `lot` n'existe pas
        c.execute(text("ALTER TABLE circuit_journal DROP COLUMN IF EXISTS lot"))
    d = client.get("/admin/circuit/journal?taille=50").json()
    # l'endpoint a ré-ajouté la colonne (ensure) et rend les lignes — jamais « 0 passage »
    assert d["total"] > 0 and len(d["entrees"]) > 0
    with engine.begin() as c:
        assert c.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name='circuit_journal'"
            " AND column_name='lot'")).scalar() == 1


# ── 1.3 — aucun filtre de date par défaut : une entrée d'il y a un an sort quand même ──
@pytest.mark.db
def test_journal_sans_filtre_date(client, engine):
    with engine.begin() as c:
        J.ensure(c)
    avant = client.get("/admin/circuit/journal?taille=1").json()
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO circuit_journal (ts, geste, cible, par, resultat, details, lot)"
            " VALUES (now() - interval '365 days', 'calculer', 'run_ancien', 'Vic', 'ok', '{}', :lot)"),
            {"lot": J.nouveau_lot()})
    apres = client.get("/admin/circuit/journal?taille=1").json()
    # une entrée d'il y a un an COMPTE dans le total : aucun filtre de date par défaut ne la coupe.
    assert apres["total"] == avant["total"] + 1
    assert isinstance(apres["aujourdhui"], int)
