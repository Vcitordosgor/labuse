"""CALCULS-FIX-1 Lot A — la zone dominante / `a_cheval` se décident sur le TYPE de zone.

Le mandat proposait de grouper `zone_dominante` par (commune, token) ; la mesure île l'a
INFIRMÉ (ne produisait que des faux positifs « à cheval » sur des parcelles d'un seul type de
zone réparties sur deux communes). Fix retenu : la sonde `_N_ZONES` clée sur (token, famille),
la MÊME clé que `_PARTS` — `a_cheval` reste type-based, jamais commune-based.

Deux gardes :
  1. statique — la sonde `_N_ZONES` compte bien par (token, famille), pas par token seul
     (une régression vers `count(DISTINCT token)` casse ce test) ;
  2. sur donnée réelle (si présente) — une parcelle d'un seul type à cheval sur deux communes
     n'est PAS « à cheval ».
"""
from __future__ import annotations

import pytest
from sqlalchemy import text


def test_sonde_n_zones_clee_sur_token_et_famille():
    """Garde statique : la sonde compte les zones distinctes par (token, famille)."""
    from labuse.faisabilite import zone_servie
    sql = str(zone_servie._N_ZONES)
    assert "count(DISTINCT (" in sql and "labuse_zone_famille" in sql, \
        "la sonde _N_ZONES doit compter par (token, famille), pas par token seul"


def test_parcelle_un_seul_type_a_cheval_deux_communes_pas_a_cheval():
    """97420000AB0002 = 100 % N réparti sur deux communes → « N » résume la parcelle → NON
    « à cheval ». Le fix littéral (commune, token) l'aurait basculée à cheval à tort."""
    try:
        from labuse.db import session_scope
    except Exception:  # pragma: no cover
        pytest.skip("db indisponible")
    from labuse.faisabilite.zone_servie import zone_dominante
    with session_scope() as s:
        try:
            pid = s.execute(text("SELECT id FROM parcels WHERE idu = :i"),
                            {"i": "97420000AB0002"}).scalar()
        except Exception:  # pragma: no cover — table absente en base de test
            pytest.skip("parcels absente de la base de test")
        if not pid:
            pytest.skip("témoin 97420000AB0002 hors base (dit, pas cassé)")
        zs = zone_dominante(s, pid)
        assert zs.zone_fam == "N", f"famille attendue N, servie {zs.zone_fam}"
        assert zs.a_cheval is False, "une parcelle 100 % N ne doit pas être « à cheval »"
