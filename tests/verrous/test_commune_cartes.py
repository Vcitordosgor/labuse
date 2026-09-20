"""COMMUNE-RANGEMENT-2 lot 5 — V5e : « tout par déclaration » (commune). Chaque donnée à la maille
commune servie sur la fiche commune est déclarée dans declarations/commune/ avec sa carte. Preuve
cassé → vert (le pendant du V5d de la fiche parcelle)."""
from __future__ import annotations

import pytest

from labuse import circuit_verrous as CV
from labuse import registre as REG
from labuse.registre import donnees as D
from labuse.registre import robinets as ROB

pytestmark = pytest.mark.verrous


def test_v5e_vert_sur_le_registre_reel():
    """Le registre réel passe : toute donnée maille commune servie sur la fiche commune a sa carte
    déclarée dans declarations/commune/ (COMMUNE-RANGEMENT-2 lot 5)."""
    r = CV.verrou_fiche_commune_cartes()
    assert r.verdict == "ok", r.details[:10]
    assert "toutes déclarées avec une carte" in r.preuve


def test_v5e_prouve_casse_sur_une_donnee_commune_sans_carte(monkeypatch):
    """Une donnée maille commune servie par un robinet fiche_commune mais jamais déclarée casse le
    verrou, et le détail NOMME la donnée — jamais un câble muet."""
    dbl = dict(D.DONNEES)
    dbl["zz_commune_nu"] = D.Donnee("Donnée commune nue", "nombre", "commune",
                                    "servie sur la fiche commune sans déclaration", None, "passe_plat", "f:x")
    monkeypatch.setattr(D, "DONNEES", dbl)
    rdbl = dict(ROB.ROBINETS)
    rdbl["fiche_commune_zz_test"] = ROB.Robinet("fiche", "Robinet commune test", "fiche_commune",
                                                "/communes/{c}/contexte", "json_puis_js", ("zz_commune_nu",))
    monkeypatch.setattr(ROB, "ROBINETS", rdbl)
    monkeypatch.setattr(REG, "ROBINETS", rdbl)
    r = CV.verrou_fiche_commune_cartes()
    assert r.verdict == "casse"
    assert any("zz_commune_nu" in d for d in r.details)
