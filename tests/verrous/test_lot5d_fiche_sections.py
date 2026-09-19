"""FICHE-RANGEMENT-2 lot 2 — V5d : « tout par déclaration ». Chaque donnée à la maille parcelle
servie sur la fiche est déclarée avec une section. Preuve cassé → vert."""
from __future__ import annotations

import pytest

from labuse import circuit_verrous as CV
from labuse import registre as REG
from labuse.registre import donnees as D
from labuse.registre import robinets as ROB

pytestmark = pytest.mark.verrous


def test_v5d_vert_sur_le_registre_reel():
    """Le registre réel passe : toute donnée maille parcelle servie sur la fiche a une section
    déclarée (FICHE-RANGEMENT-2 lot 2 a résorbé les dernières non déclarées)."""
    r = CV.verrou_fiche_sections()
    assert r.verdict == "ok", r.details[:10]
    assert "toutes déclarées avec une section" in r.preuve


def test_v5d_prouve_casse_sur_une_donnee_fiche_sans_section(monkeypatch):
    """Une donnée maille parcelle servie par un robinet fiche mais jamais déclarée casse le
    verrou, et le détail NOMME la donnée — jamais un câble muet."""
    dbl = dict(D.DONNEES)
    dbl["zz_fiche_nu"] = D.Donnee("Donnée fiche nue", "nombre", "parcelle",
                                  "servie sur la fiche sans déclaration", None, "passe_plat", "f:x")
    monkeypatch.setattr(D, "DONNEES", dbl)
    rdbl = dict(ROB.ROBINETS)
    rdbl["zz_rob_fiche"] = ROB.Robinet("fiche", "Robinet fiche test", None,
                                       "/parcels/{idu}", "json_puis_js", ("zz_fiche_nu",))
    monkeypatch.setattr(ROB, "ROBINETS", rdbl)
    monkeypatch.setattr(REG, "ROBINETS", rdbl)
    r = CV.verrou_fiche_sections()
    assert r.verdict == "casse"
    assert any("zz_fiche_nu" in d for d in r.details)
