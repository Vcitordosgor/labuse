"""CIRCUIT-1 lot 4 — la sonde de cohérence : écarts dédupliqués et soldés (historique gardé),
eau ancienne par tampon (les familles de CIRCUIT-0), verdict par passage.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse import sonde_circuit

pytestmark = pytest.mark.db


def test_41_upsert_ecart_dedup_et_reouverture(db_session):
    s = db_session
    sonde_circuit.ensure(s)
    cle = f"Commune-{uuid.uuid4().hex[:6]}"
    sonde_circuit._upsert_ecart(s, "part_zone_A_pct", cle, "moteur:zonage", 35.8,
                                "fiche_commune_zonage", 17.8, "denominateur")
    sonde_circuit._upsert_ecart(s, "part_zone_A_pct", cle, "moteur:zonage", 36.0,
                                "fiche_commune_zonage", 18.0, "denominateur")
    rows = s.execute(text(
        "SELECT valeur_a, statut FROM circuit_ecarts WHERE cle = :k"), {"k": cle}).mappings().all()
    assert len(rows) == 1, "dédupliqué par (chiffre, clé, robinets)"
    assert rows[0]["valeur_a"] == "36.0" and rows[0]["statut"] == "ouvert"


def test_44_ecart_solde_garde_sa_ligne(db_session):
    """4.4 — le passage de la sonde SOLDE un écart re-mesuré sans divergence : la ligne reste
    (statut='solde', solde_le posé) — l'historique que Vic veut voir."""
    s = db_session
    sonde_circuit.ensure(s)
    # un écart OUVERT sur le témoin n_sources (les 3 écrans sont unifiés depuis le lot 0.2 :
    # la sonde va re-mesurer et NE PAS retrouver la divergence → solde)
    sonde_circuit._upsert_ecart(s, "n_sources", "global", "admin_flux_circuit", 77,
                                "page_sources_client", 66, "perimetre")
    res = sonde_circuit.verifier_robinets(s)
    row = s.execute(text(
        "SELECT statut, solde_le FROM circuit_ecarts WHERE chiffre_id = 'n_sources' "
        "AND cle = 'global'")).mappings().first()
    assert row["statut"] == "solde" and row["solde_le"] is not None
    assert res["soldes"] >= 1


def test_42_eau_ancienne_solaire_etiquete_jamais_ouvert(db_session):
    s = db_session
    sonde_circuit.ensure(s)
    eau = sonde_circuit.verifier_eau_ancienne(s)
    sol = s.execute(text(
        "SELECT statut FROM circuit_eau_ancienne WHERE chiffre_id = 'prod_spec_kwh_kwc' "
        "ORDER BY id DESC LIMIT 1")).scalar()
    assert sol == "etiquete", "le gel solaire est ASSUMÉ (jamais une fuite ouverte)"
    assert eau["lignes"] >= 1


def test_43_controle_ecrit_le_verdict(db_session):
    s = db_session
    res = sonde_circuit.controle(s, declencheur="test")
    row = s.execute(text(
        "SELECT fuites_ouvertes, eau_ancienne, details FROM circuit_controles "
        "ORDER BY id DESC LIMIT 1")).mappings().first()
    assert row is not None
    assert row["details"]["declencheur"] == "test"
    assert res["duree_s"] >= 0
    assert "chiffres_multi_robinets" in res


def test_43_job_au_registre():
    from labuse.jobs import JOBS
    j = JOBS["coherence-robinets"]
    assert j.cadence == "quotidien" and j.heure_reunion == "07:25"
