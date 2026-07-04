"""Test d'intégration de la cascade sur le jeu de démo Saint-Paul (PostGIS réel).

Verrouille le comportement de bout en bout : verdicts, promotion phase 2,
double score, statut, et la traçabilité (cascade_results).
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from labuse import models
from labuse.cascade import evaluate_parcels
from labuse.enums import CascadeVerdict, EvaluationStatus, Severity
from labuse.ingestion import demo_saint_paul, seed_sources

pytestmark = pytest.mark.db


@pytest.fixture
def demo(db_session):
    seed_sources.seed(db_session)
    demo_saint_paul.seed_demo(db_session)
    ids = [r[0] for r in db_session.execute(select(models.Parcel.id)).all()]
    outcomes = evaluate_parcels(ids, db_session, persist=True)
    return {int(o.idu[-4:]): o for o in outcomes}


def _verdict(outcome, layer, result=None):
    for v in outcome.verdicts:
        if v.layer_name == layer and (result is None or v.result == result):
            return v
    return None


def test_statuts_attendus(demo):
    expected = {
        1: EvaluationStatus.OPPORTUNITE,
        2: EvaluationStatus.FAUX_POSITIF_PROBABLE,  # zone Ab agricole → HARD_EXCLUDE (non constructible au PLU)
        3: EvaluationStatus.EXCLUE,
        4: EvaluationStatus.FAUX_POSITIF_PROBABLE,
        5: EvaluationStatus.EXCLUE,
        6: EvaluationStatus.FAUX_POSITIF_PROBABLE,
        7: EvaluationStatus.A_CREUSER,
        8: EvaluationStatus.A_CREUSER,
    }
    for num, status in expected.items():
        assert demo[num].status == status.value, f"P{num} attendu {status}"


def test_double_score_toujours_present(demo):
    """Règle d'or : opportunité jamais seule — les deux scores sont bornés 0–100."""
    for o in demo.values():
        assert 0 <= o.opportunity.score <= 100
        assert 0 <= o.completeness.score <= 100


def test_opportunite_p1_signaux_positifs(demo):
    o = demo[1]
    assert o.promoted and o.opportunity.score >= 65 and o.completeness.score >= 80
    assert _verdict(o, "potentiel_foncier_region", CascadeVerdict.POSITIVE)
    assert _verdict(o, "proprietaire", CascadeVerdict.POSITIVE)  # personne morale
    sit = _verdict(o, "sitadel", CascadeVerdict.POSITIVE)
    assert sit and "RATTACHÉ" in sit.detail.upper()  # apparié par IDU, pas signal de zone


def test_exclusions_sont_dures(demo):
    # PPR rouge → exclue (catégorie "exclue")
    he = _verdict(demo[3], "risques", CascadeVerdict.HARD_EXCLUDE)
    assert he and he.exclude_kind == "exclue" and "rouge" in he.detail.lower()
    # cœur Parc → exclue
    assert _verdict(demo[5], "parc_national", CascadeVerdict.HARD_EXCLUDE).exclude_kind == "exclue"
    # SAR : proxy INFORMATIF (Décision 2) — l'exclusion de P4 est portée par le zonage N,
    # plus jamais par le SAR (cf. test_zonage_agricole_naturel_hard_exclude).
    sar4 = _verdict(demo[4], "sar")
    assert sar4 is not None and sar4.result == CascadeVerdict.PASS
    assert _verdict(demo[4], "zonage_plu_gpu", CascadeVerdict.HARD_EXCLUDE).exclude_kind == "faux_positif"
    # cimetière OSM → faux positif
    assert _verdict(demo[6], "osm_faux_positif", CascadeVerdict.HARD_EXCLUDE).exclude_kind == "faux_positif"
    for num in (3, 4, 5, 6):
        assert demo[num].opportunity.score == 0


def test_promotion_phase2_ne_tourne_pas_sur_exclues(demo):
    """Une parcelle HARD_EXCLUDE ne doit PAS déclencher la phase 2 (coûteuse)."""
    excluded = demo[3]
    assert not excluded.promoted
    assert _verdict(excluded, "dvf") is None
    assert _verdict(excluded, "sitadel") is None
    promoted = demo[1]
    assert promoted.promoted and _verdict(promoted, "dvf") is not None


def test_indivision_flag_fort(demo):
    flag = _verdict(demo[7], "proprietaire", CascadeVerdict.SOFT_FLAG)
    assert flag and flag.severity == Severity.FORT and "indivision" in flag.detail.lower()


def test_sar_proxy_informatif_jamais_bloquant(demo):
    """Décision 2 : le proxy SAR (espace agricole) n'émet plus AUCUN flag — PASS informatif,
    et aucun verdict SAR d'aucune parcelle n'est excluant ni pénalisant."""
    v = _verdict(demo[2], "sar")
    assert v is not None and v.result == CascadeVerdict.PASS and "proxy" in v.detail.lower()
    for o in demo.values():
        for s in (x for x in o.verdicts if x.layer_name == "sar"):
            assert s.result not in (CascadeVerdict.HARD_EXCLUDE, CascadeVerdict.SOFT_FLAG)


def test_zonage_agricole_naturel_hard_exclude(demo):
    """Décision 1 : zones A/N → HARD_EXCLUDE sensible au recouvrement (ici 100 % ≥ seuil 90 %),
    motif « Zone {libelle} PLU — inconstructible (recouvrement {pct} %) ».
    U/AU restent constructibles (testés avant A/N)."""
    for num, lib in ((2, "Ab"), (4, "N")):
        he = _verdict(demo[num], "zonage_plu_gpu", CascadeVerdict.HARD_EXCLUDE)
        assert he and he.exclude_kind == "faux_positif"
        assert f"Zone {lib} PLU — inconstructible (recouvrement" in he.detail
    assert _verdict(demo[1], "zonage_plu_gpu", CascadeVerdict.POSITIVE)  # U reste constructible


def test_surface_calculee_non_excluante(demo):
    """Surface (~2000 m²) : bonus GRADUÉ via courbe saturante, jamais éliminatoire."""
    v = _verdict(demo[1], "surface")
    # Valorisée (POSITIVE) et non plus un simple PASS, mais ne pénalise/exclut jamais.
    assert v.result == CascadeVerdict.POSITIVE
    assert v.result not in (CascadeVerdict.HARD_EXCLUDE, CascadeVerdict.SOFT_FLAG)
    assert v.bonus_key == "surface_utile"
    # magnitude ∈ ]0,1] : ~0.76 pour 2000 m² (lo=400, hi=2500) → la surface joue, bornée.
    assert v.magnitude == pytest.approx((2000 - 400) / (2500 - 400), abs=0.03)


def test_invariant_survivant_aucun_hard_exclude_en_aval(demo):
    """LIVRABLE 2 (refonte étage 0) : seul l'étage 0 (cascade phase 1) élimine. Une parcelle
    PROMUE — qui a passé l'étage 0 — ne porte AUCUN HARD_EXCLUDE dans ses verdicts finaux
    (ni couche phase 2, ni déclassement, désormais fusionné en phase 1)."""
    for o in demo.values():
        if o.promoted:
            assert not any(v.result == CascadeVerdict.HARD_EXCLUDE for v in o.verdicts), \
                f"{o.idu} promue mais porte un HARD_EXCLUDE en aval — l'étage 0 doit être seul juge"


def test_eliminee_na_pas_de_score_fantome(demo):
    """Corollaire : une parcelle éliminée (non promue) a un score brut d'opportunité = 0 —
    plus jamais l'absurdité « 78/100 — faux positif probable » que la fusion corrige."""
    for o in demo.values():
        if not o.promoted:
            assert o.opportunity.score == 0, f"{o.idu} éliminée mais score {o.opportunity.score}"


def test_persistance_cascade_et_evaluation(db_session, demo):
    pid = db_session.execute(select(models.Parcel.id).limit(1)).scalar_one()
    n_cascade = db_session.execute(
        text("SELECT count(*) FROM cascade_results WHERE parcel_id = :p"), {"p": pid}
    ).scalar()
    n_eval = db_session.execute(
        text("SELECT count(*) FROM parcel_evaluations WHERE parcel_id = :p"), {"p": pid}
    ).scalar()
    assert n_cascade > 0 and n_eval == 1
