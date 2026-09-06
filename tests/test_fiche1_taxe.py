"""FICHE-1 lot 5 — taxe d'aménagement estimée sur la fiche (Constructibilité).

DOCTRINE (CIRCUIT-3 lot 6.2) : aucun taux inventé. Sans taux communal public, le total N'EST PAS
calculé et le message « non renseigné » est servi. L'assiette = surface de plancher du scénario
table rase.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.registre import ROBINETS
from labuse.registre.donnees import DONNEES


def test_registre_taxe_estimee_declaree():
    d = DONNEES["taxe_amenagement_estimee_eur"]
    assert d.en_attente is None and d.moteur == "taxe_amenagement"
    assert "taxe_amenagement_estimee_eur" in ROBINETS["fiche_parcelle_constructibilite"].chiffres
    # distincte de l'outil (V5a) : définition différente
    assert DONNEES["taxe_amenagement_eur"].definition != d.definition


def test_taxe_sans_taux_communal_jamais_de_total_invente(monkeypatch):
    """Taux communal public inconnu (table vide) → total None + message, jamais un taux deviné."""
    from labuse.api import app as _app

    # potentiel table rase constructible avec 200 m² de plancher
    monkeypatch.setattr("labuse.faisabilite.potentiel.bloc_potentiel",
                        lambda db, pid: {"table_rase": {"constructible": True, "plancher_m2": 200.0}})
    monkeypatch.setattr("labuse.taxe_amenagement.taux_communal_public", lambda db, insee: None)
    b = _app._taxe_amenagement_block(object(), "97411000AA0001", 1)
    assert b is not None
    assert b["assiette_m2"] == 200
    assert b["taux_communal_manquant"] is True
    assert b["total_eur"] is None
    assert b["taux_communal_pct"] is None
    assert "non renseigné" in b["message_taux_communal"]


def test_taxe_omise_si_non_constructible(monkeypatch):
    from labuse.api import app as _app
    monkeypatch.setattr("labuse.faisabilite.potentiel.bloc_potentiel",
                        lambda db, pid: {"table_rase": {"constructible": False, "plancher_m2": None}})
    assert _app._taxe_amenagement_block(object(), "97411000AA0001", 1) is None
