"""CONNEXIONS-2 Lot 7 — Dashboard : actions et santé (N2, N3).

  · N2 — toggle « dépôt agence » éditable au dashboard (réglage base, relu à chaud) + read-side filter
    (#12/H5 : un dépôt agence n'est plus servi aux clients tant que le drapeau est fermé).
  · N3 — sonde des endpoints MÉTIER (avec DB) : capte « /accueil/chiffres vivant mais écran vide ».
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse import models
    from labuse.api.app import app
    models.ensure_data_sources_millesime(engine)
    from labuse import reglages
    reglages.ensure_reglages(engine)
    reglages.set_bool(reglages.CLE_DEPOT_AGENCE, False)   # défaut sûr : fermé
    yield TestClient(app, base_url="https://testserver")
    reglages.set_bool(reglages.CLE_DEPOT_AGENCE, False)


def test_toggle_depot_agence_relu_a_chaud(client):
    """N2 — l'admin ouvre/ferme le dépôt agence au dashboard ; /ouvert reflète immédiatement (réglage
    base, plus l'env figé). Échoue sur l'ancien code (flag env, lecture seule, changeable qu'au déploiement)."""
    assert client.get("/radar/depot-agence/ouvert").json()["ouvert"] is False
    assert client.post("/admin/radar/depot-agence/toggle", json={"actif": True}).json()["ok"] is True
    assert client.get("/radar/depot-agence/ouvert").json()["ouvert"] is True
    client.post("/admin/radar/depot-agence/toggle", json={"actif": False})
    assert client.get("/radar/depot-agence/ouvert").json()["ouvert"] is False


def test_where_client_exclut_depot_agence_si_ferme():
    """#12/H5 — tant que le drapeau est FERMÉ, un dépôt agence (validé par un test admin) N'EST PAS servi
    aux clients : le WHERE client l'exclut. Ouvert → plus d'exclusion. Échoue sur l'ancien `_where` (nu)."""
    from labuse import reglages
    from labuse.pige.client import _where
    reglages.set_bool(reglages.CLE_DEPOT_AGENCE, False)
    sql, _ = _where({})
    assert "NOT b.depose_par_agence" in sql
    reglages.set_bool(reglages.CLE_DEPOT_AGENCE, True)
    sql_ouvert, _ = _where({})
    assert "NOT b.depose_par_agence" not in sql_ouvert
    reglages.set_bool(reglages.CLE_DEPOT_AGENCE, False)


def test_sonde_endpoints_capte_ecran_vide(monkeypatch):
    """N3 — la sonde métier détecte le cas « /accueil/chiffres répond 200 mais parcelles=null » (écran
    vide), que /health sans DB ne verrait pas. Échoue sur l'ancienne sonde (liveness seule)."""
    from labuse.api import accueil, sante
    from labuse.db import session_scope
    with session_scope() as s:
        res = sante.sonde_metier(s)
    assert isinstance(res["endpoints"], list)
    assert any(e["endpoint"] == "/accueil/chiffres" for e in res["endpoints"])

    # simule un payload accueil VIDE (run servi introuvable) → l'endpoint est marqué en échec.
    monkeypatch.setattr(accueil, "accueil_chiffres", lambda db: {"parcelles": None})
    with session_scope() as s:
        res2 = sante.sonde_metier(s)
    acc = next(e for e in res2["endpoints"] if e["endpoint"] == "/accueil/chiffres")
    assert acc["ok"] is False and res2["ok"] is False


def test_admin_sante_endpoints_expose(client):
    """N3 — la tuile Santé lit /admin/sante-endpoints : forme stable (ok + liste d'endpoints)."""
    d = client.get("/admin/sante-endpoints").json()
    assert "ok" in d and isinstance(d["endpoints"], list) and d["endpoints"]
