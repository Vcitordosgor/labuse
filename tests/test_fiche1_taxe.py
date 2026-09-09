"""FICHE-1 lot 5 → RECETTE-8 W2 — taxe d'aménagement sur la fiche (Constructibilité).

DOCTRINE (CIRCUIT-3 lot 6.2) : aucun taux inventé. RECETTE-8 W2 : la taxe se paie sur la surface de
plancher CRÉÉE par un projet ; sur la fiche/le Dossier aucun projet n'est saisi → le bloc ne porte
JAMAIS de montant en euros (plus de total_eur ni d'assiette prise sur la table rase), seulement le
taux communal (public, daté) + la part départementale et la phrase disant sur quoi elle se calcule.
Le montant n'est chiffré qu'au Financier (sur la SDP du projet).
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
    """Taux communal public inconnu (table vide) → « non renseigné », jamais un taux deviné ; et
    JAMAIS de montant (W2 : pas de projet, pas de taxe chiffrée)."""
    from labuse.api import app as _app

    monkeypatch.setattr("labuse.taxe_amenagement.taux_communal_public", lambda db, insee: None)
    b = _app._taxe_amenagement_block(object(), "97411000AA0001", 1)
    assert b is not None
    assert b["projet_saisi"] is False
    assert b["total_eur"] is None                 # W2 — jamais un montant sans projet
    assert "assiette_m2" not in b                 # W2 — plus d'assiette prise sur la table rase
    assert b["taux_communal_manquant"] is True
    assert b["taux_communal_pct"] is None
    assert "non renseigné" in b["message_taux_communal"]


def test_taxe_ne_porte_jamais_de_montant_sans_projet(monkeypatch):
    """RECETTE-8 W2 — même avec un taux communal PUBLIC connu, le bloc de fiche ne chiffre AUCUN
    montant : il ne dépend plus du potentiel (table rase) et ne porte que le taux + la référence."""
    from labuse.api import app as _app

    monkeypatch.setattr("labuse.taxe_amenagement.taux_communal_public",
                        lambda db, insee: {"part_communale_pct": 3.0, "source": "DGFiP",
                                           "millesime": "Taux communal", "delib_date": None,
                                           "maj_at": None, "perime": False})
    b = _app._taxe_amenagement_block(object(), "97411000AA0001", 1)
    assert b is not None
    assert b["projet_saisi"] is False
    assert b["taux_communal_pct"] == 3.0          # le taux est servi…
    assert b["total_eur"] is None                 # …mais AUCUN montant (pas de projet)
    assert "assiette_m2" not in b and "assiette_eur" not in b
