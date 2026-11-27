from unittest.mock import Mock

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, TimeoutError

from labuse import comptes
from labuse.api import auth, carnet, fiche_commune, modules
from labuse.api.app import app, get_db
from labuse.communes import insee_officiel
from labuse.db import connexions_saturees, requete_bdd_indisponible


def refus_postgres():
    return OperationalError(None, None, psycopg.errors.TooManyConnections())


@pytest.mark.parametrize("route", [
    "/communes/Les%20Trois-Bassins/contexte", "/modules/verif-procedure/97414000CT0691",
    "/parcels/97414000CT0691/exposition", "/carnet-secteur/97415000CD",
])
def test_refus_postgres_sur_les_routes(route, monkeypatch):
    db = Mock()
    db.execute.side_effect = refus_postgres()
    for dependency in (get_db, modules.get_db, carnet.get_db):
        monkeypatch.setitem(app.dependency_overrides, dependency, lambda: db)
    monkeypatch.setattr(auth, "enabled", lambda: False)
    reponse = TestClient(app).get(route)
    assert reponse.status_code == 503
    assert reponse.headers["Retry-After"] == "5"
    assert "momentanément chargé" in reponse.json()["detail"]


def test_saturation_pendant_authentification(monkeypatch):
    client = TestClient(app, cookies={auth.COOKIE: "u.temoin"})
    monkeypatch.setattr(auth, "enabled", lambda: True)
    monkeypatch.setattr(auth, "configured", lambda: True)
    def lookup(db, token):
        raise TimeoutError()
    monkeypatch.setattr(comptes, "session_utilisateur", lookup)
    r = client.get("/communes")
    assert r.status_code == 503
    assert "momentanément chargé" in r.json()["detail"]
    invalide = Mock(return_value=None)
    monkeypatch.setattr(comptes, "session_utilisateur", invalide)
    assert client.get("/communes").status_code == 401
    invalide.assert_called_once()


def test_refus_de_connexion_sans_sqlstate():
    assert connexions_saturees(psycopg.OperationalError("FATAL: sorry, too many clients already"))
    assert not connexions_saturees(psycopg.OperationalError("connection refused"))
    assert not connexions_saturees(psycopg.errors.QueryCanceled())


def test_statut_sans_registre_et_stade_connu():
    db = Mock()
    db.execute.return_value.mappings.return_value.first.return_value = None
    assert fiche_commune.plu_statut(db, None, None)["indisponible"]
    db.execute.assert_not_called()
    statut = fiche_commune.plu_statut(db, insee_officiel("Saint-Leu"), "Saint-Leu")
    assert "enquête terminée le 09/10/2026" in statut["stade_texte"]
    assert "18/11/2026" in statut["stade_texte"]


@pytest.mark.db
@pytest.mark.reel
def test_classement_indisponible_preserve_le_plu(monkeypatch):
    import os
    from importlib import import_module

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    api = import_module("labuse.api.app")
    monkeypatch.setattr(api, "_tiers_hauts_commune", Mock(side_effect=psycopg.errors.QueryCanceled()))
    engine = create_engine(os.environ["LABUSE_APP_DATABASE_URL"])
    try:
        with Session(engine) as db:
            contexte = api._compute_commune_contexte(db, "Saint-Leu")
    finally:
        engine.dispose()
    assert contexte["insee"] == "97413"
    assert contexte["classement"] is None
    assert "enquête terminée le 09/10/2026" in contexte["plu_statut"]["stade_texte"]



@pytest.mark.parametrize("erreur", [
    psycopg.errors.QueryCanceled("canceling statement due to statement timeout"),
    psycopg.errors.InternalError_("lwgeom_intersection_prec: GEOS Error: InterruptedException: Interrupted!"),
])
def test_interruption_pendant_la_lecture(monkeypatch, erreur):
    db = Mock()
    db.execute.side_effect = OperationalError(None, None, erreur)
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: db)
    monkeypatch.setattr(auth, "enabled", lambda: False)
    r = TestClient(app).get("/communes/Saint-Paul/contexte")
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "5"
    assert not requete_bdd_indisponible(psycopg.errors.InternalError_("GEOS Error: TopologyException"))
