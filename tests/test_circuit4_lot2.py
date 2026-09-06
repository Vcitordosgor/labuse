"""CIRCUIT-4 lot 2 — l'agent « règle » (façade, anti-invention) et la tenue des fiches à extrait."""
from __future__ import annotations

import json

import pytest

from labuse import agent_regle, regles


# ── anti-invention (même règle 6.2 que l'agent de source) ─────────────────────────────────────
def test_verdict_positif_sans_reference_force_introuvable():
    d, raison = agent_regle._valider(json.dumps({
        "verdict": "confirmee", "reference": None, "cherche": ["légifrance"]}))
    assert d["verdict"] == "introuvable" and "forcé" in raison


def test_verdict_positif_sans_date_force_introuvable():
    d, raison = agent_regle._valider(json.dumps({
        "verdict": "version_nouvelle",
        "reference": {"titre": "t", "article": "a", "url": "https://x", "version": "",
                      "extrait": "un passage sans la moindre datation"}}))
    assert d["verdict"] == "introuvable" and raison


def test_verdict_avec_extrait_date_accepte():
    d, raison = agent_regle._valider(json.dumps({
        "verdict": "confirmee",
        "reference": {"titre": "CGI", "article": "1635 quater H", "url": "https://legifrance",
                      "version": "en vigueur au 01/07/2026",
                      "extrait": "fixée forfaitairement à 892 € (en vigueur au 01/07/2026)"}}))
    assert d["verdict"] == "confirmee" and raison is None


def test_sortie_non_json_forcee():
    d, raison = agent_regle._valider("le modèle répond en prose")
    assert d["verdict"] == "introuvable" and "non-JSON" in raison


def test_fiche_de_recherche_depuis_les_fiches():
    f = agent_regle.fiche_de_recherche("taxe_amenagement_eur")
    assert f and f["classe"] == "regle_externe"
    assert f["reference_connue"]["article"].startswith("art. 1635 quater")
    assert agent_regle.fiche_de_recherche("donnee_inexistante") is None


def test_fiches_a_reverifier_cible_les_vieilles_references():
    # toutes les références datent d'aujourd'hui (2026-09-06) → rien à revérifier sous 180 j ;
    # avec un seuil 0, toutes les fiches à référence sont cibles.
    assert agent_regle.fiches_a_reverifier(plus_de_jours=180) == []
    cibles = agent_regle.fiches_a_reverifier(plus_de_jours=0)
    assert "taxe_amenagement_eur" in cibles and "distance_arret_m" in cibles


# ── agent bout-en-bout sur fixture (aucun réseau) ─────────────────────────────────────────────
@pytest.mark.db
def test_agent_regle_ecrit_rapport_et_journal(engine):
    from sqlalchemy import text

    def faux_appel(db, fiche):
        return json.dumps({"verdict": "confirmee", "cherche": ["légifrance"],
                           "reference": {"titre": "CGI", "article": "1635 quater H",
                                         "url": "https://www.legifrance.gouv.fr/x",
                                         "version": "en vigueur au 01/07/2026",
                                         "extrait": "892 € … en vigueur au 01/07/2026"},
                           "page_js": "non"})

    with engine.begin() as c:
        out = agent_regle.lancer_agent(c, "taxe_amenagement_eur", par="test", appel=faux_appel)
        assert out["ok"] and out["verdict"] == "confirmee"
        n = c.execute(text("SELECT count(*) FROM regle_agent_rapports"
                           " WHERE donnee_id = 'taxe_amenagement_eur'")).scalar()
        assert n >= 1
        j = c.execute(text("SELECT par, resultat FROM circuit_journal WHERE geste='agent'"
                           " AND cible = 'règle taxe_amenagement_eur'"
                           " ORDER BY id DESC LIMIT 1")).mappings().first()
        assert j and j["par"] == "test" and j["resultat"] == "confirmee"


# ── tenue des fiches après le lot 2 ───────────────────────────────────────────────────────────
def test_regles_externes_conformes_portent_extrait_date():
    regles.charger()
    for f in regles.TOUTES:
        if f.verdict in ("conforme", "partiel"):
            r = f.reference
            assert r is not None and r.extrait.strip() and r.version.strip(), f.donnees
            assert r.lu_le == "2026-09-06"
        if f.verdict == "ecart":
            assert (f.ecart or "").strip(), f.donnees


def test_surface_agent_regle_declaree():
    from labuse.ai_models import SURFACES, model_for
    assert "agent_regle" in SURFACES
    assert model_for("agent_regle")
