"""M112 — les invisibles rendus atteignables. Tests DÉTERMINISTES (pure, aucun modèle) :

  1. les 11 outils invisibles + les concepts fantôme/bailleur → une porte cliquable nommée ;
  2. le piège écarté : « qui gère le financement des bailleurs sociaux » ≠ l'outil bailleur (accueil #5) ;
  3. les 4 documents → le bon kind (banquier avant « dossier » nu) ;
  4. la traduction critère facette → filtres carte (camelCase), et la porte carte d'un comptage.
"""
from __future__ import annotations

import pytest

from labuse.copilote_v2.answering import (
    _carte_depuis_compte,
    _criteres_vers_filtres,
    _match_concept,
    _match_document,
    _veut_carte,
)


# ───────────────────────── 1. concepts-outils → porte ─────────────────────────
@pytest.mark.parametrize("message, module", [
    ("le barometre du foncier", "barometre"),
    ("ou investir a La Reunion", "o6-comparateur"),
    ("qui construit quoi a Saint-Paul", "permis"),
    ("les promesses mortes", "promesses"),
    ("le simulateur zan", "zan"),
    ("la rarete du foncier", "o9-rarete"),
    ("potentiel de renouvellement", "renouvellement"),
    ("si cette zone passait constructible", "simulplu"),
    ("les bascules du mois", "o10-bascules"),
    ("suivi de secteur", "o7-carnet"),
    ("scorer une adresse", "scoreur-adresse"),
    ("les parcelles fantomes", "fantome"),
    ("montre le patrimoine des bailleurs", "bailleur"),
])
def test_concept_ouvre_une_porte(message, module):
    got = _match_concept(message)
    assert got is not None, f"{message!r} n'ouvre aucune porte"
    assert got[0] == module
    assert got[1]  # un libellé lisible, jamais nu


def test_bailleur_exige_un_mot_foncier():
    # PIÈGE accueil #5 : « qui gère le financement des bailleurs sociaux » est une question d'org
    # (réponse web), PAS une demande de l'outil bailleur (patrimoine/foncier).
    assert _match_concept("qui gere les dossiers de financement des bailleurs sociaux a la Region") is None
    # mais « parcelles de bailleurs sociaux » vise bien l'outil.
    assert _match_concept("quelles parcelles de bailleurs sociaux a Saint-Denis")[0] == "bailleur"


def test_hors_concept_ne_devine_pas():
    assert _match_concept("quelle est la meteo a Saint-Denis") is None


# ───────────────────────── 2. documents → kind ─────────────────────────
@pytest.mark.parametrize("message, kind", [
    ("edite le dossier banquier de la parcelle", "dossier-banquier"),
    ("genere l argumentaire", "argumentaire"),
    ("sors moi le pre-dossier", "pre-dossier"),
    ("sors moi le dossier", "dossier"),          # « dossier » nu, APRÈS banquier
])
def test_document_bon_kind(message, kind):
    got = _match_document(message)
    assert got is not None and got[0] == kind


# ───────────────────────── 3. critère facette → filtres carte ─────────────────────────
def test_criteres_vers_filtres_camelcase():
    f = _criteres_vers_filtres({
        "surface_min": 20000, "tier": "P,PM", "personne_morale": True, "evenement": True,
        "signaux": "friche", "adresse_absente": True, "copro": "copro", "renouvellement": True,
        "zonage": "U,AU",
    })
    assert f["surfaceMin"] == 20000
    assert f["tiers"] == ["P", "PM"]
    assert f["personneMorale"] is True
    assert f["evenement"] is True
    assert f["signaux"] == ["friche"]
    assert f["adresseAbsente"] is True
    assert f["copro"] == ["copro"]
    assert f["renouvellement"] is True
    assert f["zonagePlu"] == ["U", "AU"]


def test_defisc_devient_signal():
    assert _criteres_vers_filtres({"defisc": True})["signaux"] == ["defisc"]


class _FakeRes:
    def __init__(self, tool, data):
        self.tool, self.data = tool, data


def test_carte_depuis_compte_porte_la_carte():
    res = _FakeRes("compter_parcelles", {
        "criteres": {"commune": "Saint-Paul", "signaux": "friche"},
        "criteres_labels": ["en friche"],
    })
    p = _carte_depuis_compte(res)
    assert p["commune"] == "Saint-Paul"
    assert p["filtres"] == {"signaux": ["friche"]}
    assert "Saint-Paul" in p["libelle"]


def test_carte_seulement_pour_compter_parcelles():
    assert _carte_depuis_compte(_FakeRes("fiche_parcelle", {"criteres": {"commune": "X"}})) is None
    # un comptage sans commune NI filtre → pas de carte (rien à poser dessus).
    assert _carte_depuis_compte(_FakeRes("compter_parcelles", {"criteres": {}})) is None


# ───────────────────────── 4. la demande visuelle ─────────────────────────
@pytest.mark.parametrize("message, veut", [
    ("montre les friches a Saint-Paul", True),
    ("ou sont les parcelles en procedure", True),
    ("localise les copros", True),
    ("combien de parcelles a Saint-Paul", False),
    ("qui est le maire", False),
])
def test_veut_carte(message, veut):
    assert _veut_carte(message) is veut
