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


def test_p5_json_apres_prose_avec_accolade():
    """CIRCUIT-P5 — la prose du modèle contient une accolade ({siren}) AVANT le vrai bloc JSON :
    le parseur robuste retrouve l'objet à `verdict` (fini le « JSON invalide » alors que l'agent
    AVAIT trouvé la réponse — le cas réel d'INPI RNE)."""
    brut = ("Voici mon analyse. L'endpoint /api/companies/{siren} est en open data.\n"
            '```json\n{"verdict": "a_jour", "version_trouvee": "2.0", "date_publication": "2024-01",'
            ' "preuve": {"url": "https://inpi.fr", "extrait": "Documentation API 2.0 publiée le 15 janvier 2024"}}\n```')
    rapport, raison = agent_source._valider(brut)
    assert rapport["verdict"] == "a_jour" and raison is None
    assert rapport["version_trouvee"] == "2.0"


def test_p5_a_jour_enregistre_le_controle(db_session, source_test):
    """CIRCUIT-P5 — un verdict `a_jour` (avec preuve datée) ENREGISTRE le contrôle : la veille porte
    dernier_passage_at (la date du contrôle) + dernier_statut='ok' → la source passe « à jour »."""
    db_session.execute(text("UPDATE source_veille SET dernier_passage_at = NULL WHERE source_id = :i"),
                       {"i": source_test})
    r = agent_source.lancer_agent(db_session, source_test, par="test", appel=_fixture({
        "verdict": "a_jour", "version_trouvee": "2026-07", "date_publication": "2026-07-01",
        "preuve": {"url": "https://prod.example",
                   "extrait": "Dernier millésime : 2026-07, publié le 1er juillet 2026."},
        "cherche": ["page des millésimes"], "sonde_proposee": None, "page_js": "non"}))
    assert r["verdict"] == "a_jour" and r["raison_forcage"] is None
    v = db_session.execute(text(
        "SELECT dernier_statut, dernier_passage_at FROM source_veille WHERE source_id = :i"),
        {"i": source_test}).mappings().first()
    assert v["dernier_statut"] == "ok" and v["dernier_passage_at"] is not None


def test_p5_a_jour_cree_la_veille_pour_source_sans_sonde(db_session):
    """CIRCUIT-P5 — une source SANS ligne de veille (jamais sondée) : l'agent CRÉE la ligne
    (methode 'agent') pour rendre son contrôle visible → « à jour »."""
    sid = db_session.execute(text(
        "INSERT INTO data_sources (name, status, provider, source_millesime) "
        "VALUES (:n, 'connecte', 'Test SA', '2025') RETURNING id"),
        {"n": f"Source sans veille {uuid.uuid4().hex[:6]}"}).scalar()
    assert db_session.execute(text(
        "SELECT count(*) FROM source_veille WHERE source_id = :i"), {"i": sid}).scalar() == 0
    r = agent_source.lancer_agent(db_session, sid, par="test", appel=_fixture({
        "verdict": "a_jour", "version_trouvee": "2025", "date_publication": "2025-01-01",
        "preuve": {"url": "https://prod.example",
                   "extrait": "Version 2025 publiée le 1er janvier 2025."},
        "cherche": ["catalogue"], "sonde_proposee": None, "page_js": "non"}))
    assert r["verdict"] == "a_jour"
    v = db_session.execute(text(
        "SELECT methode, dernier_statut, dernier_passage_at FROM source_veille WHERE source_id = :i"),
        {"i": sid}).mappings().first()
    assert v and v["methode"] == "agent" and v["dernier_statut"] == "ok" and v["dernier_passage_at"] is not None


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


def test_agent_source_surface_et_plafond():
    from labuse.ai_models import SURFACES, model_for
    from labuse.jobs import JOBS
    assert "agent_source" in SURFACES
    assert model_for("agent_source")     # résout sans lever (modèle actif)
    # SOURCES-CORRECTION-2 lot 3 — REMIS SUR LA VALEUR RÉELLE (avant : « désactivé » in cadence).
    # CRON-1 a re-registré agents-sources avec un cron du DIMANCHE ; l'invariant « jamais de dépense
    # par défaut » n'est plus porté par une cadence « désactivé » mais par le PLAFOND
    # LABUSE_AGENT_PLAFOND_EUR (défaut 0 € = ne dépense rien), annoncé par le titre « plafonné ».
    j = JOBS["agents-sources"]
    # CIRCUIT-P7 (reporté RETOUCHES-1 lot A) — cadence « 1 semaine sur 2 » = « tous les 15 j (dim) ».
    assert j.cadence == "tous les 15 j (dim)" and "plafonné" in j.titre.lower()
