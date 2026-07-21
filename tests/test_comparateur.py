"""O6 — COMPARATEUR DE COMMUNES : normalisation directionnelle + composite à poids renormalisés.

Un axe manquant reste null (jamais 0 trompeur) et son poids est retiré du composite. Le composite est
une commodité, pas un score calibré — pondération réglable et documentée.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import comparateur as c


DEF = {"stock": 0.30, "velocite": 0.15, "permis": 0.15, "deficit_sru": 0.15,
       "pression_zan": 0.10, "prix_neuf": 0.15}


def _row(**kw):
    base = {k: None for k in c.INDICATEURS}
    base.update(kw)
    return base


# ───────────────────────── normalisation (pur) ─────────────────────────

def test_direction_stock_haut_mieux():
    rows = c._normalize([_row(stock=10), _row(stock=0)], DEF)
    hi = next(r for r in rows if r["stock"] == 10)
    lo = next(r for r in rows if r["stock"] == 0)
    assert hi["normalise"]["stock"] == 100.0 and lo["normalise"]["stock"] == 0.0


def test_direction_velocite_bas_mieux():
    # délai plus court (bas) → mieux → normalisé plus haut
    rows = c._normalize([_row(velocite=6), _row(velocite=18)], DEF)
    court = next(r for r in rows if r["velocite"] == 6)
    long = next(r for r in rows if r["velocite"] == 18)
    assert court["normalise"]["velocite"] == 100.0 and long["normalise"]["velocite"] == 0.0


def test_axe_manquant_reste_null_et_renormalise():
    # une commune sans prix_neuf : l'axe est null, son poids est retiré du composite
    rows = c._normalize([_row(stock=10, prix_neuf=None), _row(stock=0, prix_neuf=3000)], DEF)
    sans = next(r for r in rows if r["prix_neuf"] is None)
    assert sans["normalise"]["prix_neuf"] is None
    assert sans["score_composite"] is not None      # composite calculé sur les axes présents


def test_composite_classe_rang():
    rows = c._normalize([_row(stock=0), _row(stock=100)], DEF)
    assert rows[0]["rang"] == 1 and rows[0]["stock"] == 100   # meilleur stock → rang 1


def test_borne_degeneree_neutre():
    # tous égaux sur un axe → normalisé neutre 50 (pas de division par zéro)
    rows = c._normalize([_row(stock=5), _row(stock=5)], DEF)
    assert all(r["normalise"]["stock"] == 50.0 for r in rows)


# ───────────────────────── flux DB ─────────────────────────

@pytest.mark.db
def test_compute_24_communes_et_composite(db_session):
    s = db_session
    # le comparateur lit des tables réelles ; s'il n'y a pas de communes en base de test, on skip proprement
    n = s.execute(text("SELECT count(DISTINCT left(idu,5)) FROM parcels")).scalar()
    if not n:
        pytest.skip("pas de parcelles en base de test")
    out = c._compute(s, DEF)
    assert "communes" in out and "indicateurs" in out
    assert out["indicateurs"]["stock"]["direction"] == "haut = mieux"
    assert out["indicateurs"]["velocite"]["direction"] == "bas = mieux"
    assert "COMMODITÉ" in out["methode"]
