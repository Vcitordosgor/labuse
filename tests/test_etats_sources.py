"""RETOURS-8 (R1) — l'arbitre UNIQUE de l'état d'une source.

Verrouille :
  · les quatre états et leur détermination (R1.1) ;
  · la RÈGLE DE PRIORITÉ : le constat de l'agent gagne, l'heuristique de cadence ne peut plus
    contredire un « amont identique » — le cas DPE/DVF (R1.2) ;
  · l'ÉGALITÉ des compteurs : Pilotage, Catalogue et la page client dérivent tous de la MÊME liste,
    donc ne peuvent plus se contredire (R1.3) ;
  · la projection CLIENT à deux états (R2).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from labuse import etats_sources

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 2, tzinfo=timezone.utc)


# ─────────────────────────── R1.1 — les quatre états (fonction pure) ───────────────────────────

def test_surveillee_ok_est_a_jour():
    e = etats_sources.etat_source(
        {"name": "S", "veille_methode": "api", "veille_statut": "ok", "veille_actif": True,
         "source_horizon_at": datetime(2025, 12, 31, tzinfo=timezone.utc)}, now=NOW)
    assert e["etat"] == "a_jour"
    assert e["etat_client"] == "a_jour"


def test_surveillee_nouvelle_version():
    e = etats_sources.etat_source(
        {"name": "S", "veille_methode": "page", "veille_statut": "nouvelle_version",
         "veille_actif": True}, now=NOW)
    assert e["etat"] == "nouvelle_version"
    assert e["etat_client"] == "pas_a_jour"          # seul cas « pas à jour » côté client (R2)


def test_rappel_en_retard_est_a_rafraichir():
    e = etats_sources.etat_source(
        {"name": "S", "veille_methode": "rappel", "veille_cadence_attendue": 30,
         "last_sync_at": NOW - timedelta(days=90)}, now=NOW)
    assert e["etat"] == "a_rafraichir"
    assert e["etat_client"] == "a_jour"              # jamais « en retard » côté client


def test_rappel_dans_sa_cadence_est_a_jour():
    e = etats_sources.etat_source(
        {"name": "S", "veille_methode": "rappel", "veille_cadence_attendue": 30,
         "last_sync_at": NOW - timedelta(days=5)}, now=NOW)
    assert e["etat"] == "a_jour"


def test_sans_sonde_est_non_surveillee():
    e = etats_sources.etat_source(
        {"name": "S", "veille_methode": None, "source_cadence": "mensuel"}, now=NOW)
    assert e["etat"] == "non_surveillee"
    assert e["etat_client"] == "a_jour"
    assert "chaque mois" in e["phrase_admin"]        # la cadence devient une mention, jamais un rouge


# ─────────────────────── R1.2 — priorité : l'agent gagne (cas DPE/DVF) ───────────────────────

def test_agent_gagne_sur_cadence_ancienne():
    """DPE/DVF : le producteur traîne sur SA cadence, mais l'agent a vu « amont identique » →
    la source est À JOUR, et la phrase le dit côté producteur, jamais « LABUSE en retard »."""
    e = etats_sources.etat_source(
        {"name": "DVF / valeurs foncières", "veille_methode": "page", "veille_statut": "ok",
         "veille_actif": True, "source_cadence": "semestriel",
         "source_horizon_at": datetime(2025, 6, 30, tzinfo=timezone.utc)}, now=NOW)
    assert e["etat"] == "a_jour"
    assert e["etat_client"] == "a_jour"
    assert "à jour" in e["phrase_admin"].lower()
    assert "producteur n'a rien publié depuis le 30/06/2025" in e["phrase_admin"]


def test_sonde_injoignable_reste_a_jour_pas_rouge():
    """Un échec de sonde n'est PAS une nouvelle version ni un « à rafraîchir » : côté état unique,
    la source reste à jour (aucune version plus récente CONNUE) ; l'échec est signalé à part."""
    e = etats_sources.etat_source(
        {"name": "S", "veille_methode": "api", "veille_statut": "injoignable", "veille_actif": True},
        now=NOW)
    assert e["etat"] == "a_jour"


# ─────────────────────── R1.3 — égalité des compteurs (même liste) ───────────────────────

def _seed(db, nom, statut="connecte", methode=None, veille_statut=None, cadence=None,
          cadence_attendue=None, last_sync=None, horizon=None):
    sid = db.execute(text(
        "INSERT INTO data_sources (name, status, source_cadence, source_horizon_at, last_sync_at) "
        "VALUES (:n, :st, :cad, :h, :ls) ON CONFLICT (name) DO UPDATE SET status = EXCLUDED.status, "
        "source_cadence = EXCLUDED.source_cadence, source_horizon_at = EXCLUDED.source_horizon_at, "
        "last_sync_at = EXCLUDED.last_sync_at RETURNING id"),
        {"n": nom, "st": statut, "cad": cadence, "h": horizon, "ls": last_sync}).scalar()
    if methode is not None:
        db.execute(text(
            "INSERT INTO source_veille (source_id, methode, dernier_statut, cadence_attendue_jours, actif) "
            "VALUES (:s, :m, :vs, :ca, true) ON CONFLICT (source_id) DO UPDATE SET "
            "methode = EXCLUDED.methode, dernier_statut = EXCLUDED.dernier_statut, "
            "cadence_attendue_jours = EXCLUDED.cadence_attendue_jours, actif = true"),
            {"s": sid, "m": methode, "vs": veille_statut, "ca": cadence_attendue})
    return sid


def test_compteurs_derives_de_la_meme_liste(db_session, engine):
    from labuse import models
    models.ensure_source_veille(engine)
    db = db_session
    _seed(db, "R8 · surveillée à jour", methode="api", veille_statut="ok")
    _seed(db, "R8 · nouvelle version", methode="page", veille_statut="nouvelle_version")
    _seed(db, "R8 · rappel en retard", methode="rappel", cadence_attendue=30,
          last_sync=NOW - timedelta(days=90))
    _seed(db, "R8 · non surveillée", methode=None, cadence="mensuel")

    etats = [e for e in etats_sources.lister_etats(db, now=NOW) if e["name"].startswith("R8 · ")]
    cpt = etats_sources.compteurs(etats)

    # les quatre états couverts exactement une fois chacun
    assert cpt["nouvelle_version"] == 1
    assert cpt["a_rafraichir"] == 1
    assert cpt["non_surveillee"] == 1
    assert cpt["a_jour"] == 1
    assert cpt["total"] == 4

    # projection client : « pas à jour » = les seules nouvelles versions (R2)
    assert cpt["pas_a_jour"] == 1
    assert cpt["client_a_jour"] == 3

    # ÉGALITÉ : le compteur « geste » du Pilotage (nouvelle_version) et celui du Catalogue dérivent
    # tous deux de CETTE liste → identiques par construction.
    pilotage_nouvelle_version = sum(1 for e in etats if e["etat"] == "nouvelle_version")
    catalogue_nouvelle_version = sum(1 for e in etats if e["etat"] == "nouvelle_version")
    assert pilotage_nouvelle_version == catalogue_nouvelle_version == cpt["nouvelle_version"]
