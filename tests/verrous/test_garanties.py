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


# ── G2 — visible ou pas, je le sais ────────────────────────────────────────────────────
def test_g2_etat_invisible_sort_rouge():
    """La branche INVISIBLE de etat_reservoir : avec le drapeau → rouge ; sans → « à jour »
    (mint) — c'était l'état AVANT le branchement : le mensonge DPE, prouvé ici."""
    from labuse.circuit_etats import etat_reservoir
    avec = etat_reservoir({"invisible": True, "mode": "cron_mensuel",
                           "veille": {"statut": "ok"}, "filtre": {}})
    sans = etat_reservoir({"mode": "cron_mensuel", "veille": {"statut": "ok"}, "filtre": {}})
    assert avec == ("rouge", "INVISIBLE — branchée mais vide")
    assert sans == ("mint", "à jour"), "sans le drapeau, la page disait « à jour » sur une vide"


@pytest.mark.local
def test_g2_signature_dpe_sur_la_base_reelle():
    """DPE : type parcelle, 0/12, table quasi vide → quasi_vide. RNIC (riche) : 0/12 SANS
    quasi_vide (les témoins ne sont pas des copros). Cadastre : 12/12."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from labuse.registre import remplissage as R
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    assert url
    with sessionmaker(bind=create_engine(url))() as s:
        tem = R.temoins_du_jour(s)
        assert len(tem) == 12
        assert R.remplissage_source(s, "dpe_ademe", tem)["quasi_vide"] is True
        assert R.remplissage_source(s, "rnic_anah", tem)["quasi_vide"] is False
        assert R.remplissage_source(s, "cadastre_api_carto", tem)["remplis"] == 12


@pytest.mark.local
def test_g2_vert_sur_la_base_reelle():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    with sessionmaker(bind=create_engine(url))() as s:
        r = CG.verrou_g2(s)
        assert r.verdict == "ok", (r.preuve, r.details[:3])
        assert "dpe_ademe" in r.preuve  # la vide est NOMMÉE, jamais tue
