"""COMPTE-2 · Lot 5 — le plafond IA 2 €/jour est BLOQUANT, par compte, et couvre TOUTE surface IA.

Avant : la dépense IA était journalisée mais /parcels/{idu}/ask (barre de fiche) ne respectait pas le
budget — un compte au plafond pouvait continuer à dépenser là. Ici on prouve : A épuise → bloqué, B
continue ; le plafond est lu à CHAQUE question (édition au dashboard prise en compte tout de suite) ;
la barre de fiche court-circuite au plafond SANS appel modèle.
"""
from __future__ import annotations

import types

import pytest
from sqlalchemy import text

from labuse.api import dashboard as dash

pytestmark = pytest.mark.db


@pytest.fixture()
def deux_comptes(engine):
    dash.ensure_tables(engine)                    # colonnes copilote_budget_eur + ia_log(compte_id)
    with engine.begin() as c:
        a = c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES"
                           " ('[CT-TEST] A plafond', 'integral', 'actif') RETURNING id")).scalar()
        b = c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES"
                           " ('[CT-TEST] B plafond', 'integral', 'actif') RETURNING id")).scalar()
        c.execute(text("DELETE FROM ia_log WHERE compte_id IN (:a,:b)"), {"a": a, "b": b})
        # A a déjà dépensé 2,10 € AUJOURD'HUI (au-delà du défaut 2,00 €) ; B rien.
        for cout in (1.50, 0.60):
            c.execute(text("INSERT INTO ia_log (kind, model, stub, cout_eur, compte_id)"
                           " VALUES ('test', 'm', false, :x, :a)"), {"x": cout, "a": a})
    yield a, b
    with engine.begin() as c:
        c.execute(text("DELETE FROM ia_log WHERE compte_id IN (:a,:b)"), {"a": a, "b": b})
        c.execute(text("DELETE FROM comptes WHERE id IN (:a,:b)"), {"a": a, "b": b})


def test_A_epuise_bloque_B_continue(deux_comptes):
    a, b = deux_comptes
    da = dash.depassement_budget_eur(a)
    assert da and da["budget_atteint"] is True
    assert da["budget_eur"] == 2.0 and da["depense_eur"] >= 2.0
    assert "minuit" in da["detail"]
    assert dash.depassement_budget_eur(b) is None      # B n'a rien dépensé → continue


def test_plafond_relu_a_chaque_question(deux_comptes, engine):
    a, _b = deux_comptes
    assert dash.depassement_budget_eur(a) is not None   # bloqué à 2 €
    with engine.begin() as c:                            # Vic relève le plafond de A à 100 € au dashboard
        c.execute(text("UPDATE comptes SET copilote_budget_eur = 100 WHERE id = :a"), {"a": a})
    assert dash.depassement_budget_eur(a) is None        # la question SUIVANTE passe (relu)


def test_pilote_sans_compte_pas_de_blocage_euros(deux_comptes):
    # compte None (pilote/anonyme) : le plafond euros ne s'applique pas ici (garde en appels ailleurs).
    assert dash.depassement_budget_eur(None) is None


def test_etat_plafond_ia_delegue_a_la_garde_euros(deux_comptes, monkeypatch):
    a, _b = deux_comptes
    # etat_plafond_ia (garde unifiée /ask, /ia, missions) doit refuser A via la même garde euros.
    d = dash.etat_plafond_ia(a, f"c:{a}", "2026-09-07", nl_defaut=80)
    assert d and d.get("budget_atteint") is True


def test_fiche_ask_court_circuite_au_plafond(deux_comptes, monkeypatch, db_session):
    """La barre de fiche RESPECTE le budget : au plafond, réponse « budget atteint » et AUCUN appel
    modèle (core.complete jamais atteint)."""
    import labuse.config as _cfg
    from labuse.api import fiche_ask
    a, _b = deux_comptes
    if _cfg.get_settings().dev_mode:
        pytest.skip("dev_mode actif : le plafond euros est volontairement désactivé")
    appels = {"complete": 0}
    monkeypatch.setattr(fiche_ask.core, "cache_get", lambda *a, **k: None)
    monkeypatch.setattr(fiche_ask.core, "complete",
                        lambda *a, **k: appels.__setitem__("complete", appels["complete"] + 1))
    req = types.SimpleNamespace(state=types.SimpleNamespace(compte_id=a),
                               client=types.SimpleNamespace(host="127.0.0.1"))
    out = fiche_ask.parcel_ask("974411000AB0123", fiche_ask.AskIn(question="constructible ?"),
                               req, db=db_session)
    assert out.get("budget_atteint") is True
    assert appels["complete"] == 0                       # zéro appel modèle → zéro dépense de plus
