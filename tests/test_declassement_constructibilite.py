"""Déclassement en étage 0 — trois étiquettes distinctes (A zone fermée / B parcelle
inconstructible / C non vérifiable), JAMAIS confondues, et GARDE-FOU anti-21 077.

Le garde-fou (`test_ne_declasse_pas_name_descriptif`) est écrit AVANT le correctif (arbitrage
Vic 29/07) : il DOIT échouer si un jour la détection déclasse des parcelles à `name` descriptif
(subtype U réel). La détection ne lit QUE le verdict moteur, jamais `resolve_zone(name)`.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.faisabilite.engine import Faisabilite
from labuse.faisabilite.db import parcel_faisabilite
from labuse.faisabilite.constructibilite import (
    classify_constructibilite, DECLASSE_ZONE_FERMEE, DECLASSE_NON_CONSTRUCTIBLE,
    NON_VERIFIABLE,
)


def _faisa(constructible, cause=None, zone="Uc", verdict=""):
    return Faisabilite(zone=zone, zone_resolue=None, constructible=constructible,
                       verdict=verdict, steps=[], hypotheses=[], avertissements=[],
                       modulation=[], fourchette={}, bandeau="", calibree=True, cause=cause)


# ─────────────────────────── unités (sans DB) ───────────────────────────

def test_constructible_pas_de_declassement():
    assert classify_constructibilite(_faisa(True))[0] is None


def test_ne_declasse_pas_name_descriptif_unit():
    """GARDE-FOU 21 077 (unité) : une parcelle CONSTRUCTIBLE au moteur ne se déclasse jamais,
    même si son libellé de zone est une DESCRIPTION (que `resolve_zone(name)` dirait non
    constructible). La détection lit `constructible`, pas le name."""
    f = _faisa(True, cause=None, zone="Bourg de proximité de Rivière du Mât à l'habitat isolé")
    assert classify_constructibilite(f)[0] is None


def test_cause_A_zone_fermee():
    for cause in ("zone_transition", "habitat_interdit"):
        label, motif = classify_constructibilite(_faisa(False, cause=cause, zone="2AUd"))
        assert label == DECLASSE_ZONE_FERMEE
        assert "Zone fermée à l'urbanisation" in motif and "2AUd" in motif


def test_cause_B_parcelle_inconstructible():
    for cause in ("terrain_exigu", "redhibitoire", "hauteur_indispo"):
        label, motif = classify_constructibilite(_faisa(False, cause=cause))
        assert label == DECLASSE_NON_CONSTRUCTIBLE
        assert "surface ou reculs" in motif


def test_A_et_B_jamais_confondues():
    a = classify_constructibilite(_faisa(False, cause="habitat_interdit"))[0]
    b = classify_constructibilite(_faisa(False, cause="terrain_exigu"))[0]
    assert a != b


def test_hors_plu_non_verifiable():
    label, motif = classify_constructibilite(None)
    assert label == NON_VERIFIABLE and "non calibré" in motif


# ─────────────────────────── intégration (DB) ───────────────────────────

pytestmark_db = pytest.mark.db


@pytest.mark.db
def test_ne_declasse_pas_name_descriptif(db_session):
    """GARDE-FOU 21 077 (intégration) : 97402000AB0941 (Bras-Panon) est dans un polygone PLU
    dont le `name` est une DESCRIPTION — `resolve_zone(name).constructible_neuf` = False (un
    détecteur naïf la déclasserait, catastrophe des 21 077). Le moteur, via subtype/libellé, la
    dit CONSTRUCTIBLE → elle NE doit PAS être déclassée."""
    pid = db_session.execute(text("SELECT id FROM parcels WHERE idu='97402000AB0941'")).scalar()
    if pid is None:
        pytest.skip("parcelle de référence absente de la base")
    res = parcel_faisabilite(db_session, pid)
    assert res is not None
    _ctx, f = res
    assert f.constructible is True                     # moteur robuste au name descriptif
    assert classify_constructibilite(f)[0] is None     # → PAS déclassée (21 077 protégées)


@pytest.mark.db
def test_zone_fermee_reelle_declasse_A(db_session):
    pid = db_session.execute(text("SELECT id FROM parcels WHERE idu='97422000AD1237'")).scalar()
    if pid is None:
        pytest.skip("golden absente")
    _ctx, f = parcel_faisabilite(db_session, pid)
    assert f.constructible is False and f.cause in ("zone_transition", "habitat_interdit")
    assert classify_constructibilite(f)[0] == DECLASSE_ZONE_FERMEE


@pytest.mark.db
def test_terrain_exigu_reel_declasse_B(db_session):
    pid = db_session.execute(text("SELECT id FROM parcels WHERE idu='97402000AB0848'")).scalar()
    if pid is None:
        pytest.skip("parcelle absente")
    _ctx, f = parcel_faisabilite(db_session, pid)
    assert f.constructible is False
    assert classify_constructibilite(f)[0] == DECLASSE_NON_CONSTRUCTIBLE


@pytest.mark.db
def test_commune_non_outillee_non_verifiable(db_session):
    """Saint-André : PLU non calibré → parcel_faisabilite None → non vérifiable (signalé)."""
    pid = db_session.execute(text("SELECT id FROM parcels WHERE idu='97409000AV0985'")).scalar()
    if pid is None:
        pytest.skip("parcelle absente")
    res = parcel_faisabilite(db_session, pid)
    assert res is None
    assert classify_constructibilite(None)[0] == NON_VERIFIABLE
