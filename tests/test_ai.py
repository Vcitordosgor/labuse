"""Tests de l'agent IA : stub déterministe valide, schéma strict, persistance."""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from labuse.ai import StubProvider, validate_ai_output
from labuse.ai.schema import AI_OUTPUT_SCHEMA  # noqa: F401

SAMPLE_PAYLOAD = {
    "parcel": {"idu": "97411000AB0001", "commune": "Saint-Paul", "surface_m2": 2000},
    "computed_scores": {"completeness": 92, "completeness_band": "forte", "opportunity": 70, "cascade_status": "opportunite"},
    "cascade_verdicts": [
        {"layer": "zonage_plu_gpu", "result": "POSITIVE", "severity": None, "detail": "Zone U constructible", "source": "Urbanisme PLU/GPU (API Carto)"},
        {"layer": "sar", "result": "SOFT_FLAG", "severity": "fort", "detail": "SAR espace agricole (SAFER ; supérieur au PLU)", "source": "SAR Réunion (PEIGEO)"},
        {"layer": "risques", "result": "PASS", "severity": None, "detail": "Aucun risque", "source": "Géorisques"},
        {"layer": "safer", "result": "PASS", "severity": None, "detail": "Hors zonage SAFER.", "source": "Zonage SAFER (DAAF)"},
        {"layer": "parc_national", "result": "PASS", "severity": None, "detail": "Hors Parc National.", "source": "Parc National de La Réunion (INPN)"},
    ],
    "sources_responded": ["Urbanisme PLU/GPU (API Carto)", "Géorisques"],
    "missing_data_families": ["proprietaire"],
}


def test_stub_est_valide_et_ne_corrige_pas():
    out = StubProvider().analyze(SAMPLE_PAYLOAD)
    assert validate_ai_output(out) == []
    assert out["recommended_status"] == "opportunite"
    assert out["opportunity_score_adjustment"] == 0
    assert out["confidence_level"] == "eleve"
    # cite les sources et reprend les signaux sans inventer
    assert any(s["source"] == "SAR Réunion (PEIGEO)" for s in out["blocking_or_risk_signals"])
    assert "SAR juridiquement supérieur au PLU." in out["reunion_specific_flags"]
    # PASS « Hors Parc National » NE DOIT PAS produire de faux flag (anti-hallucination).
    # (Le flag SAFER, lui, vient légitimement du SOFT_FLAG SAR agricole.)
    assert not any("Parc National" in f for f in out["reunion_specific_flags"])
    # famille manquante → vérif Fichiers fonciers
    assert any("Fichiers fonciers" in c for c in out["must_check_before_showing_developer"])


def test_schema_rejette_les_sorties_invalides():
    bad = StubProvider().analyze(SAMPLE_PAYLOAD)
    bad["opportunity_score_adjustment"] = 50  # hors [-20, 20]
    assert validate_ai_output(bad)
    bad2 = StubProvider().analyze(SAMPLE_PAYLOAD)
    bad2["recommended_status"] = "peut-etre"  # hors énumération
    assert validate_ai_output(bad2)


@pytest.mark.db
def test_evaluate_avec_ia_stocke_ai_payload(db_session):
    from labuse import models
    from labuse.cascade import evaluate_parcels
    from labuse.ingestion import demo_saint_paul, seed_sources

    seed_sources.seed(db_session)
    demo_saint_paul.seed_demo(db_session)
    ids = [r[0] for r in db_session.execute(select(models.Parcel.id)).all()]
    outcomes = evaluate_parcels(ids, db_session, persist=True, ai_provider=StubProvider())

    assert outcomes
    n_with_payload = db_session.execute(
        text("SELECT count(*) FROM parcel_evaluations WHERE ai_payload IS NOT NULL AND model_version = 'stub'")
    ).scalar()
    assert n_with_payload == len(ids)
