"""RETOURS-12 O8 — « Communes » : le SRU (et les indicateurs partagés) concordent tableau ↔ fiche.

La fiche commune était servie d'un cache nocturne qui FIGEAIT les indicateurs partagés avec le
tableau des 24 communes (permis, prix neuf, SRU) → deux chiffres divergents. `_rafraichir_partages`
resert ces indicateurs LIVE (même moteur). On teste ici la réconciliation SRU, qui portait deux
pièges : (a) join par NOM sensible à la casse (« La Plaine-Des-Palmistes » vs « …-des-… »), (b)
arrondi du déficit divergent (5,35 → 5,3 côté tableau, 5,4 si recalculé en float au front).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api.app import _rafraichir_partages

pytestmark = pytest.mark.db


def _pose_sru(db, insee, commune, taux, obj):
    db.execute(text("DELETE FROM commune_contexte_sru WHERE insee = :i"), {"i": insee})
    db.execute(text(
        "INSERT INTO commune_contexte_sru (insee, commune, taux_lls, objectif_pct, statut) "
        "VALUES (:i, :c, :t, :o, 'deficitaire')"),
        {"i": insee, "c": commune, "t": taux, "o": obj})


def test_sru_deficit_meme_arithmetique_que_le_tableau(db_session):
    # Saint-Louis réel : 25 − 19,65 = 5,35 → le tableau sert 5,3 (round(float(...),1)), pas 5,4.
    _pose_sru(db_session, "97414", "Saint-Louis", 19.65, 25)
    out = _rafraichir_partages(db_session, "Saint-Louis", {"insee": "97414"})
    assert out["sru"]["deficit"] == 5.3          # jamais 5,4 (le recalcul float au front donnait 5,4)
    assert float(out["sru"]["taux_lls"]) == 19.65


def test_sru_join_insensible_a_la_casse(db_session):
    # bug La Plaine-des-Palmistes : nom en base SRU (« -Des- ») ≠ nom parcels (« -des- ») → fiche
    # perdait le SRU. Le repli par nom est désormais insensible à la casse (et l'INSEE prime).
    _pose_sru(db_session, "97406", "La Plaine-Des-Palmistes", 16.82, 20)
    # payload SANS insee → force le repli par nom, avec une casse différente
    out = _rafraichir_partages(db_session, "la plaine-des-palmistes", {})
    assert out["sru"] is not None
    assert float(out["sru"]["taux_lls"]) == 16.82
    assert out["sru"]["deficit"] == 3.2          # round(float(20-16.82),1)


def test_sru_absent_reste_none_jamais_un_faux_zero(db_session):
    db_session.execute(text("DELETE FROM commune_contexte_sru WHERE insee = :i"), {"i": "97499"})
    out = _rafraichir_partages(db_session, "Commune Sans SRU", {"insee": "97499"})
    assert out.get("sru") is None
