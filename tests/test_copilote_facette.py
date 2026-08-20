"""M110 — la facette interrogeable + résolution d'acronyme + concepts. Tests DÉTERMINISTES
(base réelle, aucun appel modèle) : on appelle les outils/résolveurs directement.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.copilote_v2 import answering
from labuse.copilote_v2.outils import compter_parcelles, resoudre_acronyme

pytestmark = pytest.mark.db


def test_compter_parcelles_plumbing_vers_la_facette(monkeypatch):
    """Le tool TRADUIT les critères vers FiltreCriteres (un critère = un seul endroit) et NOMME
    chaque critère appliqué — testé sans données (filtre monkeypatché), donc déterministe."""
    import labuse.api.app as app
    cap: dict = {}

    def _fake(*, c, **kw):
        cap["fc"] = c
        return {"compte": 42}
    monkeypatch.setattr(app, "filtre", _fake)
    r = compter_parcelles(None, commune=None, signaux="friche,procedure", adresse_absente=True,
                          copro="avec", defisc=True, renouvellement=True, zonage="U,AU", evenement=True)
    fc = cap["fc"]
    assert fc.signaux == "friche,procedure" and fc.adresse_absente and fc.copro == "avec"
    assert fc.defisc_active and fc.renouvellement and fc.zonage == "U,AU" and fc.evenement
    assert r.valeur == 42 and not r.criteres_non_appliques        # branchés → aucun aveu
    labels = r.data["criteres_labels"]
    for attendu in ("friche", "procédure judiciaire (BODACC)", "sans adresse (BAN)",
                    "en copropriété", "en défiscalisation", "en renouvellement urbain", "zone U/AU"):
        assert attendu in labels, attendu


def test_compter_parcelles_ignore_les_valeurs_hors_liste(monkeypatch):
    """Robustesse : un signal inconnu / une famille de zone invalide sont ÉLAGUÉS (jamais avalés)."""
    import labuse.api.app as app
    cap: dict = {}

    def _fake(*, c, **kw):
        cap["fc"] = c
        return {"compte": 0}
    monkeypatch.setattr(app, "filtre", _fake)
    compter_parcelles(None, signaux="friche,inexistant", copro="peut-être", zonage="U,ZZZ")
    fc = cap["fc"]
    assert fc.signaux == "friche" and fc.copro is None and fc.zonage == "U"


def test_resoudre_acronyme_sidr_et_shlmr(db_session):
    assert resoudre_acronyme(db_session, "la SIDR")[0] == "310863592"
    assert resoudre_acronyme(db_session, "SHLMR")[0] == "310895172"
    assert resoudre_acronyme(db_session, "SAFER")[0] == "310836309"
    assert resoudre_acronyme(db_session, "une société quelconque") is None     # pas un acronyme connu


def test_parcelles_par_entreprise_acronyme_prend_le_bon_siren(db_session, monkeypatch):
    """« la SIDR » résout le BAILLEUR (310863592) via le référentiel, jamais le lot copro homonyme."""
    from labuse.copilote_v2 import outils
    import labuse.api.modules as mods
    monkeypatch.setattr(mods, "patrimoine", lambda *, siren, db: {
        "nom": "SIDR", "n_parcelles": 4183, "sdp_totale_m2": 0, "bodacc": None, "siren": siren})
    r = outils.parcelles_par_entreprise(db_session, q="la SIDR")
    assert r.ok and r.data["siren"] == "310863592" and r.valeur == 4183


def test_match_concept_fantome_bailleur_retires():
    # M137-N — les outils « fantôme » et « bailleur » sont RETIRÉS du produit (DORMANT) : leurs
    # concept-routes ont été retirés (router vers un module absent = lien mort). Ces demandes ne
    # matchent plus un concept-outil → retombent sur le traitement normal du Copilote.
    assert answering._match_concept("montre-moi les parcelles fantômes") is None
    assert answering._match_concept("quelles parcelles de bailleurs sociaux") is None
    assert answering._match_concept("combien de parcelles à Saint-Paul") is None
