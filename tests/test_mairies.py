"""K2 (rattrapage KelFoncier) — coordonnées des mairies dans la fiche commune.

Sans réseau : on teste le PARSING de l'annuaire (champs JSON), la lecture `mairie_de`, l'affichage
dans le contexte, et le fait qu'un champ absent reste NULL (« Absent »), jamais inventé.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse.db import session_scope
from labuse.ingestion import mairies

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app)


def test_parse_adresse_physique_pas_postale():
    """L'adresse retenue est la PHYSIQUE (« Adresse »), pas l'adresse postale (CS…)."""
    champ = ('[{"type_adresse":"Adresse","numero_voie":"Place du Général","code_postal":"97460",'
             '"nom_commune":"Saint-Paul"},{"type_adresse":"Adresse postale","numero_voie":"BP 1",'
             '"code_postal":"97864"}]')
    rue, cp = mairies._adresse_physique(champ)
    assert rue == "Place du Général" and cp == "97460"


def test_parse_premier_valeur_json():
    assert mairies._premier('[{"valeur":"02 62 45 43 45"}]') == "02 62 45 43 45"
    assert mairies._premier('[{"libelle":"","valeur":"https://x.re/"}]') == "https://x.re/"
    assert mairies._premier(None) is None and mairies._premier("[]") is None


def test_mairie_de_et_absent(client, engine):
    """Une mairie seedée s'affiche ; un champ NULL sort en null (→ « Absent » côté UI)."""
    with session_scope() as s:
        mairies.ensure_table(s)
        # commune de test rattachée à un INSEE présent (Saint-Philippe 97417) sans e-mail
        s.execute(text("DELETE FROM mairies WHERE insee='99999'"))
        s.execute(text(
            "INSERT INTO mairies (insee, commune, nom, adresse, code_postal, telephone, email,"
            " site_officiel, url_annuaire, source) VALUES"
            " ('99999','KF-Test-Mairie','Mairie KF','1 rue Test','97000','02 62 00 00 00', NULL,"
            " 'https://kf.re', 'https://annuaire/kf', :src)"), {"src": mairies.SOURCE})
        s.commit()
        m = mairies.mairie_de(s, "KF-Test-Mairie")
        assert m and m["adresse"] == "1 rue Test" and m["telephone"] == "02 62 00 00 00"
        assert m["email"] is None                      # champ absent → NULL, jamais inventé
        assert m["site_officiel"] == "https://kf.re" and m["date_import"]
        s.execute(text("DELETE FROM mairies WHERE insee='99999'"))
        s.commit()


def test_contexte_expose_la_mairie_reelle(client, engine):
    """Le contexte d'une commune expose sa mairie (seedée) avec la fraîcheur."""
    with session_scope() as s:
        mairies.ensure_table(s)
        s.execute(text("DELETE FROM mairies WHERE insee='97415'"))
        s.execute(text(
            "INSERT INTO mairies (insee, commune, nom, adresse, code_postal, telephone, email,"
            " site_officiel, url_annuaire, source) VALUES"
            " ('97415','Saint-Paul','Mairie - Saint-Paul','Place du Général-de-Gaulle','97460',"
            " '02 62 45 43 45','maire@x.re','https://mairie-saintpaul.re','https://annuaire',:src)"),
            {"src": mairies.SOURCE})
        s.commit()
    d = client.get("/communes/Saint-Paul/contexte").json()
    assert d["mairie"] and d["mairie"]["telephone"] == "02 62 45 43 45"
    assert "service-public" in d["mairie"]["source"] and d["mairie"]["date_import"]
    with session_scope() as s:
        s.execute(text("DELETE FROM mairies WHERE insee='97415'")); s.commit()
