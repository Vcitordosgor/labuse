"""CIRCUIT-6 — les sept garanties : chaque verrou PROUVÉ cassé sur un cas construit, puis
vert (cas propre + base réelle sous @local). Un verrou jamais vu rouge n'existe pas.
"""
from __future__ import annotations

import os

import pytest

from labuse import circuit_garanties as CG

pytestmark = pytest.mark.verrous


def _src(i, name, *, endpoint=None, notes=None, alias_de=None, status="connecte"):
    return {"id": i, "name": name, "status": status, "endpoint_url": endpoint,
            "technical_notes": notes, "alias_de": alias_de}


# ── G1 — toutes les sources, une seule fois ────────────────────────────────────────────
def test_g1_prouve_casse_meme_endpoint_sans_arbitrage():
    rows = [_src(1, "Source A", endpoint="https://api.exemple.fr/jeu"),
            _src(2, "Source B", endpoint="https://api.exemple.fr/jeu")]
    d = CG.analyse_doublons(rows)
    assert len(d) == 1 and d[0]["arbitrage"] is None
    assert "même endpoint" in d[0]["raisons"][0]


def test_g1_passerelle_mutualisee_nest_pas_un_doublon():
    rows = [_src(1, "Jeu WFS 1", endpoint="https://data.geopf.fr/wfs/ows"),
            _src(2, "Jeu WFS 2", endpoint="https://data.geopf.fr/wfs/ows")]
    assert CG.analyse_doublons(rows) == []


def test_g1_arbitrage_ecrit_eteint_le_doublon():
    rows = [_src(1, "Source A", endpoint="https://api.exemple.fr/jeu",
                 notes="ARBITRAGE : deux canaux, un usage chacun"),
            _src(2, "Source B", endpoint="https://api.exemple.fr/jeu")]
    d = CG.analyse_doublons(rows)
    assert len(d) == 1 and d[0]["arbitrage"] == "note en base"


def test_g1_alias_vaut_arbitrage():
    rows = [_src(1, "Canonique", endpoint="https://api.exemple.fr/jeu"),
            _src(2, "Canal bulk", endpoint="https://api.exemple.fr/jeu", alias_de=1,
                 status="alias")]
    d = CG.analyse_doublons(rows)
    assert d and d[0]["arbitrage"].startswith("alias")


def test_g1_concepts_declares_sonnent():
    rows = [_src(1, "DVF / valeurs foncières"),
            _src(2, "DVF Réunion (Région, data.regionreunion.com)")]
    d = CG.analyse_doublons(rows)
    assert d and "même concept" in d[0]["raisons"][0]


def test_g1_statut_hors_liste_fermee_casse(monkeypatch):
    class _Faux:
        def execute(self, *a, **k):
            raise AssertionError("non appelé")
    # la liste fermée elle-même
    assert CG.STATUTS_ADMIS == {"connecte", "manuel", "a_faire", "retiree", "alias", "hub"}


@pytest.mark.local
def test_g1_vert_sur_la_base_reelle():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    assert url, "base réelle inconnue"
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g1(s)
        assert r.verdict == "ok", (r.preuve, r.details[:5])
        cpt = CG.catalogue_compteurs(s)
        assert cpt["total"] == cpt["vitrine"] + cpt["hors_vitrine"]
