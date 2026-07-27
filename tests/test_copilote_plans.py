"""M26-A — planificateur : plans FIGÉS au snapshot (tout écart = décision consciente)."""
from __future__ import annotations

import pytest

from labuse.copilote import plans


def test_plan_instruire_snapshot():
    assert plans.plan_serialise("instruire") == [
        {"moteur": "criblage", "bloquant": True},
        {"moteur": "faisabilite", "bloquant": True},
        {"moteur": "risques", "bloquant": True},
        {"moteur": "marche_dvf", "bloquant": False},
        {"moteur": "mutation", "bloquant": False},
        {"moteur": "assemblage", "bloquant": True},
    ]


def test_plan_shortlist_snapshot():
    assert plans.plan_serialise("shortlist") == [
        {"moteur": "criblage", "bloquant": True},
        {"moteur": "faisabilite", "bloquant": True},
        {"moteur": "risques", "bloquant": True},
        {"moteur": "mutation", "bloquant": False},
        {"moteur": "assemblage_court", "bloquant": True},
    ]


def test_plan_verifier_snapshot():
    assert plans.plan_serialise("verifier_adresse") == [
        {"moteur": "scoreur_unitaire", "bloquant": True},
        {"moteur": "assemblage_verdict", "bloquant": True},
    ]


def test_mission_inconnue_refusee():
    with pytest.raises(ValueError, match="mission inconnue"):
        plans.plan_pour("conquete_du_monde")


def test_tous_les_moteurs_des_plans_existent():
    from labuse.copilote.moteurs import MOTEURS
    for mission in plans.PLANS:
        for etape in plans.plan_pour(mission):
            assert etape.moteur in MOTEURS, f"{mission}: moteur {etape.moteur} sans wrapper"


def test_mutation_v1_jamais_dans_un_wrapper():
    # Décision Vic (GO M26-A Q1) : le Radar Mutation V1 (NON SERVI, RR 0,51) ne doit
    # jamais être appelé par le Copilote — l'étape mutation lit le champion P.
    import inspect

    from labuse.copilote import moteurs
    src = inspect.getsource(moteurs)
    assert "compute_mutation_score" not in src
    assert "mutation_for_parcels" not in src
