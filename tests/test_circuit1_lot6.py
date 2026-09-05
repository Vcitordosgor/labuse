"""CIRCUIT-1 lot 6 — les agents de source : JSON strict, ANTI-INVENTION (6.2), rapports,
la vanne qui apparaît sur `nouvelle`. Fixtures : trois pages FIGÉES (aucun réseau) donnent
les verdicts attendus ; une page SANS date donne `introuvable` forcé (6.6)."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text

from labuse import agent_source

pytestmark = pytest.mark.db


@pytest.fixture
def source_test(db_session):
    sid = db_session.execute(text(
        "INSERT INTO data_sources (name, status, provider, source_millesime) "
        "VALUES (:n, 'connecte', 'Test SA', '2026-07') RETURNING id"),
        {"n": f"Source agent {uuid.uuid4().hex[:6]}"}).scalar()
    db_session.execute(text(
        "INSERT INTO source_veille (source_id, methode, dernier_statut, dernier_vu, actif) "
        "VALUES (:i, 'api', 'ok', '2026-07', true)"), {"i": sid})
    return sid


def _fixture(reponse: dict):
    return lambda db, fiche: json.dumps(reponse, ensure_ascii=False)


def test_66_verdict_nouvelle_avec_preuve_datee(db_session, source_test):
    r = agent_source.lancer_agent(db_session, source_test, par="test", appel=_fixture({
        "verdict": "nouvelle", "version_trouvee": "2026-09",
        "date_publication": "2026-09-01",
        "preuve": {"url": "https://prod.example/millesimes",
                   "extrait": "Millésime 2026-09 publié le 1er septembre 2026."},
        "cherche": ["page des millésimes"], "sonde_proposee": {"methode": "api", "url": "https://prod.example/api"},
        "page_js": "non"}))
    assert r["verdict"] == "nouvelle" and r["raison_forcage"] is None
    # la VANNE apparaît : la veille porte le vu + nouvelle_version
    v = db_session.execute(text(
        "SELECT dernier_vu, dernier_statut FROM source_veille WHERE source_id = :i"),
        {"i": source_test}).mappings().first()
    assert v["dernier_statut"] == "nouvelle_version" and v["dernier_vu"] == "2026-09"
    # le rapport est écrit
    n = db_session.execute(text(
        "SELECT count(*) FROM source_agent_rapports WHERE source_id = :i AND verdict='nouvelle'"),
        {"i": source_test}).scalar()
    assert n == 1


def test_66_page_sans_date_force_introuvable(db_session, source_test):
    """LA règle 6.2 : `a_jour` sans extrait daté → verdict FORCÉ à introuvable, raison écrite."""
    r = agent_source.lancer_agent(db_session, source_test, par="test", appel=_fixture({
        "verdict": "a_jour", "version_trouvee": None, "date_publication": None,
        "preuve": {"url": "https://prod.example", "extrait": "Bienvenue sur notre portail."},
        "cherche": ["accueil"], "sonde_proposee": None, "page_js": "non"}))
    assert r["verdict"] == "introuvable"
    assert "sans date" in r["raison_forcage"] or "preuve" in r["raison_forcage"]
    v = db_session.execute(text(
        "SELECT dernier_statut FROM source_veille WHERE source_id = :i"), {"i": source_test}).scalar()
    assert v == "ok", "un verdict forcé n'écrit JAMAIS la veille"


def test_66_sortie_non_json_introuvable(db_session, source_test):
    r = agent_source.lancer_agent(db_session, source_test, par="test",
                                  appel=lambda db, f: "Je pense que la source est à jour !")
    assert r["verdict"] == "introuvable" and "JSON" in r["raison_forcage"]


def test_66_verdict_vide_et_page_js(db_session, source_test):
    r = agent_source.lancer_agent(db_session, source_test, par="test", appel=_fixture({
        "verdict": "vide", "version_trouvee": None, "date_publication": None,
        "preuve": {"url": "https://prod.example/jeu", "extrait": "410 Gone"},
        "cherche": ["jeu"], "sonde_proposee": None, "page_js": "oui"}))
    assert r["verdict"] == "vide" and r["page_js"] == "oui"


def test_64_surface_et_job_desactive():
    from labuse.ai_models import SURFACES, model_for
    from labuse.jobs import JOBS
    assert "agent_source" in SURFACES
    assert model_for("agent_source")     # résout sans lever (modèle actif)
    assert "désactivé" in JOBS["agents-sources"].cadence, "jamais en cron par défaut"
